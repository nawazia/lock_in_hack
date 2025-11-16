"""Hotel Agent - Searches for and processes hotel options."""

import logging
import json
import os
from typing import List, Optional
from datetime import datetime, timedelta
from langsmith import traceable
from langchain_core.prompts import ChatPromptTemplate

from config.llm_setup import get_llm
from config.hallbayes_validator import EDFLValidator
from models.travel_schemas import TravelPlanningState, Hotel
from models.observability_schemas import EvidenceData, ExtractionData, HallucinationMetrics
from tools.travel_tools import search_hotels

logger = logging.getLogger(__name__)


class HotelAgent:
    """Agent responsible for finding and processing hotel options."""

    def __init__(self, llm=None, enable_edfl_validation=None):
        """Initialize the hotel agent.

        Args:
            llm: Language model to use. If None, uses default from config.
            enable_edfl_validation: Enable EDFL validation. If None, reads from env ENABLE_EDFL_VALIDATION.
        """
        self.llm = llm or get_llm()
        self.search_tool = search_hotels

        # Initialize EDFL validator
        if enable_edfl_validation is None:
            enable_edfl_validation = os.getenv("ENABLE_EDFL_VALIDATION", "true").lower() == "true"

        try:
            self.edfl_validator = EDFLValidator(
                self.llm,
                h_star=0.05,  # Target 5% hallucination rate
                enable_validation=enable_edfl_validation
            )
        except Exception as e:
            logger.warning(f"Failed to initialize EDFL validator: {e}")
            self.edfl_validator = None

    @traceable(name="search_and_parse_hotels")
    def search_and_parse_hotels(
        self,
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 1,
        preferences: str = "",
        collector: Optional[any] = None
    ) -> List[Hotel]:
        """Search for hotels and parse results into Hotel objects.

        Args:
            location: City or area
            check_in: Check-in date (YYYY-MM-DD)
            check_out: Check-out date (YYYY-MM-DD)
            guests: Number of guests
            preferences: Hotel preferences

        Returns:
            List of Hotel objects
        """
        try:
            logger.info(f"Searching hotels in {location}: {check_in} to {check_out}")

            # Use the search tool to get Google Hotels results via SerpApi
            search_results_json = self.search_tool.invoke({
                "location": location,
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests
            })

            # Parse JSON response
            search_results = json.loads(search_results_json)

            if "error" in search_results:
                logger.error(f"Hotel search error: {search_results['error']}")
                return []

            # Extract search results
            raw_results = search_results.get("search_results", [])

            if not raw_results:
                logger.warning("No hotel search results found")
                return []

            # Use LLM to parse the search results into structured Hotel objects
            hotels = self._parse_with_llm(raw_results, location, preferences, collector=collector)

            logger.info(f"Found and parsed {len(hotels)} hotel options")
            return hotels

        except Exception as e:
            logger.error(f"Error searching/parsing hotels: {e}")
            return []

    def _parse_with_llm(
        self,
        search_results: List[dict],
        location: str,
        preferences: str = "",
        collector: Optional[any] = None
    ) -> List[Hotel]:
        """Use LLM to parse Valyu search results into Hotel objects.

        Args:
            search_results: Raw search results from Valyu
            location: Location/city
            preferences: User preferences

        Returns:
            List of Hotel objects
        """
        try:
            # Create prompt for LLM to extract hotel information
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a travel data extraction assistant. Extract hotel information from search results.

For each hotel mentioned in search results, extract:
- name: Hotel name (REQUIRED)
- location: City/area (e.g., "Paris, France" - be specific about country) (REQUIRED)
- address: Street address if mentioned, otherwise use empty string ""
- star_rating: Star rating (1-5, can be decimal, MUST NOT exceed 5.0), use 3.0 if unknown
- price_per_night: Price per night in USD (REQUIRED - must be a number). If range given, use average. If not stated, estimate typical price for the area.
- amenities: List of amenities if mentioned (e.g., ["WiFi", "Pool", "Gym"]), use empty list [] if none mentioned
- distance_to_center: Distance to city center if mentioned (e.g., "1.5 km"), otherwise null
- rating: User rating out of 5 (MUST NOT exceed 5.0, can be decimal), use 4.0 if unknown
- booking_url: URL from search result (REQUIRED - include any booking site URL, even lesser-known ones)

IMPORTANT: price_per_night, name, and booking_url are REQUIRED. Do not set them to null or omit them.

User preferences: {preferences}

ACCEPT any legitimate hotel booking website including:
- Major sites: Booking.com, Expedia, Hotels.com, Agoda, Trivago
- Hotel chain sites: Marriott.com, Hilton.com, IHG.com, etc.
- Lesser-known/regional booking sites
- Travel aggregators and comparison sites

ONLY SKIP:
- Pure blog posts with no hotel pricing (e.g., "Best Hotels in Paris - A Guide")
- News articles about hotels
- Generic travel guides without actual hotel information

If a result mentions BOTH travel advice AND actual hotel prices/names, INCLUDE IT and extract the hotel data.
If user mentioned "Paris" assume "Paris, France" unless clearly stated otherwise.
Prioritize hotels matching user preferences if provided.

Return ONLY valid JSON array, no additional text or explanation."""),
                ("user", """Search results:
{search_results}

Location: {location}

Extract hotel information as JSON array.""")
            ])

            # Format search results for LLM
            formatted_results = "\n\n".join([
                f"Result {i+1}:\nTitle: {r.get('source_title', '')}\nURL: {r.get('source_url', '')}\nContent: {r.get('content_snippet', '')}"
                for i, r in enumerate(search_results[:10])  # Parse more results (top 10)
            ])

            formatted_prompt = prompt.format_messages(
                search_results=formatted_results,
                location=location,
                preferences=preferences or "No specific preferences"
            )

            # Get LLM response - handle both chat and base LLMs
            from langchain_core.language_models import BaseChatModel
            if isinstance(self.llm, BaseChatModel):
                response = self.llm.invoke(formatted_prompt)
            else:
                # Convert messages to string for base LLM
                prompt_string = "\n\n".join([msg.content for msg in formatted_prompt])
                response = self.llm.invoke(prompt_string)

            # Extract content
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)

            # Parse JSON
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            # Try to extract JSON array from response
            # Find the first '[' and last ']'
            try:
                start_idx = content.find('[')
                end_idx = content.rfind(']')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx+1]
                    hotels_data = json.loads(json_content)
                else:
                    raise ValueError("No JSON array found in response")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Response was: {content[:300]}...")
                return []

            # Create Hotel objects
            hotels = []
            for hotel_data in hotels_data:
                try:
                    # Ensure required fields have defaults
                    if not hotel_data.get('price_per_night'):
                        logger.warning(f"Hotel {hotel_data.get('name', 'Unknown')} missing price, skipping")
                        continue

                    # Ensure amenities is a list
                    if hotel_data.get('amenities') is None:
                        hotel_data['amenities'] = []

                    hotel = Hotel(**hotel_data)
                    hotels.append(hotel)
                except Exception as e:
                    logger.warning(f"Could not create Hotel object: {e}")
                    logger.debug(f"Hotel data was: {hotel_data}")
                    continue

            # Validate extracted hotels with EDFL
            edfl_metrics = None
            if self.edfl_validator and hotels:
                try:
                    should_use, risk_bound, rationale, valid_count = self.edfl_validator.validate_extraction_batch(
                        task_description="Extract hotel information from search results. Verify all prices, names, ratings, and locations are accurately extracted.",
                        evidence=formatted_results,
                        extracted_items=hotels,
                        item_type="hotels"
                    )

                    # Store EDFL metrics
                    edfl_metrics = {
                        "edfl_decision": "PASS" if should_use else "FAIL",
                        "edfl_risk_bound": risk_bound,
                        "edfl_valid_count": valid_count,
                        "edfl_total_count": len(hotels),
                        "edfl_rationale": rationale[:200]
                    }

                    # Add EDFL metadata to each hotel
                    for hotel in hotels:
                        hotel.edfl_validation = {
                            "risk_of_hallucination": risk_bound,
                            "validation_passed": should_use,
                            "confidence": "high" if risk_bound < 0.05 else ("medium" if risk_bound < 0.5 else "low")
                        }

                    if not should_use:
                        logger.warning(f"EDFL validation FLAGGED hotels (RoH={risk_bound:.3f}) - returning anyway")
                        logger.warning(f"Rationale: {rationale}")
                        # Note: We flag but don't block - EDFL is for monitoring/confidence, not hard rejection
                    else:
                        logger.info(f"EDFL validation PASSED for {valid_count} hotels (RoH={risk_bound:.3f})")

                except Exception as e:
                    logger.error(f"EDFL validation error (continuing anyway): {e}")
                    edfl_metrics = {
                        "edfl_decision": "ERROR",
                        "edfl_error": str(e)
                    }

            # Store EDFL metrics
            if edfl_metrics:
                self._last_edfl_metrics = edfl_metrics

            # Record observability data if collector is provided
            if collector:
                try:
                    # Build EvidenceData
                    evidence_data = EvidenceData(
                        search_query=f"Hotels in {location}",
                        raw_results_count=len(search_results),
                        raw_results=search_results[:10],  # Include top 10
                        formatted_evidence=formatted_results,
                        evidence_length=len(formatted_results)
                    )

                    # Build ExtractionData
                    extraction_data = ExtractionData(
                        extracted_items=[h.model_dump() for h in hotels],
                        item_count=len(hotels),
                        extraction_prompt=str(formatted_prompt[0].content[:500]) if formatted_prompt else None,
                        llm_output_raw=content[:1000] if 'content' in locals() else None
                    )

                    # Build HallucinationMetrics if EDFL ran
                    hallucination_metrics = None
                    if edfl_metrics and edfl_metrics.get("edfl_decision") != "ERROR":
                        # Get detailed metrics from validator if available
                        detailed_metrics = getattr(self.edfl_validator, '_last_detailed_metrics', None)

                        if detailed_metrics:
                            hallucination_metrics = HallucinationMetrics(
                                validation_type="evidence_based",
                                edfl_decision=edfl_metrics["edfl_decision"],
                                risk_of_hallucination=edfl_metrics["edfl_risk_bound"],
                                confidence="high" if edfl_metrics["edfl_risk_bound"] < 0.05 else (
                                    "medium" if edfl_metrics["edfl_risk_bound"] < 0.5 else "low"
                                ),
                                delta_bar=detailed_metrics.get("delta_bar", 0.0),
                                isr=detailed_metrics.get("isr", 0.0),
                                b2t=detailed_metrics.get("b2t", 0.0),
                                p_answer=detailed_metrics.get("p_answer", 0.0),
                                q_avg=detailed_metrics.get("q_avg", 0.0),
                                q_lo=detailed_metrics.get("q_lo", 0.0),
                                n_samples=detailed_metrics.get("n_samples", 5),
                                m_skeletons=detailed_metrics.get("m_skeletons", 4),
                                rationale=edfl_metrics.get("edfl_rationale", "")
                            )

                    # Record the step
                    collector.record_step(
                        step_name="hotel_search",
                        step_type="extraction",
                        evidence=evidence_data,
                        extraction=extraction_data,
                        hallucination_metrics=hallucination_metrics,
                        status="success" if hotels else "warning",
                        metadata={
                            "location": location,
                            "preferences": preferences,
                            "hotels_extracted": len(hotels)
                        }
                    )
                    logger.info(f"Recorded observability data for hotel search: {len(hotels)} hotels")

                except Exception as e:
                    logger.warning(f"Failed to record observability data: {e}")

            return hotels

        except Exception as e:
            logger.error(f"Error parsing hotels with LLM: {e}")

            # Record error in observability if collector provided
            if collector:
                try:
                    collector.record_step(
                        step_name="hotel_search",
                        step_type="extraction",
                        status="failed",
                        error_message=str(e)
                    )
                except:
                    pass

            return []

    @traceable(name="hotel_agent_run")
    def run(self, state: TravelPlanningState) -> TravelPlanningState:
        """Run the hotel agent as part of the orchestrated workflow.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with hotel options
        """
        if not state.travel_intent:
            logger.warning("No travel intent available, skipping hotel search")
            state.completed_agents.append("hotel")
            return state

        intent = state.travel_intent
        all_hotels = []

        # Get observability collector from state metadata
        collector = state.metadata.get("observability_collector", None)

        # Parse timeframe to extract dates
        # Try to parse the timeframe intelligently
        timeframe_str = intent.timeframe or "December 2025"

        # Default dates
        check_in = "2025-12-20"
        check_out = "2025-12-27"

        try:
            # Try to extract YYYY-MM-DD pattern if present
            import re
            date_pattern = r'(\d{4})-(\d{2})-(\d{2})'
            match = re.search(date_pattern, timeframe_str)
            if match:
                check_in = match.group(0)
                check_out_date = datetime.strptime(check_in, "%Y-%m-%d") + timedelta(days=7)
                check_out = check_out_date.strftime("%Y-%m-%d")
            else:
                # Use defaults based on month mentioned
                if "december" in timeframe_str.lower() or "dec" in timeframe_str.lower():
                    check_in = "2025-12-20"
                    check_out = "2025-12-27"
                elif "january" in timeframe_str.lower() or "jan" in timeframe_str.lower():
                    check_in = "2026-01-15"
                    check_out = "2026-01-22"
                # Extract number of days/weeks if mentioned
                days_match = re.search(r'(\d+)\s*(day|week)', timeframe_str.lower())
                if days_match:
                    num = int(days_match.group(1))
                    unit = days_match.group(2)
                    nights = num if unit == "day" else num * 7
                    check_out_date = datetime.strptime(check_in, "%Y-%m-%d") + timedelta(days=nights)
                    check_out = check_out_date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Error parsing timeframe '{timeframe_str}': {e}. Using defaults.")
            check_in = "2025-12-20"
            check_out = "2025-12-27"

        # Search hotels for each destination
        for location in intent.locations:
            hotels = self.search_and_parse_hotels(
                location=location,
                check_in=check_in,
                check_out=check_out,
                guests=intent.travelers or 1,
                preferences=intent.accommodation_preferences or "",
                collector=collector
            )
            all_hotels.extend(hotels)

        state.hotels = all_hotels
        state.completed_agents.append("hotel")
        state.metadata["hotels_found"] = len(all_hotels)

        # Add EDFL validation metrics to state metadata
        if hasattr(self, '_last_edfl_metrics') and self._last_edfl_metrics:
            state.metadata["hotel_edfl_validation"] = self._last_edfl_metrics
            logger.info(f"Hotel agent completed. Found {len(all_hotels)} hotels. EDFL: {self._last_edfl_metrics.get('edfl_decision', 'N/A')} (RoH={self._last_edfl_metrics.get('edfl_risk_bound', 'N/A')})")
        else:
            logger.info(f"Hotel agent completed. Found {len(all_hotels)} hotels")

        return state

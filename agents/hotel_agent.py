"""Hotel Agent - Searches for and processes hotel options."""

import logging
import json
from typing import List
from datetime import datetime, timedelta
from langsmith import traceable
from langchain_core.prompts import ChatPromptTemplate

from config.llm_setup import get_llm
from models.travel_schemas import TravelPlanningState, Hotel
from tools.travel_tools import search_hotels

logger = logging.getLogger(__name__)


class HotelAgent:
    """Agent responsible for finding and processing hotel options."""

    def __init__(self, llm=None):
        """Initialize the hotel agent.

        Args:
            llm: Language model to use. If None, uses default from config.
        """
        self.llm = llm or get_llm()
        self.search_tool = search_hotels

    @traceable(name="search_and_parse_hotels")
    def search_and_parse_hotels(
        self,
        location: str,
        check_in: str,
        check_out: str,
        guests: int = 1,
        preferences: str = ""
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
            hotels = self._parse_with_llm(raw_results, location, preferences)

            logger.info(f"Found and parsed {len(hotels)} hotel options")
            return hotels

        except Exception as e:
            logger.error(f"Error searching/parsing hotels: {e}")
            return []

    def _parse_with_llm(
        self,
        search_results: List[dict],
        location: str,
        preferences: str = ""
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

            return hotels

        except Exception as e:
            logger.error(f"Error parsing hotels with LLM: {e}")
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
                preferences=intent.accommodation_preferences or ""
            )
            all_hotels.extend(hotels)

        state.hotels = all_hotels
        state.completed_agents.append("hotel")
        state.metadata["hotels_found"] = len(all_hotels)

        logger.info(f"Hotel agent completed. Found {len(all_hotels)} hotels")

        return state

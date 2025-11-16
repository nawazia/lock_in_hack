"""Flight Agent - Searches for and processes flight options."""

import logging
import json
from typing import List
from langsmith import traceable
from langchain_core.prompts import ChatPromptTemplate

from config.llm_setup import get_llm
from models.travel_schemas import TravelPlanningState, Flight
from tools.travel_tools import search_flights

logger = logging.getLogger(__name__)


class FlightAgent:
    """Agent responsible for finding and processing flight options."""

    def __init__(self, llm=None):
        """Initialize the flight agent.

        Args:
            llm: Language model to use. If None, uses default from config.
        """
        self.llm = llm or get_llm()
        self.search_tool = search_flights

    @traceable(name="search_and_parse_flights")
    def search_and_parse_flights(
        self,
        origin: str,
        destination: str,
        date: str,
        passengers: int = 1
    ) -> List[Flight]:
        """Search for flights and parse results into Flight objects.

        Args:
            origin: Origin airport code or city
            destination: Destination airport code or city
            date: Travel date (YYYY-MM-DD format)
            passengers: Number of passengers

        Returns:
            List of Flight objects
        """
        try:
            logger.info(f"Searching flights: {origin} -> {destination} on {date}")

            # Use the search tool to get Valyu results
            search_results_json = self.search_tool.invoke({
                "origin": origin,
                "destination": destination,
                "date": date,
                "passengers": passengers
            })

            # Parse JSON response
            search_results = json.loads(search_results_json)

            if "error" in search_results:
                logger.error(f"Flight search error: {search_results['error']}")
                return []

            # Extract search results
            raw_results = search_results.get("search_results", [])

            if not raw_results:
                logger.warning("No flight search results found")
                return []

            # Use LLM to parse the search results into structured Flight objects
            flights = self._parse_with_llm(raw_results, origin, destination, date)

            logger.info(f"Found and parsed {len(flights)} flight options")
            return flights

        except Exception as e:
            logger.error(f"Error searching/parsing flights: {e}")
            return []

    def _parse_with_llm(
        self,
        search_results: List[dict],
        origin: str,
        destination: str,
        date: str
    ) -> List[Flight]:
        """Use LLM to parse Valyu search results into Flight objects.

        Args:
            search_results: Raw search results from Valyu
            origin: Origin location
            destination: Destination location
            date: Travel date

        Returns:
            List of Flight objects
        """
        try:
            # Create prompt for LLM to extract flight information
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a travel data extraction assistant. Extract flight information from search results.

For each flight mentioned in search results, extract:
- airline: Airline name (e.g., "Air France", "Delta", "United")
- flight_number: Flight number if mentioned (e.g., "AF123"), or generate like "XX###"
- departure_airport: Departure airport code (e.g., "JFK", "LAX") or city
- arrival_airport: Arrival airport code (e.g., "CDG") or city
- departure_time: Departure time in ISO format (YYYY-MM-DDTHH:MM:SS), estimate if not exact
- arrival_time: Arrival time in ISO format, estimate based on typical flight duration
- duration: Flight duration (e.g., "7h 30m"), use typical duration if not stated
- price: Price in USD (as a number). Extract from text, use average if range given
- stops: Number of stops (0 for direct/non-stop)
- booking_url: URL from search result (REQUIRED - include any booking site URL, even lesser-known ones)

ACCEPT any legitimate flight booking website including:
- Major sites: Kayak, Expedia, Google Flights, Skyscanner, Momondo
- Airline sites: Delta.com, United.com, AirFrance.com, etc.
- Lesser-known/regional booking sites
- Hotel/travel aggregators that also sell flights

ONLY SKIP:
- Pure blog posts with no flight pricing (e.g., "10 Tips for Flying to Paris")
- News articles about travel
- Generic travel guides without actual flight information

If a result mentions BOTH travel advice AND actual flight prices/options, INCLUDE IT and extract the flight data.
Only return flights from {origin} to {destination}.

Return ONLY valid JSON array, no additional text or explanation."""),
                ("user", """Search results:
{search_results}

Origin: {origin}
Destination: {destination}
Date: {date}

Extract flight information as JSON array.""")
            ])

            # Format search results for LLM
            formatted_results = "\n\n".join([
                f"Result {i+1}:\nTitle: {r.get('source_title', '')}\nURL: {r.get('source_url', '')}\nContent: {r.get('content_snippet', '')}"
                for i, r in enumerate(search_results[:10])  # Parse more results (top 10)
            ])

            formatted_prompt = prompt.format_messages(
                search_results=formatted_results,
                origin=origin,
                destination=destination,
                date=date
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
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                # Remove ```json or ``` markers
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            # Try to extract JSON array from response
            # Find the first '[' and last ']'
            try:
                start_idx = content.find('[')
                end_idx = content.rfind(']')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx+1]
                    flights_data = json.loads(json_content)
                else:
                    raise ValueError("No JSON array found in response")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Response was: {content[:300]}...")
                return []

            # Ensure it's a list
            if not isinstance(flights_data, list):
                logger.error(f"LLM returned {type(flights_data)} instead of list")
                return []

            # Create Flight objects
            flights = []
            for flight_data in flights_data:
                try:
                    # Skip if missing required price field
                    if not flight_data.get('price'):
                        logger.warning(f"Flight missing price, skipping")
                        continue

                    flight = Flight(**flight_data)
                    flights.append(flight)
                except Exception as e:
                    logger.warning(f"Could not create Flight object: {e}")
                    continue

            return flights

        except Exception as e:
            logger.error(f"Error parsing flights with LLM: {e}")
            return []

    @traceable(name="flight_agent_run")
    def run(self, state: TravelPlanningState) -> TravelPlanningState:
        """Run the flight agent as part of the orchestrated workflow.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with flight options
        """
        if not state.travel_intent:
            logger.warning("No travel intent available, skipping flight search")
            state.completed_agents.append("flight")
            return state

        intent = state.travel_intent
        all_flights = []

        # Parse timeframe to extract dates
        timeframe_str = intent.timeframe or "December 2025"
        travel_date = "2025-12-20"  # Default date

        try:
            # Try to extract YYYY-MM-DD pattern if present
            import re
            date_pattern = r'(\d{4})-(\d{2})-(\d{2})'
            match = re.search(date_pattern, timeframe_str)
            if match:
                travel_date = match.group(0)
            else:
                # Use defaults based on month mentioned
                if "december" in timeframe_str.lower() or "dec" in timeframe_str.lower():
                    travel_date = "2025-12-20"
                elif "january" in timeframe_str.lower() or "jan" in timeframe_str.lower():
                    travel_date = "2026-01-15"
                elif "march" in timeframe_str.lower() or "mar" in timeframe_str.lower():
                    travel_date = "2026-03-15"
        except Exception as e:
            logger.warning(f"Error parsing travel date from '{timeframe_str}': {e}. Using default.")
            travel_date = "2025-12-20"

        # Search flights for each destination
        # Assume first location is origin, rest are destinations
        # Or use a default origin
        origin = "New York"  # Default origin - could be extracted from user profile

        for destination in intent.locations:
            flights = self.search_and_parse_flights(
                origin=origin,
                destination=destination,
                date=travel_date,
                passengers=intent.travelers or 1
            )
            all_flights.extend(flights)

        state.flights = all_flights
        state.completed_agents.append("flight")
        state.metadata["flights_found"] = len(all_flights)

        logger.info(f"Flight agent completed. Found {len(all_flights)} flights")

        return state

"""Simple travel planner script with clean output."""

import os
import logging
from dotenv import load_dotenv

from agents.travel_orchestrator import TravelOrchestrator

# Load environment variables
load_dotenv()

# Setup minimal logging - only show warnings and errors
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)


def plan_trip(query: str, verbose: bool = False):
    """Plan a trip based on user query.

    Args:
        query: Travel request in natural language
        verbose: If True, show detailed processing info
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    print("🌍 Travel Planning Assistant")
    print("=" * 80)
    print(f"\n{query}\n")
    print("=" * 80)
    print("\n⏳ Planning your trip...\n")

    try:
        # Initialize orchestrator
        orchestrator = TravelOrchestrator()

        # Process the query
        final_state = orchestrator.process_query(query.strip())

        # Format and display the itinerary
        formatted_output = orchestrator.format_itinerary_output(final_state)
        print(formatted_output)

        return final_state

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your API keys and try again.")
        return None


if __name__ == "__main__":
    # Example query
    travel_query = """
    I want to plan a trip to Paris, France for 1 week in December.
    My budget is around $2500.
    I'm interested in food, art, and culture.
    I'd like to visit the Louvre and try authentic French cuisine.
    Looking for a nice 4-star hotel near the city center.
    """

    # Run with minimal logging (clean output)
    plan_trip(travel_query, verbose=False)

    # To see detailed logs, use:
    # plan_trip(travel_query, verbose=True)

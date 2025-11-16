"""Example script demonstrating the travel planning multi-agent system."""

import os
import logging
from dotenv import load_dotenv

from agents.travel_orchestrator import TravelOrchestrator
from utils.langsmith_setup import setup_langsmith

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run travel planning example."""

    # Setup LangSmith tracing (optional)
    setup_langsmith(project_name="travel-planning-agents", enabled=True)

    print("=" * 80)
    print("  Multi-Agent Travel Planning System")
    print("  Powered by Valyu Search & LangChain")
    print("=" * 80)
    print()

    # Example travel query
    travel_query = """
    I want to plan a trip to Paris for 1 week in December.
    My budget is around $2500.
    I'm interested in food, art, and culture.
    I'd like to visit the Louvre and try authentic French cuisine.
    Looking for a nice 4-star hotel near the city center.
    """

    print("User Query:")
    print(travel_query)
    print()
    print("=" * 80)
    print("Processing your travel request through the agent pipeline...")
    print("=" * 80)
    print()

    try:
        # Initialize orchestrator
        orchestrator = TravelOrchestrator()

        # Process the query through all agents
        final_state = orchestrator.process_query(travel_query.strip())

        print()
        print("=" * 80)
        print("Pipeline Complete! Here's your travel plan:")
        print("=" * 80)
        print()

        # Check if clarifying questions were generated
        if final_state.get("clarifying_questions"):
            print("CLARIFYING QUESTIONS:")
            for i, question in enumerate(final_state["clarifying_questions"], 1):
                print(f"  {i}. {question}")
            print()

        # Format and display the itinerary
        formatted_output = orchestrator.format_itinerary_output(final_state)
        print(formatted_output)

        # Show some statistics
        print()
        print("=" * 80)
        print("PIPELINE STATISTICS:")
        print("=" * 80)
        metadata = final_state.get("metadata", {})
        print(f"Flights searched: {metadata.get('flights_found', 0)}")
        print(f"Hotels searched: {metadata.get('hotels_found', 0)}")
        print(f"Budget options created: {metadata.get('budget_options_created', 0)}")
        print(f"Activities found: {metadata.get('activities_found', 0)}")
        print(f"Options ranked: {metadata.get('ranked_options_count', 0)}")
        print(f"Completed agents: {', '.join(final_state.get('completed_agents', []))}")
        print()

        # Show alternative options if available
        if final_state.get("ranked_options") and len(final_state["ranked_options"]) > 1:
            print()
            print("=" * 80)
            print("ALTERNATIVE OPTIONS:")
            print("=" * 80)
            for i, option in enumerate(final_state["ranked_options"][1:4], 2):  # Show top 3 alternatives
                print(f"\nOption #{option['rank']}:")
                print(f"  {option['reasoning']}")
                print(f"  Overall Score: {option['overall_score']:.1f}/100")
                print(f"    Budget: {option['budget_score']:.1f} | Quality: {option['quality_score']:.1f}")
                print(f"    Preferences: {option['preference_score']:.1f} | Efficiency: {option['efficiency_score']:.1f}")

    except Exception as e:
        logger.error(f"Error processing travel query: {e}", exc_info=True)
        print(f"\nError: {e}")
        print("Please check your API keys and try again.")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("VALYU_API_KEY"):
        print("Error: VALYU_API_KEY not set in environment")
        print("Please set your Valyu API key in .env file")
        exit(1)

    main()

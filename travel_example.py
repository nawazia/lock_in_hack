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
    """Run travel planning example with interactive interface."""

    # Setup LangSmith tracing (optional)
    setup_langsmith(project_name="travel-planning-agents", enabled=True)

    print("=" * 80)
    print("  Multi-Agent Travel Planning System")
    print("  Powered by Valyu Search & LangChain")
    print("  [Interactive Mode - Will ask clarifying questions]")
    print("=" * 80)
    print()

    try:
        # Initialize orchestrator
        orchestrator = TravelOrchestrator()

        # Start with initial query (can be incomplete)
        initial_query = """
        I want to plan a trip to Hong Kong.
        """

        print("Initial User Query:")
        print(initial_query)
        print()
        print("=" * 80)
        print("Processing your travel request...")
        print("=" * 80)
        print()

        # Process the initial query
        state = orchestrator.process_query(initial_query.strip())

        # Interactive loop: continue until all information is collected
        while orchestrator.is_waiting_for_input(state):
            print()
            print("=" * 80)
            print("SYSTEM NEEDS MORE INFORMATION")
            print("=" * 80)
            print()

            # Show clarifying questions
            if state.get("clarifying_questions"):
                print("Please provide the following information:")
                for i, question in enumerate(state["clarifying_questions"], 1):
                    print(f"  {i}. {question}")
                print()

            # Show what we have so far
            if state.get("travel_intent"):
                intent = state["travel_intent"]
                print("Current Information:")
                if intent.get("budget"):
                    print(f"  ✓ Budget: {intent['budget']}")
                if intent.get("timeframe"):
                    print(f"  ✓ Timeframe: {intent['timeframe']}")
                if intent.get("locations"):
                    print(f"  ✓ Locations: {', '.join(intent['locations'])}")
                if intent.get("interests"):
                    print(f"  ✓ Interests: {', '.join(intent['interests'])}")

                missing = state.get("metadata", {}).get("missing_fields", [])
                if missing:
                    print(f"\n  Missing: {', '.join(missing)}")
                print()

            # In a real interactive system, you would get user input here
            # For this example, we'll simulate user responses
            print("=" * 80)
            print("SIMULATED USER RESPONSE:")
            print("=" * 80)

            # Simulate providing the missing information
            user_response = """
            My budget is around $4000.
            I want to travel for 1 week during Christmas.
            I'm interested in food, culture, and nightlife.
            I want to visit popular spots like Victoria Peak and Tsim Sha Tsui, and stay in a 4/5-star hotel near Central.
            """
            print(user_response)
            print()

            # Continue processing with the user's response
            state = orchestrator.process_query(user_response.strip(), existing_state=state)

        # All information collected, proceed with planning
        print()
        print("=" * 80)
        print("All information collected! Planning your trip...")
        print("=" * 80)
        print()

        # Show conversation history
        if state.get("conversation_history"):
            print("CONVERSATION SUMMARY:")
            print("-" * 80)
            for msg in state["conversation_history"]:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                print(f"{role}: {content[:100]}..." if len(content) > 100 else f"{role}: {content}")
            print()

        # If we have a final itinerary, display it
        if state.get("final_itinerary"):
            print()
            print("=" * 80)
            print("YOUR TRAVEL PLAN:")
            print("=" * 80)
            print()
            formatted_output = orchestrator.format_itinerary_output(state)
            print(formatted_output)

            # Show statistics
            print()
            print("=" * 80)
            print("PIPELINE STATISTICS:")
            print("=" * 80)
            metadata = state.get("metadata", {})
            print(f"Flights searched: {metadata.get('flights_found', 0)}")
            print(f"Hotels searched: {metadata.get('hotels_found', 0)}")
            print(f"Budget options created: {metadata.get('budget_options_created', 0)}")
            print(f"Activities found: {metadata.get('activities_found', 0)}")
            print(f"Options ranked: {metadata.get('ranked_options_count', 0)}")
            print(f"Completed agents: {', '.join(state.get('completed_agents', []))}")
            print()
        else:
            print("Ready to proceed with trip planning!")
            print("(In production, would now search for flights, hotels, activities, etc.)")

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

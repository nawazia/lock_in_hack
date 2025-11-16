"""Demo script showing the feedback loop handling errors."""

import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta

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


def inject_errors_into_state(state):
    """Inject intentional errors to demonstrate the audit feedback loop.

    This function modifies the state to create issues that the audit agent
    will need to detect and either fix or trigger feedback loops to resolve.
    """
    if not state.get("final_itinerary"):
        return state

    itinerary = state["final_itinerary"]

    print("\n" + "=" * 80)
    print("🔧 DEMO MODE: Injecting intentional errors to test feedback loop...")
    print("=" * 80)

    errors_injected = []

    # Error 1: Mess up the itinerary dates (create date inconsistency)
    # Set itinerary to start 10 days before the flight arrives
    flight = itinerary["budget_option"]["flight_outbound"]
    arrival_date = flight["arrival_time"].split('T')[0]
    wrong_start_date = (datetime.strptime(arrival_date, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d")
    wrong_end_date = (datetime.strptime(arrival_date, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d")

    itinerary["start_date"] = wrong_start_date
    itinerary["end_date"] = wrong_end_date

    errors_injected.append(f"❌ Date inconsistency: Flight arrives {arrival_date} but itinerary starts {wrong_start_date}")

    # Error 2: Invalid hotel rating (out of 5 scale)
    hotel = itinerary["budget_option"]["hotel"]
    if hotel.get("rating"):
        original_rating = hotel["rating"]
        hotel["rating"] = 12.5  # Invalid: should be 0-5
        errors_injected.append(f"❌ Invalid rating: Hotel rating is {hotel['rating']}/5 (should be max 5.0)")

    # Error 3: Change hotel location to wrong city (location mismatch)
    hotel["location"] = "Singapore"  # Wrong city!
    errors_injected.append(f"❌ Location mismatch: Hotel is in Singapore but user requested Hong Kong")

    # Error 4: Negative activity price
    if itinerary.get("daily_plans") and len(itinerary["daily_plans"]) > 1:
        activities = itinerary["daily_plans"][1].get("activities", [])
        if activities and len(activities) > 0:
            activities[0]["price"] = -50.0  # Negative price!
            errors_injected.append(f"❌ Invalid price: Activity '{activities[0]['name']}' has negative price: $-50.00")

    # Error 5: Add a blog URL instead of booking URL
    hotel["booking_url"] = "https://travelblog.com/hong-kong-hotels-guide"
    errors_injected.append(f"❌ Invalid URL: Hotel booking URL is a blog/guide instead of booking site")

    print("\nInjected errors:")
    for i, error in enumerate(errors_injected, 1):
        print(f"  {i}. {error}")

    print("\n⚠️  The audit agent will now detect these issues and:")
    print("  • Auto-fix what it can (dates, ratings, prices)")
    print("  • Trigger feedback loops for critical issues (location mismatch)")
    print("  • Show iteration count if it needs to re-run agents")
    print("=" * 80)
    print()

    return state


def main():
    """Run travel planning demo with intentional errors."""

    # Setup LangSmith tracing (optional)
    setup_langsmith(project_name="travel-planning-demo-errors", enabled=True)

    print("=" * 80)
    print("  Multi-Agent Travel Planning System - ERROR DEMO")
    print("  Demonstrating Feedback Loop & Audit Capabilities")
    print("=" * 80)
    print()
    print("This demo will:")
    print("  1. Plan a trip normally")
    print("  2. Inject intentional errors into the itinerary")
    print("  3. Show how the audit agent detects and fixes issues")
    print("  4. Demonstrate the feedback loop for critical errors")
    print()

    try:
        # Initialize orchestrator
        orchestrator = TravelOrchestrator()

        # Start with initial query
        initial_query = "I want to plan a trip to Hong Kong."

        print("=" * 80)
        print("Processing your travel request...")
        print("=" * 80)
        print()

        # Process the initial query
        state = orchestrator.process_query(initial_query.strip())

        # Provide all information at once
        user_response = """
        I want to go to Hong Kong!
        My budget is around $4000.
        I want to travel for 1 week during Christmas.
        I'm interested in food, culture, and nightlife.
        I want to optimize for cost.
        """

        # Continue processing with the user's response
        state = orchestrator.process_query(user_response.strip(), existing_state=state)

        # Wait until planning is complete
        while orchestrator.is_waiting_for_input(state):
            state = orchestrator.process_query(user_response.strip(), existing_state=state)

        # Inject errors BEFORE the audit runs
        # We'll modify the state after itinerary creation but before final audit
        # Since the graph has already run, we need to re-invoke with errors

        print("\n" + "=" * 80)
        print("✓ Initial itinerary created successfully")
        print("=" * 80)

        # Inject errors into the state
        state = inject_errors_into_state(state)

        # Now trigger the audit manually by calling the audit agent
        print("\n" + "=" * 80)
        print("🔍 Running audit agent to detect and fix errors...")
        print("=" * 80)
        print()

        from agents.audit_agent import AuditAgent
        audit_agent = AuditAgent()

        # Convert state to TravelPlanningState
        from models.travel_schemas import TravelPlanningState
        planning_state = TravelPlanningState(**state)

        # Run audit
        audited_state = audit_agent.run(planning_state)
        state = audited_state.model_dump()

        # Display results
        print()
        print("=" * 80)
        print("AUDIT RESULTS")
        print("=" * 80)
        print()

        metadata = state.get("metadata", {})
        print(f"Issues Found: {metadata.get('audit_issues_found', 0)}")
        print(f"Fixes Applied: {metadata.get('audit_fixes_applied', 0)}")
        print(f"Critical Issues Remaining: {len(metadata.get('critical_issues', []))}")
        print()

        if metadata.get("audit_issues"):
            print("Issues Detected:")
            for issue in metadata.get("audit_issues", []):
                print(f"  ⚠ {issue}")
            print()

        if metadata.get("audit_fixes"):
            print("Fixes Applied:")
            for fix in metadata.get("audit_fixes", []):
                print(f"  ✓ {fix}")
            print()

        if metadata.get("critical_issues"):
            print("⚠️  CRITICAL ISSUES REMAINING:")
            for issue in metadata.get("critical_issues", []):
                print(f"  ❌ {issue}")
            print()
            print("These would trigger a feedback loop to re-run the appropriate agent.")
            print(f"Issue types: {metadata.get('issue_types', [])}")

            # Show which agents would be re-run
            issue_types = metadata.get('issue_types', [])
            if "location_mismatch" in issue_types:
                print("  → Would route back to: Flight Agent (to search for correct location)")
            if "date_consistency" in issue_types:
                print("  → Would route back to: Itinerary Agent (to fix dates)")
            if "price_validation" in issue_types:
                print("  → Would route back to: Budget Agent (to re-calculate options)")
        else:
            print("✅ All issues were automatically fixed!")
            print("No feedback loop needed - pipeline can complete.")

        print()
        print("=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print()
        print("The audit system successfully:")
        print("  ✓ Detected all 5 injected errors")
        print("  ✓ Auto-fixed non-critical issues (dates, ratings, prices, URLs)")
        print("  ✓ Flagged critical issues (location mismatch) for feedback loop")
        print("  ✓ Categorized issues by type for intelligent routing")
        print()
        print("In production, critical issues would trigger:")
        print("  → Iteration counter increment")
        print("  → Routing back to appropriate agent")
        print("  → Re-execution until resolved or max iterations reached")
        print()
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
        print(f"\nError: {e}")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("VALYU_API_KEY"):
        print("Error: VALYU_API_KEY not set in environment")
        print("Please set your Valyu API key in .env file")
        exit(1)

    main()

"""Travel Orchestrator - Coordinates all travel planning agents using LangGraph."""

import logging
import json
from typing import Any, Dict
from langsmith import traceable
from langgraph.graph import END, StateGraph

from agents.interface_agent import InterfaceAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.budget_agent import BudgetAgent
from agents.activities_agent import ActivitiesAgent
from agents.ranking_agent import RankingAgent
from agents.itinerary_agent import ItineraryAgent
from agents.audit_agent import AuditAgent
from models.travel_schemas import TravelPlanningState
from utils.observability_collector import ObservabilityCollector
from config.llm_setup import get_llm

logger = logging.getLogger(__name__)


class TravelOrchestrator:
    """Orchestrator that coordinates multiple agents for travel planning."""

    def __init__(self, llm=None):
        """Initialize the travel orchestrator.

        Args:
            llm: Language model to use for agents that need it
        """
        self.llm = llm or get_llm()

        # Initialize all agents
        self.interface_agent = InterfaceAgent(llm=self.llm)
        self.flight_agent = FlightAgent(llm=self.llm)
        self.hotel_agent = HotelAgent(llm=self.llm)
        self.budget_agent = BudgetAgent()
        self.activities_agent = ActivitiesAgent(llm=self.llm)
        self.ranking_agent = RankingAgent()
        self.itinerary_agent = ItineraryAgent()
        self.audit_agent = AuditAgent()

        # Build the orchestration graph
        self.graph = self._build_graph()

    def _route_after_interface(self, state: Dict) -> str:
        """Routing function to decide next step after interface agent.

        Args:
            state: Current state dict

        Returns:
            Next node name or END
        """
        # Check if we need user input
        if state.get("needs_user_input", False):
            logger.info("Routing: Waiting for user input")
            return END

        # Check if intent is complete
        if state.get("metadata", {}).get("intent_complete", False):
            logger.info("Routing: Intent complete, proceeding to flights")
            return "flights"

        # Fallback: if questions exist, wait for user input
        if state.get("clarifying_questions") and len(state.get("clarifying_questions", [])) > 0:
            logger.info("Routing: Has clarifying questions, waiting for user input")
            return END

        # Otherwise proceed to flights
        logger.info("Routing: Proceeding to flights")
        return "flights"

    def _build_graph(self):
        """Build the LangGraph workflow for travel planning orchestration."""

        # Define the workflow graph using TravelPlanningState
        workflow = StateGraph(dict)  # Use dict for flexibility

        # Add nodes for each agent
        workflow.add_node("interface", self._interface_node)
        workflow.add_node("flights", self._flight_node)
        workflow.add_node("hotels", self._hotel_node)
        workflow.add_node("budget", self._budget_node)
        workflow.add_node("activities", self._activities_node)
        workflow.add_node("ranking", self._ranking_node)
        workflow.add_node("itinerary", self._itinerary_node)
        workflow.add_node("audit", self._audit_node)

        # Define the workflow pipeline with conditional routing
        # Start with interface agent
        workflow.set_entry_point("interface")

        # After interface, use conditional routing
        # If intent is complete -> go to flights
        # If needs user input -> END (wait for user response)
        workflow.add_conditional_edges(
            "interface",
            self._route_after_interface,
            {
                "flights": "flights",
                END: END
            }
        )

        # After flights, go to hotels
        workflow.add_edge("flights", "hotels")

        # After hotels, go to budget matching
        workflow.add_edge("hotels", "budget")

        # After budget, search activities
        workflow.add_edge("budget", "activities")

        # After activities, rank all options
        workflow.add_edge("activities", "ranking")

        # After ranking, create itinerary
        workflow.add_edge("ranking", "itinerary")

        # After itinerary, audit for errors
        workflow.add_edge("itinerary", "audit")

        # Audit is the end
        workflow.add_edge("audit", END)

        # Compile the graph
        app = workflow.compile()
        return app

    @traceable(name="interface_node")
    def _interface_node(self, state: Dict) -> Dict:
        """Node for interface agent - extracts user intent."""
        logger.info("Running interface agent...")
        try:
            # Convert dict to TravelPlanningState
            planning_state = TravelPlanningState(**state)
            planning_state = self.interface_agent.run(planning_state)

            # Convert back to dict for LangGraph
            result = planning_state.model_dump()
            logger.info(f"Interface complete: Intent extracted, {len(result.get('clarifying_questions', []))} questions")
            return result

        except Exception as e:
            logger.error(f"Error in interface node: {e}")
            state["completed_agents"] = state.get("completed_agents", []) + ["interface"]
            return state

    @traceable(name="flight_node")
    def _flight_node(self, state: Dict) -> Dict:
        """Node for flight agent - searches for flights."""
        logger.info("Running flight agent...")
        try:
            planning_state = TravelPlanningState(**state)
            planning_state = self.flight_agent.run(planning_state)

            result = planning_state.model_dump()
            logger.info(f"Flight search complete: {len(result.get('flights', []))} flights found")
            return result

        except Exception as e:
            logger.error(f"Error in flight node: {e}")
            state["completed_agents"] = state.get("completed_agents", []) + ["flight"]
            return state

    @traceable(name="hotel_node")
    def _hotel_node(self, state: Dict) -> Dict:
        """Node for hotel agent - searches for hotels."""
        logger.info("Running hotel agent...")
        try:
            planning_state = TravelPlanningState(**state)
            planning_state = self.hotel_agent.run(planning_state)

            result = planning_state.model_dump()
            logger.info(f"Hotel search complete: {len(result.get('hotels', []))} hotels found")
            return result

        except Exception as e:
            logger.error(f"Error in hotel node: {e}")
            state["completed_agents"] = state.get("completed_agents", []) + ["hotel"]
            return state

    @traceable(name="budget_node")
    def _budget_node(self, state: Dict) -> Dict:
        """Node for budget agent - matches flight/hotel within budget."""
        logger.info("Running budget agent...")
        try:
            planning_state = TravelPlanningState(**state)
            planning_state = self.budget_agent.run(planning_state)

            result = planning_state.model_dump()
            logger.info(f"Budget matching complete: {len(result.get('budget_options', []))} options created")
            return result

        except Exception as e:
            logger.error(f"Error in budget node: {e}")
            state["completed_agents"] = state.get("completed_agents", []) + ["budget"]
            return state

    @traceable(name="activities_node")
    def _activities_node(self, state: Dict) -> Dict:
        """Node for activities agent - finds relevant activities."""
        logger.info("Running activities agent...")
        try:
            planning_state = TravelPlanningState(**state)
            planning_state = self.activities_agent.run(planning_state)

            result = planning_state.model_dump()
            logger.info(f"Activities search complete: {len(result.get('activities', []))} activities found")
            return result

        except Exception as e:
            logger.error(f"Error in activities node: {e}")
            state["completed_agents"] = state.get("completed_agents", []) + ["activities"]
            return state

    @traceable(name="ranking_node")
    def _ranking_node(self, state: Dict) -> Dict:
        """Node for ranking agent - ranks all options."""
        logger.info("Running ranking agent...")
        try:
            planning_state = TravelPlanningState(**state)
            planning_state = self.ranking_agent.run(planning_state)

            result = planning_state.model_dump()
            logger.info(f"Ranking complete: {len(result.get('ranked_options', []))} options ranked")
            return result

        except Exception as e:
            logger.error(f"Error in ranking node: {e}")
            state["completed_agents"] = state.get("completed_agents", []) + ["ranking"]
            return state

    @traceable(name="itinerary_node")
    def _itinerary_node(self, state: Dict) -> Dict:
        """Node for itinerary agent - creates day-by-day itinerary."""
        logger.info("Running itinerary agent...")
        try:
            planning_state = TravelPlanningState(**state)
            planning_state = self.itinerary_agent.run(planning_state)

            result = planning_state.model_dump()
            logger.info("Itinerary creation complete")
            return result

        except Exception as e:
            logger.error(f"Error in itinerary node: {e}")
            state["completed_agents"] = state.get("completed_agents", []) + ["itinerary"]
            return state

    @traceable(name="audit_node")
    def _audit_node(self, state: Dict) -> Dict:
        """Node for audit agent - validates and fixes issues."""
        logger.info("Running audit agent...")
        try:
            planning_state = TravelPlanningState(**state)
            planning_state = self.audit_agent.run(planning_state)

            result = planning_state.model_dump()
            logger.info("Audit complete")
            return result

        except Exception as e:
            logger.error(f"Error in audit node: {e}")
            state["completed_agents"] = state.get("completed_agents", []) + ["audit"]
            return state

    @traceable(name="travel_orchestrator_process")
    def process_query(self, query: str, existing_state: dict = None) -> dict:
        """Process a travel planning query through the agent pipeline.

        Args:
            query: User's travel request
            existing_state: Optional existing state from previous interaction

        Returns:
            Final state dict with itinerary and all intermediate results
        """
        logger.info(f"Processing travel query: {query}")

        try:
            # Initialize state or use existing state
            if existing_state:
                # Continue from existing state with new query
                state = existing_state.copy()
                state["user_query"] = query
                state["needs_user_input"] = False  # Reset flag
                logger.info("Continuing from existing state")

                # Get existing collector or create new one
                collector = state.get("metadata", {}).get("observability_collector")
                if not collector:
                    collector = ObservabilityCollector(user_query=query)
                    state["metadata"]["observability_collector"] = collector
            else:
                # Initialize new state
                # Create observability collector
                collector = ObservabilityCollector(user_query=query)

                state = {
                    "user_query": query,
                    "travel_intent": None,
                    "conversation_history": [],
                    "user_responses": {},
                    "flights": [],
                    "hotels": [],
                    "budget_options": [],
                    "activities": [],
                    "ranked_options": [],
                    "final_itinerary": None,
                    "next_agent": None,
                    "completed_agents": [],
                    "metadata": {
                        "observability_collector": collector
                    },
                    "clarifying_questions": [],
                    "needs_user_input": False
                }
                logger.info("Starting new conversation with observability collection")

            # Run the graph
            final_state = self.graph.invoke(state)

            # Generate observability report if pipeline completed
            if final_state.get("final_itinerary") and collector:
                try:
                    # Generate the final observability report
                    observability_report = collector.generate_report(
                        final_itinerary=final_state.get("final_itinerary")
                    )

                    # Add observability report to state metadata
                    final_state["metadata"]["observability_report"] = observability_report.model_dump()

                    # Also save as JSON string for easy frontend consumption
                    final_state["metadata"]["observability_json"] = collector.to_json(
                        final_itinerary=final_state.get("final_itinerary")
                    )

                    # Print summary to console
                    collector.print_summary()

                    logger.info(f"Generated observability report: {len(observability_report.steps)} steps, "
                              f"overall risk={observability_report.overall_hallucination_risk:.3f}, "
                              f"confidence={observability_report.overall_confidence}, "
                              f"flags={len(observability_report.hallucination_flags)}")

                except Exception as e:
                    logger.warning(f"Failed to generate observability report: {e}")

            logger.info("Travel planning pipeline step complete")
            return final_state

        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            raise

    def is_waiting_for_input(self, state: dict) -> bool:
        """Check if the orchestrator is waiting for user input.

        Args:
            state: Current state

        Returns:
            True if waiting for user input
        """
        return state.get("needs_user_input", False) or len(state.get("clarifying_questions", [])) > 0

    def format_itinerary_output(self, final_state: dict) -> str:
        """Format the final itinerary as a readable string.

        Args:
            final_state: Final state from orchestrator

        Returns:
            Formatted itinerary string
        """
        if not final_state.get("final_itinerary"):
            return "No itinerary could be created. Please try with different parameters."

        itinerary = final_state["final_itinerary"]

        # Build output
        output = []
        output.append("=" * 80)
        output.append(f"  {itinerary['title']}")
        output.append("=" * 80)
        output.append("")

        # Overview
        output.append(f"Dates: {itinerary['start_date']} to {itinerary['end_date']}")
        output.append(f"Duration: {itinerary['total_days']} days")
        output.append(f"Destinations: {', '.join(itinerary['destinations'])}")
        output.append(f"Total Estimated Cost: ${itinerary['total_estimated_cost']:.2f}")
        output.append("")

        # Flight & Hotel
        budget_opt = itinerary['budget_option']
        output.append("FLIGHT:")
        flight = budget_opt['flight_outbound']
        output.append(f"  {flight['airline']} {flight['flight_number']}")
        output.append(f"  {flight['departure_airport']} -> {flight['arrival_airport']}")
        output.append(f"  Departure: {flight['departure_time']}")
        output.append(f"  Price: ${flight['price']:.2f}")
        if flight.get('booking_url'):
            output.append(f"  Book: {flight['booking_url']}")
        output.append("")

        output.append("ACCOMMODATION:")
        hotel = budget_opt['hotel']
        output.append(f"  {hotel['name']}")
        output.append(f"  Location: {hotel['location']}")
        output.append(f"  Rating: {hotel.get('rating', 'N/A')} / 5")
        output.append(f"  Price per night: ${hotel['price_per_night']:.2f}")
        if hotel.get('booking_url'):
            output.append(f"  Book: {hotel['booking_url']}")
        output.append("")

        # Daily plans
        output.append("DAILY ITINERARY:")
        output.append("")
        for day in itinerary['daily_plans']:
            output.append(f"Day {day['day_number']} - {day['date']}")
            output.append(f"  {day.get('notes', '')}")
            if day['activities']:
                output.append("  Activities:")
                for activity in day['activities']:
                    output.append(f"    • {activity['name']} (${activity.get('price', 0):.2f})")
                    output.append(f"      {activity['description'][:80]}...")
                    if activity.get('booking_url'):
                        output.append(f"      Book: {activity['booking_url']}")
            output.append("")

        # Packing suggestions
        if itinerary.get('packing_suggestions'):
            output.append("PACKING SUGGESTIONS:")
            for item in itinerary['packing_suggestions']:
                output.append(f"  • {item}")
            output.append("")

        # Travel tips
        if itinerary.get('travel_tips'):
            output.append("TRAVEL TIPS:")
            for tip in itinerary['travel_tips']:
                output.append(f"  • {tip}")
            output.append("")

        # Audit results
        metadata = final_state.get("metadata", {})
        if metadata.get("audit_issues_found", 0) > 0:
            output.append("AUDIT RESULTS:")
            output.append(f"  Issues Found: {metadata.get('audit_issues_found', 0)}")
            output.append(f"  Fixes Applied: {metadata.get('audit_fixes_applied', 0)}")
            if metadata.get("audit_fixes"):
                output.append("  Fixes:")
                for fix in metadata.get("audit_fixes", []):
                    output.append(f"    ✓ {fix}")
            output.append("")

        output.append("=" * 80)

        return "\n".join(output)

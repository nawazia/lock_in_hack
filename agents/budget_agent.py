"""Budget Agent - Matches flight and hotel combinations within budget."""

import logging
import re
from typing import List, Optional, Tuple
from langsmith import traceable

from models.travel_schemas import TravelPlanningState, BudgetOption, Flight, Hotel

logger = logging.getLogger(__name__)


class BudgetAgent:
    """Agent responsible for matching flights and hotels within budget constraints."""

    def __init__(self):
        """Initialize the budget agent."""
        pass

    def parse_budget(self, budget_string: Optional[str]) -> Tuple[float, float]:
        """Parse budget string into min and max values.

        Args:
            budget_string: Budget string (e.g., "$1000-2000", "budget-friendly", "luxury")

        Returns:
            Tuple of (min_budget, max_budget) in USD
        """
        if not budget_string:
            return (0, float('inf'))

        # Try to extract numeric values
        numbers = re.findall(r'\d+', budget_string)

        if len(numbers) >= 2:
            # Range like "$1000-2000"
            return (float(numbers[0]), float(numbers[1]))
        elif len(numbers) == 1:
            # Single value like "$2000"
            value = float(numbers[0])
            return (0, value)
        else:
            # Text-based budget
            budget_lower = budget_string.lower()
            if "budget" in budget_lower or "cheap" in budget_lower or "affordable" in budget_lower:
                return (0, 1500)
            elif "luxury" in budget_lower or "premium" in budget_lower or "high-end" in budget_lower:
                return (3000, 10000)
            elif "mid" in budget_lower or "moderate" in budget_lower:
                return (1500, 3000)
            else:
                # Default to wide range
                return (0, float('inf'))

    def calculate_nights(self, timeframe: Optional[str]) -> int:
        """Calculate number of nights from timeframe.

        Args:
            timeframe: Timeframe string

        Returns:
            Number of nights
        """
        # Simple heuristic - try to find number of days/nights
        if not timeframe:
            return 7  # Default to 1 week

        # Look for patterns like "5 days", "1 week", "2 weeks"
        if "week" in timeframe.lower():
            weeks = re.findall(r'(\d+)\s*week', timeframe.lower())
            if weeks:
                return int(weeks[0]) * 7
            return 7  # Default to 1 week

        days = re.findall(r'(\d+)\s*day', timeframe.lower())
        if days:
            return max(1, int(days[0]) - 1)  # N days = N-1 nights

        # Try to parse date ranges
        # Look for patterns like "Dec 20-27"
        date_numbers = re.findall(r'\d+', timeframe)
        if len(date_numbers) >= 2:
            # Assume it's day numbers in a range
            try:
                start = int(date_numbers[0])
                end = int(date_numbers[1])
                if end > start:
                    return end - start
            except:
                pass

        return 7  # Default

    def calculate_budget_fit_score(
        self,
        total_cost: float,
        min_budget: float,
        max_budget: float
    ) -> float:
        """Calculate how well the option fits within budget.

        Args:
            total_cost: Total cost of the option
            min_budget: Minimum budget
            max_budget: Maximum budget

        Returns:
            Score from 0-1 (1 is perfect fit)
        """
        if max_budget == float('inf'):
            # No upper limit, just check if positive
            return 1.0 if total_cost > 0 else 0.0

        if total_cost > max_budget:
            # Over budget - penalize based on how much over
            overage = (total_cost - max_budget) / max_budget
            return max(0, 1.0 - overage)

        if total_cost < min_budget:
            # Under budget - might be suspicious or low quality
            underage = (min_budget - total_cost) / min_budget
            return max(0.5, 1.0 - underage * 0.5)

        # Within budget - score based on how well it uses budget
        # Prefer options that use 70-90% of budget
        utilization = total_cost / max_budget
        if 0.7 <= utilization <= 0.9:
            return 1.0
        elif utilization < 0.7:
            return 0.8 + (utilization / 0.7) * 0.2
        else:
            return 0.9

    @traceable(name="match_budget_options")
    def match_budget_options(
        self,
        flights: List[Flight],
        hotels: List[Hotel],
        budget_string: Optional[str],
        timeframe: Optional[str],
        travelers: int = 1
    ) -> List[BudgetOption]:
        """Match flight and hotel combinations within budget.

        Args:
            flights: Available flights
            hotels: Available hotels
            budget_string: Budget constraint
            timeframe: Trip timeframe
            travelers: Number of travelers

        Returns:
            List of BudgetOption objects
        """
        try:
            logger.info(f"Matching budget options: {len(flights)} flights, {len(hotels)} hotels")

            min_budget, max_budget = self.parse_budget(budget_string)
            nights = self.calculate_nights(timeframe)

            logger.info(f"Budget range: ${min_budget}-${max_budget}, Nights: {nights}")

            budget_options = []

            # Match each flight with each hotel
            for flight in flights:
                for hotel in hotels:
                    # Calculate total cost
                    flight_cost = flight.price * travelers
                    hotel_cost = hotel.price_per_night * nights * travelers  # Assume price is per person
                    total_cost = flight_cost + hotel_cost

                    # Calculate budget fit score
                    budget_fit_score = self.calculate_budget_fit_score(
                        total_cost, min_budget, max_budget
                    )

                    # Only include options with reasonable budget fit (>0.3)
                    if budget_fit_score > 0.3:
                        option = BudgetOption(
                            flight_outbound=flight,
                            flight_return=None,  # Would need return flight logic
                            hotel=hotel,
                            total_cost=total_cost,
                            nights=nights,
                            budget_fit_score=budget_fit_score
                        )
                        budget_options.append(option)

            # Sort by budget fit score (best first)
            budget_options.sort(key=lambda x: x.budget_fit_score, reverse=True)

            logger.info(f"Created {len(budget_options)} budget options")
            return budget_options

        except Exception as e:
            logger.error(f"Error matching budget options: {e}")
            return []

    @traceable(name="budget_agent_run")
    def run(self, state: TravelPlanningState) -> TravelPlanningState:
        """Run the budget agent as part of the orchestrated workflow.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with budget options
        """
        if not state.travel_intent:
            logger.warning("No travel intent available, skipping budget matching")
            state.completed_agents.append("budget")
            return state

        if not state.flights or not state.hotels:
            logger.warning("No flights or hotels available, skipping budget matching")
            state.completed_agents.append("budget")
            return state

        intent = state.travel_intent

        budget_options = self.match_budget_options(
            flights=state.flights,
            hotels=state.hotels,
            budget_string=intent.budget,
            timeframe=intent.timeframe,
            travelers=intent.travelers or 1
        )

        state.budget_options = budget_options
        state.completed_agents.append("budget")
        state.metadata["budget_options_created"] = len(budget_options)

        logger.info(f"Budget agent completed. Created {len(budget_options)} options")

        return state

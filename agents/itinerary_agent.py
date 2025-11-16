"""Itinerary Agent - Creates detailed day-by-day travel itineraries."""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from langsmith import traceable

from models.travel_schemas import (
    TravelPlanningState,
    Itinerary,
    DayPlan,
    RankedOption,
    Activity
)

logger = logging.getLogger(__name__)


class ItineraryAgent:
    """Agent responsible for creating detailed day-by-day itineraries."""

    def __init__(self):
        """Initialize the itinerary agent."""
        pass

    def parse_start_date(self, timeframe: Optional[str]) -> datetime:
        """Parse start date from timeframe string.

        Args:
            timeframe: Timeframe string

        Returns:
            Start date as datetime
        """
        if not timeframe:
            # Default to 30 days from now
            return datetime.now() + timedelta(days=30)

        # Try to find a date pattern
        # This is simplified - in production, use proper date parsing
        try:
            # Look for YYYY-MM-DD pattern
            import re
            date_pattern = r'(\d{4})-(\d{2})-(\d{2})'
            match = re.search(date_pattern, timeframe)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day))
        except:
            pass

        # Default
        return datetime.now() + timedelta(days=30)

    def distribute_activities(
        self,
        activities: List[Activity],
        num_days: int
    ) -> List[List[Activity]]:
        """Distribute activities across days.

        Args:
            activities: List of activities to distribute
            num_days: Number of days in the trip

        Returns:
            List of activity lists, one for each day
        """
        if not activities or num_days <= 0:
            return [[] for _ in range(max(1, num_days))]

        # Simple distribution - aim for 2-3 activities per day
        activities_per_day = max(1, len(activities) // num_days)

        daily_activities = []
        for day in range(num_days):
            start_idx = day * activities_per_day
            end_idx = start_idx + activities_per_day
            if day == num_days - 1:
                # Last day gets any remaining activities
                daily_activities.append(activities[start_idx:])
            else:
                daily_activities.append(activities[start_idx:end_idx])

        return daily_activities

    def generate_packing_suggestions(
        self,
        destination: str,
        activities: List[Activity],
        nights: int
    ) -> List[str]:
        """Generate packing suggestions based on destination and activities.

        Args:
            destination: Destination name
            activities: Planned activities
            nights: Number of nights

        Returns:
            List of packing suggestions
        """
        suggestions = [
            "Passport and travel documents",
            "Phone charger and adapters",
            "Medications and basic first aid",
            f"Clothing for {nights + 1} days"
        ]

        # Activity-based suggestions
        activity_categories = {a.category.lower() for a in activities}

        if "adventure" in activity_categories or "hiking" in activity_categories:
            suggestions.extend([
                "Comfortable hiking shoes",
                "Daypack or backpack",
                "Water bottle"
            ])

        if "beach" in activity_categories or "water" in activity_categories:
            suggestions.extend([
                "Swimsuit",
                "Sunscreen",
                "Beach towel"
            ])

        if "food" in activity_categories or "dining" in activity_categories:
            suggestions.append("Semi-formal attire for dining")

        if "museum" in activity_categories or "culture" in activity_categories:
            suggestions.append("Comfortable walking shoes")

        return suggestions

    def generate_travel_tips(
        self,
        destination: str,
        activities: List[Activity]
    ) -> List[str]:
        """Generate travel tips for the destination.

        Args:
            destination: Destination name
            activities: Planned activities

        Returns:
            List of travel tips
        """
        tips = [
            f"Research local customs and etiquette in {destination}",
            "Check visa requirements well in advance",
            "Notify your bank of international travel",
            "Download offline maps of the area",
            "Learn a few basic phrases in the local language"
        ]

        # Activity-specific tips
        if any(a.booking_required for a in activities):
            tips.append("Book popular activities in advance to avoid disappointment")

        if any(a.price and a.price > 100 for a in activities):
            tips.append("Consider purchasing travel insurance for expensive activities")

        return tips

    @traceable(name="create_itinerary")
    def create_itinerary(
        self,
        ranked_option: RankedOption,
        timeframe: Optional[str]
    ) -> Itinerary:
        """Create detailed itinerary from the top-ranked option.

        Args:
            ranked_option: Top-ranked travel option
            timeframe: Travel timeframe string

        Returns:
            Complete Itinerary object
        """
        try:
            logger.info("Creating detailed itinerary")

            budget_option = ranked_option.budget_option
            activities = ranked_option.recommended_activities

            # Determine dates
            start_date = self.parse_start_date(timeframe)
            nights = budget_option.nights
            total_days = nights + 1  # N nights = N+1 days
            end_date = start_date + timedelta(days=nights)

            # Get destination from hotel location
            destination = budget_option.hotel.location

            # Distribute activities across days
            daily_activity_lists = self.distribute_activities(activities, total_days)

            # Create daily plans
            daily_plans = []
            for day_num in range(total_days):
                current_date = start_date + timedelta(days=day_num)
                day_activities = daily_activity_lists[day_num]

                # Calculate estimated cost for the day
                estimated_cost = sum(a.price or 0 for a in day_activities)

                # Generate notes based on day
                notes = ""
                if day_num == 0:
                    notes = f"Arrival day - Flight {budget_option.flight_outbound.flight_number} arrives at {budget_option.flight_outbound.arrival_time}"
                elif day_num == total_days - 1:
                    notes = "Departure day - Check out and head to airport"
                else:
                    notes = f"Full day in {destination}"

                day_plan = DayPlan(
                    day_number=day_num + 1,
                    date=current_date.strftime("%Y-%m-%d"),
                    activities=day_activities,
                    accommodation=budget_option.hotel.name,
                    notes=notes,
                    estimated_cost=estimated_cost
                )
                daily_plans.append(day_plan)

            # Calculate total estimated cost
            total_activities_cost = sum(a.price or 0 for a in activities)
            total_estimated_cost = budget_option.total_cost + total_activities_cost

            # Generate packing and tips
            packing_suggestions = self.generate_packing_suggestions(
                destination, activities, nights
            )
            travel_tips = self.generate_travel_tips(destination, activities)

            # Create itinerary
            itinerary = Itinerary(
                title=f"{total_days}-Day {destination} {', '.join([a.category.title() for a in activities[:2]])} Experience",
                destinations=[destination],
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                total_days=total_days,
                budget_option=budget_option,
                daily_plans=daily_plans,
                total_estimated_cost=total_estimated_cost,
                packing_suggestions=packing_suggestions,
                travel_tips=travel_tips
            )

            logger.info(f"Created itinerary: {itinerary.title}")
            return itinerary

        except Exception as e:
            logger.error(f"Error creating itinerary: {e}")
            raise

    @traceable(name="itinerary_agent_run")
    def run(self, state: TravelPlanningState) -> TravelPlanningState:
        """Run the itinerary agent as part of the orchestrated workflow.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with final itinerary
        """
        if not state.travel_intent:
            logger.warning("No travel intent available, skipping itinerary creation")
            state.completed_agents.append("itinerary")
            return state

        if not state.ranked_options or len(state.ranked_options) == 0:
            logger.warning("No ranked options available, skipping itinerary creation")
            state.completed_agents.append("itinerary")
            return state

        # Take the top-ranked option
        top_option = state.ranked_options[0]

        # Create itinerary
        itinerary = self.create_itinerary(
            ranked_option=top_option,
            timeframe=state.travel_intent.timeframe
        )

        state.final_itinerary = itinerary
        state.completed_agents.append("itinerary")
        state.metadata["itinerary_created"] = True

        logger.info(f"Itinerary agent completed. Created: {itinerary.title}")

        return state

"""Itinerary Agent - Creates detailed day-by-day travel itineraries."""

import logging
import os
import json
from typing import List, Optional
from datetime import datetime, timedelta
from langsmith import traceable

from config.llm_setup import get_llm
from config.hallbayes_validator import EDFLValidator
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

    def __init__(self, llm=None, enable_edfl_validation=None):
        """Initialize the itinerary agent.

        Args:
            llm: Language model to use. If None, uses default from config.
            enable_edfl_validation: Enable EDFL validation. If None, reads from env ENABLE_EDFL_VALIDATION.
        """
        self.llm = llm or get_llm()

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
        """Distribute activities evenly across days using round-robin.

        Args:
            activities: List of activities to distribute
            num_days: Number of days in the trip

        Returns:
            List of activity lists, one for each day
        """
        if not activities or num_days <= 0:
            return [[] for _ in range(max(1, num_days))]

        # Skip first and last day (arrival/departure), distribute across middle days
        # If trip is 2 days or less, use all days
        if num_days > 2:
            activity_days = num_days - 2  # Skip first and last day
            start_day = 1  # Start from day 2 (index 1)
        else:
            activity_days = num_days
            start_day = 0

        # Initialize empty lists for all days
        daily_activities = [[] for _ in range(num_days)]

        # Distribute activities round-robin across activity days
        for idx, activity in enumerate(activities):
            day_idx = start_day + (idx % activity_days)
            daily_activities[day_idx].append(activity)

        logger.info(
            f"Distributed {len(activities)} activities across {num_days} days "
            f"(using days {start_day + 1} to {start_day + activity_days})"
        )

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

    @traceable(name="validate_final_itinerary")
    def validate_final_itinerary(
        self,
        itinerary: Itinerary,
        all_flights: List,
        all_hotels: List,
        all_activities: List
    ) -> Itinerary:
        """Validate the final itinerary against all collected evidence using EDFL.

        This is the critical final validation step that ensures the itinerary
        presented to the user is grounded in actual search results with no hallucinations.

        Args:
            itinerary: Generated itinerary to validate
            all_flights: All flights collected from search
            all_hotels: All hotels collected from search
            all_activities: All activities collected from search

        Returns:
            Itinerary with EDFL validation metadata added
        """
        if not self.edfl_validator:
            logger.info("EDFL validator not available, skipping final validation")
            return itinerary

        try:
            logger.info("=== FINAL EDFL VALIDATION: Verifying itinerary against collected evidence ===")

            # Build comprehensive evidence bundle from all collected data
            evidence_parts = []

            # Flight evidence
            evidence_parts.append("=== COLLECTED FLIGHT OPTIONS ===")
            for i, flight in enumerate(all_flights[:10], 1):  # Top 10 flights
                flight_info = f"""Flight {i}:
- Airline: {flight.airline}
- Flight Number: {flight.flight_number}
- Route: {flight.departure_airport} → {flight.arrival_airport}
- Departure: {flight.departure_time}
- Arrival: {flight.arrival_time}
- Duration: {flight.duration}
- Price: ${flight.price:.2f}
- Stops: {flight.stops}
- Booking URL: {flight.booking_url or 'N/A'}"""
                evidence_parts.append(flight_info)

            # Hotel evidence
            evidence_parts.append("\n=== COLLECTED HOTEL OPTIONS ===")
            for i, hotel in enumerate(all_hotels[:10], 1):  # Top 10 hotels
                hotel_info = f"""Hotel {i}:
- Name: {hotel.name}
- Location: {hotel.location}
- Address: {hotel.address or 'N/A'}
- Star Rating: {hotel.star_rating or 'N/A'}/5
- User Rating: {hotel.rating or 'N/A'}/5
- Price per Night: ${hotel.price_per_night:.2f}
- Amenities: {', '.join(hotel.amenities[:5]) if hotel.amenities else 'N/A'}
- Booking URL: {hotel.booking_url or 'N/A'}"""
                evidence_parts.append(hotel_info)

            # Activity evidence
            evidence_parts.append("\n=== COLLECTED ACTIVITY OPTIONS ===")
            for i, activity in enumerate(all_activities[:15], 1):  # Top 15 activities
                activity_price = f"${activity.price:.2f}" if activity.price else "N/A"
                activity_info = f"""Activity {i}:
- Name: {activity.name}
- Description: {activity.description[:100]}...
- Location: {activity.location}
- Category: {activity.category}
- Duration: {activity.duration or 'N/A'}
- Price: {activity_price}
- Rating: {activity.rating or 'N/A'}/5
- Booking URL: {activity.booking_url or 'N/A'}"""
                evidence_parts.append(activity_info)

            evidence = "\n".join(evidence_parts)

            # Build itinerary claims to verify
            claims_parts = []

            claims_parts.append("=== FINAL ITINERARY TO VERIFY ===")
            claims_parts.append(f"Title: {itinerary.title}")
            claims_parts.append(f"Destinations: {', '.join(itinerary.destinations)}")
            claims_parts.append(f"Dates: {itinerary.start_date} to {itinerary.end_date} ({itinerary.total_days} days)")
            claims_parts.append(f"Total Cost: ${itinerary.total_estimated_cost:.2f}")

            # Selected flight details
            flight = itinerary.budget_option.flight_outbound
            claims_parts.append(f"\nSELECTED FLIGHT:")
            claims_parts.append(f"- Airline: {flight.airline}")
            claims_parts.append(f"- Flight Number: {flight.flight_number}")
            claims_parts.append(f"- Route: {flight.departure_airport} → {flight.arrival_airport}")
            claims_parts.append(f"- Departure: {flight.departure_time}")
            claims_parts.append(f"- Arrival: {flight.arrival_time}")
            claims_parts.append(f"- Duration: {flight.duration}")
            claims_parts.append(f"- Price: ${flight.price:.2f}")
            claims_parts.append(f"- Booking URL: {flight.booking_url or 'N/A'}")

            # Selected hotel details
            hotel = itinerary.budget_option.hotel
            claims_parts.append(f"\nSELECTED HOTEL:")
            claims_parts.append(f"- Name: {hotel.name}")
            claims_parts.append(f"- Location: {hotel.location}")
            claims_parts.append(f"- Star Rating: {hotel.star_rating or 'N/A'}/5")
            claims_parts.append(f"- User Rating: {hotel.rating or 'N/A'}/5")
            claims_parts.append(f"- Price per Night: ${hotel.price_per_night:.2f}")
            claims_parts.append(f"- Total Hotel Cost for {itinerary.budget_option.nights} nights: ${hotel.price_per_night * itinerary.budget_option.nights:.2f}")
            claims_parts.append(f"- Booking URL: {hotel.booking_url or 'N/A'}")

            # Selected activities
            claims_parts.append(f"\nSELECTED ACTIVITIES ({len(itinerary.daily_plans)} days):")
            total_activity_cost = 0
            for day_plan in itinerary.daily_plans:
                claims_parts.append(f"\nDay {day_plan.day_number} ({day_plan.date}):")
                claims_parts.append(f"  Notes: {day_plan.notes}")
                if day_plan.activities:
                    for act in day_plan.activities:
                        act_price = f"${act.price:.2f}" if act.price else "$0.00"
                        claims_parts.append(f"  - {act.name} ({act_price})")
                        claims_parts.append(f"    Category: {act.category}, Location: {act.location}")
                        if act.price:
                            total_activity_cost += act.price
                else:
                    claims_parts.append(f"  - No activities scheduled")
                claims_parts.append(f"  Day Cost: ${day_plan.estimated_cost:.2f}")

            claims_parts.append(f"\nTOTAL BREAKDOWN:")
            claims_parts.append(f"- Flight Cost: ${flight.price:.2f}")
            claims_parts.append(f"- Hotel Cost ({itinerary.budget_option.nights} nights): ${hotel.price_per_night * itinerary.budget_option.nights:.2f}")
            claims_parts.append(f"- Activities Cost: ${total_activity_cost:.2f}")
            claims_parts.append(f"- TOTAL: ${itinerary.total_estimated_cost:.2f}")

            claims = "\n".join(claims_parts)

            # Run evidence-based EDFL validation
            logger.info("Running EDFL evidence-based validation on final itinerary...")

            should_use, risk_bound, rationale = self.edfl_validator.validate_evidence_based(
                task_description="""Verify the FINAL ITINERARY against collected search results.

This is the FINAL validation before presenting to the user. Check that:
1. Flight details (airline, number, times, price, URL) match the collected flight options
2. Hotel details (name, location, rating, price, URL) match the collected hotel options
3. Activity details (name, price, category, location) match the collected activity options
4. All prices are accurately extracted from the evidence
5. All URLs, names, and dates are correctly copied from source data
6. Total cost calculations are accurate
7. No information is fabricated or hallucinated

This is CRITICAL - the user will make booking decisions based on this itinerary.""",
                evidence=evidence,
                llm_output=claims,
                n_samples=5,  # More samples for final validation
                m=6  # More skeleton prompts for higher confidence
            )

            # Store comprehensive EDFL metrics
            itinerary.edfl_validation = {
                "risk_of_hallucination": risk_bound,
                "validation_passed": should_use,
                "confidence": "high" if risk_bound < 0.05 else ("medium" if risk_bound < 0.5 else "low"),
                "rationale": rationale,
                "validation_type": "evidence_based_final",
                "evidence_items": {
                    "flights_checked": min(len(all_flights), 10),
                    "hotels_checked": min(len(all_hotels), 10),
                    "activities_checked": min(len(all_activities), 15)
                }
            }

            if not should_use:
                logger.warning("=" * 80)
                logger.warning("⚠️  EDFL FINAL VALIDATION FAILED ⚠️")
                logger.warning(f"Risk of Hallucination: {risk_bound:.3f} (threshold: 0.05)")
                logger.warning(f"Rationale: {rationale}")
                logger.warning("The itinerary may contain hallucinated or inaccurate information!")
                logger.warning("Audit agent will attempt to fix issues.")
                logger.warning("=" * 80)
            else:
                logger.info("=" * 80)
                logger.info("✓ EDFL FINAL VALIDATION PASSED ✓")
                logger.info(f"Risk of Hallucination: {risk_bound:.3f} (threshold: 0.05)")
                logger.info(f"Confidence: {itinerary.edfl_validation['confidence']}")
                logger.info("Itinerary is grounded in collected evidence.")
                logger.info("=" * 80)

        except Exception as e:
            logger.error(f"EDFL final validation error: {e}")
            logger.error("Continuing without validation metrics")
            itinerary.edfl_validation = {
                "error": str(e),
                "validation_type": "evidence_based_final"
            }

        return itinerary

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

        # CRITICAL: Validate final itinerary against ALL collected evidence
        # This is the last line of defense against hallucinations before presenting to user
        itinerary = self.validate_final_itinerary(
            itinerary=itinerary,
            all_flights=state.flights,
            all_hotels=state.hotels,
            all_activities=state.activities
        )

        state.final_itinerary = itinerary
        state.completed_agents.append("itinerary")
        state.metadata["itinerary_created"] = True

        # Add EDFL validation metrics to state metadata
        if hasattr(itinerary, 'edfl_validation') and itinerary.edfl_validation:
            state.metadata["itinerary_edfl_validation"] = itinerary.edfl_validation

            validation_status = "PASS" if itinerary.edfl_validation.get('validation_passed') else "FAIL"
            risk = itinerary.edfl_validation.get('risk_of_hallucination', 'N/A')
            confidence = itinerary.edfl_validation.get('confidence', 'N/A')

            logger.info(f"Itinerary agent completed. Created: {itinerary.title}")
            logger.info(f"Final EDFL Validation: {validation_status} | RoH={risk} | Confidence={confidence}")
        else:
            logger.info(f"Itinerary agent completed. Created: {itinerary.title}")

        return state

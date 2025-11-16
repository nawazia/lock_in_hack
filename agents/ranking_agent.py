"""Ranking Agent - Scores and ranks travel option bundles."""

import logging
from typing import List
from langsmith import traceable

from models.travel_schemas import (
    TravelPlanningState,
    RankedOption,
    BudgetOption,
    Activity,
    TravelIntent
)

logger = logging.getLogger(__name__)


class RankingAgent:
    """Agent responsible for scoring and ranking travel options."""

    def __init__(self):
        """Initialize the ranking agent."""
        pass

    def calculate_budget_score(
        self,
        budget_option: BudgetOption
    ) -> float:
        """Calculate budget score for an option.

        Args:
            budget_option: Budget option to score

        Returns:
            Score from 0-100
        """
        # Use the budget_fit_score from the budget agent
        return budget_option.budget_fit_score * 100

    def calculate_preference_score(
        self,
        budget_option: BudgetOption,
        intent: TravelIntent
    ) -> float:
        """Calculate preference match score.

        Args:
            budget_option: Budget option to score
            intent: User's travel intent

        Returns:
            Score from 0-100
        """
        score = 50.0  # Base score

        hotel = budget_option.hotel

        # Check accommodation preferences
        if intent.accommodation_preferences:
            prefs_lower = intent.accommodation_preferences.lower()

            # Star rating preferences
            if "luxury" in prefs_lower or "5-star" in prefs_lower or "5 star" in prefs_lower:
                if hotel.star_rating and hotel.star_rating >= 4.5:
                    score += 20
            elif "4-star" in prefs_lower or "4 star" in prefs_lower:
                if hotel.star_rating and 3.5 <= hotel.star_rating < 4.5:
                    score += 20
            elif "budget" in prefs_lower or "cheap" in prefs_lower:
                if hotel.star_rating and hotel.star_rating <= 3:
                    score += 20

            # Amenity preferences
            hotel_amenities_lower = [a.lower() for a in hotel.amenities]
            if "pool" in prefs_lower and any("pool" in a for a in hotel_amenities_lower):
                score += 10
            if "gym" in prefs_lower and any("gym" in a or "fitness" in a for a in hotel_amenities_lower):
                score += 10
            if "spa" in prefs_lower and any("spa" in a for a in hotel_amenities_lower):
                score += 10
            if "beach" in prefs_lower and hotel.distance_to_center:
                # Simplified - would need actual beach proximity data
                score += 5

        return min(100, score)

    def calculate_quality_score(
        self,
        budget_option: BudgetOption
    ) -> float:
        """Calculate quality score based on ratings.

        Args:
            budget_option: Budget option to score

        Returns:
            Score from 0-100
        """
        hotel = budget_option.hotel
        flight = budget_option.flight_outbound

        score = 0

        # Hotel rating (0-5 scale)
        if hotel.rating:
            score += (hotel.rating / 5.0) * 50

        # Hotel star rating
        if hotel.star_rating:
            score += (hotel.star_rating / 5.0) * 30

        # Flight quality factors
        # Direct flights score higher
        if flight.stops == 0:
            score += 20
        elif flight.stops == 1:
            score += 10

        return min(100, score)

    def calculate_efficiency_score(
        self,
        budget_option: BudgetOption
    ) -> float:
        """Calculate efficiency score (time, convenience).

        Args:
            budget_option: Budget option to score

        Returns:
            Score from 0-100
        """
        score = 50.0  # Base score

        flight = budget_option.flight_outbound
        hotel = budget_option.hotel

        # Direct flights are more efficient
        if flight.stops == 0:
            score += 30
        elif flight.stops == 1:
            score += 15

        # Hotels closer to center are more efficient
        if hotel.distance_to_center:
            try:
                # Extract distance value
                distance_str = hotel.distance_to_center.lower()
                if "km" in distance_str:
                    distance = float(distance_str.replace("km", "").strip())
                    if distance <= 1:
                        score += 20
                    elif distance <= 3:
                        score += 10
            except:
                pass

        return min(100, score)

    def select_activities_for_option(
        self,
        budget_option: BudgetOption,
        all_activities: List[Activity],
        intent: TravelIntent,
        max_activities: int = 5
    ) -> List[Activity]:
        """Select relevant activities for this option.

        Args:
            budget_option: Budget option
            all_activities: All available activities
            intent: User's travel intent
            max_activities: Maximum number of activities to recommend

        Returns:
            List of recommended activities
        """
        # Filter activities by location
        hotel_location = budget_option.hotel.location.lower()
        relevant_activities = [
            a for a in all_activities
            if hotel_location in a.location.lower() or a.location.lower() in hotel_location
        ]

        # Score activities based on interest match
        scored_activities = []
        for activity in relevant_activities:
            score = 0

            # Match against user interests
            activity_cat_lower = activity.category.lower()
            activity_name_lower = activity.name.lower()
            activity_desc_lower = activity.description.lower()

            for interest in intent.interests:
                interest_lower = interest.lower()
                if interest_lower in activity_cat_lower:
                    score += 10
                if interest_lower in activity_name_lower:
                    score += 5
                if interest_lower in activity_desc_lower:
                    score += 3

            # Bonus for high ratings
            if activity.rating:
                score += activity.rating

            scored_activities.append((activity, score))

        # Sort by score and take top N
        scored_activities.sort(key=lambda x: x[1], reverse=True)
        return [a for a, s in scored_activities[:max_activities]]

    def generate_reasoning(
        self,
        rank: int,
        budget_score: float,
        preference_score: float,
        quality_score: float,
        efficiency_score: float,
        budget_option: BudgetOption
    ) -> str:
        """Generate human-readable reasoning for this ranking.

        Args:
            rank: Rank position
            budget_score: Budget score
            preference_score: Preference score
            quality_score: Quality score
            efficiency_score: Efficiency score
            budget_option: The budget option

        Returns:
            Reasoning string
        """
        reasons = []

        if budget_score >= 90:
            reasons.append("excellent budget fit")
        elif budget_score >= 70:
            reasons.append("good budget fit")

        if quality_score >= 80:
            reasons.append("high quality accommodations and flights")
        elif quality_score >= 60:
            reasons.append("good quality options")

        if efficiency_score >= 80:
            reasons.append("convenient direct flights and central location")
        elif efficiency_score >= 60:
            reasons.append("reasonably convenient travel")

        if preference_score >= 80:
            reasons.append("strong match with your preferences")

        if budget_option.flight_outbound.stops == 0:
            reasons.append("direct flights")

        if not reasons:
            reasons.append("balanced option across all criteria")

        return f"Ranked #{rank}: {', '.join(reasons)}. Total cost: ${budget_option.total_cost:.2f}"

    @traceable(name="rank_options")
    def rank_options(
        self,
        budget_options: List[BudgetOption],
        activities: List[Activity],
        intent: TravelIntent,
        max_options: int = 5
    ) -> List[RankedOption]:
        """Rank and score budget options.

        Args:
            budget_options: Available budget options
            activities: Available activities
            intent: User's travel intent
            max_options: Maximum options to return

        Returns:
            List of RankedOption objects, sorted by overall score
        """
        try:
            logger.info(f"Ranking {len(budget_options)} budget options")

            ranked_options = []

            for budget_option in budget_options:
                # Calculate individual scores
                budget_score = self.calculate_budget_score(budget_option)
                preference_score = self.calculate_preference_score(budget_option, intent)
                quality_score = self.calculate_quality_score(budget_option)
                efficiency_score = self.calculate_efficiency_score(budget_option)

                # Calculate weighted overall score
                overall_score = (
                    budget_score * 0.35 +      # 35% weight on budget
                    preference_score * 0.25 +  # 25% weight on preferences
                    quality_score * 0.25 +     # 25% weight on quality
                    efficiency_score * 0.15    # 15% weight on efficiency
                )

                # Select activities for this option
                recommended_activities = self.select_activities_for_option(
                    budget_option, activities, intent
                )

                # Create ranked option (rank will be assigned after sorting)
                ranked_option = RankedOption(
                    rank=0,  # Temporary, will be updated
                    budget_option=budget_option,
                    recommended_activities=recommended_activities,
                    overall_score=overall_score,
                    budget_score=budget_score,
                    preference_score=preference_score,
                    quality_score=quality_score,
                    efficiency_score=efficiency_score,
                    reasoning=""  # Will be generated after sorting
                )
                ranked_options.append(ranked_option)

            # Sort by overall score
            ranked_options.sort(key=lambda x: x.overall_score, reverse=True)

            # Assign ranks and generate reasoning
            for i, option in enumerate(ranked_options[:max_options], start=1):
                option.rank = i
                option.reasoning = self.generate_reasoning(
                    i,
                    option.budget_score,
                    option.preference_score,
                    option.quality_score,
                    option.efficiency_score,
                    option.budget_option
                )

            logger.info(f"Ranked top {min(len(ranked_options), max_options)} options")
            return ranked_options[:max_options]

        except Exception as e:
            logger.error(f"Error ranking options: {e}")
            return []

    @traceable(name="ranking_agent_run")
    def run(self, state: TravelPlanningState) -> TravelPlanningState:
        """Run the ranking agent as part of the orchestrated workflow.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with ranked options
        """
        if not state.travel_intent:
            logger.warning("No travel intent available, skipping ranking")
            state.completed_agents.append("ranking")
            return state

        if not state.budget_options:
            logger.warning("No budget options available, skipping ranking")
            state.completed_agents.append("ranking")
            return state

        ranked_options = self.rank_options(
            budget_options=state.budget_options,
            activities=state.activities,
            intent=state.travel_intent,
            max_options=5
        )

        state.ranked_options = ranked_options
        state.completed_agents.append("ranking")
        state.metadata["ranked_options_count"] = len(ranked_options)

        logger.info(f"Ranking agent completed. Ranked {len(ranked_options)} options")

        return state

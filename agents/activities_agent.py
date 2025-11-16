"""Activities Agent - Finds and recommends activities based on interests."""

import logging
import json
import re
from typing import List
from datetime import datetime
from langsmith import traceable
from langchain_core.prompts import ChatPromptTemplate

from config.llm_setup import get_llm
from models.travel_schemas import TravelPlanningState, Activity
from tools.travel_tools import search_activities

logger = logging.getLogger(__name__)


class ActivitiesAgent:
    """Agent responsible for finding and recommending activities."""

    def __init__(self, llm=None):
        """Initialize the activities agent.

        Args:
            llm: Language model to use. If None, uses default from config.
        """
        self.llm = llm or get_llm()
        self.search_tool = search_activities

    def _calculate_trip_days(self, timeframe: str) -> int:
        """Calculate the number of days in the trip from timeframe string.

        Args:
            timeframe: Timeframe string (e.g., "Dec 20-27", "1 week", "5 days")

        Returns:
            Number of days (defaults to 3 if cannot be determined)
        """
        try:
            # Check for explicit day mentions (e.g., "5 days", "1 week")
            days_match = re.search(r'(\d+)\s*days?', timeframe, re.IGNORECASE)
            if days_match:
                return int(days_match.group(1))

            weeks_match = re.search(r'(\d+)\s*weeks?', timeframe, re.IGNORECASE)
            if weeks_match:
                return int(weeks_match.group(1)) * 7

            # Try to parse date ranges (e.g., "Dec 20-27", "2025-12-20 to 2025-12-27")
            # Look for patterns like "Dec 20-27" or "20-27"
            date_range_match = re.search(r'(\d{1,2})-(\d{1,2})', timeframe)
            if date_range_match:
                start_day = int(date_range_match.group(1))
                end_day = int(date_range_match.group(2))
                return end_day - start_day + 1

            # Look for full date ranges like "2025-12-20 to 2025-12-27"
            full_date_match = re.findall(r'\d{4}-\d{2}-\d{2}', timeframe)
            if len(full_date_match) >= 2:
                start_date = datetime.strptime(full_date_match[0], '%Y-%m-%d')
                end_date = datetime.strptime(full_date_match[1], '%Y-%m-%d')
                return (end_date - start_date).days + 1

            logger.warning(f"Could not parse timeframe: {timeframe}, defaulting to 3 days")
            return 3

        except Exception as e:
            logger.error(f"Error calculating trip days: {e}")
            return 3  # Default to 3 days if parsing fails

    @traceable(name="search_and_parse_activities")
    def search_and_parse_activities(
        self,
        location: str,
        interests: List[str] = None,
        category: str = ""
    ) -> List[Activity]:
        """Search for activities and parse results into Activity objects.

        Args:
            location: City or area
            interests: List of user interests
            category: Activity category filter

        Returns:
            List of Activity objects
        """
        try:
            logger.info(f"Searching activities in {location} for interests: {interests}")

            # Format interests for search
            interests_str = ", ".join(interests) if interests else ""

            # Use the search tool to get Valyu results
            search_results_json = self.search_tool.invoke({
                "location": location,
                "interests": interests_str,
                "category": category
            })

            # Parse JSON response
            search_results = json.loads(search_results_json)

            if "error" in search_results:
                logger.error(f"Activity search error: {search_results['error']}")
                return []

            # Extract search results
            raw_results = search_results.get("search_results", [])

            if not raw_results:
                logger.warning("No activity search results found")
                return []

            # Use LLM to parse the search results into structured Activity objects
            activities = self._parse_with_llm(raw_results, location, interests or [])

            logger.info(f"Found and parsed {len(activities)} activities")
            return activities

        except Exception as e:
            logger.error(f"Error searching/parsing activities: {e}")
            return []

    def _parse_with_llm(
        self,
        search_results: List[dict],
        location: str,
        interests: List[str]
    ) -> List[Activity]:
        """Use LLM to parse Valyu search results into Activity objects.

        Args:
            search_results: Raw search results from Valyu
            location: Location/city
            interests: User interests

        Returns:
            List of Activity objects
        """
        try:
            # Create prompt for LLM to extract activity information
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a travel data extraction assistant. Extract activity and experience information from search results.

For each activity mentioned in the search results, extract:
- name: Activity name
- description: Brief description
- location: City/area
- category: Category (e.g., "museum", "food", "adventure", "culture", "nature")
- duration: Duration (e.g., "3 hours", "half day", "full day")
- price: Price in USD (as a number, 0 if free)
- rating: User rating out of 5 (can be decimal)
- booking_required: true/false
- booking_url: URL for booking (if available)

User interests: {interests}

Return a JSON array of activity objects. Prioritize activities that match the user's interests.
If you cannot extract all information, make reasonable estimates based on typical activities.

Return ONLY valid JSON, no additional text."""),
                ("user", """Search results:
{search_results}

Location: {location}

Extract activity information as JSON array.""")
            ])

            # Format search results for LLM
            formatted_results = "\n\n".join([
                f"Result {i+1}:\nTitle: {r.get('source_title', '')}\nURL: {r.get('source_url', '')}\nContent: {r.get('content_snippet', '')}"
                for i, r in enumerate(search_results[:5])  # Limit to top 5
            ])

            formatted_prompt = prompt.format_messages(
                search_results=formatted_results,
                location=location,
                interests=", ".join(interests) if interests else "General tourism"
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
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            activities_data = json.loads(content)

            # Create Activity objects
            activities = []
            for activity_data in activities_data:
                try:
                    activity = Activity(**activity_data)
                    activities.append(activity)
                except Exception as e:
                    logger.warning(f"Could not create Activity object: {e}")
                    continue

            return activities

        except Exception as e:
            logger.error(f"Error parsing activities with LLM: {e}")
            return []

    @traceable(name="activities_agent_run")
    def run(self, state: TravelPlanningState) -> TravelPlanningState:
        """Run the activities agent as part of the orchestrated workflow.

        Auto-recommends activities based on the formula: 2 * number_of_days activities total.
        If user suggests activities, the agent recommends (2*days - user_suggested) additional activities.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with activity recommendations
        """
        if not state.travel_intent:
            logger.warning("No travel intent available, skipping activity search")
            state.completed_agents.append("activities")
            return state

        intent = state.travel_intent

        # Calculate number of days from timeframe
        num_days = 3  # default
        if intent.timeframe:
            num_days = self._calculate_trip_days(intent.timeframe)

        # Calculate target number of activities: 2 * number_of_days
        target_activities = 2 * num_days

        # Count user-suggested activities
        user_suggested_count = len(intent.activities) if intent.activities else 0

        # Calculate how many activities to auto-recommend
        activities_to_recommend = max(0, target_activities - user_suggested_count)

        logger.info(
            f"Trip days: {num_days}, Target activities: {target_activities}, "
            f"User suggested: {user_suggested_count}, Auto-recommend: {activities_to_recommend}"
        )

        all_activities = []
        seen = set()  # Track duplicates early

        # Search activities for each destination
        for location in intent.locations:
            # If user mentioned specific activities, search for those first
            for specific_activity in intent.activities:
                specific_results = self.search_and_parse_activities(
                    location=location,
                    interests=[specific_activity],
                    category=""
                )
                # Add only unique activities
                for activity in specific_results:
                    key = (activity.name.lower(), activity.location.lower())
                    if key not in seen:
                        seen.add(key)
                        all_activities.append(activity)

            # Keep searching with different interests until we reach target
            # Search for general activities based on interests
            interest_combinations = [
                intent.interests,  # All interests
                [intent.interests[0]] if intent.interests else [],  # First interest
                [intent.interests[1]] if len(intent.interests) > 1 else [],  # Second interest
                ["popular", "top rated"],  # Fallback to popular activities
                ["tourist attractions"],  # Fallback to tourist attractions
            ]

            for interest_combo in interest_combinations:
                # Stop if we have enough activities
                if len(all_activities) >= target_activities:
                    break

                if not interest_combo:
                    continue

                activities = self.search_and_parse_activities(
                    location=location,
                    interests=interest_combo,
                    category=""
                )

                # Add unique activities
                for activity in activities:
                    key = (activity.name.lower(), activity.location.lower())
                    if key not in seen:
                        seen.add(key)
                        all_activities.append(activity)

                        # Stop if we've reached target
                        if len(all_activities) >= target_activities:
                            break

        # Take exactly target number of activities (or all if we have fewer)
        final_activities = all_activities[:target_activities]

        state.activities = final_activities
        state.completed_agents.append("activities")
        state.metadata["activities_found"] = len(final_activities)
        state.metadata["activities_target"] = target_activities
        state.metadata["user_suggested_activities"] = user_suggested_count
        state.metadata["auto_recommended_activities"] = len(final_activities) - user_suggested_count

        logger.info(
            f"Activities agent completed. Found {len(final_activities)} activities "
            f"(target: {target_activities})"
        )

        return state

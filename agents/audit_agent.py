"""Audit Agent - Validates and fixes issues in the final itinerary."""

import logging
from typing import List, Dict, Any
from langsmith import traceable

from models.travel_schemas import TravelPlanningState, Itinerary, Hotel, Flight, Activity

logger = logging.getLogger(__name__)


class AuditAgent:
    """Agent responsible for auditing and validating the final itinerary."""

    def __init__(self):
        """Initialize the audit agent."""
        self.issues_found = []
        self.fixes_applied = []
        self.critical_issues = []  # Issues that require re-processing
        self.issue_types = []  # Types of issues found for routing

        # Known booking site domains
        self.booking_domains = [
            'kayak.com', 'expedia.com', 'booking.com', 'hotels.com',
            'priceline.com', 'tripadvisor.com', 'skyscanner.com',
            'google.com/flights', 'airbnb.com', 'airfrance.com',
            'delta.com', 'united.com', 'american.com'
        ]

        # Known blog/article/non-booking domains to flag
        self.blog_domains = [
            'blog', 'article', 'guide', 'tips', 'post', 'news',
            'travel-guide', 'travelblog'
        ]

        # Non-legitimate booking sites to block
        self.blocked_domains = [
            'reddit.com', 'quora.com', 'tripadvisor.com/ShowTopic',  # Forums/discussions
            'facebook.com', 'instagram.com', 'twitter.com', 'x.com',  # Social media
            'youtube.com', 'tiktok.com', 'pinterest.com',  # Video/image sharing
            'medium.com', 'substack.com',  # Blog platforms
            '/forum/', '/forums/', '/discussion/',  # Forum paths
            'wikipedia.org', 'wikivoyage.org',  # Wikis
        ]

    def validate_rating(self, rating: float, field_name: str) -> float:
        """Validate and fix ratings to be within 0-5 range.

        Args:
            rating: Rating value to validate
            field_name: Name of the field for logging

        Returns:
            Fixed rating value (0-5)
        """
        if rating is None:
            return None

        if rating > 5.0:
            issue = f"{field_name} has invalid rating {rating}/5 (max is 5.0)"
            self.issues_found.append(issue)
            # Fix: Scale down proportionally if it looks like out of 10
            if rating <= 10.0:
                fixed = rating / 2.0
                self.fixes_applied.append(f"Scaled {field_name} from {rating}/10 to {fixed}/5")
                return fixed
            else:
                # Cap at 5.0
                self.fixes_applied.append(f"Capped {field_name} from {rating} to 5.0")
                return 5.0

        if rating < 0:
            issue = f"{field_name} has negative rating {rating}"
            self.issues_found.append(issue)
            self.fixes_applied.append(f"Set {field_name} to 0.0 (was {rating})")
            return 0.0

        return rating

    def validate_booking_url(self, url: str, item_type: str) -> tuple[str, bool]:
        """Validate that URL is from a booking site, not a blog.

        Args:
            url: URL to validate
            item_type: Type of item (flight/hotel/activity)

        Returns:
            Tuple of (url, is_valid)
        """
        if not url:
            return url, False

        url_lower = url.lower()

        # Check if it's a blog/article URL
        is_blog = any(domain in url_lower for domain in self.blog_domains)
        if is_blog:
            issue = f"{item_type} has blog/article URL instead of booking site: {url[:50]}..."
            self.issues_found.append(issue)
            return url, False

        # Accept any URL that isn't a blog (including lesser-known booking sites)
        # Just log a warning if it's not from a known major site
        is_booking_site = any(domain in url_lower for domain in self.booking_domains)
        if not is_booking_site:
            logger.info(f"{item_type} URL from non-major booking site (accepting anyway): {url[:70]}...")

        return url, True

    def validate_location(self, location: str, expected_location: str) -> tuple[str, bool]:
        """Validate location matches expected destination.

        Args:
            location: Actual location string
            expected_location: Expected location from user query

        Returns:
            Tuple of (corrected_location, is_valid)
        """
        location_lower = location.lower()
        expected_lower = expected_location.lower()

        # Check for common confusion: Paris, Texas vs Paris, France
        if "paris" in expected_lower and "paris" in location_lower:
            if "texas" in location_lower and "texas" not in expected_lower:
                issue = f"Location confusion: Found 'Paris, Texas' but user requested 'Paris' (likely Paris, France)"
                self.issues_found.append(issue)
                corrected = "Paris, France"
                self.fixes_applied.append(f"Corrected location from '{location}' to '{corrected}'")
                return corrected, False
            elif "france" in location_lower or ("paris" in location_lower and "texas" not in location_lower):
                return location, True

        # Check if location contains expected location
        if expected_lower in location_lower or location_lower in expected_lower:
            return location, True

        # Location mismatch - this is critical!
        issue = f"Location mismatch: Found '{location}' but expected '{expected_location}'"
        self.issues_found.append(issue)
        self.critical_issues.append(issue)
        self.issue_types.append("location_mismatch")
        return location, False

    def validate_price(self, price: float, item_name: str, max_reasonable: float = 10000) -> float:
        """Validate price is reasonable.

        Args:
            price: Price to validate
            item_name: Name of item for logging
            max_reasonable: Maximum reasonable price

        Returns:
            Fixed price value
        """
        if price is None:
            return None

        if price < 0:
            issue = f"{item_name} has negative price: ${price}"
            self.issues_found.append(issue)
            self.fixes_applied.append(f"Set {item_name} price to $0.00 (was ${price})")
            return 0.0

        if price > max_reasonable:
            issue = f"{item_name} has suspiciously high price: ${price}"
            self.issues_found.append(issue)
            # Don't auto-fix extreme prices, just flag them
            logger.warning(f"Price validation: {issue}")

        return price

    def validate_date_consistency(self, itinerary: Itinerary, auto_fix: bool = True) -> bool:
        """Validate dates are consistent across the itinerary.

        Args:
            itinerary: Itinerary to validate
            auto_fix: Whether to automatically fix date issues

        Returns:
            True if dates are consistent
        """
        issues = []
        from datetime import timedelta

        # Check flight arrival matches itinerary start
        flight = itinerary.budget_option.flight_outbound
        arrival_date = flight.arrival_time.split('T')[0] if 'T' in flight.arrival_time else flight.arrival_time

        # Allow some flexibility (flight might arrive day after departure)
        # Just log if there's a major discrepancy
        if arrival_date != itinerary.start_date:
            days_diff = abs((self._parse_date(arrival_date) - self._parse_date(itinerary.start_date)).days)
            if days_diff > 2:
                issue = f"Flight arrives {arrival_date} but itinerary starts {itinerary.start_date} ({days_diff} days difference)"
                issues.append(issue)

                # Mark as critical issue that needs re-processing
                self.critical_issues.append(issue)
                self.issue_types.append("date_consistency")

                # Attempt to auto-fix by adjusting itinerary dates to match flight
                if auto_fix:
                    try:
                        arrival_datetime = self._parse_date(arrival_date)
                        old_start = itinerary.start_date
                        old_end = itinerary.end_date

                        # Adjust start date to match flight arrival
                        itinerary.start_date = arrival_date

                        # Adjust end date to maintain same trip duration
                        old_duration = (self._parse_date(old_end) - self._parse_date(old_start)).days
                        new_end_datetime = arrival_datetime + timedelta(days=old_duration)
                        itinerary.end_date = new_end_datetime.strftime("%Y-%m-%d")

                        # Update daily plans dates
                        for i, day_plan in enumerate(itinerary.daily_plans):
                            new_day_date = arrival_datetime + timedelta(days=i)
                            day_plan.date = new_day_date.strftime("%Y-%m-%d")

                        fix_msg = f"Adjusted itinerary dates to match flight arrival: {old_start} → {itinerary.start_date}, {old_end} → {itinerary.end_date}"
                        self.fixes_applied.append(fix_msg)
                        logger.info(f"Auto-fixed date consistency: {fix_msg}")

                        # Remove from critical issues since we fixed it
                        self.critical_issues.remove(issue)
                        if "date_consistency" in self.issue_types:
                            self.issue_types.remove("date_consistency")

                        return True
                    except Exception as e:
                        logger.error(f"Failed to auto-fix date consistency: {e}")

        if issues:
            self.issues_found.extend(issues)
            return False

        return True

    def _parse_date(self, date_str: str):
        """Parse date string."""
        from datetime import datetime
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return datetime.now()

    @traceable(name="audit_itinerary")
    def audit_itinerary(self, itinerary: Itinerary, expected_location: str) -> Itinerary:
        """Audit and fix issues in the itinerary.

        Args:
            itinerary: Itinerary to audit
            expected_location: Expected destination from user query

        Returns:
            Fixed itinerary
        """
        logger.info("Auditing itinerary for errors and inconsistencies...")
        self.issues_found = []
        self.fixes_applied = []
        self.critical_issues = []
        self.issue_types = []

        # Validate hotel
        hotel = itinerary.budget_option.hotel

        # Check location
        corrected_location, is_valid = self.validate_location(hotel.location, expected_location)
        if not is_valid or corrected_location != hotel.location:
            hotel.location = corrected_location

        # Check ratings
        if hotel.rating:
            hotel.rating = self.validate_rating(hotel.rating, f"Hotel '{hotel.name}' rating")

        if hotel.star_rating:
            hotel.star_rating = self.validate_rating(hotel.star_rating, f"Hotel '{hotel.name}' star rating")

        # Check hotel booking URL
        if hotel.booking_url:
            _, is_valid_url = self.validate_booking_url(hotel.booking_url, f"Hotel '{hotel.name}'")
            if not is_valid_url:
                hotel.booking_url = None  # Remove invalid booking URL
                self.fixes_applied.append(f"Removed invalid booking URL for hotel '{hotel.name}'")

        # Validate prices
        hotel.price_per_night = self.validate_price(
            hotel.price_per_night,
            f"Hotel '{hotel.name}' price per night",
            max_reasonable=2000
        )

        # Validate flight
        flight = itinerary.budget_option.flight_outbound

        # Check booking URL
        if flight.booking_url:
            _, is_valid_url = self.validate_booking_url(flight.booking_url, f"Flight {flight.flight_number}")
            if not is_valid_url:
                flight.booking_url = None  # Remove invalid booking URL
                self.fixes_applied.append(f"Removed invalid booking URL for flight {flight.flight_number}")

        # Validate price
        flight.price = self.validate_price(
            flight.price,
            f"Flight {flight.flight_number}",
            max_reasonable=5000
        )

        # Validate activities
        for day_plan in itinerary.daily_plans:
            for activity in day_plan.activities:
                if activity.rating:
                    activity.rating = self.validate_rating(activity.rating, f"Activity '{activity.name}' rating")

                activity.price = self.validate_price(
                    activity.price,
                    f"Activity '{activity.name}'",
                    max_reasonable=1000
                )

        # Update destination in itinerary
        if corrected_location and corrected_location != itinerary.destinations[0]:
            itinerary.destinations = [corrected_location]

        # Update title if location was corrected
        if "Paris, Texas" in itinerary.title and "Paris, France" in corrected_location:
            itinerary.title = itinerary.title.replace("Paris, Texas", "Paris")
            self.fixes_applied.append("Updated itinerary title to remove 'Texas' reference")

        # Update all day plan locations
        for day_plan in itinerary.daily_plans:
            if "Paris, Texas" in (day_plan.notes or ""):
                day_plan.notes = day_plan.notes.replace("Paris, Texas", "Paris, France")

        # Validate date consistency
        self.validate_date_consistency(itinerary)

        # Log results
        if self.issues_found:
            logger.warning(f"Audit found {len(self.issues_found)} issues:")
            for issue in self.issues_found:
                logger.warning(f"  - {issue}")

        if self.fixes_applied:
            logger.info(f"Audit applied {len(self.fixes_applied)} fixes:")
            for fix in self.fixes_applied:
                logger.info(f"  ✓ {fix}")
        else:
            logger.info("Audit complete: No issues found")

        return itinerary

    @traceable(name="audit_agent_run")
    def run(self, state: TravelPlanningState) -> TravelPlanningState:
        """Run the audit agent as part of the orchestrated workflow.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with audited itinerary
        """
        if not state.final_itinerary:
            logger.warning("No itinerary to audit")
            state.completed_agents.append("audit")
            return state

        if not state.travel_intent or not state.travel_intent.locations:
            logger.warning("No expected location for validation")
            state.completed_agents.append("audit")
            return state

        expected_location = state.travel_intent.locations[0]

        # Audit the itinerary
        audited_itinerary = self.audit_itinerary(state.final_itinerary, expected_location)
        state.final_itinerary = audited_itinerary

        # Add audit metadata
        state.metadata["audit_issues_found"] = len(self.issues_found)
        state.metadata["audit_fixes_applied"] = len(self.fixes_applied)
        state.metadata["audit_issues"] = self.issues_found
        state.metadata["audit_fixes"] = self.fixes_applied
        state.metadata["critical_issues"] = self.critical_issues  # For routing decisions
        state.metadata["issue_types"] = self.issue_types  # For routing to correct agent

        state.completed_agents.append("audit")

        logger.info(f"Audit agent completed. Found {len(self.issues_found)} issues, applied {len(self.fixes_applied)} fixes")
        logger.info(f"Critical issues remaining: {len(self.critical_issues)}, Types: {set(self.issue_types)}")

        return state

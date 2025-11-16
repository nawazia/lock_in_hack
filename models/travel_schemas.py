"""Data models for the travel planning system."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import Enum


class TravelIntent(BaseModel):
    """User's travel intent extracted from conversation."""

    budget: Optional[str] = Field(None, description="Budget range (e.g., '$1000-2000', 'budget-friendly', 'luxury')")
    timeframe: Optional[str] = Field(None, description="Travel dates or duration (e.g., 'Dec 20-27', '1 week in January')")
    locations: List[str] = Field(default_factory=list, description="Destination cities/countries")
    interests: List[str] = Field(default_factory=list, description="User interests (e.g., 'food', 'adventure', 'culture')")
    activities: List[str] = Field(default_factory=list, description="Specific activities requested")
    travelers: Optional[int] = Field(1, description="Number of travelers")
    accommodation_preferences: Optional[str] = Field(None, description="Hotel preferences (e.g., 'near beach', '4-star')")

    class Config:
        json_schema_extra = {
            "example": {
                "budget": "$2000-3000",
                "timeframe": "Dec 20-27, 2025",
                "locations": ["Paris", "Rome"],
                "interests": ["art", "food", "history"],
                "activities": ["visit Louvre", "pasta making class"],
                "travelers": 2
            }
        }

    def is_complete(self) -> bool:
        """Check if all required fields are present for planning.

        Required fields:
        - Budget
        - Timeframe
        - Locations
        - Interests
        - Activities (optional but good to have)

        Returns:
            True if all required information is present
        """
        has_budget = bool(self.budget)
        has_timeframe = bool(self.timeframe)
        has_locations = bool(self.locations and len(self.locations) > 0)
        has_interests = bool(self.interests and len(self.interests) > 0)

        return has_budget and has_timeframe and has_locations and has_interests

    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields.

        Returns:
            List of field names that are missing or incomplete
        """
        missing = []

        if not self.budget:
            missing.append("budget")
        if not self.timeframe:
            missing.append("timeframe")
        if not self.locations or len(self.locations) == 0:
            missing.append("locations")
        if not self.interests or len(self.interests) == 0:
            missing.append("interests")

        return missing


class Flight(BaseModel):
    """Flight option."""

    airline: str
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    duration: str
    price: float
    currency: str = "USD"
    stops: int = 0
    booking_url: Optional[str] = None
    edfl_validation: Optional[Dict[str, Any]] = Field(None, description="EDFL hallucination detection metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "airline": "United Airlines",
                "flight_number": "UA123",
                "departure_airport": "JFK",
                "arrival_airport": "CDG",
                "departure_time": "2025-12-20T18:00:00",
                "arrival_time": "2025-12-21T08:00:00",
                "duration": "7h 30m",
                "price": 650.00,
                "stops": 0
            }
        }


class Hotel(BaseModel):
    """Hotel option."""

    name: str
    location: str
    address: Optional[str] = None
    star_rating: Optional[float] = None
    price_per_night: float
    currency: str = "USD"
    amenities: List[str] = Field(default_factory=list)
    distance_to_center: Optional[str] = None
    rating: Optional[float] = None  # User rating (e.g., 4.5/5)
    booking_url: Optional[str] = None
    edfl_validation: Optional[Dict[str, Any]] = Field(None, description="EDFL hallucination detection metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Hotel Le Marais",
                "location": "Paris",
                "star_rating": 4,
                "price_per_night": 180.00,
                "amenities": ["WiFi", "Breakfast", "Air Conditioning"],
                "rating": 4.5
            }
        }


class Activity(BaseModel):
    """Activity or experience option."""

    name: str
    description: str
    location: str
    category: str  # e.g., "museum", "food tour", "adventure"
    duration: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    rating: Optional[float] = None
    booking_required: bool = False
    booking_url: Optional[str] = None
    edfl_validation: Optional[Dict[str, Any]] = Field(None, description="EDFL hallucination detection metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Louvre Museum Tour",
                "description": "3-hour guided tour of the Louvre",
                "location": "Paris",
                "category": "museum",
                "duration": "3 hours",
                "price": 65.00,
                "rating": 4.8
            }
        }


class BudgetOption(BaseModel):
    """Matched flight + hotel option within budget."""

    flight_outbound: Flight
    flight_return: Optional[Flight] = None
    hotel: Hotel
    total_cost: float
    nights: int
    budget_fit_score: float  # 0-1 score for how well it fits budget

    class Config:
        json_schema_extra = {
            "example": {
                "total_cost": 2100.00,
                "nights": 5,
                "budget_fit_score": 0.95
            }
        }


class RankedOption(BaseModel):
    """A ranked travel option bundle."""

    rank: int
    budget_option: BudgetOption
    recommended_activities: List[Activity]
    overall_score: float  # Combined score (0-100)
    budget_score: float
    preference_score: float
    quality_score: float
    efficiency_score: float
    reasoning: str  # Why this option is ranked here

    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "overall_score": 92.5,
                "reasoning": "Best balance of price, quality, and alignment with cultural interests"
            }
        }


class DayPlan(BaseModel):
    """Plan for a single day."""

    day_number: int
    date: str
    activities: List[Activity]
    accommodation: Optional[str] = None
    notes: Optional[str] = None
    estimated_cost: float = 0.0


class Itinerary(BaseModel):
    """Complete travel itinerary."""

    title: str
    destinations: List[str]
    start_date: str
    end_date: str
    total_days: int
    budget_option: BudgetOption
    daily_plans: List[DayPlan]
    total_estimated_cost: float
    packing_suggestions: List[str] = Field(default_factory=list)
    travel_tips: List[str] = Field(default_factory=list)
    edfl_validation: Optional[Dict[str, Any]] = Field(None, description="EDFL hallucination detection metrics")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "7-Day Paris Cultural Experience",
                "destinations": ["Paris"],
                "start_date": "2025-12-20",
                "end_date": "2025-12-27",
                "total_days": 7,
                "total_estimated_cost": 2450.00
            }
        }


class TravelPlanningState(BaseModel):
    """State shared across all agents in the travel planning orchestration."""

    # User input
    user_query: str = Field(..., description="Original user request")
    travel_intent: Optional[TravelIntent] = Field(None, description="Extracted travel intent")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="User-agent conversation history")
    user_responses: Dict[str, str] = Field(default_factory=dict, description="User responses to questions")

    # Agent outputs
    flights: List[Flight] = Field(default_factory=list)
    hotels: List[Hotel] = Field(default_factory=list)
    budget_options: List[BudgetOption] = Field(default_factory=list)
    activities: List[Activity] = Field(default_factory=list)
    ranked_options: List[RankedOption] = Field(default_factory=list)
    final_itinerary: Optional[Itinerary] = None

    # Orchestration metadata
    next_agent: Optional[str] = Field(None, description="Which agent to call next")
    completed_agents: List[str] = Field(default_factory=list, description="Agents that have completed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    clarifying_questions: List[str] = Field(default_factory=list, description="Questions for user")
    needs_user_input: bool = Field(False, description="Whether system is waiting for user input")

    class Config:
        arbitrary_types_allowed = True

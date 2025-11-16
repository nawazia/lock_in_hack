# Multi-Agent Travel Planning System

A sophisticated multi-agent system built with LangChain, LangGraph, and Valyu Search that creates personalized travel itineraries through an orchestrated workflow of specialized agents.

## 🏗️ Architecture

The system consists of 8 specialized agents orchestrated via LangGraph:

```
User Travel Query
    ↓
┌──────────────────────────────────────────────────────────────┐
│             Travel Orchestrator (LangGraph)                  │
└──────────────────────────────────────────────────────────────┘
    ↓
┌──────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│Interface │ → │ Flight │ → │ Hotel  │ → │ Budget │
│  Agent   │   │ Agent  │   │ Agent  │   │ Agent  │
└──────────┘   └────────┘   └────────┘   └────────┘
                                              ↓
┌────────────┐   ┌────────┐   ┌────────┐
│ Activities │ → │Ranking │ → │Itinerary│
│   Agent    │   │ Agent  │   │  Agent  │
└────────────┘   └────────┘   └────────┘
```

### Agent Responsibilities

1. **Interface Agent** (`interface_agent.py`)
   - Extracts structured travel intent from natural language
   - Identifies: budget, timeframe, locations, interests, activities, travelers
   - Generates clarifying questions for missing information
   - Uses LLM to parse user requests into `TravelIntent` schema

2. **Flight Agent** (`flight_agent.py`)
   - Searches for flights using Valyu real-time search
   - Parses search results into structured `Flight` objects
   - Uses LLM to extract flight details from web results
   - Handles multiple destinations and passenger counts

3. **Hotel Agent** (`hotel_agent.py`)
   - Searches for hotels using Valyu real-time search
   - Extracts hotel information: ratings, prices, amenities
   - Considers user accommodation preferences
   - Uses LLM to structure search results

4. **Budget Agent** (`budget_agent.py`)
   - Matches flight + hotel combinations within budget
   - Parses budget constraints (numeric ranges or text like "luxury")
   - Calculates total costs including all travelers
   - Scores each option by budget fit (0-1 scale)

5. **Activities Agent** (`activities_agent.py`)
   - Searches for activities based on user interests
   - Uses Valyu to find tours, experiences, restaurants
   - Matches activities to user's interest categories
   - Provides pricing and booking information

6. **Ranking Agent** (`ranking_agent.py`)
   - Scores each option across 4 dimensions:
     - **Budget Score** (35% weight): How well it fits budget
     - **Preference Score** (25% weight): Match with user preferences
     - **Quality Score** (25% weight): Ratings and star ratings
     - **Efficiency Score** (15% weight): Direct flights, central location
   - Calculates overall weighted score (0-100)
   - Selects relevant activities for each option
   - Generates human-readable reasoning

7. **Itinerary Agent** (`itinerary_agent.py`)
   - Creates detailed day-by-day itinerary
   - Distributes activities across travel days
   - Generates packing suggestions based on activities
   - Provides travel tips for the destination
   - Includes arrival/departure logistics

8. **Travel Orchestrator** (`travel_orchestrator.py`)
   - Coordinates all agents using LangGraph
   - Manages state flow through the pipeline
   - Handles errors gracefully
   - Formats final itinerary output

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Valyu API key (for real-time search)
- LLM provider API key (OpenAI, OpenRouter, or AWS Bedrock)

### Installation

1. Navigate to the project:
```bash
cd lock_in_hack
```

2. Create and activate conda environment:
```bash
conda create -n travel-agent python=3.10
conda activate travel-agent
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```
VALYU_API_KEY=your-valyu-api-key
LLM_PROVIDER=bedrock  # or openai, openrouter

# If using AWS Bedrock:
TEAM_ID=your-team-id
API_TOKEN=your-api-token
API_ENDPOINT=your-bedrock-endpoint

# If using OpenAI:
OPENAI_API_KEY=sk-...

# Optional LangSmith tracing:
LANGSMITH_ENABLED=true
LANGSMITH_API_KEY=ls-...
LANGSMITH_PROJECT=travel-planning
```

### Usage

#### Run the Example

```bash
python travel_example.py
```

This will process a sample travel query and generate a complete itinerary.

#### Programmatic Usage

```python
from agents.travel_orchestrator import TravelOrchestrator

# Initialize orchestrator
orchestrator = TravelOrchestrator()

# Process a travel query
query = """
I want to visit Tokyo for 5 days in March.
Budget is $3000. Interested in food, culture, and technology.
Looking for a modern hotel in Shibuya.
"""

result = orchestrator.process_query(query)

# Get formatted itinerary
itinerary = orchestrator.format_itinerary_output(result)
print(itinerary)

# Access structured data
final_itinerary = result["final_itinerary"]
ranked_options = result["ranked_options"]
```

## 📁 Project Structure

```
lock_in_hack/
├── agents/
│   ├── interface_agent.py       # Intent extraction
│   ├── flight_agent.py          # Flight search
│   ├── hotel_agent.py           # Hotel search
│   ├── budget_agent.py          # Budget matching
│   ├── activities_agent.py      # Activity recommendations
│   ├── ranking_agent.py         # Option scoring
│   ├── itinerary_agent.py       # Itinerary creation
│   └── travel_orchestrator.py   # LangGraph orchestration
├── models/
│   └── travel_schemas.py        # Pydantic data models
├── tools/
│   └── travel_tools.py          # Valyu search tools
├── config/
│   └── llm_setup.py             # LLM configuration
├── utils/
│   └── langsmith_setup.py       # Tracing setup
├── travel_example.py            # Example usage
├── TRAVEL_README.md             # This file
└── requirements.txt
```

## 📊 Data Models

### TravelIntent
```python
class TravelIntent(BaseModel):
    budget: Optional[str]                    # "$2000-3000", "luxury"
    timeframe: Optional[str]                 # "Dec 20-27", "1 week"
    locations: List[str]                     # ["Paris", "Rome"]
    interests: List[str]                     # ["food", "art", "history"]
    activities: List[str]                    # ["visit Louvre"]
    travelers: Optional[int] = 1
    accommodation_preferences: Optional[str] # "4-star", "near beach"
```

### Flight
```python
class Flight(BaseModel):
    airline: str
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    duration: str
    price: float
    stops: int = 0
    booking_url: Optional[str]
```

### Hotel
```python
class Hotel(BaseModel):
    name: str
    location: str
    star_rating: Optional[float]
    price_per_night: float
    amenities: List[str]
    distance_to_center: Optional[str]
    rating: Optional[float]
    booking_url: Optional[str]
```

### RankedOption
```python
class RankedOption(BaseModel):
    rank: int
    budget_option: BudgetOption
    recommended_activities: List[Activity]
    overall_score: float              # 0-100
    budget_score: float               # 35% weight
    preference_score: float           # 25% weight
    quality_score: float              # 25% weight
    efficiency_score: float           # 15% weight
    reasoning: str
```

### Itinerary
```python
class Itinerary(BaseModel):
    title: str
    destinations: List[str]
    start_date: str
    end_date: str
    total_days: int
    budget_option: BudgetOption
    daily_plans: List[DayPlan]
    total_estimated_cost: float
    packing_suggestions: List[str]
    travel_tips: List[str]
```

## 🎯 Key Features

### Real-Time Search with Valyu
- All flight, hotel, and activity searches use Valyu's real-time web search
- No mock data - real booking information from the web
- Intelligent parsing of search results using LLMs

### Multi-Criteria Ranking
- Budget fit (35%): How well option fits your budget
- Preferences (25%): Match with accommodation preferences
- Quality (25%): Ratings, reviews, star ratings
- Efficiency (15%): Direct flights, central locations

### Intelligent Activity Matching
- Matches activities to your specific interests
- Considers mentioned activities explicitly
- Filters by location and category
- Includes pricing and booking information

### Complete Itinerary Generation
- Day-by-day planning
- Activity distribution across days
- Arrival and departure logistics
- Packing suggestions based on activities
- Destination-specific travel tips

### LangSmith Tracing
- Full observability of agent pipeline
- Track each agent's execution
- Debug and optimize workflows
- Monitor performance

## 🔧 Advanced Configuration

### Customize Ranking Weights

Edit `ranking_agent.py`:
```python
overall_score = (
    budget_score * 0.40 +      # Increase budget importance
    preference_score * 0.30 +  # Increase preference weight
    quality_score * 0.20 +
    efficiency_score * 0.10
)
```

### Add Custom Activity Categories

Edit `activities_agent.py` to add new categories:
```python
category_keywords = {
    "adventure": ["hiking", "climbing", "rafting"],
    "wellness": ["spa", "yoga", "meditation"],
    "nightlife": ["bars", "clubs", "entertainment"]
}
```

### Integrate Real Booking APIs

Replace Valyu search in `travel_tools.py` with APIs:
- **Amadeus** for flights and hotels
- **Skyscanner** for flight comparison
- **Booking.com** API for hotels
- **GetYourGuide** for activities

## 📈 Example Output

```
================================================================================
  7-Day Paris Cultural Experience
================================================================================

Dates: 2025-12-20 to 2025-12-27
Duration: 7 days
Destinations: Paris
Total Estimated Cost: $2,450.00

FLIGHT:
  Air France AF789
  JFK -> CDG
  Departure: 2025-12-20T18:00:00
  Price: $720.00

ACCOMMODATION:
  Grand Hotel Central
  Location: Paris
  Rating: 4.5 / 5
  Price per night: $180.00

DAILY ITINERARY:

Day 1 - 2025-12-20
  Arrival day - Flight AF789 arrives at 2025-12-21T08:00:00

Day 2 - 2025-12-21
  Full day in Paris
  Activities:
    • Louvre Museum Tour ($65.00)
      3-hour guided tour of the Louvre...
    • Food Walking Tour ($85.00)
      Taste local cuisine at 5 authentic restaurants...

...

PACKING SUGGESTIONS:
  • Passport and travel documents
  • Comfortable walking shoes
  • Clothing for 7 days
  • Semi-formal attire for dining

TRAVEL TIPS:
  • Research local customs and etiquette in Paris
  • Book popular activities in advance
  • Download offline maps of the area

================================================================================
```

## 🚧 Future Enhancements

- [ ] Multi-city itineraries with optimal routing
- [ ] Return flight booking
- [ ] Real-time price tracking
- [ ] Weather-aware activity suggestions
- [ ] Budget optimization algorithms
- [ ] Collaborative planning for groups
- [ ] Web UI with Streamlit
- [ ] PDF itinerary export

## 🙏 Acknowledgments

- **Valyu** for real-time search capabilities
- **LangChain** for agent framework
- **LangGraph** for workflow orchestration
- **OpenAI/Anthropic** for LLM capabilities

"""Interface Agent - Extracts user travel intent from natural language."""

import logging
from typing import Optional
from langsmith import traceable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.llm_setup import get_llm
from models.travel_schemas import TravelIntent, TravelPlanningState

logger = logging.getLogger(__name__)


class InterfaceAgent:
    """Agent responsible for extracting structured travel intent from user queries."""

    def __init__(self, llm=None):
        """Initialize the interface agent.

        Args:
            llm: Language model to use. If None, uses default from config.
        """
        self.llm = llm or get_llm()
        self.parser = JsonOutputParser(pydantic_object=TravelIntent)

    @traceable(name="extract_travel_intent")
    def extract_intent(self, user_query: str, existing_intent: Optional[TravelIntent] = None,
                      conversation_history: list = None) -> TravelIntent:
        """Extract structured travel intent from user's natural language query.

        Args:
            user_query: User's travel request in natural language
            existing_intent: Previously extracted intent to merge with
            conversation_history: Previous conversation context

        Returns:
            TravelIntent object with extracted information
        """
        try:
            logger.info(f"Extracting travel intent from query: {user_query}")

            # Build context from conversation history
            context = ""
            if conversation_history:
                context = "\n\nPrevious conversation:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages for context
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    context += f"{role}: {content}\n"

            # If we have existing intent, include it in the prompt
            existing_info = ""
            if existing_intent:
                existing_info = f"\n\nAlready collected information:\n"
                if existing_intent.budget:
                    existing_info += f"- Budget: {existing_intent.budget}\n"
                if existing_intent.timeframe:
                    existing_info += f"- Timeframe: {existing_intent.timeframe}\n"
                if existing_intent.locations:
                    existing_info += f"- Locations: {', '.join(existing_intent.locations)}\n"
                if existing_intent.interests:
                    existing_info += f"- Interests: {', '.join(existing_intent.interests)}\n"
                if existing_intent.activities:
                    existing_info += f"- Activities: {', '.join(existing_intent.activities)}\n"

            # Create prompt template for intent extraction
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are a travel planning assistant that extracts structured information from user queries.

Extract the following information from the user's travel request:
- budget: Budget range or constraints (e.g., "$1000-2000", "budget-friendly", "luxury")
- timeframe: Travel dates or duration (e.g., "Dec 20-27", "1 week in January", "next summer")
- locations: List of destination cities or countries
- interests: List of user interests (e.g., "food", "adventure", "culture", "history", "beaches")
- activities: Specific activities mentioned (e.g., "visit Eiffel Tower", "scuba diving")
- travelers: Number of travelers (default: 1)
- accommodation_preferences: Hotel preferences (e.g., "near beach", "4-star", "boutique hotels")

{existing_info}

IMPORTANT: Merge any new information from the current message with the existing information above.
If the user provides an answer to a specific question, update that field accordingly.
{context}

Return the information as a JSON object. If information is not mentioned, use null or empty list.

{{format_instructions}}"""),
                ("user", "{query}")
            ])

            # Format the prompt
            formatted_prompt = prompt.format_messages(
                query=user_query,
                format_instructions=self.parser.get_format_instructions()
            )

            # Convert messages to string for base LLM classes
            from langchain_core.language_models import BaseChatModel
            if isinstance(self.llm, BaseChatModel):
                # Chat model - can use messages directly
                response = self.llm.invoke(formatted_prompt)
            else:
                # Base LLM - needs string prompt
                prompt_string = "\n".join([
                    f"{msg.type}: {msg.content}" if hasattr(msg, 'type') else str(msg)
                    for msg in formatted_prompt
                ])
                response = self.llm.invoke(prompt_string)

            # Parse the response
            if hasattr(response, 'content'):
                parsed_data = self.parser.parse(response.content)
            else:
                parsed_data = self.parser.parse(str(response))

            # Create TravelIntent object
            travel_intent = TravelIntent(**parsed_data)

            logger.info(f"Successfully extracted travel intent: {travel_intent}")
            return travel_intent

        except Exception as e:
            logger.error(f"Error extracting travel intent: {e}")
            # Return existing intent or minimal intent on error
            if existing_intent:
                return existing_intent
            return TravelIntent(
                locations=[],
                interests=[],
                activities=[]
            )

    @traceable(name="generate_clarifying_questions")
    def generate_clarifying_questions(self, intent: TravelIntent) -> list[str]:
        """Generate clarifying questions for missing or ambiguous information.

        Args:
            intent: Current TravelIntent object

        Returns:
            List of clarifying questions
        """
        questions = []

        try:
            logger.info("Generating clarifying questions")

            # Get missing fields from the intent
            missing_fields = intent.get_missing_fields()

            # Generate specific questions for each missing field
            for field in missing_fields:
                if field == "budget":
                    questions.append("What is your budget for this trip? (e.g., $2000-3000, budget-friendly, luxury)")
                elif field == "timeframe":
                    questions.append("When are you planning to travel? Please provide dates or duration (e.g., Dec 20-27, 1 week in January)")
                elif field == "locations":
                    questions.append("Where would you like to travel to? Please specify city/cities or country/countries.")
                elif field == "interests":
                    questions.append("What are your main interests for this trip? (e.g., food, culture, adventure, relaxation, history, nature)")

            # Additional questions for optional but useful fields
            if not intent.travelers or intent.travelers == 0:
                questions.append("How many people will be traveling?")

            if intent.locations and not intent.accommodation_preferences:
                questions.append("Do you have any hotel preferences? (e.g., near city center, 4-star, boutique)")

            logger.info(f"Generated {len(questions)} clarifying questions for missing fields: {missing_fields}")
            return questions

        except Exception as e:
            logger.error(f"Error generating clarifying questions: {e}")
            return []

    @traceable(name="interface_agent_run")
    def run(self, state: TravelPlanningState) -> TravelPlanningState:
        """Run the interface agent as part of the orchestrated workflow.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with extracted travel intent and clarifying questions
        """
        # Extract travel intent from user query, merging with existing intent if available
        intent = self.extract_intent(
            state.user_query,
            existing_intent=state.travel_intent,
            conversation_history=state.conversation_history
        )
        state.travel_intent = intent

        # Add current query to conversation history
        state.conversation_history.append({
            "role": "user",
            "content": state.user_query
        })

        # Check if intent is complete
        if intent.is_complete():
            # All required information collected
            state.needs_user_input = False
            state.clarifying_questions = []
            state.metadata["intent_complete"] = True
            state.metadata["missing_fields"] = []

            # Add confirmation message to conversation
            state.conversation_history.append({
                "role": "assistant",
                "content": "Great! I have all the information needed. Let me start planning your trip..."
            })

            logger.info(f"Interface agent completed. Intent is COMPLETE: {intent}")

        else:
            # Generate clarifying questions for missing information
            questions = self.generate_clarifying_questions(intent)
            state.clarifying_questions = questions
            state.needs_user_input = True
            state.metadata["intent_complete"] = False
            state.metadata["missing_fields"] = intent.get_missing_fields()

            # Add questions to conversation history
            questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
            state.conversation_history.append({
                "role": "assistant",
                "content": f"I need some more information to plan your trip:\n{questions_text}"
            })

            logger.info(f"Interface agent waiting for input. Missing fields: {intent.get_missing_fields()}")

        # Mark this agent as completed (or re-run if needed)
        if "interface" not in state.completed_agents:
            state.completed_agents.append("interface")

        # Add metadata
        state.metadata["intent_extraction_complete"] = True

        return state

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
    def extract_intent(self, user_query: str) -> TravelIntent:
        """Extract structured travel intent from user's natural language query.

        Args:
            user_query: User's travel request in natural language

        Returns:
            TravelIntent object with extracted information
        """
        try:
            logger.info(f"Extracting travel intent from query: {user_query}")

            # Create prompt template for intent extraction
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a travel planning assistant that extracts structured information from user queries.

Extract the following information from the user's travel request:
- budget: Budget range or constraints (e.g., "$1000-2000", "budget-friendly", "luxury")
- timeframe: Travel dates or duration (e.g., "Dec 20-27", "1 week in January", "next summer")
- locations: List of destination cities or countries
- interests: List of user interests (e.g., "food", "adventure", "culture", "history", "beaches")
- activities: Specific activities mentioned (e.g., "visit Eiffel Tower", "scuba diving")
- travelers: Number of travelers (default: 1)
- accommodation_preferences: Hotel preferences (e.g., "near beach", "4-star", "boutique hotels")

Return the information as a JSON object. If information is not mentioned, use null or empty list.

{format_instructions}"""),
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
            # Return minimal intent on error
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

            # Check for missing critical information
            if not intent.locations or len(intent.locations) == 0:
                questions.append("Where would you like to travel to?")

            if not intent.timeframe:
                questions.append("When are you planning to travel? (dates or duration)")

            if not intent.budget:
                questions.append("What is your budget for this trip?")

            if not intent.travelers or intent.travelers == 0:
                questions.append("How many people will be traveling?")

            # Ask about interests if none provided and locations are specified
            if intent.locations and (not intent.interests or len(intent.interests) == 0):
                questions.append("What are your main interests for this trip? (e.g., food, culture, adventure, relaxation)")

            logger.info(f"Generated {len(questions)} clarifying questions")
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
        # Extract travel intent from user query
        intent = self.extract_intent(state.user_query)
        state.travel_intent = intent

        # Generate clarifying questions if needed
        questions = self.generate_clarifying_questions(intent)
        state.clarifying_questions = questions

        # Mark this agent as completed
        state.completed_agents.append("interface")

        # Add metadata
        state.metadata["intent_extraction_complete"] = True
        state.metadata["needs_clarification"] = len(questions) > 0

        logger.info(f"Interface agent completed. Intent: {intent}, Questions: {len(questions)}")

        return state

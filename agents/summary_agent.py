"""Summary Agent - Generates comprehensive summaries of news articles."""
import logging
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from models.schemas import NewsArticle, AgentState
from config.llm_setup import get_llm

logger = logging.getLogger(__name__)


class SummaryAgent:
    """Agent responsible for generating intelligent summaries of news articles."""

    def __init__(self, llm=None):
        """Initialize the summary agent.

        Args:
            llm: Language model to use. If None, uses configured provider from LLM_PROVIDER env var.
        """
        self.llm = llm or get_llm()
        self.chain = self._create_summary_chain()

    def _create_summary_chain(self):
        """Create the summary generation chain using LCEL."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert news summarizer and analyst. Your job is to create comprehensive,
insightful summaries of news articles that are:

1. **Accurate**: Stick to the facts presented in the articles
2. **Comprehensive**: Cover all key points and perspectives
3. **Clear**: Write in clear, professional language
4. **Contextual**: Provide relevant context and background
5. **Balanced**: Present multiple viewpoints when they exist
6. **Actionable**: Highlight key takeaways and implications

Structure your summary with:
- **Executive Summary**: Brief 2-3 sentence overview
- **Key Points**: Main findings and developments
- **Analysis**: Deeper insights and implications
- **Context**: Relevant background information
- **Outlook**: Future implications or expected developments (if applicable)
- **Sources**: List the articles used

Use markdown formatting for readability."""),
            ("human", """User Query: {query}

Analysis Context:
{analysis}

Selected Articles to Summarize:
{articles}

Please create a comprehensive summary that addresses the user's query."""),
        ])

        parser = StrOutputParser()
        chain = prompt | self.llm | parser
        return chain

    def _format_articles(self, articles: List[NewsArticle]) -> str:
        """Format articles for the summary prompt."""
        if not articles:
            return "No articles available for summary."

        formatted = []
        for i, article in enumerate(articles, 1):
            formatted.append(f"""
{'='*60}
Article {i}: {article.title}
Source: {article.source}
URL: {article.url}
{'='*60}

{article.content}
""")
        return "\n".join(formatted)

    def generate_summary(
        self,
        query: str,
        articles: List[NewsArticle],
        analysis: Optional[str] = None
    ) -> str:
        """Generate a comprehensive summary of the articles.

        Args:
            query: User's original query
            articles: Articles to summarize
            analysis: Optional analysis context

        Returns:
            Formatted summary text
        """
        try:
            logger.info(f"Generating summary for {len(articles)} articles...")

            if not articles:
                return "No articles available to summarize. Please try a different search query."

            # Format articles for the prompt
            articles_formatted = self._format_articles(articles)

            # Run the summary chain
            summary = self.chain.invoke({
                "query": query,
                "analysis": analysis or "No analysis available.",
                "articles": articles_formatted
            })

            logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Return a simple fallback summary
            fallback = f"""# Summary Generation Error

An error occurred while generating the summary: {str(e)}

## Available Articles

"""
            for article in articles[:3]:
                fallback += f"- **{article.title}**\n  {article.url}\n\n"

            return fallback

    def generate_brief_summary(
        self,
        query: str,
        articles: List[NewsArticle]
    ) -> str:
        """Generate a brief, concise summary.

        Args:
            query: User's original query
            articles: Articles to summarize

        Returns:
            Brief summary text
        """
        # Create a modified prompt for brief summaries
        brief_prompt = ChatPromptTemplate.from_messages([
            ("system", """Create a concise 3-5 sentence summary of the key information from these articles.
Focus on the most important facts and findings relevant to the user's query."""),
            ("human", "Query: {query}\n\nArticles:\n{articles}")
        ])

        brief_chain = brief_prompt | self.llm | StrOutputParser()

        try:
            articles_formatted = self._format_articles(articles)
            summary = brief_chain.invoke({
                "query": query,
                "articles": articles_formatted
            })
            return summary
        except Exception as e:
            logger.error(f"Error generating brief summary: {e}")
            return f"Error generating summary: {str(e)}"

    def run(self, state: AgentState) -> AgentState:
        """Run the summary agent as part of the orchestrated workflow.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with summary
        """
        # Get selected articles from analysis metadata
        selected_articles = state.metadata.get("selected_articles", [])

        # If no articles were selected, use search results
        if not selected_articles:
            logger.warning("No articles selected by analysis, using all search results")
            selected_articles = state.search_results[:5]

        # Generate comprehensive summary
        summary = self.generate_summary(
            query=state.user_query,
            articles=selected_articles,
            analysis=state.analysis
        )

        state.summary = summary
        state.completed_agents.append("summary")

        return state

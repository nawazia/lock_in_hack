"""News Search Agent - Searches for news using Valyu."""
import logging
from typing import List, Dict, Any

from tools.agent_tools import valyu_search_tool
from models.schemas import NewsArticle, AgentState
from config.llm_setup import get_llm_openai

logger = logging.getLogger(__name__)


class NewsSearchAgent:
    """Agent responsible for searching news using Valyu API."""

    def __init__(self, llm=None):
        """Initialize the news search agent.

        Args:
            llm: Language model to use. If None, uses default OpenAI model.
        """
        self.llm = llm or get_llm_openai()
        self.search_tool = valyu_search_tool

    def search(self, query: str) -> List[NewsArticle]:
        """Search for news articles based on query.

        Args:
            query: Search query string

        Returns:
            List of NewsArticle objects
        """
        try:
            logger.info(f"Searching for news: {query}")

            # Directly invoke the search tool
            result = self.search_tool.invoke(query)

            # Parse the output and structure it
            articles = self._parse_search_results(result, query)
            logger.info(f"Found {len(articles)} articles")
            return articles

        except Exception as e:
            logger.error(f"Error searching news: {e}")
            return []

    def _parse_search_results(self, output: str, query: str) -> List[NewsArticle]:
        """Parse the agent's output into structured NewsArticle objects.

        Args:
            output: Raw output from the agent
            query: Original search query

        Returns:
            List of NewsArticle objects
        """
        articles = []

        # Simple parsing - looks for Result N: patterns
        # This could be made more robust with regex or structured output
        lines = output.split('\n')
        current_article = {}

        for line in lines:
            line = line.strip()
            if line.startswith("Result "):
                if current_article:
                    # Save previous article
                    if 'title' in current_article:
                        articles.append(NewsArticle(
                            title=current_article.get('title', 'Unknown'),
                            url=current_article.get('url', ''),
                            content=current_article.get('content', ''),
                            query=query
                        ))
                current_article = {}
            elif line.startswith("Title:"):
                current_article['title'] = line.replace("Title:", "").strip()
            elif line.startswith("URL:"):
                current_article['url'] = line.replace("URL:", "").strip()
            elif line.startswith("Content snippet:"):
                current_article['content'] = line.replace("Content snippet:", "").strip()

        # Don't forget the last article
        if current_article and 'title' in current_article:
            articles.append(NewsArticle(
                title=current_article.get('title', 'Unknown'),
                url=current_article.get('url', ''),
                content=current_article.get('content', ''),
                query=query
            ))

        return articles

    def run(self, state: AgentState) -> AgentState:
        """Run the news search agent as part of the orchestrated workflow.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with search results
        """
        articles = self.search(state.user_query)
        state.search_results = articles
        state.completed_agents.append("news_search")
        return state

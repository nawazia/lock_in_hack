"""Analysis Agent - Analyzes and selects relevant news articles."""
import logging
from typing import List, Dict, Any
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough

from models.schemas import NewsArticle, AgentState, AnalysisResult
from config.llm_setup import get_llm_openai

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Agent responsible for analyzing news articles and selecting the most relevant ones."""

    def __init__(self, llm=None):
        """Initialize the analysis agent.

        Args:
            llm: Language model to use. If None, uses default OpenAI model.
        """
        self.llm = llm or get_llm_openai()
        self.chain = self._create_analysis_chain()

    def _create_analysis_chain(self):
        """Create the analysis chain using LCEL."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert news analyst. Your job is to:

1. Analyze all provided news articles (both new search results and historical articles)
2. Identify key topics and themes
3. Determine which articles are most relevant and credible
4. Assess the overall sentiment
5. Select the most important articles for summarization

Be critical and prioritize:
- Recent and timely information
- Credible sources
- Unique perspectives
- Relevance to the user's query

Provide your analysis in the following JSON format:
{{
    "key_topics": ["topic1", "topic2", ...],
    "selected_article_urls": ["url1", "url2", ...],
    "reasoning": "Brief explanation of your selection criteria and findings",
    "sentiment": "positive/negative/neutral/mixed"
}}"""),
            ("human", """User Query: {query}

NEW SEARCH RESULTS:
{search_results}

HISTORICAL ARTICLES FROM RAG:
{rag_results}

Please analyze these articles and select the most relevant ones."""),
        ])

        # Use JsonOutputParser for structured output
        parser = JsonOutputParser()

        chain = prompt | self.llm | parser
        return chain

    def _format_articles(self, articles: List[NewsArticle]) -> str:
        """Format articles for the prompt."""
        if not articles:
            return "No articles available."

        formatted = []
        for i, article in enumerate(articles, 1):
            formatted.append(f"""
Article {i}:
Title: {article.title}
URL: {article.url}
Content: {article.content[:500]}...
Source: {article.source}
""")
        return "\n".join(formatted)

    def analyze(
        self,
        query: str,
        search_results: List[NewsArticle],
        rag_results: List[NewsArticle]
    ) -> Dict[str, Any]:
        """Analyze articles and select the most relevant ones.

        Args:
            query: User's original query
            search_results: Articles from search
            rag_results: Articles from RAG retrieval

        Returns:
            Dictionary containing analysis results
        """
        try:
            logger.info("Analyzing articles...")

            # Format articles for the prompt
            search_formatted = self._format_articles(search_results)
            rag_formatted = self._format_articles(rag_results)

            # Run the analysis chain
            result = self.chain.invoke({
                "query": query,
                "search_results": search_formatted,
                "rag_results": rag_formatted
            })

            logger.info(f"Analysis complete. Selected {len(result.get('selected_article_urls', []))} articles")
            return result

        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            # Return a fallback analysis
            return {
                "key_topics": ["Error in analysis"],
                "selected_article_urls": [a.url for a in search_results[:3]],
                "reasoning": f"Analysis failed: {str(e)}. Defaulting to first 3 search results.",
                "sentiment": "unknown"
            }

    def _select_articles_by_urls(
        self,
        urls: List[str],
        search_results: List[NewsArticle],
        rag_results: List[NewsArticle]
    ) -> List[NewsArticle]:
        """Select articles based on URLs from analysis.

        Args:
            urls: List of URLs to select
            search_results: Articles from search
            rag_results: Articles from RAG

        Returns:
            List of selected NewsArticle objects
        """
        all_articles = search_results + rag_results
        url_to_article = {article.url: article for article in all_articles}

        selected = []
        for url in urls:
            if url in url_to_article:
                selected.append(url_to_article[url])

        # If no matches, return top search results
        if not selected:
            logger.warning("No articles matched selected URLs, using top search results")
            selected = search_results[:3]

        return selected

    def run(self, state: AgentState) -> AgentState:
        """Run the analysis agent as part of the orchestrated workflow.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with analysis results
        """
        # Perform analysis
        analysis_result = self.analyze(
            query=state.user_query,
            search_results=state.search_results,
            rag_results=state.rag_results
        )

        # Select articles based on analysis
        selected_urls = analysis_result.get("selected_article_urls", [])
        selected_articles = self._select_articles_by_urls(
            selected_urls,
            state.search_results,
            state.rag_results
        )

        # Create structured analysis output
        analysis_text = f"""
Key Topics: {', '.join(analysis_result.get('key_topics', []))}
Sentiment: {analysis_result.get('sentiment', 'unknown')}
Reasoning: {analysis_result.get('reasoning', 'N/A')}
Selected {len(selected_articles)} articles for detailed summary.
"""

        state.analysis = analysis_text
        state.metadata["selected_articles"] = selected_articles
        state.metadata["analysis_result"] = analysis_result
        state.completed_agents.append("analysis")

        return state

"""Data models for the multi-agent news system."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class NewsArticle(BaseModel):
    """Structured representation of a news article."""

    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    content: str = Field(..., description="Article content/snippet")
    source: str = Field(default="valyu", description="Source of the article")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the article was retrieved")
    query: Optional[str] = Field(None, description="The search query that found this article")
    relevance_score: Optional[float] = Field(None, description="Relevance score if available")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Breaking News",
                "url": "https://example.com/news",
                "content": "Article content here...",
                "source": "valyu",
                "query": "latest tech news"
            }
        }
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentState(BaseModel):
    """State shared across all agents in the orchestration."""

    # User input
    user_query: str = Field(..., description="Original user query")

    # Agent outputs
    search_results: List[NewsArticle] = Field(default_factory=list, description="News articles from search")
    rag_results: List[NewsArticle] = Field(default_factory=list, description="Retrieved articles from RAG")
    analysis: Optional[str] = Field(None, description="Analysis output")
    summary: Optional[str] = Field(None, description="Final summary output")

    # Orchestration metadata
    next_agent: Optional[str] = Field(None, description="Which agent to call next")
    completed_agents: List[str] = Field(default_factory=list, description="Agents that have completed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        arbitrary_types_allowed = True


class AnalysisResult(BaseModel):
    """Output from the analysis agent."""

    key_topics: List[str] = Field(..., description="Key topics identified")
    selected_articles: List[NewsArticle] = Field(..., description="Articles selected for summary")
    reasoning: str = Field(..., description="Why these articles were selected")
    sentiment: Optional[str] = Field(None, description="Overall sentiment")

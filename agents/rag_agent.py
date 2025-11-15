"""RAG Agent - Manages retrieval and storage of news articles using vector store."""
import logging
import os
from typing import List, Optional
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from models.schemas import NewsArticle, AgentState

logger = logging.getLogger(__name__)


class RAGAgent:
    """Agent responsible for storing and retrieving news articles using RAG."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_model: Optional[OpenAIEmbeddings] = None,
        collection_name: str = "news_articles"
    ):
        """Initialize the RAG agent.

        Args:
            persist_directory: Directory to persist the vector store
            embedding_model: Embeddings model to use
            collection_name: Name of the collection in vector store
        """
        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "storage",
                "chroma_db"
            )

        self.persist_directory = persist_directory
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        self.embeddings = embedding_model or OpenAIEmbeddings(
            model="text-embedding-3-small"
        )

        self.collection_name = collection_name
        self.vectorstore = self._initialize_vectorstore()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def _initialize_vectorstore(self) -> Chroma:
        """Initialize or load the vector store."""
        try:
            vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            logger.info(f"Vector store initialized at {self.persist_directory}")
            return vectorstore
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            raise

    def store_articles(self, articles: List[NewsArticle]) -> int:
        """Store news articles in the vector store.

        Args:
            articles: List of NewsArticle objects to store

        Returns:
            Number of articles successfully stored
        """
        if not articles:
            logger.warning("No articles to store")
            return 0

        try:
            documents = []
            for article in articles:
                # Create metadata for better retrieval
                metadata = {
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "timestamp": article.timestamp.isoformat(),
                    "query": article.query or "",
                }

                # Create document with content
                doc = Document(
                    page_content=f"Title: {article.title}\n\n{article.content}",
                    metadata=metadata
                )
                documents.append(doc)

            # Split documents if they're too long
            split_docs = self.text_splitter.split_documents(documents)

            # Add to vector store
            self.vectorstore.add_documents(split_docs)
            logger.info(f"Stored {len(articles)} articles ({len(split_docs)} chunks)")

            return len(articles)

        except Exception as e:
            logger.error(f"Error storing articles: {e}")
            return 0

    def retrieve_articles(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[NewsArticle]:
        """Retrieve relevant articles from the vector store.

        Args:
            query: Query string to search for
            k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of relevant NewsArticle objects
        """
        try:
            logger.info(f"Retrieving articles for query: {query}")

            # Perform similarity search
            if filter_dict:
                docs = self.vectorstore.similarity_search(
                    query,
                    k=k,
                    filter=filter_dict
                )
            else:
                docs = self.vectorstore.similarity_search(query, k=k)

            # Convert documents back to NewsArticle objects
            articles = []
            for doc in docs:
                metadata = doc.metadata
                articles.append(NewsArticle(
                    title=metadata.get("title", "Unknown"),
                    url=metadata.get("url", ""),
                    content=doc.page_content,
                    source=metadata.get("source", "rag"),
                    query=query,
                    relevance_score=None  # Could add similarity score here
                ))

            logger.info(f"Retrieved {len(articles)} articles from RAG")
            return articles

        except Exception as e:
            logger.error(f"Error retrieving articles: {e}")
            return []

    def retrieve_with_scores(
        self,
        query: str,
        k: int = 5
    ) -> List[tuple[NewsArticle, float]]:
        """Retrieve articles with relevance scores.

        Args:
            query: Query string to search for
            k: Number of results to return

        Returns:
            List of (NewsArticle, score) tuples
        """
        try:
            docs_and_scores = self.vectorstore.similarity_search_with_score(query, k=k)

            results = []
            for doc, score in docs_and_scores:
                metadata = doc.metadata
                article = NewsArticle(
                    title=metadata.get("title", "Unknown"),
                    url=metadata.get("url", ""),
                    content=doc.page_content,
                    source=metadata.get("source", "rag"),
                    query=query,
                    relevance_score=float(score)
                )
                results.append((article, score))

            return results

        except Exception as e:
            logger.error(f"Error retrieving articles with scores: {e}")
            return []

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        try:
            collection = self.vectorstore._collection
            count = collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def run(self, state: AgentState) -> AgentState:
        """Run the RAG agent as part of the orchestrated workflow.

        This will:
        1. Store any new search results
        2. Retrieve relevant historical articles

        Args:
            state: Current agent state

        Returns:
            Updated agent state with RAG results
        """
        # Store new articles if we have search results
        if state.search_results:
            self.store_articles(state.search_results)

        # Retrieve relevant historical articles
        rag_articles = self.retrieve_articles(state.user_query, k=5)
        state.rag_results = rag_articles
        state.completed_agents.append("rag")

        return state

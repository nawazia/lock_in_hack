#!/usr/bin/env python3
"""
Example: Using the Multi-Agent News System API

This script demonstrates how to use the Flask API to query the multi-agent system.
"""
import requests
import json


def query_news_system(query: str, api_url: str = "http://localhost:5000"):
    """
    Query the multi-agent news system via the API.

    Args:
        query: Your news query
        api_url: Base URL of the API (default: http://localhost:5000)

    Returns:
        dict: Response from the API
    """
    print(f"\n{'=' * 80}")
    print(f"Query: {query}")
    print('=' * 80)

    try:
        # Send POST request to the API
        response = requests.post(
            f"{api_url}/api/query",
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 minute timeout
        )

        # Check if request was successful
        response.raise_for_status()

        # Parse JSON response
        result = response.json()

        if result.get("success"):
            data = result["data"]

            print(f"\n📊 Statistics:")
            print(f"  - Search results found: {data['search_results_count']}")
            print(f"  - Historical articles retrieved: {data['rag_results_count']}")
            print(f"  - Agents completed: {', '.join(data['completed_agents'])}")

            print(f"\n📝 Analysis:")
            print(data["analysis"])

            print(f"\n📰 Summary:")
            print(data["summary"])

            # Show LangSmith info if available
            if "langsmith_info" in result:
                ls_info = result["langsmith_info"]
                print(f"\n🔍 LangSmith Tracing:")
                print(f"  - Project: {ls_info['project']}")
                print(f"  - View traces: {ls_info['dashboard_url']}")

            return result

        else:
            print(f"❌ Error: {result.get('error')}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to API at {api_url}")
        print("   Make sure the server is running: python api.py")
        return None

    except requests.exceptions.Timeout:
        print("❌ Request timed out (took more than 2 minutes)")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None


def main():
    """Run example queries."""
    print("=" * 80)
    print("Multi-Agent News System - API Usage Example")
    print("=" * 80)
    print("\nMake sure the API server is running:")
    print("  python api.py")
    print("\nAnd that you have set up your .env file with:")
    print("  - VALYU_API_KEY")
    print("  - OPENROUTER_API_KEY (or OPENAI_API_KEY)")
    print("  - LANGCHAIN_API_KEY (optional, for tracing)")

    # Example queries
    queries = [
        "What are the latest developments in AI and machine learning?",
        # "Tell me about recent climate change news",
        # "What's happening in the cryptocurrency markets?",
    ]

    for query in queries:
        result = query_news_system(query)

        if result:
            print("\n✅ Query completed successfully!")
        else:
            print("\n❌ Query failed!")

        print("\n" + "=" * 80)

    # Example: Getting RAG statistics
    print("\n📚 Fetching RAG Statistics...")
    try:
        response = requests.get("http://localhost:5000/api/stats")
        if response.status_code == 200:
            stats = response.json()["stats"]
            print(f"  - Total documents stored: {stats.get('total_documents', 0)}")
            print(f"  - Collection name: {stats.get('collection_name', 'N/A')}")
            print(f"  - Storage location: {stats.get('persist_directory', 'N/A')}")
        else:
            print("  ❌ Could not fetch stats")
    except Exception as e:
        print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    main()

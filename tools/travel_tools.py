"""Travel search tools for flights, hotels, and activities using Valyu."""
from langchain.tools import tool
from typing import List, Dict, Any
from langsmith import traceable
import json
import os
import logging
from dotenv import load_dotenv
from valyu import Valyu

load_dotenv()
logger = logging.getLogger(__name__)

def validate_urls_with_llm(urls_with_titles: List[Dict[str, str]]) -> List[str]:
    """Use LLM to validate which URLs are legitimate booking sites.

    Args:
        urls_with_titles: List of dicts with 'url' and 'title' keys

    Returns:
        List of legitimate URLs
    """
    if not urls_with_titles:
        return []

    try:
        from config.llm_setup import get_llm

        llm = get_llm()

        # Format URLs for LLM review
        url_list = "\n".join([
            f"{i+1}. {item['title'][:80]}... | {item['url']}"
            for i, item in enumerate(urls_with_titles[:15])  # Check up to 15 URLs
        ])

        prompt = f"""Which URLs should be REJECTED because they're forums/social media/generic blogs?

URLs:
{url_list}

❌ REJECT ONLY these types:
- Social media: Reddit, Quora, Facebook, Twitter, Instagram, TikTok
- Forums: TripAdvisor forums, travel discussion boards
- News: CNN, BBC, NYTimes (generic travel articles, not deals)
- Wikipedia, general encyclopedias
- Blogs with ZERO pricing (just tips/guides)

✅ KEEP everything else including:
- Booking sites, airlines, hotels
- Deal sites, price aggregators, flight deal alerts
- Travel cost guides, price comparison sites
- ANY site mentioning prices, deals, or costs

If in doubt, KEEP IT (we'll validate content later).

Return:
- "NONE" if all URLs are good (keep all)
- Comma-separated numbers to reject (e.g., "2,5")
NO explanations."""

        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        content = content.strip()

        # Parse the response (now returns URLs to REJECT, not accept)
        if "NONE" in content.upper():
            logger.info("LLM said NONE to reject - keeping all URLs")
            return [item['url'] for item in urls_with_titles]

        # Extract numbers to reject
        import re
        numbers = re.findall(r'\d+', content)

        if not numbers:
            logger.info(f"No reject numbers found in LLM response - keeping all URLs")
            # No numbers to reject = keep all
            return [item['url'] for item in urls_with_titles]

        try:
            # Indices to REJECT (1-indexed from LLM)
            reject_indices = set(int(n) - 1 for n in numbers)
            # Keep URLs NOT in reject list
            legitimate_urls = [
                urls_with_titles[i]['url']
                for i in range(len(urls_with_titles))
                if i not in reject_indices
            ]
            rejected_count = len(urls_with_titles) - len(legitimate_urls)
            logger.info(f"LLM rejected {rejected_count}/{len(urls_with_titles)} URLs (keeping {len(legitimate_urls)})")
            return legitimate_urls
        except Exception as e:
            logger.warning(f"Error parsing reject indices: {e}")
            # Be lenient: return all URLs
            return [item['url'] for item in urls_with_titles]

    except Exception as e:
        logger.error(f"Error in LLM URL validation: {e}")
        # Fallback: return all URLs
        return [item['url'] for item in urls_with_titles]


@tool
@traceable(name="search_flights", run_type="tool")
def search_flights(
    origin: str,
    destination: str,
    date: str,
    passengers: int = 1
) -> str:
    """Search for flights between origin and destination using Valyu.

    Args:
        origin: Origin airport code or city
        destination: Destination airport code or city
        date: Travel date (YYYY-MM-DD format)
        passengers: Number of passengers

    Returns:
        JSON string with flight options from Valyu search
    """
    api_key = os.getenv("VALYU_API_KEY")
    if not api_key:
        return json.dumps({"error": "VALYU_API_KEY is not set in the environment."})

    try:
        valyu = Valyu(api_key=api_key)

        # Construct a specific search query with booking keywords
        # Extract month/year from date (format: YYYY-MM-DD)
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            month_year = date_obj.strftime("%B %Y")  # e.g., "December 2025"
        except:
            month_year = "December 2025"  # Fallback

        query = f"{origin} to {destination} flights {month_year} booking price reserve buy tickets"

        response = valyu.search(query)

        if not getattr(response, "results", None):
            return json.dumps({
                "query": {
                    "origin": origin,
                    "destination": destination,
                    "date": date,
                    "passengers": passengers
                },
                "flights": [],
                "count": 0,
                "raw_search": f"No results found for: {query}"
            })

        # Extract flight information from Valyu results
        all_results = []
        for result in response.results[:25]:  # Get many results (top 25)
            title = getattr(result, "title", "")
            url = getattr(result, "url", "")
            content = getattr(result, "content", "")

            all_results.append({
                "title": title,
                "url": url,
                "content": content
            })

        # Use LLM to validate which URLs are legitimate booking sites
        urls_for_validation = [{"title": r["title"], "url": r["url"]} for r in all_results]
        legitimate_urls = validate_urls_with_llm(urls_for_validation)

        # Only keep results with legitimate URLs
        flights_data = []
        for result in all_results:
            if result["url"] in legitimate_urls:
                flights_data.append({
                    "source_title": result["title"],
                    "source_url": result["url"],
                    "content_snippet": result["content"][:500],
                    "relevance": "Valyu ranked result"
                })

        result = {
            "query": {
                "origin": origin,
                "destination": destination,
                "date": date,
                "passengers": passengers
            },
            "search_results": flights_data,
            "count": len(flights_data),
            "note": "Search results from Valyu. Parse content for flight details."
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "query": {
                "origin": origin,
                "destination": destination,
                "date": date,
                "passengers": passengers
            }
        })


@tool
@traceable(name="search_hotels", run_type="tool")
def search_hotels(
    location: str,
    check_in: str,
    check_out: str,
    guests: int = 1
) -> str:
    """Search for hotels in a location using Valyu search.

    Args:
        location: City or area
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        guests: Number of guests

    Returns:
        JSON string with hotel options from Valyu search
    """
    api_key = os.getenv("VALYU_API_KEY")
    if not api_key:
        return json.dumps({"error": "VALYU_API_KEY is not set in the environment."})

    try:
        valyu = Valyu(api_key=api_key)

        # Construct a specific search query with booking keywords
        # Extract month/year from check_in date
        try:
            from datetime import datetime
            date_obj = datetime.strptime(check_in, "%Y-%m-%d")
            month_year = date_obj.strftime("%B %Y")  # e.g., "December 2025"
        except:
            month_year = "December 2025"  # Fallback

        query = f"hotels {location} {month_year} booking price reserve accommodation book now"

        response = valyu.search(query)

        if not getattr(response, "results", None):
            return json.dumps({
                "query": {
                    "location": location,
                    "check_in": check_in,
                    "check_out": check_out,
                    "guests": guests
                },
                "hotels": [],
                "count": 0,
                "raw_search": f"No results found for: {query}"
            })

        # Extract hotel information from Valyu results
        all_results = []
        for result in response.results[:25]:  # Get many results (top 25)
            title = getattr(result, "title", "")
            url = getattr(result, "url", "")
            content = getattr(result, "content", "")

            all_results.append({
                "title": title,
                "url": url,
                "content": content
            })

        # Use LLM to validate which URLs are legitimate booking sites
        urls_for_validation = [{"title": r["title"], "url": r["url"]} for r in all_results]
        legitimate_urls = validate_urls_with_llm(urls_for_validation)

        # Only keep results with legitimate URLs
        hotels_data = []
        for result in all_results:
            if result["url"] in legitimate_urls:
                hotels_data.append({
                    "source_title": result["title"],
                    "source_url": result["url"],
                    "content_snippet": result["content"][:500],
                    "relevance": "Valyu ranked result"
                })

        result = {
            "query": {
                "location": location,
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests
            },
            "search_results": hotels_data,
            "count": len(hotels_data),
            "note": "Search results from Valyu. Parse content for hotel details."
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "query": {
                "location": location,
                "check_in": check_in,
                "check_out": check_out,
                "guests": guests
            }
        })


@tool
@traceable(name="search_activities", run_type="tool")
def search_activities(
    location: str,
    interests: str = "",
    category: str = ""
) -> str:
    """Search for activities and experiences in a location using Valyu.

    Args:
        location: City or area
        interests: User interests (comma-separated)
        category: Activity category (e.g., 'museum', 'food', 'adventure')

    Returns:
        JSON string with activity options from Valyu search
    """
    api_key = os.getenv("VALYU_API_KEY")
    if not api_key:
        return json.dumps({"error": "VALYU_API_KEY is not set in the environment."})

    try:
        valyu = Valyu(api_key=api_key)

        # Construct a detailed search query for activities
        query_parts = [f"activities and things to do in {location}"]
        if interests:
            query_parts.append(f"interests: {interests}")
        if category:
            query_parts.append(f"category: {category}")
        query_parts.append("prices ratings reviews booking")

        query = " ".join(query_parts)

        response = valyu.search(query)

        if not getattr(response, "results", None):
            return json.dumps({
                "query": {
                    "location": location,
                    "interests": interests,
                    "category": category
                },
                "activities": [],
                "count": 0,
                "raw_search": f"No results found for: {query}"
            })

        # Extract activity information from Valyu results
        activities_data = []
        for result in response.results[:10]:  # Limit to top 10 results
            title = getattr(result, "title", "")
            url = getattr(result, "url", "")
            content = getattr(result, "content", "")

            activities_data.append({
                "source_title": title,
                "source_url": url,
                "content_snippet": content[:300],  # Truncate long content
                "relevance": "Valyu ranked result"
            })

        result = {
            "query": {
                "location": location,
                "interests": interests,
                "category": category
            },
            "search_results": activities_data,
            "count": len(activities_data),
            "note": "Real-time search results from Valyu. Parse content for activity details."
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "query": {
                "location": location,
                "interests": interests,
                "category": category
            }
        })

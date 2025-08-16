#!/usr/bin/env python3
"""Web search tools for House Whisperer Inspector AI using Tavily.

Adapted from Deep Research notebook for home inspection context.
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from tavily import TavilyClient
from langchain_core.tools import tool
from langchain_core.documents import Document

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Tavily client
def get_tavily_client():
    """Get Tavily client with proper error handling."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables")
    return TavilyClient(api_key=api_key)

# Score threshold configuration
# Tavily scores range from 0.0 to 1.0
# - 0.7+ = Highly relevant
# - 0.5-0.7 = Moderately relevant  
# - 0.3-0.5 = Somewhat relevant
# - Below 0.3 = Less relevant
DEFAULT_MIN_SCORE = 0.3  # Lowered to get more results

# Domain configuration for home inspection sources
TRUSTED_DOMAINS = [
    "nachi.org",           # InterNACHI
    "nchilb.nc.gov",      # NC Home Inspector Licensure Board
    "ashireporter.org",    # ASHI Reporter
    "cpsc.gov",           # Consumer Product Safety Commission (recalls)
    "nfpa.org",           # National Fire Protection Association
    "buildingcodes.nc.gov" # NC Building Codes
]

EXCLUDED_DOMAINS = [
    "pinterest.com",
    "facebook.com",
    "amazon.com",
    "ebay.com",
    "youtube.com",  # Exclude video results for now
    "reddit.com"    # Can be added back for specific queries
]

async def tavily_search_async(
    query: str,
    max_results: int = 5,
    include_raw_content: bool = True,
    search_depth: str = "advanced"
) -> List[Dict[str, Any]]:
    """
    Async Tavily search with home inspection context.
    
    Adapted from Deep Research notebook with specific domains for inspection.
    """
    try:
        client = get_tavily_client()
        
        # Enhance query with inspection context
        enhanced_query = f"home inspection {query}"
        if "north carolina" not in query.lower() and "nc" not in query.lower():
            enhanced_query += " North Carolina"
        
        logger.info(f"🔍 Searching web for: {enhanced_query}")
        
        # Perform search with domain filtering
        # Note: Removing domain restrictions might get better content
        response = client.search(
            query=enhanced_query,
            max_results=max_results * 2,  # Get more results to filter
            include_raw_content=include_raw_content,
            search_depth=search_depth,
            # include_domains=TRUSTED_DOMAINS,  # Temporarily disabled for better results
            exclude_domains=EXCLUDED_DOMAINS
        )
        
        # Debug: Log raw response structure
        logger.info(f"   Tavily returned {len(response.get('results', []))} raw results")
        if response.get('results'):
            first = response['results'][0]
            logger.info(f"   First result keys: {list(first.keys())}")
            logger.info(f"   Score value: {first.get('score', 'NO SCORE KEY')}")
        
        # Format results similar to Deep Research
        formatted_results = []
        for result in response.get('results', []):
            score = result.get('score', 0.0)
            # Log scores for debugging
            logger.info(f"   Score: {score:.3f} - {result.get('title', '')[:50]}...")
            
            formatted_results.append({
                "query": query,
                "title": result.get('title', ''),
                "url": result.get('url', ''),
                "content": result.get('content', ''),  # Use content, not raw_content
                "raw_content": None,  # Don't store raw_content to avoid confusion
                "score": score,
                "source": extract_source_name(result.get('url', '')),
                "fetched_at": datetime.now().isoformat()
            })
        
        logger.info(f"✅ Found {len(formatted_results)} results")
        
        # Debug: Show what Tavily actually returned
        if formatted_results:
            logger.info(f"   First result score: {formatted_results[0].get('score', 'NO SCORE')}")
            logger.info(f"   Content length: {len(formatted_results[0].get('content', ''))}")
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"❌ Tavily search error: {str(e)}")
        return []

def extract_source_name(url: str) -> str:
    """Extract human-readable source name from URL."""
    domain_mapping = {
        "nachi.org": "InterNACHI",
        "nchilb.nc.gov": "NC Home Inspector Licensure Board",
        "ashireporter.org": "ASHI Reporter",
        "cpsc.gov": "Consumer Product Safety Commission",
        "nfpa.org": "National Fire Protection Association",
        "buildingcodes.nc.gov": "NC Building Codes"
    }
    
    for domain, name in domain_mapping.items():
        if domain in url:
            return name
    
    # Extract domain name as fallback
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        return domain.split('.')[0].title()
    except:
        return "Web Source"

def deduplicate_and_format_sources(
    search_results: List[Dict[str, Any]],
    max_length: int = 2000,
    min_score: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Deduplicate and format search results.
    
    Adapted from Deep Research to maintain unique sources.
    """
    seen_urls = set()
    unique_results = []
    raw_count = len(search_results or [])
    below_threshold_count = 0
    duplicate_count = 0
    
    for result in search_results:
        url = result.get('url', '')
        score = result.get('score', 0.0)
        
        # Apply score threshold
        if score < min_score:
            below_threshold_count += 1
            logger.info(f"   Filtered out (score<{min_score:.2f}) {score:.3f}: {result.get('title', '')[:50]}...")
            continue
            
        if url:
            if url in seen_urls:
                duplicate_count += 1
                logger.info(f"   Filtered out duplicate URL: {url}")
                continue
            seen_urls.add(url)

        # Use 'content' field which has the actual useful text, not 'raw_content' which has navigation
        content = result.get('content', '')
        if len(content) > max_length:
            content = content[:max_length] + "..."

        unique_results.append({
            **result,
            'content': content  # This ensures we use the clean content, not raw HTML
        })
    
    # Sort by relevance score
    kept_sorted = sorted(unique_results, key=lambda x: x.get('score', 0), reverse=True)
    kept_count = len(kept_sorted)
    try:
        logger.info(
            f"🔎 Web filter summary: raw={raw_count}, below_threshold={below_threshold_count}, duplicates={duplicate_count}, kept={kept_count} (min_score={min_score})"
        )
    except Exception:
        pass
    return kept_sorted

@tool
def search_web_for_inspection_info(
    query: str,
    max_results: int = 5,
    min_score: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Search the web for home inspection information.
    
    This tool searches trusted inspection sources and returns relevant content
    for questions about home inspection standards, best practices, recalls,
    and current industry information.
    
    Args:
        query: Search query related to home inspection
        max_results: Maximum number of results to return (default 5)
        min_score: Minimum relevance score threshold (0.0-1.0, default 0.5)
                   Results below this score are filtered out
    
    Returns:
        List of search results with title, content, URL, and relevance score
        Only includes results with score >= min_score
    """
    try:
        logger.info(f"🛠️ search_web_for_inspection_info params: max_results={max_results}, min_score={min_score:.2f}")
        # Handle async in existing event loop (FastAPI/uvicorn environment)
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context already (like FastAPI)
                # Use asyncio.create_task or run_coroutine_threadsafe
                import concurrent.futures
                import threading
                
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            tavily_search_async(query, max_results)
                        )
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    results = future.result()
            else:
                # No running loop, we can use run_until_complete
                results = loop.run_until_complete(
                    tavily_search_async(query, max_results)
                )
        except RuntimeError:
            # No event loop exists, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(
                tavily_search_async(query, max_results)
            )
        
        # Deduplicate and format with score filtering
        formatted_results = deduplicate_and_format_sources(results, min_score=min_score)

        # Convert to format expected by LangGraph
        final = [{
            "content": r['content'],
            "source": f"{r['source']}: {r['title']}",
            "url": r['url'],
            "score": r['score'],
            "type": "web_resource"  # Different from "regulatory"
        } for r in formatted_results[:max_results]]

        try:
            logger.info(f"✅ Web results after filtering: {len(formatted_results)}; returned (capped) {len(final)} (cap={max_results})")
        except Exception:
            pass

        return final
        
    except Exception as e:
        logger.error(f"Web search tool error: {str(e)}")
        return []

@tool
def search_for_recalls(
    product_name: str,
    manufacturer: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search specifically for product recalls related to home inspection.
    
    This tool focuses on CPSC and manufacturer recall information for
    products commonly found during home inspections.
    
    Args:
        product_name: Name of the product (e.g., "Federal Pacific panel")
        manufacturer: Optional manufacturer name for more specific search
    
    Returns:
        List of recall information with details and recommendations
    """
    # Build specific recall query
    recall_query = f"recall {product_name}"
    if manufacturer:
        recall_query += f" {manufacturer}"
    
    # Search with CPSC priority
    try:
        client = get_tavily_client()
        response = client.search(
            query=recall_query,
            max_results=3,
            include_raw_content=True,
            include_domains=["cpsc.gov", "recalls.gov"],
            search_depth="advanced"
        )
        
        results = []
        for result in response.get('results', []):
            results.append({
                "content": result.get('content', ''),
                "source": f"Recall Notice: {result.get('title', '')}",
                "url": result.get('url', ''),
                "type": "recall_notice",
                "score": result.get('score', 1.0),  # Recalls are highly relevant by default
                "product": product_name,
                "date": extract_date_from_content(result.get('content', ''))
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Recall search error: {str(e)}")
        return []

def extract_date_from_content(content: str) -> Optional[str]:
    """Extract date from recall content if possible."""
    # Simple date extraction - could be enhanced
    import re
    date_pattern = r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
    match = re.search(date_pattern, content)
    return match.group() if match else None

# Utility function for testing
def test_web_search():
    """Test the web search functionality."""
    print("🧪 Testing web search tools...\n")
    
    # Test general search
    results = search_web_for_inspection_info.invoke({"query": "electrical panel clearance requirements"})
    print(f"✅ General search returned {len(results)} results")
    if results:
        print(f"   Top result: {results[0]['source']}")
    
    # Test recall search
    recall_results = search_for_recalls.invoke({"product_name": "Federal Pacific", "manufacturer": "Stab-Lok"})
    print(f"✅ Recall search returned {len(recall_results)} results")
    if recall_results:
        print(f"   Top recall: {recall_results[0]['source']}")
    
    print("\n✨ Web search tools ready!")

if __name__ == "__main__":
    test_web_search()
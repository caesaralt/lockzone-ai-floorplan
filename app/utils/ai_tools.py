"""
AI tool utilities for web search and tool execution.
"""

import os

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


# Tool schema for Anthropic's tool use
SEARCH_TOOL_SCHEMA = {
    "name": "web_search",
    "description": "Search the web for real-time information about professional standards, building codes, electrical requirements, installation best practices, and any other knowledge needed for accurate analysis. Use this tool whenever you need to verify information, look up codes, or understand professional requirements.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query. Be specific about what you're looking for (e.g., 'NEC code kitchen outlet spacing requirements', 'professional security keypad placement residential', 'typical room dimensions residential architecture')"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of search results to return (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}


def web_search(query, max_results=5):
    """
    Perform web search using Tavily API to get real-time knowledge.
    AI agents use this to look up professional standards, codes, best practices.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
    
    Returns:
        dict with success/error status and search results
    """
    if not TAVILY_AVAILABLE:
        return {
            "error": "Tavily not available",
            "results": [],
            "message": "Install tavily-python for web search capabilities"
        }

    tavily_api_key = os.environ.get('TAVILY_API_KEY')
    if not tavily_api_key:
        return {
            "error": "No Tavily API key",
            "results": [],
            "message": "Set TAVILY_API_KEY environment variable"
        }

    try:
        client = TavilyClient(api_key=tavily_api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",  # More thorough search
            include_answer=True,  # Get AI-generated answer
            include_raw_content=False  # Don't need full HTML
        )

        return {
            "success": True,
            "query": query,
            "answer": response.get("answer", ""),
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0)
                }
                for r in response.get("results", [])
            ]
        }
    except Exception as e:
        return {
            "error": str(e),
            "results": [],
            "message": "Web search failed"
        }


def execute_tool(tool_name, tool_input):
    """
    Execute a tool based on tool name and input.
    
    Args:
        tool_name: Name of the tool to execute
        tool_input: Dictionary of tool parameters
    
    Returns:
        Formatted string result of tool execution
    """
    if tool_name == "web_search":
        query = tool_input.get("query", "")
        max_results = tool_input.get("max_results", 5)
        result = web_search(query, max_results)

        if result.get("success"):
            # Format results for AI consumption
            formatted = f"Search Query: {result['query']}\n\n"
            if result.get('answer'):
                formatted += f"Summary Answer: {result['answer']}\n\n"
            formatted += "Search Results:\n"
            for i, r in enumerate(result['results'], 1):
                formatted += f"{i}. {r['title']}\n   {r['content'][:300]}...\n   Source: {r['url']}\n\n"
            return formatted
        else:
            return f"Search failed: {result.get('error', 'Unknown error')}"

    return f"Unknown tool: {tool_name}"


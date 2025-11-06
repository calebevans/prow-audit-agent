"""Agent tools for web search and documentation lookup."""

from duckduckgo_search import DDGS


class WebSearchTool:
    """Tool for performing web searches using DuckDuckGo."""

    def __init__(self, max_results: int = 5) -> None:
        """Initialize the web search tool.

        Args:
            max_results: Maximum number of search results to return
        """
        self.max_results = max_results
        self.search_count = 0

    def search(self, query: str) -> str:
        """Perform a web search.

        Args:
            query: Search query

        Returns:
            Formatted search results
        """
        self.search_count += 1

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self.max_results))

            if not results:
                return f"No results found for query: {query}"

            formatted_results = [f"# Search Results for: {query}\n"]

            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                body = result.get("body", "No description")
                link = result.get("href", "")

                formatted_results.append(f"## Result {i}: {title}")
                formatted_results.append(f"{body}")
                formatted_results.append(f"Source: {link}\n")

            return "\n".join(formatted_results)

        except Exception as e:
            return f"Search failed: {str(e)}"

    def get_search_count(self) -> int:
        """Get the number of searches performed.

        Returns:
            Search count
        """
        return self.search_count


class ToolRegistry:
    """Registry for managing agent tools."""

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self.web_search = WebSearchTool()

    def perform_web_search(self, query: str) -> str:
        """Perform a web search.

        Args:
            query: Search query

        Returns:
            Search results
        """
        return self.web_search.search(query)

    def get_usage_stats(self) -> dict[str, int]:
        """Get usage statistics for all tools.

        Returns:
            Dictionary with usage counts
        """
        return {
            "web_searches": self.web_search.get_search_count(),
        }

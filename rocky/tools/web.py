"""Web search and fetch tools for Rocky.AI."""

import re
from typing import Optional
from urllib.parse import quote_plus, urlparse
import httpx
from bs4 import BeautifulSoup
from rocky.tools.base import Tool, ToolResult, ToolParameter
from rocky.utils.network import is_online
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


class WebSearchTool(Tool):
    """Search the web using DuckDuckGo."""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information. Requires internet connection.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results",
                    required=False,
                    default=5
                ),
            ]
        )
    
    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        if not is_online():
            return ToolResult.fail(
                "No internet connection. Connect to the internet for web search."
            )
        
        try:
            results = self._search_duckduckgo(query, max_results)
            
            if not results:
                return ToolResult.ok("No results found.", data={"results": []})
            
            output_lines = [f"Search results for: {query}\n"]
            for i, r in enumerate(results, 1):
                output_lines.append(f"{i}. {r['title']}")
                output_lines.append(f"   {r['url']}")
                output_lines.append(f"   {r['snippet'][:150]}...")
                output_lines.append("")
            
            return ToolResult.ok("\n".join(output_lines), data={"results": results})
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return ToolResult.fail(f"Search failed: {e}")
    
    def _search_duckduckgo(self, query: str, max_results: int) -> list[dict]:
        """Search using DuckDuckGo HTML."""
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        for result in soup.select(".result")[:max_results]:
            title_elem = result.select_one(".result__title")
            snippet_elem = result.select_one(".result__snippet")
            link_elem = result.select_one(".result__url")
            
            if title_elem and snippet_elem:
                # Extract actual URL from DuckDuckGo redirect
                href = title_elem.find("a")
                url = ""
                if href and href.get("href"):
                    url = href.get("href")
                    if url.startswith("//duckduckgo.com/l/?"):
                        # Parse redirect URL
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                        url = parsed.get("uddg", [url])[0]
                
                results.append({
                    "title": title_elem.get_text(strip=True),
                    "snippet": snippet_elem.get_text(strip=True),
                    "url": url or (link_elem.get_text(strip=True) if link_elem else ""),
                })
        
        return results


class WebFetchTool(Tool):
    """Fetch and parse a webpage."""
    
    def __init__(self):
        super().__init__(
            name="web_fetch",
            description="Fetch and extract text content from a webpage URL.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="URL to fetch",
                    required=True
                ),
                ToolParameter(
                    name="max_length",
                    type="integer",
                    description="Maximum content length to return",
                    required=False,
                    default=5000
                ),
            ]
        )
    
    def execute(self, url: str, max_length: int = 5000) -> ToolResult:
        if not is_online():
            return ToolResult.fail(
                "No internet connection. Connect to the internet to fetch web pages."
            )
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            with httpx.Client(timeout=15.0, follow_redirects=True, verify=False) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            
            if "text/html" in content_type:
                text = self._extract_text(response.text)
            else:
                text = response.text
            
            # Truncate if needed
            if len(text) > max_length:
                text = text[:max_length] + "\n\n[Content truncated...]"
            
            return ToolResult.ok(text, data={"url": url, "length": len(text)})
            
        except httpx.HTTPStatusError as e:
            return ToolResult.fail(f"HTTP error {e.response.status_code}: {url}")
        except Exception as e:
            logger.error(f"Web fetch error: {e}")
            return ToolResult.fail(f"Failed to fetch URL: {e}")
    
    def _extract_text(self, html: str) -> str:
        """Extract readable text from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator="\n", strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)
        
        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text

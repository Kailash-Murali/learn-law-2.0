"""
Springer Nature API Agent for Legal Research

Integrates both Meta API (discovery + metadata) and OpenAccess API (full-text) 
to provide comprehensive academic paper search capabilities.
"""

import requests
import json
import logging as _logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import Config

_logger = _logging.getLogger(__name__)
_verbose: bool = False


def set_verbose(v: bool) -> None:
    """Enable/disable verbose logging."""
    global _verbose
    _verbose = v


class SpringerAgent:
    """
    Springer Nature API Agent for discovering and retrieving academic papers.
    
    This agent does NOT inherit from LegalAgent because:
      • It doesn't call the Groq LLM (pure API integration)
      • It doesn't need XAI reasoning traces (API calls are deterministic)
      • It performs simple REST API operations, not LLM-based reasoning
    
    Instead, it's a data-fetching utility that returns structured results
    for integration into the research pipeline.
    """

    def __init__(self):
        self.meta_api_key = Config.SPRINGER_META_API_KEY
        self.openaccess_api_key = Config.SPRINGER_OPENACCESS_API_KEY
        self.meta_available = bool(self.meta_api_key)
        self.openaccess_available = bool(self.openaccess_api_key)
        self.results: List[Dict[str, Any]] = []
        self.search_performed = False

    def search_meta_api(
        self, 
        query: str, 
        topic_keywords: List[str], 
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search Springer Meta API for articles matching the legal topic.
        
        Returns structured results with metadata (abstract, DOI, link, etc.)
        """
        if not self.meta_available:
            if _verbose:
                print("⚠️  Springer Meta API key not configured")
            return {"status": "unavailable", "papers": [], "error": "API key not set"}

        if _verbose:
            print(f"🔍 Springer Meta API: Searching for '{query}'...")

        # Build query with legal focus
        refined_query = self._build_query(query, topic_keywords)
        
        try:
            # Springer Meta API endpoint
            url = "https://api.springernature.com/metadata/json"
            
            params = {
                "q": refined_query,
                "api_key": self.meta_api_key,
                "p": max_results,  # page size (max 100)
                "s": 1,            # start page
                "sort": "relevance",
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            papers = self._parse_meta_response(data)

            if _verbose:
                print(f"✅ Springer Meta API: Found {len(papers)} papers")

            return {
                "status": "success",
                "papers": papers,
                "query_used": refined_query,
                "source": "Springer Meta API"
            }

        except requests.exceptions.Timeout:
            msg = "Springer Meta API timeout"
            if _verbose:
                print(f"⚠️  {msg}")
            return {"status": "timeout", "papers": [], "error": msg}

        except requests.exceptions.HTTPError as e:
            error_msg = f"Springer Meta API error: {e.response.status_code}"
            if e.response.status_code == 401:
                error_msg = "Springer Meta API: Invalid API key"
            elif e.response.status_code == 429:
                error_msg = "Springer Meta API: Rate limit exceeded"
            
            if _verbose:
                print(f"⚠️  {error_msg}")
            return {"status": "error", "papers": [], "error": error_msg}

        except Exception as e:
            error_msg = f"Springer Meta API error: {str(e)}"
            if _verbose:
                print(f"⚠️  {error_msg}")
            return {"status": "error", "papers": [], "error": error_msg}

    def search_openaccess_api(
        self,
        query: str,
        topic_keywords: List[str],
        max_results: int = 3
    ) -> Dict[str, Any]:
        """
        Search Springer OpenAccess API for freely available full-text papers.
        """
        if not self.openaccess_available:
            if _verbose:
                print("⚠️  Springer OpenAccess API key not configured")
            return {"status": "unavailable", "papers": [], "error": "API key not set"}

        if _verbose:
            print(f"📖 Springer OpenAccess API: Searching for '{query}'...")

        refined_query = self._build_query(query, topic_keywords)

        try:
            # Springer OpenAccess API endpoint
            url = "https://api.springernature.com/openaccess/json"

            params = {
                "q": refined_query,
                "api_key": self.openaccess_api_key,
                "p": max_results,
                "s": 1,
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            papers = self._parse_openaccess_response(data)

            if _verbose:
                print(f"✅ Springer OpenAccess API: Found {len(papers)} open-access papers")

            return {
                "status": "success",
                "papers": papers,
                "query_used": refined_query,
                "source": "Springer OpenAccess API"
            }

        except requests.exceptions.Timeout:
            msg = "Springer OpenAccess API timeout"
            if _verbose:
                print(f"⚠️  {msg}")
            return {"status": "timeout", "papers": [], "error": msg}

        except requests.exceptions.HTTPError as e:
            error_msg = f"Springer OpenAccess API error: {e.response.status_code}"
            if e.response.status_code == 401:
                error_msg = "Springer OpenAccess API: Invalid API key"
            elif e.response.status_code == 429:
                error_msg = "Springer OpenAccess API: Rate limit exceeded"
            
            if _verbose:
                print(f"⚠️  {error_msg}")
            return {"status": "error", "papers": [], "error": error_msg}

        except Exception as e:
            error_msg = f"Springer OpenAccess API error: {str(e)}"
            if _verbose:
                print(f"⚠️  {error_msg}")
            return {"status": "error", "papers": [], "error": error_msg}

    def search(
        self,
        query: str,
        topic_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform combined search across both Meta and OpenAccess APIs.
        
        Returns:
            {
                "status": "completed" | "partial" | "failed",
                "meta_results": [...],
                "openaccess_results": [...],
                "combined_papers": [...],
                "total_papers": int,
                "errors": [...]
            }
        """
        if not topic_keywords:
            topic_keywords = query.split()[:3]

        if _verbose:
            print("\n" + "=" * 60)
            print("🔬 Springer Agent: Starting API search")
            print("=" * 60)

        errors = []
        meta_results = []
        openaccess_results = []

        # Try Meta API (broader discovery)
        if self.meta_available:
            meta_response = self.search_meta_api(query, topic_keywords, max_results=5)
            meta_results = meta_response.get("papers", [])
            if meta_response.get("status") == "error":
                errors.append(meta_response.get("error"))
        else:
            errors.append("Springer Meta API key not configured")

        # Try OpenAccess API (full-text)
        if self.openaccess_available:
            oa_response = self.search_openaccess_api(query, topic_keywords, max_results=3)
            openaccess_results = oa_response.get("papers", [])
            if oa_response.get("status") == "error":
                errors.append(oa_response.get("error"))
        else:
            errors.append("Springer OpenAccess API key not configured")

        # Combine and deduplicate results
        combined = self._deduplicate_papers(meta_results + openaccess_results)

        # Determine overall status
        if meta_results or openaccess_results:
            status = "completed"
        elif errors:
            status = "failed"
        else:
            status = "no_results"

        result = {
            "status": status,
            "meta_results": meta_results,
            "openaccess_results": openaccess_results,
            "combined_papers": combined,
            "total_papers": len(combined),
            "query": query,
            "keywords": topic_keywords,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }

        if _verbose:
            print(f"\n✅ Springer search complete: {len(combined)} total papers found")
            if errors:
                for err in errors:
                    print(f"   ⚠️  {err}")
            print("=" * 60 + "\n")

        self.search_performed = True
        self.results = combined
        return result

    def _build_query(self, query: str, keywords: List[str]) -> str:
        """
        Build an optimized query for Springer APIs.
        Adds legal context and combines keywords.
        """
        # Clean and filter keywords
        keywords = [kw for kw in keywords if len(kw) > 2][:5]
        keyword_str = " AND ".join(keywords)

        # Legal context
        legal_terms = "AND (law OR legal OR constitution OR statute OR case OR court)"

        return f'("{query}") {legal_terms} {keyword_str}'

    def _parse_meta_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Springer Meta API JSON response."""
        papers = []
        
        try:
            records = data.get("records", [])
            for record in records:
                paper = {
                    "title": record.get("title", "N/A"),
                    "authors": self._extract_authors(record.get("creators", [])),
                    "publication_date": record.get("publicationDate", "N/A"),
                    "doi": record.get("doi", ""),
                    "abstract": record.get("abstract", ""),
                    "url": record.get("url", [{}])[0].get("value", "") if record.get("url") else "",
                    "journal": record.get("publicationName", ""),
                    "source": "Springer Meta API",
                    "full_text_available": False,  # Meta API doesn't have full-text
                }
                if paper["title"] != "N/A":
                    papers.append(paper)
        except Exception as e:
            if _verbose:
                print(f"⚠️  Error parsing Meta API response: {e}")

        return papers

    def _parse_openaccess_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Springer OpenAccess API JSON response."""
        papers = []
        
        try:
            records = data.get("records", [])
            for record in records:
                paper = {
                    "title": record.get("title", "N/A"),
                    "authors": self._extract_authors(record.get("creators", [])),
                    "publication_date": record.get("publicationDate", "N/A"),
                    "doi": record.get("doi", ""),
                    "abstract": record.get("abstract", ""),
                    "url": record.get("url", [{}])[0].get("value", "") if record.get("url") else "",
                    "journal": record.get("publicationName", ""),
                    "source": "Springer OpenAccess API",
                    "full_text_available": True,  # OpenAccess = full-text available
                    "content_type": record.get("contentType", ""),
                }
                if paper["title"] != "N/A":
                    papers.append(paper)
        except Exception as e:
            if _verbose:
                print(f"⚠️  Error parsing OpenAccess API response: {e}")

        return papers

    def _extract_authors(self, creators: List[Any]) -> str:
        """Extract author names from creators list."""
        if not creators:
            return "N/A"
        try:
            names = [c if isinstance(c, str) else c.get("name", "Unknown") for c in creators]
            return ", ".join(names[:3])  # Limit to first 3 authors
        except Exception:
            return "N/A"

    def _deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers (by DOI or title)."""
        seen = set()
        deduplicated = []

        for paper in papers:
            # Use DOI as primary key, title as fallback
            key = paper.get("doi") or paper.get("title", "")
            if key and key not in seen:
                seen.add(key)
                deduplicated.append(paper)

        return deduplicated

    def format_results_for_research(self) -> str:
        """
        Format Springer results into a readable string for LLM integration.
        This string can be injected into the research prompt.
        """
        if not self.results:
            return ""

        formatted = "\n\n--- ACADEMIC PAPERS FROM SPRINGER NATURE ---\n"
        for i, paper in enumerate(self.results[:5], 1):  # Limit to top 5
            formatted += f"\n{i}. {paper.get('title', 'N/A')}\n"
            formatted += f"   Authors: {paper.get('authors', 'N/A')}\n"
            formatted += f"   Journal: {paper.get('journal', 'N/A')}\n"
            formatted += f"   Date: {paper.get('publication_date', 'N/A')}\n"
            formatted += f"   DOI: {paper.get('doi', 'N/A')}\n"
            formatted += f"   Full-text available: {'Yes' if paper.get('full_text_available') else 'No'}\n"
            
            if paper.get("abstract"):
                abstract = paper["abstract"][:200] + "..." if len(paper["abstract"]) > 200 else paper["abstract"]
                formatted += f"   Abstract: {abstract}\n"
            
            if paper.get("url"):
                formatted += f"   Link: {paper['url']}\n"

        return formatted


def create_springer_agent() -> SpringerAgent:
    """Factory function to create a Springer agent."""
    return SpringerAgent()


if __name__ == "__main__":
    # Test the agent
    agent = SpringerAgent()
    set_verbose(True)
    
    result = agent.search(
        query="right to privacy under Article 21 of Indian Constitution",
        topic_keywords=["privacy", "constitution", "article 21"]
    )
    
    print("\n" + "=" * 60)
    print("SEARCH RESULTS")
    print("=" * 60)
    print(json.dumps({
        "status": result["status"],
        "total_papers": result["total_papers"],
        "errors": result["errors"],
    }, indent=2))
    
    if result["combined_papers"]:
        print("\nFORMATTED FOR RESEARCH:")
        print(agent.format_results_for_research())

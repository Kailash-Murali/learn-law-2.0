"""
Springer Nature API Integration for Legal Research
Provides async methods to search academic articles using Meta and OpenAccess APIs
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
import springernature_api_client.meta as meta
import springernature_api_client.openaccess as openaccess


@dataclass
class SpringerConfig:
    """Configuration for Springer APIs"""
    meta_api_key: str
    openaccess_api_key: str
    results_per_page: int = 20
    max_results: int = 50
    enable_openaccess: bool = True


class SpringerLegalResearch:
    """
    Wrapper for Springer Nature API focused on legal research.
    Handles query transformation and result normalization.
    """

    def __init__(self, config: SpringerConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize API clients
        self.meta_client = meta.MetaAPI(api_key=config.meta_api_key)
        if config.enable_openaccess:
            self.openaccess_client = openaccess.OpenAccessAPI(api_key=config.openaccess_api_key)
        
        # Legal subject areas in Springer
        self.legal_subjects = [
            "Law",
            "Constitutional Law",
            "Human Rights",
            "Political Science",
            "Legal Philosophy",
            "International Law"
        ]

    def transform_query(self, raw_query: str, filters: Optional[Dict[str, Any]] = None, 
                   use_basic_plan: bool = True) -> str:
        """
        Transform a natural language query into Springer API query format.
        FIXED VERSION - Works with Basic plan
        """
        if not raw_query or raw_query.strip() == "":
            return ""
        
        # Clean the query
        query = raw_query.strip().strip('"\'')
        
        # Extract keywords
        keywords = [kw.strip() for kw in query.replace(',', ' ').split() if kw.strip()]
        
        if not keywords:
            return ""
        
        # Build query parts
        query_parts = []
        
        if use_basic_plan:
            # BASIC PLAN: Keep it SIMPLE
            # Option 1: Just use the keywords as-is (simplest, often works best)
            if len(keywords) <= 3:
                # For 1-3 keywords, just join them (API will search all)
                query_parts.append(' '.join(keywords))
            else:
                # For more keywords, take the most important 3-4
                query_parts.append(' '.join(keywords[:4]))
            
            # Optional: Add "law" if it's clearly a legal query and not already present
            # But DO NOT make this mandatory - it's too restrictive
            if 'law' not in [kw.lower() for kw in keywords] and 'legal' not in [kw.lower() for kw in keywords]:
                # Only add if query seems legal-related
                if any(term in query.lower() for term in ['constitution', 'court', 'rights', 'judicial', 'article']):
                    query_parts.append('law')
        
        else:
            # PREMIUM PLAN: Can use more advanced syntax
            if len(keywords) == 1:
                query_parts.append(f'keyword:"{keywords[0]}"')
            else:
                # Use OR for broader results
                keyword_queries = [f'keyword:"{kw}"' for kw in keywords[:5]]
                query_parts.append(f'({" OR ".join(keyword_queries)})')
            
            # Add subject constraint
            query_parts.append('subject:"Law"')
        
        # Apply filters (available on both plans)
        if filters:
            # Year filtering - use correct syntax
            if 'year_from' in filters:
                query_parts.append(f'year:{filters["year_from"]}-')
            if 'year_to' in filters:
                query_parts.append(f'-{filters["year_to"]}')
            if 'year' in filters:
                query_parts.append(f'year:{filters["year"]}')
        
        # Join parts with spaces
        final_query = ' '.join(query_parts)
        self.logger.info(f"Transformed query: '{raw_query}' -> '{final_query}'")
        
        return final_query


    async def search_meta(self, query: str, filters: Optional[Dict[str, Any]] = None, 
                         use_basic_plan: bool = True) -> List[Dict[str, Any]]:
        """
        Search using Meta API (broader coverage, metadata only)
        
        Args:
            query: Raw query string
            filters: Optional filters dict
            use_basic_plan: If True, use only Basic plan constraints
            
        Returns:
            List of normalized article metadata
        """
        try:
            springer_query = self.transform_query(query, filters, use_basic_plan)
            
            if not springer_query:
                self.logger.warning("Empty query after transformation")
                return []
            
            self.logger.info(f"Searching Meta API with query: {springer_query}")
            
            # Execute search
            response = self.meta_client.search(
                q=springer_query,
                p=self.config.results_per_page,
                s=1,
                fetch_all=False,
                is_premium=not use_basic_plan
            )
            
            # Parse and normalize results
            results = self._parse_meta_response(response)
            self.logger.info(f"Meta API returned {len(results)} results")
            
            return results[:self.config.max_results]
        
        except Exception as e:
            self.logger.error(f"Meta API search failed: {str(e)}")
            return []

    async def search_openaccess(self, query: str, filters: Optional[Dict[str, Any]] = None,
                               use_basic_plan: bool = True) -> List[Dict[str, Any]]:
        """
        Search using OpenAccess API (only open access content, includes full text)
        
        Args:
            query: Raw query string
            filters: Optional filters dict
            use_basic_plan: If True, use only Basic plan constraints
            
        Returns:
            List of normalized article metadata with OA flag
        """
        if not self.config.enable_openaccess:
            self.logger.warning("OpenAccess API disabled in config")
            return []
        
        try:
            springer_query = self.transform_query(query, filters, use_basic_plan)
            
            if not springer_query:
                self.logger.warning("Empty query after transformation")
                return []
            
            self.logger.info(f"Searching OpenAccess API with query: {springer_query}")
            
            # Execute search
            response = self.openaccess_client.search(
                q=springer_query,
                p=self.config.results_per_page,
                s=1,
                fetch_all=False,
                is_premium=not use_basic_plan
            )
            
            # Parse and normalize results
            results = self._parse_openaccess_response(response)
            self.logger.info(f"OpenAccess API returned {len(results)} results")
            
            return results[:self.config.max_results]
        
        except Exception as e:
            self.logger.error(f"OpenAccess API search failed: {str(e)}")
            return []

    async def search_combined(self, query: str, filters: Optional[Dict[str, Any]] = None,
                             use_basic_plan: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search both APIs concurrently and return combined results
        
        Args:
            query: Raw query string
            filters: Optional filters dict
            use_basic_plan: If True, use only Basic plan constraints
            
        Returns:
            Dict with 'meta' and 'openaccess' keys containing respective results
        """
        tasks = [
            self.search_meta(query, filters, use_basic_plan),
        ]
        
        if self.config.enable_openaccess:
            tasks.append(self.search_openaccess(query, filters, use_basic_plan))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            'meta': results[0] if not isinstance(results[0], Exception) else [],
            'openaccess': results[1] if len(results) > 1 and not isinstance(results[1], Exception) else []
        }

    def _parse_meta_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse Meta API response into normalized format"""
        results = []
        
        if not response or 'records' not in response:
            return results
        
        for record in response.get('records', []):
            try:
                # Extract publication date year
                pub_date = record.get('publicationDate', '')
                year = None
                if pub_date:
                    year = int(pub_date.split('-')[0]) if '-' in pub_date else int(pub_date[:4])
                
                # Extract authors
                authors = []
                for creator in record.get('creators', []):
                    if isinstance(creator, dict):
                        authors.append(creator.get('creator', ''))
                    else:
                        authors.append(str(creator))
                
                # Build URL from DOI or use provided URL
                doi = record.get('doi', '')
                url = record.get('url', f"https://doi.org/{doi}" if doi else None)
                
                article = {
                    'title': record.get('title', 'No title'),
                    'authors': authors,
                    'journal': record.get('publicationName', 'Unknown'),
                    'year': year,
                    'abstract': record.get('abstract', ''),
                    'doi': doi,
                    'url': url,
                    'publication_type': record.get('contentType', 'Article'),
                    'open_access': record.get('openaccess', False),
                    'relevance_score': 0.85,  # Default score
                    'source': 'Springer Meta API'
                }
                
                results.append(article)
            
            except Exception as e:
                self.logger.warning(f"Failed to parse record: {str(e)}")
                continue
        
        return results

    def _parse_openaccess_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse OpenAccess API response into normalized format"""
        results = []
        
        if not response or 'records' not in response:
            return results
        
        for record in response.get('records', []):
            try:
                # Extract publication date year
                pub_date = record.get('publicationDate', '')
                year = None
                if pub_date:
                    year = int(pub_date.split('-')[0]) if '-' in pub_date else int(pub_date[:4])
                
                # Extract authors
                authors = []
                for creator in record.get('creators', []):
                    if isinstance(creator, dict):
                        authors.append(creator.get('creator', ''))
                    else:
                        authors.append(str(creator))
                
                # Build URL from DOI
                doi = record.get('doi', '')
                url = record.get('url', f"https://doi.org/{doi}" if doi else None)
                
                article = {
                    'title': record.get('title', 'No title'),
                    'authors': authors,
                    'journal': record.get('publicationName', 'Unknown'),
                    'year': year,
                    'abstract': record.get('abstract', ''),
                    'doi': doi,
                    'url': url,
                    'publication_type': record.get('contentType', 'Article'),
                    'open_access': True,  # All OpenAccess API results are OA
                    'relevance_score': 0.90,  # Slightly higher for OA
                    'source': 'Springer OpenAccess API'
                }
                
                results.append(article)
            
            except Exception as e:
                self.logger.warning(f"Failed to parse OA record: {str(e)}")
                continue
        
        return results

async def debug_test():
    """Minimal test to see if API is working"""
    logging.basicConfig(level=logging.INFO)
    
    config = SpringerConfig(
        meta_api_key="cfbab3fb1ac671d4b411e034375edd54",
        openaccess_api_key="1adc3c130fae757475f10ef16013f0bb",
        results_per_page=5,
        max_results=10
    )
    
    springer = SpringerLegalResearch(config)
    
    # Test 1: Simplest possible query
    print("\n" + "="*60)
    print("TEST 1: Ultra-simple query")
    print("="*60)
    
    simple_queries = [
        "law",  # Single word
        "constitutional law",  # Two words
        "human rights",  # Another two words
    ]
    
    for query in simple_queries:
        print(f"\nTesting: '{query}'")
        results = await springer.search_meta(query, use_basic_plan=True)
        print(f"Results: {len(results)}")
        if results:
            print(f"First result: {results[0]['title']}")
    
    # Test 2: Check raw API response
    print("\n" + "="*60)
    print("TEST 2: Raw API call")
    print("="*60)
    
    try:
        raw_response = springer.meta_client.search(
            q="constitutional law",
            p=5,
            s=1,
            fetch_all=False,
            is_premium=False
        )
        print(f"Raw response keys: {raw_response.keys() if hasattr(raw_response, 'keys') else type(raw_response)}")
        print(f"Number of records: {len(raw_response.get('records', []))}")
        
        if 'records' in raw_response and raw_response['records']:
            first_record = raw_response['records'][0]
            print(f"\nFirst record keys: {first_record.keys()}")
            print(f"Title: {first_record.get('title', 'N/A')}")
    except Exception as e:
        print(f"Raw API call failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_test())
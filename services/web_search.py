"""
PlagioScan AI — Internet Plagiarism Detection
Searches the web using DuckDuckGo with robust retries, timeouts, and exception handling.
"""
import re
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict

logger = logging.getLogger('plagioscan')

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def _get_session() -> requests.Session:
    """Create a session with retry logic to prevent freezing and handle transient failures."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[ 500, 502, 503, 504 ])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def _get_ddg_results(query: str, max_results: int = 5, timeout: int = 8) -> List[Dict]:
    """
    Scrape DuckDuckGo HTML results safely.
    Returns list of {title, url, snippet}.
    """
    results = []
    try:
        from bs4 import BeautifulSoup
        session = _get_session()
        
        url = 'https://html.duckduckgo.com/html/'
        resp = session.post(url, data={'q': query, 'b': '', 'kl': ''},
                            headers=_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"Web search returned status code {resp.status_code}")
            return results

        soup = BeautifulSoup(resp.text, 'html.parser')
        for result in soup.select('.result__body')[:max_results]:
            title_tag   = result.select_one('.result__title')
            snippet_tag = result.select_one('.result__snippet')
            link_tag    = result.select_one('.result__url')

            title   = title_tag.get_text(strip=True)   if title_tag   else ''
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ''
            href    = ''
            if link_tag:
                href = link_tag.get('href', '') or link_tag.get_text(strip=True)
            if not href.startswith('http'):
                href = 'https://' + href

            if title or snippet:
                results.append({'title': title, 'url': href, 'snippet': snippet})

    except ImportError:
        logger.warning('Web search requires: pip install beautifulsoup4')
    except requests.exceptions.RequestException as e:
        logger.warning(f"Web search connection error: {e}")
    except Exception as e:
        logger.warning(f"Web search unexpected error: {e}")

    return results


def search_web_matches(text: str, timeout: int = 8, max_results: int = 5) -> List[Dict]:
    """
    Extracts key sentences and searches the web for them.
    Returns matching snippets and similarity approximations.
    """
    from services.similarity import get_sentences, _manual_cosine
    sents = get_sentences(text)
    
    # Pick top 3 longest sentences as search queries to avoid IP bans and save time
    queries = sorted(sents, key=len, reverse=True)[:3]
    
    all_matches = []
    seen_urls = set()
    
    for q in queries:
        try:
            logger.info(f"Searching web for: {q[:50]}...")
            raw_results = _get_ddg_results(q, max_results, timeout)
            
            for res in raw_results:
                if res['url'] in seen_urls:
                    continue
                seen_urls.add(res['url'])
                
                sim = _manual_cosine(q, res['snippet'])
                # Only include if similarity > 15% to filter out pure noise
                if sim > 15.0:
                    all_matches.append({
                        'matched_sentence': q,
                        'title': res['title'],
                        'url': res['url'],
                        'snippet': res['snippet'],
                        'similarity': sim
                    })
        except Exception as e:
            logger.error(f"Error processing query '{q[:20]}': {e}")
            
    # Sort by highest similarity
    all_matches.sort(key=lambda x: x['similarity'], reverse=True)
    return all_matches[:max_results]

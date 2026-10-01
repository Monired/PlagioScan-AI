"""
PlagioScan AI — Academic Search Service
Priority order: OpenAlex → Semantic Scholar → Crossref → DuckDuckGo
All APIs are free — no API key required (polite crawling with email).
"""
import time
import logging
import requests
from typing import List, Dict

logger = logging.getLogger('plagioscan')

HEADERS = {
    'User-Agent': 'PlagioScan-AI/1.0 (plagiarism checker; mailto:user@plagioscan.ai)',
    'Accept':     'application/json',
}
TIMEOUT = 8


# ─── OpenAlex ────────────────────────────────────────────────────────────────
def search_openalex(query: str, max_results: int = 5) -> List[Dict]:
    """
    OpenAlex free academic API — best coverage of scholarly works.
    Docs: https://docs.openalex.org/api-entities/works/search-works
    """
    if not query:
        return []
    try:
        url = 'https://api.openalex.org/works'
        params = {
            'search':   query[:200],
            'per-page': max_results,
            'select':   'id,title,authorships,publication_year,doi,abstract_inverted_index,primary_location',
            'mailto':   'user@plagioscan.ai',
        }
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        results = []
        for item in r.json().get('results', []):
            title   = item.get('title') or ''
            doi     = item.get('doi', '') or ''
            year    = item.get('publication_year', '')
            authors = [a['author']['display_name']
                       for a in (item.get('authorships') or [])[:3]
                       if a.get('author')]
            source_url = doi if doi.startswith('http') else (f'https://doi.org/{doi}' if doi else '')
            venue = ''
            if item.get('primary_location'):
                src = item['primary_location'].get('source') or {}
                venue = src.get('display_name', '')
            # Reconstruct abstract from inverted index
            abstract = _reconstruct_abstract(item.get('abstract_inverted_index'))
            if title:
                results.append({
                    'source':    'OpenAlex',
                    'title':     title,
                    'authors':   ', '.join(authors) or 'Unknown',
                    'year':      str(year),
                    'venue':     venue,
                    'url':       source_url or f'https://openalex.org/{item.get("id","").split("/")[-1]}',
                    'abstract':  abstract[:300] if abstract else '',
                    'similarity': 0.0,  # filled in by caller
                })
        return results
    except Exception as e:
        logger.debug(f'[OpenAlex] {e}')
        return []


# ─── Semantic Scholar ─────────────────────────────────────────────────────────
def search_semantic_scholar(query: str, max_results: int = 5) -> List[Dict]:
    """
    Semantic Scholar free API.
    Docs: https://api.semanticscholar.org/graph/v1
    """
    if not query:
        return []
    try:
        url = 'https://api.semanticscholar.org/graph/v1/paper/search'
        params = {
            'query':  query[:200],
            'limit':  max_results,
            'fields': 'title,authors,year,venue,externalIds,abstract,url',
        }
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        results = []
        for item in r.json().get('data', []):
            doi_id = (item.get('externalIds') or {}).get('DOI', '')
            results.append({
                'source':    'Semantic Scholar',
                'title':     item.get('title', ''),
                'authors':   ', '.join(a['name'] for a in (item.get('authors') or [])[:3]),
                'year':      str(item.get('year') or ''),
                'venue':     item.get('venue', ''),
                'url':       item.get('url') or (f'https://doi.org/{doi_id}' if doi_id else ''),
                'abstract':  (item.get('abstract') or '')[:300],
                'similarity': 0.0,
            })
        return results
    except Exception as e:
        logger.debug(f'[SemanticScholar] {e}')
        return []


# ─── Crossref ─────────────────────────────────────────────────────────────────
def search_crossref(query: str, max_results: int = 5) -> List[Dict]:
    """
    Crossref free metadata API.
    Docs: https://api.crossref.org/works?query=...
    """
    if not query:
        return []
    try:
        url = 'https://api.crossref.org/works'
        params = {
            'query':          query[:200],
            'rows':           max_results,
            'select':         'title,author,published,DOI,container-title',
            'mailto':         'user@plagioscan.ai',
        }
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        items = r.json().get('message', {}).get('items', [])
        results = []
        for item in items:
            title   = (item.get('title') or [''])[0]
            authors = [f"{a.get('given','')} {a.get('family','')}".strip()
                       for a in (item.get('author') or [])[:3]]
            year    = ''
            if item.get('published'):
                parts = item['published'].get('date-parts', [['']])[0]
                year  = str(parts[0]) if parts else ''
            doi = item.get('DOI', '')
            venue = (item.get('container-title') or [''])[0]
            if title:
                results.append({
                    'source':    'Crossref',
                    'title':     title,
                    'authors':   ', '.join(authors) or 'Unknown',
                    'year':      year,
                    'venue':     venue,
                    'url':       f'https://doi.org/{doi}' if doi else '',
                    'abstract':  '',
                    'similarity': 0.0,
                })
        return results
    except Exception as e:
        logger.debug(f'[Crossref] {e}')
        return []


# ─── DuckDuckGo (web fallback) ────────────────────────────────────────────────
def search_duckduckgo(query: str, max_results: int = 5) -> List[Dict]:
    """DuckDuckGo instant answers API — fallback for general web search."""
    if not query:
        return []
    try:
        r = requests.get(
            'https://html.duckduckgo.com/html/',
            params={'q': query[:200], 'ia': 'web'},
            headers={**HEADERS, 'Accept': 'text/html'},
            timeout=TIMEOUT,
        )
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        results = []
        for result in soup.select('.result')[:max_results]:
            title_el = result.select_one('.result__title')
            url_el   = result.select_one('.result__url')
            snip_el  = result.select_one('.result__snippet')
            title = title_el.get_text(strip=True) if title_el else ''
            url   = url_el.get_text(strip=True)   if url_el   else ''
            snip  = snip_el.get_text(strip=True)  if snip_el  else ''
            if not url.startswith('http'):
                url = 'https://' + url
            if title:
                results.append({
                    'source':    'Web',
                    'title':     title,
                    'authors':   '',
                    'year':      '',
                    'venue':     url,
                    'url':       url,
                    'abstract':  snip[:300],
                    'similarity': 0.0,
                })
        return results
    except Exception as e:
        logger.debug(f'[DuckDuckGo] {e}')
        return []


# ─── Orchestrator ─────────────────────────────────────────────────────────────
def multi_source_academic_search(text: str, max_per_source: int = 3,
                                  timeout: int = 8) -> List[Dict]:
    """
    Search all academic sources in priority order.
    Returns deduplicated list of academic matches with similarity scores.
    """
    # Extract meaningful query from text (first 120 non-stopword chars)
    query = _extract_query(text)
    if not query:
        return []

    all_results: List[Dict] = []

    # Priority: OpenAlex → Semantic Scholar → Crossref → DuckDuckGo
    for fn in [search_openalex, search_semantic_scholar, search_crossref]:
        try:
            results = fn(query, max_results=max_per_source)
            all_results.extend(results)
        except Exception:
            pass
        if len(all_results) >= max_per_source * 2:
            break

    # Score each result against the document text
    for result in all_results:
        ref_text = ' '.join([result.get('title',''), result.get('abstract',''),
                             result.get('venue','')])
        try:
            from services.similarity import _tfidf_cosine
            result['similarity'] = round(_tfidf_cosine(text[:2000], ref_text), 1)
        except Exception:
            result['similarity'] = 0.0

    # Deduplicate by title
    seen   = set()
    unique = []
    for r in sorted(all_results, key=lambda x: x.get('similarity', 0), reverse=True):
        key = r.get('title', '').lower()[:60]
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    return unique[:max_per_source * 2]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _extract_query(text: str, words: int = 12) -> str:
    """Extract a search query from the first meaningful words of the text."""
    import re
    STOP = {'a','an','the','and','or','but','in','on','at','to','for','of',
            'with','by','from','as','is','was','are','were','be','been','this',
            'that','these','those','it','its','we','they','our','their'}
    tokens = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    content = [t for t in tokens if t not in STOP]
    return ' '.join(content[:words])


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstruct abstract text from OpenAlex inverted index."""
    if not inverted_index:
        return ''
    try:
        positions = {}
        for word, pos_list in inverted_index.items():
            for pos in pos_list:
                positions[pos] = word
        return ' '.join(positions[i] for i in sorted(positions))
    except Exception:
        return ''

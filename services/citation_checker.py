"""
PlagioScan AI — Citation Checker Service
Detects APA, IEEE, MLA, Harvard citations and evaluates reference quality.
"""
import re
from typing import Dict, List


# ── Citation Patterns ──────────────────────────────────────────────────────────
PATTERNS = {
    # APA: (Author, Year) or Author (Year)
    'APA': [
        re.compile(r'\([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*(?:\s*&\s*[A-Z][a-z]+)?,?\s*\d{4}[a-z]?\)'),
        re.compile(r'[A-Z][a-z]+(?:\s*&\s*[A-Z][a-z]+)?\s*\(\d{4}[a-z]?\)'),
    ],
    # IEEE: [1], [2], [3,4], [1-5]
    'IEEE': [
        re.compile(r'\[\d+(?:[-,]\d+)*\]'),
    ],
    # MLA: (Author page) or (Author Title page)
    'MLA': [
        re.compile(r'\([A-Z][a-z]+\s+\d+\)'),
        re.compile(r'\([A-Z][a-z]+\s+"[^"]+"\s+\d+\)'),
    ],
    # Harvard: (Author Year: page) or (Author Year, page)
    'Harvard': [
        re.compile(r'\([A-Z][a-z]+\s+\d{4}[a-z]?(?::\s*\d+)?\)'),
        re.compile(r'\([A-Z][a-z]+\s+et\s+al\.?\s+\d{4}\)'),
    ],
}

# DOI pattern
DOI_RE    = re.compile(r'\b10\.\d{4,}/\S+')
URL_RE    = re.compile(r'https?://[^\s<>"\']+')
# Reference list line (typical numbered or bulleted)
REF_LINE  = re.compile(r'^\s*(?:\[\d+\]|\d+\.|[•\-–])\s+[A-Z]', re.MULTILINE)

# Common journal/conference markers
JOURNAL_RE = re.compile(
    r'\b(?:journal|review|transactions|letters|proceedings|conference|symposium|'
    r'workshop|annual|international|advances|bulletin|science|nature|ieee|acm|'
    r'springer|elsevier|wiley|sage|taylor)\b',
    re.IGNORECASE
)
BOOK_RE = re.compile(
    r'\b(?:press|publisher|publishing|edition|isbn|chapter|book|volume|handbook|'
    r'oxford|cambridge|pearson|mcgraw|addison)\b',
    re.IGNORECASE
)
GOV_RE = re.compile(r'\b(?:\.gov|government|federal|ministry|department|committee)\b', re.IGNORECASE)


def check_citations(text: str) -> Dict:
    """
    Full citation analysis of a document.
    Returns style_detected, counts per style, DOIs, URLs, reference lines,
    diversity score, and missing-citation warnings.
    """
    results = {
        'style_detected':   'None',
        'style_counts':     {},
        'total_citations':  0,
        'dois':             [],
        'urls':             [],
        'reference_lines':  0,
        'journal_refs':     0,
        'book_refs':        0,
        'gov_refs':         0,
        'web_refs':         0,
        'diversity_score':  0,
        'citation_score':   0,
        'warnings':         [],
        'examples':         {},
    }

    # Count each style
    style_counts = {}
    examples     = {}
    for style, pats in PATTERNS.items():
        matches = []
        for pat in pats:
            matches.extend(pat.findall(text))
        if matches:
            style_counts[style] = len(matches)
            examples[style]     = matches[:3]

    results['style_counts'] = style_counts

    # Detect dominant style
    if style_counts:
        results['style_detected'] = max(style_counts, key=style_counts.get)
    results['total_citations'] = sum(style_counts.values())

    # Mixed-style warning
    if len(style_counts) > 1:
        styles = list(style_counts.keys())
        results['warnings'].append(f'Mixed citation styles detected: {", ".join(styles)}. Use one style consistently.')

    # DOIs
    dois = DOI_RE.findall(text)
    results['dois'] = list(set(dois[:20]))

    # URLs
    urls = URL_RE.findall(text)
    results['urls'] = list(set(urls[:20]))

    # Reference list lines
    ref_lines = REF_LINE.findall(text)
    results['reference_lines'] = len(ref_lines)

    # Source type diversity
    results['journal_refs'] = len(JOURNAL_RE.findall(text))
    results['book_refs']    = len(BOOK_RE.findall(text))
    results['gov_refs']     = len(GOV_RE.findall(text))
    results['web_refs']     = len([u for u in urls if '.gov' not in u])

    # Warnings
    if results['total_citations'] == 0:
        results['warnings'].append('No citations detected. Academic writing requires proper references.')
    if results['reference_lines'] == 0 and results['total_citations'] > 0:
        results['warnings'].append('In-text citations found but no reference list detected.')
    if results['web_refs'] > results['journal_refs'] + results['book_refs']:
        results['warnings'].append('High ratio of web sources — consider adding peer-reviewed journal references.')

    # Diversity score (0–100)
    n    = results['total_citations']
    types = sum([
        min(results['journal_refs'], 3),
        min(results['book_refs'],    2),
        min(results['gov_refs'],     1),
        1 if results['dois'] else 0,
    ])
    diversity = min(100, types * 14 + min(n, 10) * 3)
    results['diversity_score'] = diversity

    # Citation score (0–100)
    base = min(n * 5, 50)                  # up to 50 for quantity
    div  = diversity * 0.4                 # up to 40 for diversity
    ref  = min(results['reference_lines'] * 2, 10)  # up to 10 for ref list
    results['citation_score'] = round(min(100, base + div + ref), 1)
    results['examples']       = {k: [str(e) for e in v] for k, v in examples.items()}

    return results


def get_missing_citations_warning(text: str) -> List[str]:
    """
    Detect sentences that make factual claims but have no nearby citation.
    Returns list of suspicious sentences.
    """
    CLAIM_RE = re.compile(
        r'\b(?:studies show|research suggests|according to|evidence indicates|'
        r'it has been found|data shows|the results|it is known|'
        r'researchers found|scientists discovered|reports indicate)\b',
        re.IGNORECASE
    )
    CITE_NEARBY = re.compile(r'\(\d{4}|\[\d+\]|\([A-Z][a-z]+', re.IGNORECASE)

    sentences = re.split(r'(?<=[.!?])\s+', text)
    warnings  = []
    for sent in sentences:
        if CLAIM_RE.search(sent) and not CITE_NEARBY.search(sent):
            warnings.append(sent.strip()[:200])
        if len(warnings) >= 5:
            break
    return warnings

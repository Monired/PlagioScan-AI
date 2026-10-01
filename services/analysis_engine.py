"""
PlagioScan AI — Analysis Engine
Implements 20+ AI analysis features: readability, style, passive voice,
keyword density, academic scoring, AI-content indicator, and more.
"""
import re
import math
from collections import Counter
from typing import Dict, List, Any

from services.similarity import tokenize, get_sentences, STOP_WORDS


# ─── Readability ─────────────────────────────────────────────────────────────
def count_syllables(word: str) -> int:
    """Approximate syllable count using vowel clusters."""
    word = word.lower().rstrip('es')
    count = len(re.findall(r'[aeiou]+', word))
    return max(1, count)


def flesch_reading_ease(text: str) -> float:
    """Flesch Reading Ease: 0–100, higher = easier."""
    sents = get_sentences(text)
    words = re.findall(r'\b\w+\b', text)
    if not sents or not words:
        return 0.0
    syllables = sum(count_syllables(w) for w in words)
    asl = len(words) / len(sents)          # avg sentence length
    asw = syllables / len(words)           # avg syllables per word
    score = 206.835 - 1.015 * asl - 84.6 * asw
    return round(max(0.0, min(100.0, score)), 1)


def flesch_kincaid_grade(text: str) -> float:
    """Flesch-Kincaid Grade Level."""
    sents = get_sentences(text)
    words = re.findall(r'\b\w+\b', text)
    if not sents or not words:
        return 0.0
    syllables = sum(count_syllables(w) for w in words)
    asl = len(words) / len(sents)
    asw = syllables / len(words)
    grade = 0.39 * asl + 11.8 * asw - 15.59
    return round(max(0.0, min(20.0, grade)), 1)


# ─── Vocabulary ──────────────────────────────────────────────────────────────
def vocabulary_richness(text: str) -> float:
    """Type-Token Ratio: unique/total (%) — higher = richer."""
    tokens = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    if not tokens:
        return 0.0
    return round(len(set(tokens)) / len(tokens) * 100, 1)


def vocabulary_score(text: str) -> float:
    """Combine richness and avg word length into a 0-100 score."""
    richness = vocabulary_richness(text)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    avg_len = sum(len(w) for w in words) / max(len(words), 1)
    # Scale: richness is already 0-100; avg word length 3-8 → 0-100
    len_score = min(100, (avg_len - 3) / 5 * 100)
    return round(richness * 0.6 + len_score * 0.4, 1)


# ─── Passive Voice ───────────────────────────────────────────────────────────
_PASSIVE_PATTERN = re.compile(
    r'\b(is|are|was|were|be|been|being|am)\s+'
    r'(being\s+)?'
    r'(\w+ed|written|done|seen|known|shown|given|taken|made|found|'
    r'used|said|told|shown|helped|created|developed|implemented|designed|'
    r'built|tested|analyzed|evaluated|studied|examined|discussed|presented)\b',
    re.IGNORECASE
)

def passive_voice_percentage(text: str) -> float:
    """Estimate % of sentences containing passive voice."""
    sents = get_sentences(text)
    if not sents:
        return 0.0
    passive_count = sum(1 for s in sents if _PASSIVE_PATTERN.search(s))
    return round(passive_count / len(sents) * 100, 1)


# ─── Repeated Phrases ────────────────────────────────────────────────────────
def find_repeated_phrases(text: str, min_len: int = 4,
                           threshold: int = 3) -> List[Dict]:
    """Find phrases (bigrams+) repeated more than threshold times."""
    tokens = tokenize(text, remove_stops=True)
    phrases: Counter = Counter()
    # Collect bigrams → 4-grams
    for n in (2, 3, 4):
        for i in range(len(tokens) - n + 1):
            phrase = ' '.join(tokens[i:i + n])
            if len(phrase) >= min_len:
                phrases[phrase] += 1
    return [{'phrase': p, 'count': c}
            for p, c in phrases.most_common(15)
            if c >= threshold]


# ─── Keyword Density ─────────────────────────────────────────────────────────
def keyword_density(text: str, top_n: int = 15) -> List[Dict]:
    """Top N keywords with frequency and density %."""
    tokens = tokenize(text, remove_stops=True)
    if not tokens:
        return []
    counts = Counter(tokens)
    total  = len(tokens)
    return [{'keyword': w, 'count': c, 'density': round(c / total * 100, 2)}
            for w, c in counts.most_common(top_n)]


# ─── Writing Tone ────────────────────────────────────────────────────────────
_FORMAL_MARKERS    = {'therefore','however','furthermore','nevertheless','consequently',
                      'subsequently','alternatively','additionally','accordingly',
                      'particularly','specifically','significantly','approximately',
                      'demonstrate','indicate','suggest','examine','analyze',
                      'evaluate','conclude','implement','methodology','hypothesis'}

_INFORMAL_MARKERS  = {"don't","can't","won't","isn't","aren't","i'm","you're",
                      "we're","they're","it's","wasn't","weren't","didn't",
                      "very","really","quite","pretty","totally","awesome",
                      "amazing","great","bad","good","nice","cool","okay","ok"}

def writing_tone(text: str) -> Dict:
    """Classify writing tone as formal/informal/mixed."""
    lower = text.lower()
    tokens = set(re.findall(r"\b[\w']+\b", lower))
    formal   = len(tokens & _FORMAL_MARKERS)
    informal = len(tokens & _INFORMAL_MARKERS)
    total    = max(formal + informal, 1)
    formal_pct   = round(formal   / total * 100, 1)
    informal_pct = round(informal / total * 100, 1)
    if formal_pct >= 60:   tone = 'Formal'
    elif informal_pct >= 60: tone = 'Informal'
    else:                   tone = 'Mixed'
    return {'tone': tone, 'formal_pct': formal_pct, 'informal_pct': informal_pct,
            'formal_count': formal, 'informal_count': informal}


# ─── Citation Analysis ───────────────────────────────────────────────────────
_CITATION_PATTERNS = [
    re.compile(r'\([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|&\s+[A-Z][a-zA-Z]+))?,\s*\d{4}\)'),  # APA
    re.compile(r'\[[0-9]+\]'),                                       # IEEE
    re.compile(r'\([0-9]+\)'),                                       # Numbered
    re.compile(r'https?://[^\s<>"]+'),                               # URLs
    re.compile(r'\b10\.\d{4,}/[^\s]+'),                              # DOI
    re.compile(r'(?:et\s+al\.)', re.IGNORECASE),                     # et al.
    re.compile(r'\bISSN\b|\bISBN\b|\bDOI\b', re.IGNORECASE),
]

def analyze_citations(text: str) -> Dict:
    citations = []
    for pat in _CITATION_PATTERNS:
        citations.extend(pat.findall(text))
    unique_urls = set(re.findall(r'https?://[^\s<>"]+', text))
    unique_dois = set(re.findall(r'10\.\d{4,}/[^\s]+', text))
    count = len(citations)
    score = min(100, count * 5 + len(unique_dois) * 10 + len(unique_urls) * 3)
    return {
        'count':       count,
        'unique_urls': len(unique_urls),
        'unique_dois': len(unique_dois),
        'score':       round(score, 1),
        'quality':     'Strong' if score >= 70 else 'Moderate' if score >= 35 else 'Weak'
    }


# ─── Academic Vocabulary ─────────────────────────────────────────────────────
_ACADEMIC_WORDS = {
    'analyze','analysis','methodology','hypothesis','empirical','theoretical',
    'paradigm','significant','correlation','variable','framework','phenomenon',
    'literature','research','study','evidence','data','results','conclusion',
    'objective','subjective','qualitative','quantitative','validate','evaluate',
    'demonstrate','investigate','examine','implement','assess','illustrate',
    'indicate','suggest','propose','review','compare','contrast','classify',
    'interpret','observe','measure','calculate','estimate','determine',
    'fundamental','conceptual','systematic','comprehensive','substantial',
    'subsequent','previous','current','contemporary','traditional','conventional',
    'critical','important','essential','relevant','appropriate','effective',
    'efficient','accurate','reliable','valid','consistent','representative'
}

def academic_vocabulary_score(text: str) -> float:
    """% of academic words used relative to total unique words."""
    unique = set(re.findall(r'\b[a-zA-Z]{4,}\b', text.lower()))
    if not unique:
        return 0.0
    academic_used = unique & _ACADEMIC_WORDS
    # Bonus for density
    tokens = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    density = sum(1 for t in tokens if t in _ACADEMIC_WORDS) / max(len(tokens), 1)
    score = len(academic_used) / len(_ACADEMIC_WORDS) * 50 + density * 100 * 0.5
    return round(min(100, score), 1)


# ─── AI-Generated Content Indicator ─────────────────────────────────────────
_AI_MARKERS = {
    'phrases': [
        'it is worth noting', 'it is important to note', 'it should be noted',
        'furthermore', 'moreover', 'in conclusion', 'in summary', 'to summarize',
        'in addition', 'additionally', 'on the other hand', 'with that being said',
        'it can be argued', 'one can argue', 'it is evident', 'it is clear that',
        'a wide range of', 'a variety of', 'diverse range of', 'in today\'s world',
        'plays a crucial role', 'plays a vital role', 'plays an important role',
        'first and foremost', 'last but not least', 'needless to say',
        'delve into', 'it\'s worth mentioning', 'let\'s explore',
        'unlock the potential', 'leverage', 'in the realm of',
    ]
}

def ai_content_indicator(text: str) -> Dict:
    """
    Heuristic AI-generated content indicator.
    NOTE: This is experimental and NOT a guaranteed classifier.
    """
    lower = text.lower()
    found = [p for p in _AI_MARKERS['phrases'] if p in lower]

    sents  = get_sentences(text)
    tokens = re.findall(r'\b\w+\b', text)
    avg_sent_len = len(tokens) / max(len(sents), 1)

    # AI text tends to have uniform sentence lengths + many transition phrases
    variation = 0.0
    if sents:
        lengths = [len(s.split()) for s in sents]
        mean = sum(lengths) / len(lengths)
        variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
        variation = math.sqrt(variance)

    phrase_score  = min(100, len(found) * 8)
    uniform_score = max(0, 60 - variation * 2)   # low variation → more AI-like
    combined      = round(phrase_score * 0.6 + uniform_score * 0.4, 1)

    return {
        'probability': combined,
        'label': 'Likely AI-Assisted' if combined >= 55 else 'Likely Human' if combined < 30 else 'Uncertain',
        'markers_found': found[:8],
        'avg_sentence_length': round(avg_sent_len, 1),
        'sentence_length_variation': round(variation, 1),
        'disclaimer': 'Experimental indicator only — not a definitive classifier.'
    }


# ─── Document Structure ──────────────────────────────────────────────────────
def analyze_structure(text: str) -> Dict:
    """Analyze document sections and structure quality."""
    paras = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 20]
    sents = get_sentences(text)
    words = re.findall(r'\b\w+\b', text)

    has_intro      = any(re.search(r'\b(introduction|overview|background|abstract)\b', p, re.I) for p in paras[:3])
    has_conclusion = any(re.search(r'\b(conclusion|summary|findings|result)\b', p, re.I) for p in paras[-3:])
    has_references = bool(re.search(r'\b(references|bibliography|works cited)\b', text, re.I))

    structure_score = 0
    if has_intro:       structure_score += 25
    if has_conclusion:  structure_score += 25
    if has_references:  structure_score += 25
    if len(paras) >= 4: structure_score += 25

    return {
        'paragraph_count': len(paras),
        'sentence_count':  len(sents),
        'word_count':      len(words),
        'has_intro':       has_intro,
        'has_conclusion':  has_conclusion,
        'has_references':  has_references,
        'structure_score': structure_score,
        'avg_para_length': round(len(words) / max(len(paras), 1), 1),
    }


# ─── Contribution Scoring ────────────────────────────────────────────────────
_OPINION_KW    = {'i think','i believe','in my opinion','i argue','i propose',
                  'i suggest','we argue','we propose','our approach','we believe'}
_ANALYSIS_KW   = {'therefore','thus','hence','consequently','as a result',
                  'this shows','this indicates','this suggests','this demonstrates',
                  'which means','which implies'}
_DEFINITION_KW = {'is defined as','refers to','means that','is known as',
                  'can be described as','is characterized by'}

def contribution_score(text: str) -> Dict:
    lower = text.lower()
    opinion    = sum(1 for kw in _OPINION_KW    if kw in lower)
    analysis   = sum(1 for kw in _ANALYSIS_KW   if kw in lower)
    definition = sum(1 for kw in _DEFINITION_KW if kw in lower)
    sents      = get_sentences(text)

    raw_score = min(100, (opinion * 8 + analysis * 6 + definition * 4) * 2)
    return {
        'contribution_score': round(raw_score, 1),
        'opinion_signals':    opinion,
        'analysis_signals':   analysis,
        'definition_signals': definition,
        'total_sentences':    len(sents),
    }


# ─── Duplicate Paragraph Detection ──────────────────────────────────────────
def find_duplicate_paragraphs(text: str) -> List[Dict]:
    """Find paragraphs that are very similar to each other within the document."""
    from services.similarity import _fuzzy
    paras = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
    duplicates = []
    seen: set = set()
    for i in range(len(paras)):
        for j in range(i + 1, len(paras)):
            key = (i, j)
            if key in seen:
                continue
            score = _fuzzy(paras[i], paras[j])
            if score >= 75:
                duplicates.append({
                    'para1_index': i,
                    'para2_index': j,
                    'similarity': score,
                    'para1_snippet': paras[i][:120],
                    'para2_snippet': paras[j][:120],
                })
                seen.add(key)
    return duplicates


# ─── Grammar Quality Estimate ────────────────────────────────────────────────
def grammar_quality_estimate(text: str) -> float:
    """
    Heuristic grammar quality score based on:
    - Sentence capitalization
    - Basic punctuation patterns
    - Common error patterns
    """
    sents = get_sentences(text)
    if not sents:
        return 50.0
    score = 100.0
    penalties = 0

    for s in sents:
        s = s.strip()
        if not s:
            continue
        if not s[0].isupper():
            penalties += 2
        if not s.rstrip().endswith(('.', '?', '!')):
            penalties += 1
        # Double spaces
        if '  ' in s:
            penalties += 1
        # Common mistakes
        if re.search(r'\b(their|there|they\'re)\b', s, re.I):
            pass  # legitimate words, skip
        if re.search(r'\bI [a-z]', s):
            pass  # check "I" capitalization
        if re.search(r'\s[,;.!?]', s):
            penalties += 2  # space before punctuation

    score = max(0.0, score - penalties * 0.5)
    return round(min(100, score), 1)


# ─── Research Depth ──────────────────────────────────────────────────────────
def research_depth(text: str, citations: Dict) -> float:
    """Composite research depth score."""
    citation_score = citations.get('score', 0)
    academic_vocab = academic_vocabulary_score(text)
    words          = re.findall(r'\b\w+\b', text)
    word_count     = len(words)

    length_score   = min(100, word_count / 30)  # 3000 words → 100
    score = (citation_score * 0.40 + academic_vocab * 0.35 + length_score * 0.25)
    return round(min(100, score), 1)


# ─── Full Analysis Entry Point ────────────────────────────────────────────────
def run_full_analysis(text: str) -> Dict[str, Any]:
    """
    Run all AI analysis features on the given text.
    Returns a comprehensive dict of all metrics.
    """
    if not text or len(text.split()) < 10:
        return {'error': 'Insufficient text for analysis.'}

    citations   = analyze_citations(text)
    contrib     = contribution_score(text)
    structure   = analyze_structure(text)
    tone        = writing_tone(text)
    ai_ind      = ai_content_indicator(text)
    keywords    = keyword_density(text)
    rep_phrases = find_repeated_phrases(text)
    dup_paras   = find_duplicate_paragraphs(text)

    read_ease   = flesch_reading_ease(text)
    fk_grade    = flesch_kincaid_grade(text)
    vocab_r     = vocabulary_richness(text)
    vocab_s     = vocabulary_score(text)
    passive_pct = passive_voice_percentage(text)
    grammar     = grammar_quality_estimate(text)
    acad_vocab  = academic_vocabulary_score(text)
    res_depth   = research_depth(text, citations)

    # Normalize readability to 0-100 (Flesch: higher=easier; invert for academic)
    readability_score = round((read_ease * 0.5 + max(0, 100 - fk_grade * 5) * 0.5), 1)
    readability_score = max(0, min(100, readability_score))

    writing_quality = round((
        grammar        * 0.25 +
        vocab_s        * 0.25 +
        readability_score * 0.20 +
        max(0, 100 - passive_pct) * 0.15 +
        tone.get('formal_pct', 0) * 0.15
    ), 1)

    return {
        # Readability
        'readability_ease':    read_ease,
        'fk_grade_level':      fk_grade,
        'readability_score':   readability_score,

        # Vocabulary
        'vocabulary_richness': vocab_r,
        'vocabulary_score':    round(vocab_s, 1),
        'academic_vocab_score': acad_vocab,

        # Style
        'passive_voice_pct':   passive_pct,
        'grammar_score':       grammar,
        'writing_quality':     writing_quality,

        # Tone
        'tone':                tone,

        # Citations & Research
        'citations':           citations,
        'research_depth':      res_depth,

        # Contribution
        'contribution':        contrib,

        # Structure
        'structure':           structure,

        # AI indicator
        'ai_indicator':        ai_ind,

        # Keywords
        'keywords':            keywords,
        'repeated_phrases':    rep_phrases,
        'duplicate_paras':     dup_paras,
    }

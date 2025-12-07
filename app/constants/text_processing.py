"""
Text Processing Constants.

Keyword extraction parameters, stop words, and other text processing settings.
"""

# ============================================================================
# KEYWORD EXTRACTION PARAMETERS
# ============================================================================

KEYWORD_MIN_LENGTH = 3
"""Minimum word length for keyword extraction."""

ARXIV_MIN_WORD_LENGTH_FALLBACK = 4
"""Minimum word length for ArXiv fallback keyword extraction."""

ARXIV_MAX_KEYWORDS_FALLBACK = 4
"""Maximum keywords for ArXiv fallback search."""

QUERY_GEN_MIN_WORD_LENGTH = 3
"""Minimum word length for query generation."""

QUERY_GEN_MAX_KEYWORDS = 5
"""Maximum keywords to extract for query generation."""


# ============================================================================
# YOUTUBE CONFIGURATION
# ============================================================================

YOUTUBE_VIDEO_ID_LENGTH = 11
"""Standard YouTube video ID length."""

TEMP_COOKIE_FILE_PREFIX = "/tmp/cookies_"
"""Prefix for temporary cookie files."""


# ============================================================================
# STOP WORDS FOR KEYWORD EXTRACTION
# ============================================================================

FRENCH_STOP_WORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou",
    "mais", "donc", "car", "ni", "que", "qui", "quoi", "dont", "où",
    "ce", "cet", "cette", "ces", "mon", "ton", "son", "notre", "votre",
    "leur", "mes", "tes", "ses", "nos", "vos", "leurs", "je", "tu",
    "il", "elle", "on", "nous", "vous", "ils", "elles", "être", "avoir",
    "faire", "dire", "aller", "voir", "savoir", "pouvoir", "vouloir",
    "falloir", "devoir", "croire", "prendre", "donner", "tenir", "venir",
    "trouver", "mettre", "passer", "tout", "tous", "toute", "toutes",
    "pour", "dans", "par", "sur", "avec", "sans", "sous", "vers", "chez",
    "entre", "depuis", "pendant", "comme", "si", "plus", "moins", "très",
    "bien", "peu", "beaucoup", "trop", "assez", "encore", "déjà", "jamais",
    "toujours", "souvent", "parfois", "aussi", "ainsi", "alors", "après",
    "avant", "maintenant", "ici", "là", "partout", "ailleurs", "aujourd'hui",
    "hier", "demain", "ne", "pas", "point", "rien", "aucun", "personne",
    "quelque", "plusieurs", "autre", "même", "tel", "quel", "quelle", "quels"
}
"""Common French stop words to exclude from keyword extraction."""

ENGLISH_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "when",
    "at", "from", "by", "to", "of", "in", "on", "for", "with", "about",
    "as", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "should", "could", "may",
    "might", "must", "can", "this", "that", "these", "those", "i", "you",
    "he", "she", "it", "we", "they", "what", "which", "who", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "s", "t", "just", "now", "d", "ll", "m",
    "o", "re", "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn",
    "hasn", "haven", "isn", "ma", "mightn", "mustn", "needn", "shan",
    "shouldn", "wasn", "weren", "won", "wouldn"
}
"""Common English stop words to exclude from keyword extraction."""

COMMON_STOP_WORDS_EN_FR = ENGLISH_STOP_WORDS | FRENCH_STOP_WORDS
"""Combined English and French stop words."""

"""
community/content_filter.py
----------------------------
Lightweight text filter for community post content.

Uses better-profanity (English wordlist) plus leet-speak normalisation.
Extend CUSTOM_BAD_WORDS with Roman Urdu / Urdu terms as you encounter them.
The profanity instance is initialised once at module load — zero overhead
per request.
"""

import re
import unicodedata

from better_profanity import profanity as _profanity

# ---------------------------------------------------------------------------
# Custom words — add Roman Urdu / regional terms here.
# Use lower-case. The library handles case-insensitive matching.
# ---------------------------------------------------------------------------
CUSTOM_BAD_WORDS: list[str] = [
    # Add Roman Urdu abuse terms here as you discover them, e.g.:
    # "gandu", "madarchod", "bhen", "harami",
]

# ---------------------------------------------------------------------------
# Leet-speak / character-substitution map
# ---------------------------------------------------------------------------
_LEET = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a',
    '5': 's', '6': 'g', '7': 't', '8': 'b',
    '@': 'a', '$': 's', '!': 'i', '+': 't',
})

# ---------------------------------------------------------------------------
# Initialise profanity checker once
# ---------------------------------------------------------------------------
_profanity.load_censor_words(whitelist_words=[])
if CUSTOM_BAD_WORDS:
    _profanity.add_censor_words(CUSTOM_BAD_WORDS)


def _normalise(text: str) -> str:
    """
    Reduce common evasion tricks to their plain equivalents:
      - Unicode → ASCII (strips diacritics and lookalike glyphs)
      - Leet-speak digit/symbol substitution
      - Collapse runs of 3+ repeated characters to 2 (shiiit → shiit)
      - Collapse whitespace
    """
    t = unicodedata.normalize("NFKD", text)
    t = t.encode("ascii", "ignore").decode()
    t = t.translate(_LEET)
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_abusive(text: str | None) -> bool:
    """
    Return True if text contains profanity or abusive language.

    Safe to call with None or empty string — returns False.
    """
    if not text or not text.strip():
        return False
    return _profanity.contains_profanity(_normalise(text))

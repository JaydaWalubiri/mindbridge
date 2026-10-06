"""Conservative phrase matching; this is not a clinical language classifier."""
import re
import unicodedata


# These are explicit test variants, not fuzzy guesses. Administrators can add
# locally reviewed phrases to the keyword library without changing this module.
VARIANTS = {
    "want to die": ("wanna die", "want 2 die"),
    "want to kill myself": ("wanna kill myself", "want to kill my self"),
    "want to hurt myself": ("wanna hurt myself", "want to hurt my self"),
    "want to end my life": ("wanna end my life",),
    "feel hopeless": ("feeling hopeless",),
    "feel worthless": ("feeling worthless",),
    "feel trapped": ("feeling trapped",),
    "feel like a burden": ("feeling like a burden",),
    "feel completely alone": ("feeling completely alone",),
}

# Suppress only direct English negation immediately before a recognised
# predicate. Do not suppress ambiguous statements or arbitrary custom phrases.
NEGATABLE = re.compile(r"^(?:want|wanna|feel|feeling|thinking)\b")
DIRECT_NEGATION = re.compile(
    r"\b(?:do not|don't|dont|does not|doesn't|not|never|no longer)"
    r"(?:\s+(?:really|actually|ever))?\s*$"
)


def normalise(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("’", "'").replace("‘", "'")
    # Keep sentence/clause punctuation: a denial in one clause must not hide
    # an affirmative phrase in the next. Hyphens are word separators.
    text = re.sub(r"[-‐‑–—]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def matches_keyword(text, term):
    text, term = normalise(text), normalise(term)
    if not term:
        return False
    for phrase in (term, *VARIANTS.get(term, ())):
        pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
        for match in re.finditer(pattern, text):
            prefix = text[:match.start()]
            if NEGATABLE.match(phrase) and DIRECT_NEGATION.search(prefix):
                continue
            return True
    return False

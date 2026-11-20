"""Public, non-sensitive bindings for externally checked product descriptions."""
import hashlib
import math
import re
import unicodedata

ORIGINALITY_POLICY = 'tavily-keyless-description-v1'
ORIGINALITY_LANGUAGES = ('ru', 'en', 'pt', 'es', 'fr', 'he')


def description_hash(text):
    """Ignore canonical Unicode/whitespace differences, never wording or case."""
    if not isinstance(text, str):
        raise TypeError('description must be a string')
    canonical = ' '.join(unicodedata.normalize('NFC', text).split())
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def receipt_hashes(receipt):
    """Return the six checked hashes, or None for missing/invalid evidence."""
    if not isinstance(receipt, dict) or receipt.get('policy') != ORIGINALITY_POLICY:
        return None
    locales = receipt.get('locales')
    if not isinstance(locales, dict) or set(locales) != set(ORIGINALITY_LANGUAGES):
        return None
    hashes = {}
    for language in ORIGINALITY_LANGUAGES:
        evidence = locales[language]
        if not isinstance(evidence, dict):
            return None
        digest, checked_at = evidence.get('sha256'), evidence.get('checked_at')
        if (not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)
                or type(checked_at) not in (int, float) or not math.isfinite(checked_at) or checked_at <= 0):
            return None
        hashes[language] = digest
    return hashes

"""Two lifetime copy drafts per seller-fact version, with durable review resumes.

The caller owns the product journal and serializes writers. Checkpoint reservations
before requests: a lost response consumes its opportunity, including quota waits.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

from .gemini_client import COPY_POLICY, GeminiDeferred


def copy_source_version(title):
    text = unicodedata.normalize('NFKC', str(title or '')).casefold()
    # Formatting is immaterial. Preserve signs, fractions, ranges and unit symbols
    # when punctuation conveys a factual difference in a seller specification.
    text = re.sub(r'(?<=\d)[.,](?=\d)', '\ue000', text)
    text = re.sub(r'(?<=\d)\s*[/\u2044]\s*(?=\d)', '\ue001', text)
    text = re.sub(r'(?<=\d)\s*[-\u2013\u2014]\s*(?=\d)', '\ue002', text)
    text = re.sub(r'(?<!\w)[-\u2212](?=\d)', '\ue003', text)
    normalized = ''.join(c for c in text if c.isalnum() or c in '+%\u00b0\u00b1\u2030\ue000\ue001\ue002\ue003')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


class GeminiCopyStopped(GeminiDeferred):
    """Terminal for this seller-text version; retry requires new factual evidence."""
    def __init__(self, reason, source_version):
        self.reason = re.sub(r'[^a-z0-9_-]', '_', str(reason).lower())[:100]
        self.source_version = source_version
        super().__init__('gemini_copy_validation_failed')


def _journal(source_title, state, scope):
    version = copy_source_version(source_title)
    if state is None:
        state = {}
    if not isinstance(state, dict):
        raise GeminiCopyStopped('copy_state_invalid', version)
    versions = state.setdefault('versions', {})
    if not isinstance(versions, dict):
        raise GeminiCopyStopped('copy_state_invalid', version)
    history = versions.setdefault(version, {})
    if not isinstance(history, dict):
        raise GeminiCopyStopped('copy_state_invalid', version)
    journal = history.setdefault(scope, {'drafts': []})
    if (not isinstance(journal, dict) or not isinstance(journal.get('drafts'), list)
            or len(journal['drafts']) > 2 or not all(isinstance(draft, dict) for draft in journal['drafts'])):
        raise GeminiCopyStopped('copy_state_invalid', version)
    return version, journal


def _persist(checkpoint):
    if checkpoint is not None:
        try:
            checkpoint()
        except Exception:
            raise GeminiDeferred('checkpoint_unavailable') from None


def reject_cached_copy(title, copy_state, checkpoint=None, reason='copy_outer_validation_failed', *, problems=()):
    """An outer lint failure invalidates acceptance, never resets consumed drafts."""
    version, journal = _journal(title, copy_state, 'bundle')
    if journal.get('stopped_reason'):
        raise GeminiCopyStopped(journal['stopped_reason'], version)
    reason = re.sub(r'[^a-z0-9_-]', '_', str(reason).lower())[:100]
    if not journal['drafts']:
        # A validated cache predating this journal still consumed the first draft.
        journal['drafts'].append({'status': 'rejected', 'review_attempts': 0})
    journal['drafts'][-1].update(status='rejected', reason=reason,
        problems=[str(problem)[:500] for problem in problems][:24] or ['Outer copy validation failed; rewrite using only seller facts.'])
    exhausted = len(journal['drafts']) >= 2
    if exhausted:
        journal['stopped_reason'] = reason
    _persist(checkpoint)
    if exhausted:
        raise GeminiCopyStopped(reason, version)


TRANSIENT_PROVIDER_CODES = frozenset({
    'gemini_http_500', 'gemini_http_502', 'gemini_http_503', 'gemini_http_504',
    'gemini_http_429', 'gemini_rate_wait', 'gemini_daily_budget', 'gemini_timeout',
    'checkpoint_unavailable',
})
# Retained for import compatibility; transient provider outages no longer count toward lifetime draft bans.
MAX_TRANSIENT_RETRIES = 4


def run_bounded_copy(source_title, *, scope, state, checkpoint, generate, validate, review,
                     verify_external=None, before_generate=None):
    """Return one accepted draft; callbacks never gain additional retry loops here."""
    version, journal = _journal(source_title, state, scope)

    def persist():
        _persist(checkpoint)

    def stop(reason):
        journal['stopped_reason'] = reason
        persist()
        raise GeminiCopyStopped(reason, version)

    if journal.get('stopped_reason'):
        raise GeminiCopyStopped(journal['stopped_reason'], version)
    drafts = journal['drafts']
    while True:
        draft = drafts[-1] if drafts else None
        if draft and draft.get('status') == 'reserved':
            # A previous process died between reserving and saving its response.
            draft.update(status='failed', reason='copy_generation_response_lost')
            persist()
        if draft is None or draft.get('status') in ('failed', 'rejected'):
            if len(drafts) >= 2:
                stop(draft.get('reason', 'copy_generation_reservations_exhausted'))
            if before_generate is not None:
                before_generate()
            problems = (draft or {}).get('problems', [])
            draft = {'status': 'reserved', 'review_attempts': 0}
            drafts.append(draft)
            try:
                persist()
            except GeminiDeferred:
                # Failed to checkpoint BEFORE calling the provider: undo phantom reservation.
                drafts.pop()
                raise
            try:
                candidate, provider = generate(problems)
            except GeminiDeferred as error:
                transient_count = int(journal.get('transient_retries', 0))
                if error.code in TRANSIENT_PROVIDER_CODES:
                    # Transient provider overload/rate-limit/checkpoint blip must never burn a lifetime draft.
                    drafts.pop()
                    journal['transient_retries'] = transient_count + 1
                    try:
                        persist()
                    except GeminiDeferred:
                        pass
                    raise
                draft.update(status='failed', reason='copy_generation_' + error.code)
                persist()
                if len(drafts) >= 2:
                    stop(draft['reason'])
                raise
            draft.update(status='draft', candidate=candidate, provider=provider)
            persist()
        if draft.get('status') not in ('draft', 'accepted') or 'candidate' not in draft:
            stop('copy_state_invalid')
        candidate = draft['candidate']
        problems = validate(candidate)
        if problems:
            draft.update(status='rejected', problems=problems[:24], reason='copy_lint_failed')
            persist()
            continue
        if draft.get('status') != 'accepted' or draft.get('policy') != COPY_POLICY:
            attempts = draft.get('review_attempts', 0)
            if type(attempts) is not int or attempts < 0:
                stop('copy_state_invalid')
            if attempts >= 2:
                stop(draft.get('reason', 'copy_claim_review_response_lost'))
            draft['review_attempts'] = attempts + 1
            draft['status'] = 'draft'
            try:
                persist()
            except GeminiDeferred:
                draft['review_attempts'] = attempts
                raise
            try:
                problems = review(candidate)
            except GeminiDeferred as error:
                transient_count = int(journal.get('transient_review_retries', 0))
                if error.code in TRANSIENT_PROVIDER_CODES:
                    draft['review_attempts'] = attempts
                    draft['reason'] = 'copy_claim_review_' + error.code
                    journal['transient_review_retries'] = transient_count + 1
                    try:
                        persist()
                    except GeminiDeferred:
                        pass
                    raise
                draft['reason'] = 'copy_claim_review_' + error.code
                persist()
                if draft['review_attempts'] >= 2:
                    stop(draft['reason'])
                raise
            if problems and problems[0].startswith('source_claims: incomplete'):
                # A malformed checker response says nothing about the existing draft.
                draft['reason'] = 'copy_claim_review_invalid'
                persist()
                if draft['review_attempts'] >= 2:
                    stop(draft['reason'])
                raise GeminiDeferred('gemini_claim_review_invalid')
            if problems:
                draft.update(status='rejected', problems=problems[:24], reason='copy_source_claims_failed')
                persist()
                continue
            draft.update(status='accepted', policy=COPY_POLICY)
            persist()
        if verify_external is not None:
            # May defer here. The accepted fact review and the draft bytes are durable.
            # The search cache decides which locales still need fresh online evidence.
            problems = verify_external(candidate)
            if problems:
                draft.update(status='rejected', problems=problems[:24], reason='copy_external_overlap')
                persist()
                continue
        return candidate, draft['provider']

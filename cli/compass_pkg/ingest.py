#!/usr/bin/env python3
# =============================================================================
# compass - reading an existing brief into an issue
# =============================================================================
# Most teams arriving at Compass already have a brief somewhere - Notion, Jira,
# a Google Doc, a file called anything at all. Until this existed, the only way
# in was to open it, read it, and retype it through the intake stage, which is
# transcription and so the kind of step people skip.
#
# THIS MODULE IS THE MECHANICAL HALF, AND ONLY THAT. Resolving a source,
# refusing a scheme, following a redirect, hashing what arrived - the same
# input gives the same answer every time, so it belongs here where it can be
# tested without a person and without a network.
#
# Turning the document into intent.md is JUDGEMENT and lives in a skill:
# deciding that a paragraph about "who this is for" belongs under Users, and
# noticing that no non-goals are stated so a question needs asking. Nothing in
# this module writes intent.md. See technical-design.md DD-1.
#
# DEPENDENCY: `urllib.request` is standard library, so nothing joins the
# dependency set and ADR-013 (vendored third-party code) is not in play. What
# is new is that Compass makes an outbound request at all - it had made none,
# anywhere, before this. That is why the scheme rule below is enforced twice.
# =============================================================================
"""Resolving and reading a brief that already exists, by path or https URL."""
from __future__ import annotations

import hashlib
import os
import urllib.error
import urllib.request

from compass_pkg.core import CompassError

#: The only URL scheme a brief is fetched over.
#:
#: A brief becomes the issue's intent, so a document altered in transit would
#: silently shape the acceptance criteria, the design, and everything after
#: them. Recording that it arrived over plain HTTP would not prevent any of
#: that - recording is not preventing.
#:
#: Private and internal addresses are fine, as long as they are https: an
#: internal wiki is the likeliest real source, and the person typing the URL is
#: the person running the tool, on their own machine, with their own network
#: access. The usual argument for blocking them is about a server fetching an
#: attacker's URL, and there is no attacker here.
ALLOWED_URL_SCHEME = "https"

#: Schemes that name a URL rather than a path, so a bad one is reported as a
#: refused scheme rather than as a missing file.
_URLISH = ("http://", "https://", "ftp://", "file://", "gopher://", "data:")


class SourceDocument:
    """A brief that was read, and where it came from.

    `origin` is where the document ACTUALLY came from - after redirects, not
    the address that was typed. The risk the redirect rule exists for is
    ingesting a different document from the one asked for, and recording the
    typed address would hide exactly that.
    """

    __slots__ = ("text", "origin", "scheme", "sha256")

    def __init__(self, text, origin, scheme):
        self.text = text
        self.origin = origin
        self.scheme = scheme
        self.sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    def __repr__(self):
        return "SourceDocument(origin=%r, scheme=%r, sha256=%r)" % (
            self.origin, self.scheme, self.sha256[:12])


def _looks_like_url(spec):
    return spec.split("?", 1)[0].lower().startswith(_URLISH)


def _refuse_empty(text, origin):
    """A document that reads as nothing is not a brief.

    A fetch can succeed and return an empty body - a login page that
    redirected to nothing, a file someone truncated. Accepting it produces an
    intent.md built on no material at all, and every stage after would proceed
    as though there were an intent.
    """
    if not text.strip():
        raise CompassError(
            "the source at %s is empty - there is nothing to build an intent "
            "from. Check it is the document you meant, and that it is not a "
            "login page or a truncated export." % origin)
    return text


def _read_file(spec):
    if os.path.isdir(spec):
        # `os.path.exists` is true for a directory, so a check that only asks
        # whether the path exists gets an IsADirectoryError out of `open` - a
        # traceback rather than a message. Different mistake, different fix,
        # so it earns its own sentence.
        raise CompassError(
            "the source %s is a directory, not a document. Name the file "
            "inside it that holds the brief." % spec)
    if not os.path.isfile(spec):
        raise CompassError(
            "no such source: %s - nothing was read and no issue directory was "
            "created. Check the path, or pass an https URL." % spec)
    try:
        with open(spec, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise CompassError("could not read the source %s: %s" % (spec, exc))
    except UnicodeDecodeError:
        raise CompassError(
            "the source %s is not UTF-8 text. Compass reads briefs as text; "
            "export it to Markdown or plain text first." % spec)
    return SourceDocument(_refuse_empty(text, spec), spec, "file")


def validate_source(spec):
    """Check the source SPEC alone - no filesystem, no network, no issue state.

    Split out so a caller can refuse a bad argument before it looks at anything
    else. Running the state checks first meant an `http://` URL on an issue
    that had already ingested something was refused with "intent-source.md
    already exists" - true, unrelated, and confidently pointing the reader at
    the wrong thing to fix. A refusal that names the wrong cause is worse than
    a vague one.

    Returns the cleaned spec.
    """
    spec = (spec or "").strip()
    if not spec:
        raise CompassError(
            "no source given - name a file or an https URL holding the brief.")
    if _looks_like_url(spec):
        scheme = spec.split(":", 1)[0].lower()
        if scheme != ALLOWED_URL_SCHEME:
            raise CompassError(
                "%s is not an https source, and Compass fetches briefs over "
                "https only - a document altered in transit would shape this "
                "issue's acceptance criteria and everything after them. "
                "Export it to a file and pass the path instead." % spec)
    return spec


def read_source(spec, opener=None):
    """Read a brief from a local path or an https URL.

    `opener` is injected so the fetch path is testable with no network at all -
    a test that needs one is a test that does not get run.

    Raises CompassError for every failure, always naming the source it tried.
    "Could not read the source" sends a reader nowhere; most of the time the
    answer is a typo they can see the moment it is quoted back to them.
    """
    spec = validate_source(spec)

    if not _looks_like_url(spec):
        return _read_file(spec)

    fetch = opener or _fetch_https
    try:
        text, final_url = fetch(spec)
    except CompassError:
        raise
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise CompassError(
                "the source %s needs credentials Compass does not have (HTTP "
                "%d). Compass does not authenticate to fetch a brief - export "
                "it to a file and pass the path instead." % (spec, exc.code))
        raise CompassError(
            "could not fetch the source %s: HTTP %d %s"
            % (spec, exc.code, exc.reason))
    except Exception as exc:                       # noqa: BLE001
        # Deliberately broad, and re-raised rather than swallowed. The danger
        # is not the error - it is an empty document arriving as though it were
        # the brief. The underlying reason is kept, so a reader can tell a typo
        # from an outage.
        raise CompassError(
            "could not fetch the source %s: %s" % (spec, exc))

    # The opener's contract is (text, final_url). It is stated here rather than
    # defended against: a branch tolerating some other shape could never fire
    # after the unpack above, and dead tolerance reads as care while checking
    # nothing.
    final_url = final_url or spec
    return SourceDocument(_refuse_empty(text, final_url), final_url, "https")


class _HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-applies the scheme rule to every redirect hop.

    THE POINT OF THIS CLASS: `urllib.request` follows redirects AUTOMATICALLY.
    An https URL that redirects to http would be fetched with the caller never
    seeing it - so checking the scheme only on the URL the person typed passes
    on paper and fails in fact, which is the shape of guard this repository has
    found several of. `test_ing_d4b` proves the refusal by attempting a real
    downgrade rather than by asserting a clean run.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.lower().startswith(ALLOWED_URL_SCHEME + "://"):
            raise CompassError(
                "the source redirected to %s, which is not https - Compass "
                "will not follow a redirect off https, because a document "
                "altered in transit would shape this issue's acceptance "
                "criteria and everything after them. Export it to a file and "
                "pass the path instead." % newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _https_only_redirect_handler():
    """The handler, for the guard that proves it refuses a downgrade."""
    return _HttpsOnlyRedirectHandler()


#: What a fetch says it is. A brief is a document, and a server that content-
#: negotiates should be told so rather than guessing from a default.
_ACCEPT = "text/markdown, text/plain, text/html;q=0.9, */*;q=0.1"
_USER_AGENT = "compass/%s (+https://github.com/jed72/compass)"

#: Enough for a brief, and a ceiling so a misdirected fetch cannot pull an
#: arbitrarily large body into memory before anyone notices.
MAX_SOURCE_BYTES = 5 * 1024 * 1024

#: A fetch that hangs is indistinguishable from one that is slow, and a stage
#: that never returns is worse than one that fails.
FETCH_TIMEOUT_SECONDS = 30


def _fetch_https(url):
    """Fetch a brief over https. Returns (text, final_url_after_redirects).

    No authentication handler is installed, deliberately: a 401 or 403 is
    refused with a way forward rather than retried with credentials. Compass is
    not growing an auth story - see ING-D1.
    """
    from compass_pkg.core import COMPASS_VERSION

    opener = urllib.request.build_opener(_HttpsOnlyRedirectHandler())
    request = urllib.request.Request(url, headers={
        "Accept": _ACCEPT,
        "User-Agent": _USER_AGENT % COMPASS_VERSION,
    })
    with opener.open(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        raw = response.read(MAX_SOURCE_BYTES + 1)
        final_url = response.geturl()
    if len(raw) > MAX_SOURCE_BYTES:
        raise CompassError(
            "the source at %s is larger than %d MB. A brief should not be - "
            "check the address points at the document rather than an archive "
            "or an export bundle."
            % (final_url, MAX_SOURCE_BYTES // (1024 * 1024)))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise CompassError(
            "the source at %s is not UTF-8 text. Compass reads briefs as "
            "text; export it to Markdown or plain text first." % final_url)
    return text, final_url


# =============================================================================
# The verb
# =============================================================================

#: The snapshot of what actually arrived, kept beside intent.md and never
#: edited. This is what makes the invention rule auditable: the rule is that
#: every statement in intent.md traces to the source or to a recorded answer,
#: and nobody can check that afterwards against a document that is not there.
#: A hash proves the source has not changed; it cannot show what was in it.
SNAPSHOT_NAME = "intent-source.md"


def cmd_intent_ingest(args):
    """`compass intent ingest --from <path-or-https-url>`.

    Brings a brief that already exists into the issue and stops. It writes the
    snapshot and the provenance record; it does NOT write intent.md, because
    reshaping the document is judgement and lives in a skill - see
    technical-design.md DD-1.

    Nothing is written until the source has been read successfully, so a bad
    path leaves the issue exactly as it was.
    """
    from compass_pkg.core import load_task, now_iso, resolve_task_dir, save_task
    from compass_pkg.terminal import say

    # The argument first, before anything about the issue. See validate_source.
    source = validate_source(args.source)

    task_dir = resolve_task_dir(getattr(args, "task", None))
    snapshot = os.path.join(task_dir, SNAPSHOT_NAME)

    # Checked BEFORE the fetch: re-ingesting must not silently replace the
    # record of what arrived the first time, and the second run is exactly when
    # someone is unsure what the first one did.
    if os.path.exists(snapshot):
        raise CompassError(
            "%s already exists in this issue - a brief has been ingested "
            "before, and overwriting it would destroy the record that "
            "intent.md is checked against. Move it aside first if you really "
            "mean to start over." % SNAPSHOT_NAME)

    document = read_source(source)

    with open(snapshot, "w", encoding="utf-8") as fh:
        fh.write(document.text)

    task, path = load_task(task_dir)
    task["intent_source"] = {
        "origin": document.origin,
        "scheme": document.scheme,
        "sha256": document.sha256,
        "ingested_at": now_iso(),
        "snapshot": SNAPSHOT_NAME,
        # Filled by the elicitation skill as it asks and is answered. Present
        # and empty means "nothing asked yet", which is different from absent.
        "elicitation": [],
    }
    save_task(task, path)

    return say(args, "compass intent ingest: read %s" % document.origin,
               detail=["snapshot -> %s" % snapshot,
                       "sha256   -> %s" % document.sha256[:16],
                       "intent.md is NOT written here - the reshaping stage "
                       "asks its questions first"],
               origin=document.origin, sha256=document.sha256,
               snapshot=snapshot)

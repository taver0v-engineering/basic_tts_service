"""
Safe HTTP header construction.

HTTP header values must be encodable as latin-1 (RFC 7230 §3.2.4, and
what Starlette/FastAPI actually enforce when building a Response). Any
user- or library-derived value -- an article title, a voice label, a
detected-language display name -- can contain arbitrary Unicode and will
crash the response *after* the expensive work has already been done, with
a UnicodeEncodeError deep inside starlette.responses.Response.init_headers.

Rather than sprinkling urllib.parse.quote() at each Response(...) call
site (trivially forgotten when someone adds a new header later), every
value destined for a custom header on our responses is routed through
safe_headers(). Values are percent-encoded to guaranteed-ASCII; the
frontend decodes each one it reads with decodeURIComponent (see
frontend/index.html's readHeader()).

Keys are left untouched -- header *names* are ASCII by spec; only values
can carry user data.
"""

from urllib.parse import quote


def _encode(value) -> str:
    """Percent-encode a single header value to guaranteed-ASCII.

    None becomes an empty string (so callers can pass optional values
    directly instead of `x or ""` at every site). Everything else goes
    through str() first, so numbers are fine to pass as-is.
    """
    if value is None:
        return ""
    return quote(str(value), safe="")


def safe_headers(headers: dict) -> dict:
    """Return a copy of `headers` with every value percent-encoded to ASCII.

    Use for the `headers=` argument of any Response/JSONResponse you
    construct. Values may be str, int, float, None, or anything whose
    str() is meaningful.
    """
    return {key: _encode(value) for key, value in headers.items()}
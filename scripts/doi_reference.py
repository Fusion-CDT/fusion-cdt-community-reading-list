"""
DOI Reference — a Python Markdown preprocessor extension.

Reads a `doi` field from a Markdown page's YAML front matter, fetches metadata
from the appropriate API, and inserts a formatted reference header at build time
without modifying source (Markdown) files.

Zensical strips front matter before passing content to `md.convert()`, so it is
not available in the text the preprocessor receives. However, Zensical has
already parsed it into a `meta` local in its `render()` frame before calling
`md.convert()`. We read that variable directly via `inspect.stack()`.

Two metadata sources are supported, dispatched on the DOI prefix:
  - Crossref  (default) — journal articles, books, etc.
  - DataCite  (10.48550) — arXiv preprints
"""

import inspect
import json
import urllib.request
from markdown import Extension
from markdown.preprocessors import Preprocessor

# In-memory cache: one HTTP request per DOI per build
_cache = {}

# DOI prefixes registered with DataCite rather than Crossref
_DATACITE_PREFIXES = ("10.48550",)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def _fetch(doi):
    if doi in _cache:
        return _cache[doi]
    if doi.startswith(_DATACITE_PREFIXES):
        data = _fetch_datacite(doi)
    else:
        data = _fetch_crossref(doi)
    _cache[doi] = data
    return data


def _fetch_crossref(doi):
    url = f"https://doi.org/{doi}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _fetch_datacite(doi):
    url = f"https://api.datacite.org/dois/{doi}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _first_or_str(value):
    """Return the first element if value is a list, otherwise the value itself.

    The Crossref API schema defines fields like `title` and `container-title`
    as arrays even though a given article only ever has one value. This handles
    both the array and plain-string forms defensively.
    """
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _initials(given):
    """Return concatenated initials from a given name string.

    E.g. "Gregory G." -> "GG", "William" -> "W", "E. G." -> "EG".
    """
    return "".join(part[0] for part in given.split())


def _header_lines(title, authors, journal_line, doi):
    """Return the common list of Markdown/HTML lines for a reference header."""
    doi_url = f"https://doi.org/{doi}"
    return [
        f"# {title}",
        f"<p class='ref-authors'>{authors}</p>",
        f"<p class='ref-journal'>{journal_line}</p>",
        f"<p class='ref-doi'><b>DOI:</b> <a href='{doi_url}'>{doi_url}</a></p>",
        "",
        "---",
        "",
    ]


# ---------------------------------------------------------------------------
# Per-source formatters
# ---------------------------------------------------------------------------


def _format_crossref(data, doi):
    """Format a Crossref metadata record (journal articles, etc.)."""
    title = _first_or_str(data["title"])
    authors = ", ".join(
        _initials(a["given"]) + " " + a["family"]
        for a in data["author"]
    )
    journal = _first_or_str(data["container-title"])
    vol = data["volume"]
    issue = data["issue"]
    pages = data.get("page", data.get("article-number", "")).replace("-", "\u2013")
    year = str(data["issued"]["date-parts"][0][0])

    journal_line = f"<em>{journal}</em>, <b>{vol}</b>({issue}), {pages} ({year})"
    return _header_lines(title, authors, journal_line, doi)


def _format_datacite_arxiv(data, doi):
    """Format a DataCite metadata record for an arXiv preprint."""
    attrs = data["data"]["attributes"]

    title = attrs["titles"][0]["title"]
    authors = ", ".join(
        _initials(c["givenName"]) + " " + c["familyName"]
        for c in attrs["creators"]
    )
    arxiv_id = next(
        i["identifier"]
        for i in attrs["identifiers"]
        if i["identifierType"] == "arXiv"
    )
    year = attrs["publicationYear"]

    journal_line = f"arXiv:{arxiv_id} ({year})"
    return _header_lines(title, authors, journal_line, doi)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _format_header(data, doi):
    if doi.startswith(_DATACITE_PREFIXES):
        return _format_datacite_arxiv(data, doi)
    return _format_crossref(data, doi)


# ---------------------------------------------------------------------------
# Markdown extension
# ---------------------------------------------------------------------------


class DoiReferencePreprocessor(Preprocessor):
    """Inject a formatted reference header for pages with a frontmatter doi."""

    def _doi_from_render_frame(self):
        """Read doi from Zensical's `render()` frame.

        Zensical parses frontmatter into a `meta` local before calling
        `md.convert()` and therefore before preprocessors run. We walk
        the call stack to find that frame and read the value directly.
        """
        for frame_info in inspect.stack():
            func = frame_info.function
            name = frame_info.frame.f_globals.get("__name__")
            if (func == "render") and (name == "zensical.markdown"):
                meta = frame_info.frame.f_locals.get("meta", {})
                return meta.get("doi")
        return None

    def run(self, lines):
        doi = self._doi_from_render_frame()
        if not doi:
            return lines

        try:
            data = _fetch(doi)
        except Exception:
            return lines

        return _format_header(data, doi) + lines


class DoiReferenceExtension(Extension):
    """Python Markdown extension that wires up the DOI reference preprocessor.

    Registered in `zensical.toml` under `[project.markdown_extensions.doi_reference]`.
    The priority of 30 places it before Python Markdown's built-in `meta`
    preprocessor (priority 27), though in practice Zensical strips front matter
    before calling `md.convert()`, so the ordering is not significant here.
    """

    def extendMarkdown(self, md):
        md.preprocessors.register(
            DoiReferencePreprocessor(md), "doi_reference", 30
        )


def makeExtension(**kwargs):
    """Entry point called by Python Markdown when loading the extension by name."""
    return DoiReferenceExtension(**kwargs)

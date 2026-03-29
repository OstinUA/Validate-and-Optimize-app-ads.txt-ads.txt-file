"""UI rendering helpers for templated HTML and static CSS.

This module centralizes file-backed rendering primitives used by the Streamlit
application so HTML/CSS snippets remain externalized from orchestration logic.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"


def _read_file(path: Path) -> str:
    """Read a UTF-8 text file and return its content.

    Args:
        path (Path): Absolute or relative filesystem path to a UTF-8 text file.

    Returns:
        str: Full file content as a decoded string.

    Raises:
        FileNotFoundError: If the target file does not exist.
        OSError: If the file cannot be read due to filesystem issues.

    Examples:
        >>> from pathlib import Path
        >>> _read_file(Path("templates/result_header.html")).startswith("<h3")
        True
    """
    return path.read_text(encoding="utf-8")


def load_css() -> str:
    """Load the project stylesheet and wrap it in an HTML style tag.

    Args:
        None.

    Returns:
        str: HTML style block string ready to be passed to
        ``st.markdown(..., unsafe_allow_html=True)``.

    Raises:
        FileNotFoundError: If ``assets/css/styles.css`` is missing.
        OSError: If the stylesheet cannot be read.

    Examples:
        >>> load_css().startswith("<style>")
        True
    """
    css = _read_file(ASSETS_DIR / "css" / "styles.css")
    return f"<style>{css}</style>"


def render_result_header(domain: str) -> str:
    """Render the results heading template for the active domain.

    Args:
        domain (str): Domain label displayed in the heading.

    Returns:
        str: Rendered HTML heading string with the injected ``domain`` value.

    Raises:
        FileNotFoundError: If ``templates/result_header.html`` is missing.
        KeyError: If template placeholders do not match expected keys.
        OSError: If the template cannot be read.

    Examples:
        >>> "example.com" in render_result_header("example.com")
        True
    """
    template = _read_file(TEMPLATES_DIR / "result_header.html")
    return template.format(domain=domain)


def render_metrics(stats: dict) -> str:
    """Render metrics summary cards from the HTML template.

    Args:
        stats (dict): Aggregate metrics dictionary expected to contain
            ``valid``, ``unique``, ``errors``, and ``duplicates`` integer keys.

    Returns:
        str: Rendered HTML block containing the current metrics values.

    Raises:
        FileNotFoundError: If ``templates/metrics.html`` is missing.
        KeyError: If required metric keys are absent in ``stats`` or template
            placeholders are inconsistent.
        OSError: If the template cannot be read.

    Examples:
        >>> html = render_metrics({"valid": 1, "unique": 1, "errors": 0, "duplicates": 0})
        >>> "Valid Records" in html
        True
    """
    template = _read_file(TEMPLATES_DIR / "metrics.html")
    return template.format(
        valid=stats["valid"],
        unique=stats["unique"],
        errors=stats["errors"],
        duplicates=stats["duplicates"],
    )


def render_logs(logs: list[dict]) -> str:
    """Render warning and error messages for the UI log panel.

    Args:
        logs (list[dict]): Ordered list of log dictionaries. Each entry is
            expected to include ``type`` (``error`` or ``warning``) and
            ``msg`` string fields.

    Returns:
        str: Rendered HTML container for issue messages or a success-state
        message when the input list is empty.

    Raises:
        KeyError: If a log entry omits required keys.

    Examples:
        >>> render_logs([]).count("No issues found.") == 1
        True
        >>> "log-error" in render_logs([{"type": "error", "msg": "Line 1"}])
        True
    """
    if not logs:
        return "<div class='log-container'><div class='log-success'>No issues found.</div></div>"

    entries = []
    for log in logs:
        if log["type"] == "error":
            entries.append(
                f"<div class='log-item log-error'><span class='icon-red'>●</span>{log['msg']}</div>"
            )
        else:
            entries.append(
                f"<div class='log-item log-warning'><span class='icon-yellow'>▲</span>{log['msg']}</div>"
            )

    return f"<div class='log-container'>{''.join(entries)}</div>"

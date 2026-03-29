"""UI rendering helpers for templated HTML and static CSS."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_css() -> str:
    """Load stylesheet content and wrap it for Streamlit markdown injection."""
    css = _read_file(ASSETS_DIR / "css" / "styles.css")
    return f"<style>{css}</style>"


def render_result_header(domain: str) -> str:
    """Render the result heading with the active domain label."""
    template = _read_file(TEMPLATES_DIR / "result_header.html")
    return template.format(domain=domain)


def render_metrics(stats: dict) -> str:
    """Render metric cards from the metrics template."""
    template = _read_file(TEMPLATES_DIR / "metrics.html")
    return template.format(
        valid=stats["valid"],
        unique=stats["unique"],
        errors=stats["errors"],
        duplicates=stats["duplicates"],
    )


def render_logs(logs: list[dict]) -> str:
    """Render warning/error entries for the log panel."""
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

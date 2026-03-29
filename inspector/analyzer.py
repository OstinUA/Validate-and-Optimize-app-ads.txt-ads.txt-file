"""Core parsing and validation helpers for ads.txt-style content.

This module provides deterministic parsing and validation utilities used by the
Streamlit UI layer. Functions here are side-effect free and intentionally kept
independent from rendering concerns.
"""

from urllib.parse import urlparse

VALID_TYPES = {"DIRECT", "RESELLER"}


def clean_url(url):
    """Normalize user input into a domain token used for remote fetches.

    Args:
        url (str | None): Raw domain or URL value from user input. The value
            may be a bare host (for example, ``example.com``) or a full URL
            (for example, ``https://example.com/path``).

    Returns:
        str | None: Normalized domain/host component if parsing succeeds, the
        original value when parsing fallback is required, or ``None`` when the
        input is falsy.

    Raises:
        None: This function catches URL parsing errors and returns a fallback
        string instead of propagating exceptions.

    Examples:
        >>> clean_url("example.com")
        'example.com'
        >>> clean_url("https://news.example.com/path")
        'news.example.com'
        >>> clean_url("")
        None
    """
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else parsed.path
    except Exception:
        return url


def parse_line_data(line):
    """Parse one ads.txt line into a structured record payload.

    Args:
        line (str): Raw line content from an ads.txt-style file. The value may
            include comments after ``#`` and optional whitespace.

    Returns:
        dict[str, str | bool] | None: A normalized record dictionary containing
        parsed fields and validity metadata, or ``None`` when the effective
        line is empty after stripping comments and whitespace.

    Raises:
        None: The function performs defensive parsing and does not raise
        exceptions for malformed line content.

    Examples:
        >>> parse_line_data("google.com, pub-1, DIRECT, f08c47 # note")["type"]
        'DIRECT'
        >>> parse_line_data("# comment only") is None
        True
    """
    clean = line.split("#")[0].strip()
    if not clean:
        return None

    parts = [part.strip() for part in clean.split(",")]
    is_valid_format = len(parts) >= 3
    is_valid_type = is_valid_format and parts[2].upper() in VALID_TYPES

    return {
        "domain": parts[0] if len(parts) > 0 else "",
        "pub_id": parts[1] if len(parts) > 1 else "",
        "type": parts[2].upper() if len(parts) > 2 else "",
        "auth_id": parts[3] if len(parts) > 3 else "",
        "raw": line,
        "clean": clean,
        "is_error": not (is_valid_format and is_valid_type),
    }


def analyze_text(content):
    """Analyze ads.txt content and return records, diagnostics, and statistics.

    Args:
        content (str): Full text content of an ads.txt or app-ads.txt style
            document. The function processes the text line by line, preserving
            source ordering and line numbers.

    Returns:
        tuple[list[dict[str, int | str]], list[dict[str, int | str]],
        dict[str, int], list[dict[str, str]]]: A tuple containing:
            1. Per-line metadata with status labels.
            2. Structured unique valid records for downstream display/export.
            3. Aggregate counters (`valid`, `errors`, `duplicates`, `unique`).
            4. Human-readable warning/error messages with line references.

    Raises:
        None: Parsing and validation are intentionally non-throwing for
        malformed input lines.

    Examples:
        >>> text = "a.com, pub-1, DIRECT\\na.com, pub-1, DIRECT\\ninvalid"
        >>> _, _, stats, warnings = analyze_text(text)
        >>> stats["duplicates"], stats["errors"]
        (1, 1)
        >>> len(warnings) >= 1
        True
    """
    lines = content.splitlines()
    data_objects = []
    seen_keys = {}

    warnings = []
    output_lines = []
    stats = {"valid": 0, "errors": 0, "duplicates": 0, "unique": 0}

    for idx, line in enumerate(lines, 1):
        parsed = parse_line_data(line)

        if not parsed:
            output_lines.append({"num": idx, "text": line, "status": "neutral"})
            continue

        unique_key = f"{parsed['domain']}_{parsed['pub_id']}_{parsed['type']}".lower()
        is_duplicate = unique_key in seen_keys

        status = "valid"
        if parsed["is_error"]:
            status = "error"
            stats["errors"] += 1
            warnings.append({"type": "error", "msg": f"Line {idx}: Invalid syntax"})
        elif is_duplicate:
            status = "duplicate"
            stats["duplicates"] += 1
            original_line = seen_keys[unique_key]
            warnings.append(
                {
                    "type": "warning",
                    "msg": f"Line {idx}: Duplicated record, already in line {original_line}",
                }
            )
        else:
            stats["valid"] += 1
            stats["unique"] += 1
            seen_keys[unique_key] = idx
            data_objects.append(
                {
                    "Line": idx,
                    "Domain": parsed["domain"],
                    "Publisher ID": parsed["pub_id"],
                    "Type": parsed["type"],
                    "Authority ID": parsed["auth_id"],
                }
            )

        output_lines.append({"num": idx, "text": line, "status": status})

    return output_lines, data_objects, stats, warnings

"""Core parsing and validation helpers for ads.txt-style content."""

from urllib.parse import urlparse

VALID_TYPES = {"DIRECT", "RESELLER"}


def clean_url(url):
    """Normalize user input to a domain used for fetch URLs."""
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
    """Parse one line into a normalized record plus validation status."""
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
    """Return per-line status, unique records, summary stats, and warnings."""
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

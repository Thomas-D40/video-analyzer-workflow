import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


def extract_video_id(youtube_url: str) -> Optional[str]:
    parsed = urlparse(youtube_url)
    if parsed.hostname in {"www.youtube.com", "youtube.com"}:
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
        # short urls like /embed/<id>
        match = re.match(r"^/embed/([\w-]{11})$", parsed.path)
        if match:
            return match.group(1)
    if parsed.hostname in {"youtu.be"}:
        match = re.match(r"^/([\w-]{11})$", parsed.path)
        if match:
            return match.group(1)
    return None

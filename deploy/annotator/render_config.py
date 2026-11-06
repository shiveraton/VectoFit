#!/usr/bin/env python3
"""Render deployment files locally; does not install or contact the host."""

import argparse
import re
import secrets
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New private output directory; never overwrite secrets",
    )
    args = parser.parse_args()
    domain = args.domain.lower()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.duckdns\.org", domain):
        parser.error("Expected one valid NAME.duckdns.org hostname")
    source = Path(__file__).resolve().parent
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    replacements = {
        "annotator.example.org": domain,
        "REPLACE_WITH_RANDOM_DJANGO_SECRET": secrets.token_urlsafe(64),
        "REPLACE_WITH_RANDOM_INVITATION_SECRET": secrets.token_urlsafe(32),
        "REPLACE_PASSWORD": secrets.token_urlsafe(32),
    }
    for template, target in (
        ("nginx.conf", "nginx.conf"),
        ("backend.env.example", "backend.env"),
    ):
        content = (source / template).read_text(encoding="utf-8")
        for old, new in replacements.items():
            content = content.replace(old, new)
        path = args.output / target
        path.write_text(content, encoding="utf-8", newline="\n")
        path.chmod(0o600)
    print(
        "Rendered nginx.conf and backend.env. Secrets remain in the private output directory."
    )


if __name__ == "__main__":
    main()

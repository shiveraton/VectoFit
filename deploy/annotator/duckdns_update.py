#!/usr/bin/env python3
"""DuckDNS updater. Token stays in the environment, never command arguments or logs."""

import ipaddress
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def main():
    domain = os.environ.get("DUCKDNS_SUBDOMAIN", "")
    token = os.environ.get("DUCKDNS_TOKEN", "")
    address = os.environ.get("DUCKDNS_IPV4", "")
    if (
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", domain)
        or not token
        or token.startswith("REPLACE")
    ):
        sys.exit("DuckDNS requires a valid subdomain and server-only token.")
    if address:
        ipaddress.IPv4Address(address)
    query = urllib.parse.urlencode({"domains": domain, "token": token, "ip": address})
    try:
        with urllib.request.urlopen(
            "https://www.duckdns.org/update?" + query, timeout=30
        ) as response:
            result = response.read(32).decode("ascii").strip()
    except (urllib.error.URLError, TimeoutError, UnicodeError):
        # Do not log the exception: its URL can include the token.
        sys.exit(
            "DuckDNS update failed; inspect connectivity and server-side configuration."
        )
    if result != "OK":
        sys.exit("DuckDNS rejected the update; inspect server-side configuration.")
    print("DuckDNS update succeeded.")


if __name__ == "__main__":
    main()

"""Run the test suite with every outbound connection blocked.

    python -m scripts.check_no_network

The song loader is network-bound by nature: YouTube, and a lyrics database. A
test that quietly reached either would be flaky in CI, slow, and dependent on a
third party's uptime -- and would pass locally for whoever wrote it, which is
how such a test survives review.

So the seams (`rhymemap.sources.youtube._import_yt_dlp` and
`rhymemap.sources.lrclib.fetch`) are substituted in tests, and this asserts that
they really are. Loopback is allowed: the server tests genuinely bind a socket.

Exits non-zero if any test fails *or* if anything tried to leave the machine.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _proxy_endpoints() -> set[tuple[str, int]]:
    """Host/port pairs of any configured HTTP proxy.

    A proxy defeats the whole check. Behind one, a request to lrclib.net opens a
    socket to 127.0.0.1 and the proxy makes the real call, so loopback-only
    filtering sees nothing and reports success. That is exactly what happened
    while this script was being written: it passed locally and CI, running
    without a proxy, immediately caught four connections to lrclib's addresses.
    """
    endpoints = set()
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        value = os.environ.get(name)
        if not value:
            continue
        parsed = urlparse(value if "://" in value else f"http://{value}")
        if parsed.hostname:
            endpoints.add((parsed.hostname, parsed.port or 80))
    return endpoints


_PROXIES = _proxy_endpoints()

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex

_attempts: list = []


def _is_local(address) -> bool:
    try:
        host, port = address[0], address[1]
    except (TypeError, IndexError):
        return True                       # AF_UNIX and friends: not the network

    # A proxy listens on loopback but forwards off the machine. Treat reaching
    # it as leaving, or the check silently passes everywhere a proxy is set.
    if (host, port) in _PROXIES:
        return False

    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False                      # a hostname that is not localhost


def _guarded_connect(self, address, *args, **kwargs):
    if not _is_local(address):
        _attempts.append(address)
        raise OSError(f"blocked outbound connection to {address}")
    return _real_connect(self, address, *args, **kwargs)


def _guarded_connect_ex(self, address, *args, **kwargs):
    if not _is_local(address):
        _attempts.append(address)
        return 1
    return _real_connect_ex(self, address, *args, **kwargs)


def main(argv=None) -> int:
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex

    suite = unittest.TestLoader().discover(
        str(PROJECT_ROOT / "tests"), top_level_dir=str(PROJECT_ROOT))
    result = unittest.TextTestRunner(verbosity=1).run(suite)

    print()
    if _attempts:
        print(f"FAIL: {len(_attempts)} outbound connection(s) attempted:")
        for address in dict.fromkeys(map(str, _attempts)):
            print(f"  - {address}")
        print("\nSubstitute the network seam instead. See DOC_DEV.md section 5f.")
        return 1

    note = f" (proxy at {', '.join(f'{h}:{p}' for h, p in sorted(_PROXIES))} also blocked)" if _PROXIES else ""
    print(f"{result.testsRun} tests, no outbound connections attempted{note}.")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

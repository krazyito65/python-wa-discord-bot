#!/usr/bin/env python3
"""
Simple HTTP server to serve documentation locally.

This script serves the generated Sphinx documentation on localhost
for easy local viewing and testing.

Usage:
    python serve_docs.py [--port PORT]

Example:
    python serve_docs.py --port 8080
"""

import argparse
import http.server
import os
import socketserver
import webbrowser
from pathlib import Path


def serve_docs(port: int = 8000) -> None:
    """Serve documentation on localhost.

    Args:
        port (int): Port to serve on. Defaults to 8000.

    Raises:
        FileNotFoundError: If documentation has not been built.
        OSError: If port is already in use.
    """
    docs_dir = Path("docs/_build/html")

    if not docs_dir.exists():
        print("❌ Documentation not found!")
        print("Please build documentation first:")
        print("  cd docs && uv run sphinx-build -b html . _build/html")
        return

    os.chdir(docs_dir)

    handler = http.server.SimpleHTTPRequestHandler
    handler.extensions_map[".js"] = "application/javascript"

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            url = f"http://localhost:{port}"
            print(f"🌐 Serving documentation at {url}")
            print("Press Ctrl+C to stop the server")

            # Try to open browser
            try:
                webbrowser.open(url)
                print("📖 Opening documentation in your default browser...")
            except Exception:
                print(f"📖 Open {url} in your browser to view the documentation")

            httpd.serve_forever()

    except OSError as e:
        # errno 48 = Address already in use (EADDRINUSE)
        address_in_use_error = 48
        if e.errno == address_in_use_error:
            print(f"❌ Port {port} is already in use. Try a different port:")
            print(f"  python serve_docs.py --port {port + 1}")
        else:
            print(f"❌ Error starting server: {e}")
    except KeyboardInterrupt:
        print("\n👋 Documentation server stopped")


def main() -> None:
    """Main entry point for the documentation server."""
    parser = argparse.ArgumentParser(
        description="Serve WeakAuras Discord Bot documentation locally"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to serve documentation on (default: 8000)",
    )

    args = parser.parse_args()
    serve_docs(args.port)


if __name__ == "__main__":
    main()

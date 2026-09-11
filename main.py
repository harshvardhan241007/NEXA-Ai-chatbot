"""
NEXA AI Chatbot - entry point.

Usage:
  python main.py cli              # run in terminal chat mode
  python main.py api              # run the FastAPI web server
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="NEXA AI Chatbot")
    parser.add_argument(
        "mode",
        nargs="?",
        default="cli",
        choices=["cli", "api"],
        help="Run mode: 'cli' for terminal chat, 'api' for the web server",
    )
    args = parser.parse_args()

    if args.mode == "cli":
        from app.cli import run_cli
        run_cli()
    else:
        try:
            import uvicorn
        except ImportError:
            print(
                "FastAPI/uvicorn are not installed.\n"
                "Run: pip install -r requirements.txt\n"
                "Then: python main.py api"
            )
            sys.exit(1)
        from app.config import settings
        uvicorn.run("app.api:app", host=settings.HOST, port=settings.PORT, reload=True)


if __name__ == "__main__":
    main()

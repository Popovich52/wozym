from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8617


def run_compose(args: list[str]) -> int:
    return subprocess.call(["docker", "compose", *args], cwd=ROOT_DIR)


def run_migrations() -> int:
    return subprocess.call(["alembic", "upgrade", "head"], cwd=BACKEND_DIR)


def serve(host: str, port: int, reload: bool) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Missing backend dependencies. Run: pip install -r requirements.txt", file=sys.stderr)
        return 1

    print(f"WOzYm - AI платформа продаж backend: http://{host}:{port}")
    print("Debug reload:", "on" if reload else "off")
    print("Stop with Ctrl+C.")

    try:
        uvicorn_log_level = "debug" if reload else "info"
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            reload_dirs=[str(BACKEND_DIR / "app")] if reload else None,
            log_level=uvicorn_log_level,
            access_log=True,
        )
    except KeyboardInterrupt:
        print("\nBackend stopped.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="WOzYm - AI платформа продаж backend runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=["serve", "infra-up", "infra-down", "status", "migrate"],
        help="serve starts FastAPI; infra-* manages local Docker services",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-reload", action="store_true")
    args = parser.parse_args()

    if args.command == "infra-up":
        return run_compose(["up", "-d"])
    if args.command == "infra-down":
        return run_compose(["down", "-v"])
    if args.command == "status":
        return run_compose(["ps"])
    if args.command == "migrate":
        return run_migrations()

    return serve(args.host, args.port, reload=not args.no_reload)


if __name__ == "__main__":
    raise SystemExit(main())


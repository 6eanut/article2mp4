import sys

if __name__ == "__main__":
    if sys.version_info < (3, 11):
        raise SystemExit(
            f"article2mp4 requires Python 3.11+; this interpreter is "
            f"{sys.version.split()[0]} ({sys.executable}). "
            "Activate the project environment or run its python executable."
        )
    from .cli import main

    sys.exit(main())

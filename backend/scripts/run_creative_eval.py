"""Internal creative evaluation lab.

    uv run python -m scripts.run_creative_eval --case sweatshirt_01 --mode fixed
    uv run python -m scripts.run_creative_eval --case sweatshirt_01 --mode director
"""

from scripts.creative_eval.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())

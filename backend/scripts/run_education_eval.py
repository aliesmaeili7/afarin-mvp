"""Educational smoke harness.

    uv run python -m scripts.run_education_eval
    uv run python -m scripts.run_education_eval --case fa_math_decimals
    uv run python -m scripts.run_education_eval --no-image
    uv run python -m scripts.run_education_eval --live
"""

from scripts.education_eval.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())

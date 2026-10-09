"""Entry point for local runs and Windows packaging."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from blurout_pdf.app import main


if __name__ == "__main__":
    raise SystemExit(main())

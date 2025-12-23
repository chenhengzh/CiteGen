import os
import sys

# Add the current directory to sys.path to ensure we can import the package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import PAPER_LIST_DIR
from utils import setup_logging


def main():
    setup_logging("analysis")

    # Check paper list directory
    if os.path.exists(PAPER_LIST_DIR):
        try:
            from comment_analysis.analyzer import run_analysis

            print("Running Citation Analysis...")
            run_analysis()
        except ImportError as e:
            print(f"Failed to import analysis module: {e}")
            print(
                "Please ensure requirements are installed: pip install -r requirements.txt"
            )
        except Exception as e:
            print(f"An error occurred during analysis: {e}")
    else:
        print(
            "Please use CitationSpider to get citation data in advance (missing ./paper_list directory)"
        )


if __name__ == "__main__":
    main()

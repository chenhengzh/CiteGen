import argparse
import config
import os
import sys

# Add the current directory to sys.path to ensure we can import the package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import get_papers, setup_logging
from report_gen.generator import generate_all_reports


def main():
    parser = argparse.ArgumentParser(
        description="Report Generator for Zlin's students."
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging("docx_gen")

    # Check paper list directory
    if os.path.exists(config.PAPER_LIST_DIR):
        paper_list = get_papers()
        if not paper_list:
            print(f"No paper directories found in {config.PAPER_LIST_DIR}")
            return

        print(f"Running in Report Generation mode.")
        generate_all_reports(paper_list)
    else:
        print(
            f"Please use CitationSpider to get citation data in advance (missing {config.PAPER_LIST_DIR} directory)"
        )


if __name__ == "__main__":
    main()


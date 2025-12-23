import argparse
import os
import sys

# Add the current directory to sys.path to ensure we can import the package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import get_papers, setup_logging
from docx_gen.generator import generate_all_docx


def main():
    parser = argparse.ArgumentParser(
        description="Citation Generator for Zlin's students."
    )

    # Argument for GetPDF mode
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Generate Word documents using only local PDFs (do not crawl online).",
    )

    args = parser.parse_args()

    # Determine mode
    get_pdf_mode = not args.no_pdf

    # Setup logging
    setup_logging("docx_gen")

    # Check paper list directory
    if os.path.exists("./paper_list"):
        paper_list = get_papers()
        if not paper_list:
            print("No paper directories found in ./paper_list")
            return

        print(f"Running in {'PDF Download' if get_pdf_mode else 'Local Link'} mode.")
        generate_all_docx(paper_list, get_pdf_flag=get_pdf_mode)
    else:
        print(
            "Please use CitationSpider to get citation data in advance (missing ./paper_list directory)"
        )


if __name__ == "__main__":
    main()


import os
import sys

# Add the current directory to sys.path to ensure we can import the package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import get_papers, setup_logging
from citation_spider.pdf_downloader import download_all_pdfs


def main():

    # Setup logging
    setup_logging("pdf_download")

    # Check paper list directory
    if os.path.exists("./paper_list"):
        paper_list = get_papers()
        if not paper_list:
            print("No paper directories found in ./paper_list")
            return

        print(f"Running in PDF Download mode.")
        download_all_pdfs(paper_list)
    else:
        print(
            "Please use CitationSpider to get citation data in advance (missing ./paper_list directory)"
        )


if __name__ == "__main__":
    main()


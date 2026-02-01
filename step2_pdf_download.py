
import os
import sys
import config

# Add the current directory to sys.path to ensure we can import the package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import get_papers, setup_logging
from citation_spider.pdf_downloader import download_all_pdfs


def main():

    # Setup logging
    setup_logging("pdf_download")

    # Check paper list directory
    if os.path.exists(config.PAPER_LIST_DIR):
        paper_list = get_papers()
        if not paper_list:
            print(f"No paper directories found in {config.PAPER_LIST_DIR}")
            return

        print(f"Running in PDF Download mode.")
        download_all_pdfs(paper_list)
    else:
        print(
            f"Please use CitationSpider to get citation data in advance (missing {config.PAPER_LIST_DIR} directory)"
        )


if __name__ == "__main__":
    main()


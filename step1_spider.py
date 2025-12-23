import argparse
import config
import os
import sys

# Add the current directory to sys.path to ensure we can import the package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from citation_spider.paper_crawler import paper_crawler
from citation_spider.author_crawler import crawl_author_papers
from utils import setup_logging


def main():
    parser = argparse.ArgumentParser(description="Citation Spider")
    parser.add_argument(
        "--mode",
        choices=["author", "paper"],
        required=True,
        help="Crawl mode: by author or by paper list",
    )

    args = parser.parse_args()

    # Setup logging for the main spider process

    if not os.path.exists("./paper_list"):
        os.makedirs("./paper_list")

    if args.mode == "author":
        setup_logging("author_spider")
        if not config.author_id or config.author_id == "Your_Author_ID_Here":
            print("Please set 'author_id' in config.py")
            return
        print(f"Crawling papers for author ID: {config.author_id}")

        # Use the new function to get filtered papers and save author_info
        paper_ls = crawl_author_papers(config.author_id)

        # if paper_ls:
        #     print(f"Starting detailed citation crawling for {len(paper_ls)} papers...")
        #     # paper_crawler will setup its own logging, which is fine
        #     paper_crawler(paper_ls)
        # else:
        #     print("No papers found or error occurred.")

    elif args.mode == "paper":
        setup_logging("paper_spider")
        print("Crawling papers from config list...")
        if not config.paper_list:
            print(
                "Paper list in config is empty. Please add paper titles to 'paper_list' in config.py"
            )
            return
        paper_crawler(config.paper_list)


if __name__ == "__main__":
    main()

import logging
import os
import pickle
import json
from datetime import datetime
from fuzzywuzzy import fuzz
import config


# Define ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to console output."""

    def format(self, record):
        message = super().format(record)
        # Apply colors based on message content tags
        if "[SUCCESS]" in message:
            return f"{GREEN}{message}{RESET}"
        elif "[FAILED]" in message:
            return f"{RED}{message}{RESET}"
        return message


def setup_logging(module_name):
    """Setup logging configuration with timestamped filename in ./log directory."""
    log_dir = "./log"
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_filename = f"{module_name}-{timestamp}.log"
    log_file_path = os.path.join(log_dir, log_filename)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # File Handler - writes plain text
    file_handler = logging.FileHandler(log_file_path, mode="a")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    # Console Handler - writes colored text
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter("%(message)s"))
    logger.addHandler(console_handler)

    # Suppress verbose logging from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("arxiv").setLevel(logging.WARNING)

    print(f"Logging initialized. Log file: {log_file_path}")


def are_strings_almost_matching(string1, string2, threshold=90):
    """Check if two strings are similar using fuzzy matching."""
    # Use fuzz.ratio() to compare string similarity
    similarity_ratio = fuzz.ratio(string1.lower(), string2.lower())
    return similarity_ratio >= threshold


def get_filename(paper_title):
    """Generate a safe filename from a paper title."""
    words = paper_title.split()
    if len(words) <= config.NUM_WORDS_IN_FILENAME:
        fn = paper_title
    else:
        fn = " ".join(words[:config.NUM_WORDS_IN_FILENAME])
    fn = fn.replace(":", "")
    fn = fn.replace("?", "")
    fn = fn.replace("/", "_")  # Extra safety
    return fn


def get_citation(dir_name, file_name, base_dir="./paper_list"):
    """Load citation data from a pickle file."""
    pth = os.path.join(base_dir, dir_name, "data", file_name)
    with open(pth, "rb") as file:
        paper = pickle.load(file)
    return paper


def list_data_in_directory(dir_name, base_dir="./paper_list"):
    """List all files in the data directory of a paper."""
    folder_path = os.path.join(base_dir, dir_name, "data")
    if not os.path.exists(folder_path):
        return []
    files = os.listdir(folder_path)
    files.sort()
    return files


def get_papers(base_dir="./paper_list"):
    """Get a list of paper directories."""
    if not os.path.exists(base_dir):
        return []
    dir_ls = os.listdir(base_dir)
    # Keep only directories
    paper_ls = sorted([d for d in dir_ls if os.path.isdir(os.path.join(base_dir, d))])
    return paper_ls

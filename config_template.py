import os
from comment_analysis import prompts
from comment_analysis.model_config import ModelConfig

# Configuration settings
GET_PDF = True  # Default value, can be overridden by CLI arguments
TIMEOUT = 30
PAPER_LIST_DIR = "./paper_list"

API_KEY = ""  # SerpApi

start_year = 2025
end_year = 2025
num_ls = 20  # Number of citations to crawl per batch (step size)

author_id = ""  # Google Scholar Author ID
author_name = ""  # For author crawler

NUM_WORDS_IN_FILENAME = 8  # Number of words to keep in the filename

# Paper List for crawler (example)
paper_list = [
    "CFA: Class-wise Calibrated Fair Adversarial Training",
]

# Default configurations
DEEPSEEK_API_KEY = ""

deepseek_short = ModelConfig(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
    pause_seconds=0,
    system_prompt=prompts.short_system,
    user_prompt_template=prompts.user_template,
    response_format={"type": "json_object"},
)

# Active model configuration
ANALYSIS_MODEL = deepseek_short

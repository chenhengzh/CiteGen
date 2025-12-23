import os
import json
import logging
import time
import traceback
import fitz  # PyMuPDF
import openai
import config
from .citation_utils import (
    loadPaperInfo,
    extract_references,
    extract_citation_positions,
    extract_citation_snippets,
    validate_output,
    load_citation_info,
    PaperInfo,
)


class CitationAnalyzer:
    def __init__(self, model_config=None):
        self.config = model_config or config.ANALYSIS_MODEL
        self.total_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        # Initialize client here to reuse connection
        if self.config.api_key:
            self.client = openai.OpenAI(
                api_key=self.config.api_key, base_url=self.config.base_url
            )
        else:
            self.client = None
            logging.warning(
                "No API key provided for CitationAnalyzer. Analysis will fail if attempted."
            )

    def json_model_query(self, system, user):
        if not self.client:
            raise Exception("OpenAI client not initialized (missing API key?)")

        time.sleep(self.config.pause_seconds)

        # Log outgoing messages
        logging.info("Sending request with system message:\n %s", system)
        logging.info("Sending request with user message:\n %s", user)

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=self.config.response_format,
            temperature=0.2,
        )

        # Log full response content from the model
        logging.info("Received response: %s", response.choices[0].message.content)

        if response.usage:
            self.total_tokens["prompt_tokens"] += response.usage.prompt_tokens
            self.total_tokens["completion_tokens"] += response.usage.completion_tokens
            self.total_tokens["total_tokens"] += response.usage.total_tokens
            logging.info(
                f"Token usage for this request: Prompt: {response.usage.prompt_tokens}, "
                f"Completion: {response.usage.completion_tokens}, Total: {response.usage.total_tokens}"
            )

        if response.choices[0].finish_reason != "stop":
            raise Exception(
                f"OpenAI API response did not finish normally: {response.choices[0].finish_reason}"
            )
        try:
            msg = response.choices[0].message.content.strip()
            # Find JSON object in response
            start_idx = msg.find("{")
            end_idx = msg.rfind("}")
            if start_idx != -1 and end_idx != -1:
                msg = msg[start_idx : end_idx + 1]

            result = json.loads(msg)
            # Normalize keys if needed (case sensitivity)
            if "citations" in result and "Citations" not in result:
                result["Citations"] = []
                for c in result["citations"]:
                    new_c = {}
                    new_c["Text"] = c.get("text", "")
                    new_c["Analysis"] = c.get("analysis", "")
                    new_c["Positive"] = c.get("positive", False)
                    result["Citations"].append(new_c)

            validate_output(result)
        except Exception as e:
            raise Exception(
                f"Parsing failed.\nResponse:\n{response.choices[0].message.content}\nMessage:\n{str(e)}"
            )
        return result

    def pdf_to_text(self, pdf_path):
        """Extracts text from PDF without saving to disk."""
        if not os.path.exists(pdf_path):
            logging.warning(f"PDF not found: {pdf_path}")
            return None

        try:
            with fitz.open(pdf_path) as pdf_document:
                text = ""
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    text += page.get_text()
                logging.info(f"Extracted text from {pdf_path}")
                return text
        except Exception as e:
            logging.error(f"Error reading {pdf_path}: {e}")
            return None

    def analyze_paper_folder(self, paper_dir):
        """
        Analyzes all citations for a given paper directory.
        """
        logging.info(f"Starting analysis for paper directory: {paper_dir}")

        # Prepare output directory
        analysis_output_dir = os.path.join(paper_dir, "comment_analysis")
        os.makedirs(analysis_output_dir, exist_ok=True)

        # Load target paper info
        paper_info = loadPaperInfo(paper_dir)
        if not paper_info:
            logging.warning(
                f"paper_info.json not found in {paper_dir}. Searching in author_info..."
            )
            dirname = os.path.basename(os.path.normpath(paper_dir))

            # Search in author_info
            found_info = None
            author_info_dir = "author_info"
            if os.path.exists(author_info_dir):
                for filename in os.listdir(author_info_dir):
                    if filename.endswith(".json"):
                        try:
                            with open(
                                os.path.join(author_info_dir, filename),
                                "r",
                                encoding="utf-8",
                            ) as f:
                                papers = json.load(f)
                                if not isinstance(papers, list):
                                    continue
                                for p in papers:
                                    p_dirname = p.get("dirname", "")
                                    # Relaxed matching: check if dirname is contained in title (case-insensitive)
                                    # or if title is contained in dirname (handles cases where dirname has extra info)
                                    # Using simple inclusion for now as per "according to dirname"
                                    if (
                                        dirname == p_dirname
                                    ):
                                        found_info = p
                                        break
                        except Exception as e:
                            logging.warning(f"Error reading {filename}: {e}")

                # Construct PaperInfo
                paper_info = PaperInfo(
                    authors=found_info.get("authors", []),
                    approach_name="",  # Default empty as requested
                    title=found_info.get("title", ""),
                    year=None,  # author_info usually doesn't have year field separated
                    publication=found_info.get("publication", ""),
                )

                # Save as paper_info.json
                save_data = found_info.copy()
                save_data["approach_name"] = ""  # Ensure this field exists and is empty
                # Ensure year exists if missing
                if "year" not in save_data:
                    save_data["year"] = None

                try:
                    with open(
                        os.path.join(paper_dir, "paper_info.json"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(save_data, f, indent=4, ensure_ascii=False)
                    logging.info(f"Saved paper_info.json to {paper_dir}")
                except Exception as e:
                    logging.error(f"Failed to save paper_info.json: {e}")

            else:
                logging.warning(
                    f"Paper info not found for {dirname}. Loading from scratch."
                )
                paper_info = PaperInfo(
                    authors="",
                    approach_name="",
                    title=dirname,
                    year=None,
                    publication=None,
                )

        # Load citation list
        citation_info_path = os.path.join(paper_dir, "citation_info.json")
        if not os.path.exists(citation_info_path):
            logging.error(f"citation_info.json not found in {paper_dir}.")
            return

        with open(citation_info_path, "r", encoding="utf-8") as f:
            citations = json.load(f)

        analyzed_results = []

        for i, citation in enumerate(citations):
            # Identify PDF file
            filename = citation.get("filename")
            if not filename:
                continue

            pdf_path = os.path.join(paper_dir, f"{filename}.pdf")
            analysis_path = os.path.join(analysis_output_dir, f"{filename}.json")

            # 1. Convert PDF to Text (In Memory)
            paper_text = self.pdf_to_text(pdf_path)
            if not paper_text:
                continue

            # 2. Extract Snippets
            # Identify references to target paper
            reference_number = extract_references(paper_info.title, paper_text)

            positions = extract_citation_positions(
                paper_text,
                paper_info.authors,
                paper_info.year,
                reference_number,
                paper_info.approach_name,
            )
            snippets = extract_citation_snippets(paper_text, positions)

            # 3. Analyze Snippets
            # Load existing analysis to resume/avoid re-analysis
            citation_results = []
            analyzed_snippet_indices = set()
            encountered_exceptions = []

            if os.path.exists(analysis_path):
                try:
                    with open(analysis_path, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                        analyzed_snippet_indices = set(
                            existing_data.get("AnalyzedSnippetIndices", [])
                        )
                        citation_results = existing_data.get("Citations", [])
                except Exception as e:
                    logging.warning(
                        f"Failed to load existing analysis for {filename}: {e}"
                    )

            updated = False

            for index, snippet in enumerate(snippets, start=1):
                if index in analyzed_snippet_indices:
                    continue

                user_prompt = self.config.user_prompt_template.format(
                    paper=paper_info.citation(),
                    reference_number=reference_number,
                    approach_name=(
                        ", 或者".join(paper_info.approach_name)
                        if isinstance(paper_info.approach_name, list)
                        else paper_info.approach_name
                    ),
                    text=snippet,
                )

                try:
                    result = self.json_model_query(
                        self.config.system_prompt, user_prompt
                    )
                    citation_results.extend(result["Citations"])
                    analyzed_snippet_indices.add(index)
                    updated = True
                    logging.info(f"Analyzed snippet {index} of {filename}")
                except Exception as e:
                    logging.error(
                        f"Error analyzing snippet {index} of {filename}:\n{traceback.format_exc()}"
                    )
                    encountered_exceptions.append((index, str(e)))

                # Save intermediate results (including Snippets inside)
                if updated:
                    with open(analysis_path, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "Filename": filename,
                                "PaperInfo": citation.get("info", ""),
                                "Citations": citation_results,
                                "AnalyzedSnippetIndices": list(
                                    analyzed_snippet_indices
                                ),
                                "EncounteredExceptions": encountered_exceptions,
                                "Snippets": snippets,
                            },
                            f,
                            ensure_ascii=False,
                            indent=2,
                        )

            # Sort results by Positive=True first
            citation_results.sort(key=lambda x: not x["Positive"])

            # Helper to get citation display text
            title = citation.get("title", "")
            info = citation.get("info", "")
            display_text = f"{title}. {info}"

            analyzed_results.append(
                {
                    "Citations": citation_results,
                    "Paper": display_text,
                    "ID": i + 1,
                    "Filename": filename,
                }
            )

        # 3. Aggregate Results
        # Sort papers by number of positive citations
        sorted_papers = sorted(
            analyzed_results,
            key=lambda paper: sum(
                1 for snippet in paper["Citations"] if snippet["Positive"]
            ),
            reverse=True,
        )

        # Save aggregated sorted results
        all_snippets_path = os.path.join(analysis_output_dir, "all_snippets.json")
        with open(all_snippets_path, "w", encoding="utf-8") as f:
            json.dump(sorted_papers, f, ensure_ascii=False, indent=2)

        print(
            f"Analysis completed for {os.path.basename(paper_dir)}. Results saved to {analysis_output_dir}/"
        )


def run_analysis(paper_list_dir=None):
    if paper_list_dir is None:
        paper_list_dir = config.PAPER_LIST_DIR

    if not os.path.exists(paper_list_dir):
        print("Paper list directory not found.")
        return

    analyzer = CitationAnalyzer()

    paper_dirs = [
        os.path.join(paper_list_dir, d)
        for d in os.listdir(paper_list_dir)
        if os.path.isdir(os.path.join(paper_list_dir, d))
    ]

    for paper_dir in sorted(paper_dirs):
        analyzer.analyze_paper_folder(paper_dir)

    logging.info(
        f"Total token usage for this run: Prompt: {analyzer.total_tokens['prompt_tokens']}, "
        f"Completion: {analyzer.total_tokens['completion_tokens']}, "
        f"Total: {analyzer.total_tokens['total_tokens']}"
    )

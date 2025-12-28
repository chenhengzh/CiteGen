import json
import os
import time
import re
from fuzzywuzzy import fuzz
import jsonschema


class PaperInfo:
    def __init__(self, authors, approach_name, title, year, publication):
        self.title = title
        self.authors = authors
        self.approach_name = approach_name
        self.year = year
        self.publication = publication

    def __repr__(self):
        return f"PaperInfo(title={self.title}, authors={self.authors}, approach_name={self.approach_name}, year={self.year})"

    def citation(self):
        authors_str = (
            ", ".join(self.authors)
            if isinstance(self.authors, list)
            else str(self.authors)
        )
        return f"{authors_str}. {self.title}. {self.publication}."


def load_citation_info(paper_id, citation_id):
    # This was used in the old structure. In the new structure, we pass the citation dict directly.
    # Leaving it here for compatibility if needed, but likely unused.
    with open(f"{paper_id}/Citation_{citation_id}.json", "r", encoding="utf-8") as f:
        return json.load(f)


def loadPaperInfo(paper_dir, info_file_path=None):
    if info_file_path is None:
        info_file_path = os.path.join(paper_dir, "paper_info.json")

    if not os.path.exists(info_file_path):
        return None

    with open(info_file_path, "r", encoding="utf-8") as file:
        info_data = json.load(file)

    authors = info_data.get("authors", [])
    approachName = info_data.get("approach_name", "")
    title = info_data.get("title")
    year = info_data.get("year")
    publication = info_data.get("publication")
    if not approachName and title and ":" in title:
        approachName = title.split(":")[0].strip()

    return PaperInfo(authors, approachName, title, year, publication)


def extract_references(title, paper_text):
    """
    Extracts the references section from the paper text and finds the reference number matching the title.
    """
    # Common headers for references section
    reference_titles = ["References", "Bibliography", "Works Cited", "参考文献"]

    reference_start = None
    for rt in reference_titles:
        matches = list(
            re.finditer(rf"^\s*{rt}\s*$", paper_text, re.IGNORECASE | re.MULTILINE)
        )
        match = (
            matches[-1] if matches else None
        )  # Use the last match as sometimes "References" appears in TOC
        if match:
            reference_start = match.start()
            break

    if reference_start is None:
        # print("No references section found.")
        reference_start = 0

    # Sliding window to find the title in the references section
    window_size = len(title)
    max_similarity = 0
    match_position = -1

    # Optimize search range: assume references are at the end, search last 30% if text is long
    start_search = reference_start
    if start_search == 0 and len(paper_text) > 10000:
        start_search = int(len(paper_text) * 0.7)

    for i in range(start_search, len(paper_text) - window_size + 1):
        window_text = paper_text[i : i + window_size]
        # Quick check first char match to speed up? No, fuzzy matching handles it.
        # But for large text, fuzz is slow.
        # Let's trust the original implementation for now, but be aware of performance.
        # Original: search from reference_start.
        similarity = fuzz.ratio(title.lower(), window_text.lower())

        if similarity > max_similarity:
            max_similarity = similarity
            match_position = i

    if max_similarity < 80:  # Threshold
        return None

    matched_reference = paper_text[match_position : match_position + window_size]

    # Analyze citation format
    analysis_length = 1000
    expected_consecutive_numbers = 3

    distance_to_start = (
        analysis_length // 2
        if match_position - reference_start > analysis_length // 2
        else match_position - reference_start
    )
    distance_to_end = (
        analysis_length // 2
        if len(paper_text) - match_position > analysis_length // 2
        else len(paper_text) - match_position
    )
    snippet = paper_text[
        max(
            match_position - (analysis_length - distance_to_end), reference_start
        ) : min(match_position + (analysis_length - distance_to_start), len(paper_text))
    ]

    all_patterns = [r"\[\s*(\d+)\s*\]", r"\b(\d+)\s*\.", r"^\s*(\d+)\s*$"]

    def contains_subsequence(nums, expected):
        dp = {}
        for num in nums:
            prev = num - 1
            current_length = dp.get(prev, 0) + 1
            if current_length >= expected:
                return True
            if current_length > dp.get(num, 0):
                dp[num] = current_length
        return False

    patterns = []
    if len(snippet) < analysis_length:
        patterns = all_patterns
    else:
        for pattern in all_patterns:
            matches = re.findall(pattern, snippet, re.MULTILINE)
            numbers = [int(match) for match in matches if 0 <= int(match) <= 1500]
            if contains_subsequence(numbers, expected_consecutive_numbers):
                patterns.append(pattern)
                break

        if len(patterns) == 0:
            return None

    search_text = paper_text[match_position - 500 : match_position]

    reference_number = None

    def find_last_match(search_text, patterns):
        last_match = None
        last_pos = -1

        for pattern in patterns:
            matches = list(
                re.finditer(pattern, search_text, re.IGNORECASE | re.MULTILINE)
            )
            match = matches[-1] if matches else None
            if match is None:
                continue
            if match.start() > last_pos:
                last_match = match
                last_pos = match.start()

        return last_match

    match = find_last_match(search_text, patterns)
    reference_number = int(match.group(1)) if match else None

    return reference_number


def extract_citation_positions(
    paper_text, authors, year, reference_number=None, methodNames=[]
):
    results = []

    # Match numeric citations
    if reference_number is not None:
        numeric_pattern = r"\[([0-9\,\-\–\s\[\]]+)\]"
        numeric_matches = re.finditer(numeric_pattern, paper_text)
        for match in numeric_matches:
            elements = (
                match.group(1)
                .replace(" ", "")
                .replace("][", ",")
                .replace("]-[", "-")
                .replace("]–[", "–")
                .split(",")
            )
            found = False
            for elem in elements:
                if "-" in elem or "–" in elem:
                    parts = re.split(r"[-–]", elem)
                    if len(parts) != 2:
                        continue
                    try:
                        start_num = int(parts[0].strip())
                        end_num = int(parts[1].strip())
                    except ValueError:
                        continue
                    if start_num <= reference_number <= end_num:
                        found = True
                        break
                else:
                    try:
                        num = int(elem.strip())
                    except ValueError:
                        continue
                    if num == reference_number:
                        found = True
                        break
            if found:
                results.append((match.start(), match.end()))

    # Match author and year citations
    if authors and year:
        # Ensure authors is a list
        if isinstance(authors, str):
            authors = [authors]

        surnames = [name.split()[-1] for name in authors]
        if surnames:
            separator = r"(?:\s+and\s+|\s*&\s*|\s*,\s*|\s+)"
            author_pattern = rf"(?P<name0>{surnames[0]}){separator}+"
            for i in range(1, len(surnames)):
                author_pattern += rf"((?P<name{i}>{surnames[i]}){separator}+)?"
            author_pattern += rf"(?P<etal>et\s+al\.?)?\s*(,\s*)?(?:\(\s*{year}\s*\)|{year}|\[\s*{year}\s*\])"

            try:
                author_regex = re.compile(author_pattern, re.IGNORECASE)
                for match in author_regex.finditer(paper_text):
                    # Basic check to ensure we matched something valid
                    # If using grouped regex, ensure we aren't matching empty strings inadvertently
                    results.append((match.start(), match.end()))
            except re.error:
                pass  # Pattern compilation failed

    # Match method name citations
    if methodNames:
        if isinstance(methodNames, str):
            methodNames = [methodNames]
        for methodName in methodNames:
            if not methodName:
                continue
            method_pattern = rf"{re.escape(methodName)}"
            method_regex = re.compile(method_pattern, re.IGNORECASE)
            for match in method_regex.finditer(paper_text):
                results.append((match.start(), match.end()))

    # Sort results by start position
    results.sort(key=lambda x: x[0])

    return results


def extract_citation_snippets(paper_text, citation_positions):
    snippet_length = 1000
    snippets = []
    for start, end in citation_positions:
        snippet_start = max(0, start - snippet_length // 2)
        snippet_end = min(len(paper_text), end + snippet_length // 2)
        snippets.append((snippet_start, snippet_end))

    # Merge overlapping snippets
    merged_snippets = []
    for snippet in snippets:
        if not merged_snippets or merged_snippets[-1][1] < snippet[0]:
            merged_snippets.append(snippet)
        else:
            merged_snippets[-1] = (
                merged_snippets[-1][0],
                max(merged_snippets[-1][1], snippet[1]),
            )

    snippet_strings = [paper_text[start:end] for start, end in merged_snippets]
    return snippet_strings


def validate_output(json_result):
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "Citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "Text": {"type": "string"},
                        "Analysis": {"type": "string"},
                        "Positive": {"type": "boolean"},
                    },
                    "required": ["Text", "Analysis", "Positive"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["Citations"],
        "additionalProperties": False,
    }

    jsonschema.validate(instance=json_result, schema=schema)

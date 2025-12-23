import os
import json
import logging
from .paper_crawler import paper_crawler, google_search, get_filename
import config


def get_author_info_path():
    if not os.path.exists("./author_info"):
        os.makedirs("./author_info")
    return f"./author_info/{config.author_name.replace(' ', '_')}.json"


def save_author_info(paper_list):
    path = get_author_info_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(paper_list, f, indent=4, ensure_ascii=False)


def get_cite_id(paper):
    if "cited_by" not in paper or "link" not in paper["cited_by"]:
        return "no citation"
    cite_link = paper["cited_by"]["link"]
    return cite_link.split("cites=")[-1].split('"')[0]


def get_papers(aid):
    params = {
        "engine": "google_scholar_author",
        "author_id": aid,
        "api_key": config.API_KEY,
        "num": "100",
        "start": "0",
    }

    paper_ls = []
    st = 0
    while True:
        params["start"] = str(st)
        search = google_search(params)
        results = search.get_dict()
        if "author" not in results:
            print("Author not found or API error")
            break
        author = results["author"]["name"]
        if "articles" not in results:
            break
        articles = results["articles"]

        # import pdb; pdb.set_trace()
        for article in articles:
            if article["title"].startswith("Supplementary"):
                continue
            # paper_ls.append(article["title"])
            authors = article.get("authors", "")
            # 去除author中的*号
            authors = authors.replace("*", "")
            title = article.get("title", "")
            data = {
                "title": title,
                "authors": authors,
                "year": article.get("year", ""),
                "publication": article.get("publication", ""),
                "link": article.get("link", ""),
                "cite_id": get_cite_id(article),
                "dirname": get_filename(title),
            }
            paper_ls.append(data)
        if len(articles) < 100:
            break
        st += 100

    return paper_ls


def check_citation_count(paper):
    if paper["cite_id"] == "no citation":
        return 0

    params = {
        "engine": "google_scholar",
        "api_key": config.API_KEY,
        "cites": paper["cite_id"],
        "as_ylo": str(config.start_year),
        "as_yhi": str(config.end_year),
        "num": "1",  # We just need the count
        "start": "0",
    }

    search = google_search(params)
    if not search:
        return 0

    results = search.get_dict()

    if (
        "search_information" not in results
        or "total_results" not in results["search_information"]
    ):
        return 0

    return int(results["search_information"]["total_results"])


def crawl_author_papers(aid):
    print(f"Fetching papers for author ID: {aid}")

    # 1. Load existing papers to support resume
    path = get_author_info_path()
    filtered_papers = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                filtered_papers = json.load(f)
            print(f"Loaded {len(filtered_papers)} existing papers from {path}")
        except Exception as e:
            print(f"Error loading existing papers: {e}")

    existing_titles = {p.get("title") for p in filtered_papers}

    # 2. Get raw paper list
    raw_papers = get_papers(aid)
    print(
        f"Found {len(raw_papers)} raw papers. Checking citations within {config.start_year}-{config.end_year}..."
    )

    for paper in raw_papers:
        title = paper.get("title")
        if title in existing_titles:
            continue

        # Check citation count within timeframe
        count = check_citation_count(paper)
        if count > 0:
            paper["cite_num_within_time"] = count
            filtered_papers.append(paper)
            print(f"  [KEEP] {title} ({count} citations)")

            # Save immediately (Incremental Save)
            save_author_info(filtered_papers)
        else:
            # print(f"  [DROP] {title} (0 citations)")
            print(f"  [DROP] {title} (0 citations)")
            pass

    print(f"Total papers saved: {len(filtered_papers)}")
    return filtered_papers


if __name__ == "__main__":
    if not os.path.exists("./paper_list"):
        os.makedirs("./paper_list")

    # In independent execution, we run the full pipeline
    paper_ls = crawl_author_papers(config.author_id)
    if paper_ls:
        paper_crawler(paper_ls)

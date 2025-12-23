import logging
import requests
import arxiv
import os
import re
from bs4 import BeautifulSoup
from utils import are_strings_almost_matching
from config import TIMEOUT


def download_file(url, save_path):
    """Download file from a direct URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, stream=True, timeout=TIMEOUT, headers=headers)

        # Check status code and content type
        if response.status_code == 200:
            # Check for PDF content type or magic numbers
            is_pdf = "application/pdf" in response.headers.get("Content-Type", "")
            if not is_pdf:
                # Peek at the first few bytes
                chunk = next(response.iter_content(chunk_size=4), b"")
                if chunk.startswith(b"%PDF"):
                    is_pdf = True
                else:
                    # Put back the chunk? iter_content is a generator.
                    # Simpler to just re-request or assume if content-type fails it might be wrong.
                    # But let's trust Content-Type or file extension in URL mostly.
                    pass

            if is_pdf:
                with open(save_path, "wb") as pdf_file:
                    for chunk in response.iter_content(chunk_size=128):
                        pdf_file.write(chunk)
                logging.info(f"[SUCCESS] PDF has been downloaded from URL: {save_path}")
                return True
            else:
                logging.info(
                    f"[FAILED] URL content is not PDF: {url} (Type: {response.headers.get('Content-Type')})"
                )
                return False
        else:
            logging.info(
                f"[FAILED] Download failed from URL (status: {response.status_code}): {url}"
            )
            return False

    except requests.Timeout:
        logging.info(f"[FAILED] Request timed out for {url}.")
        return False
    except requests.RequestException as e:
        logging.info(f"[FAILED] Network error for {url}: {e}")
        return False


# --- Source Specific Downloaders ---


def download_arxiv_direct(cit, save_path):
    """Try to convert arXiv abstract URL to PDF URL."""
    url = cit.get("link", "")
    if "arxiv.org/abs" in url:
        pdf_url = url.replace("arxiv.org/abs", "arxiv.org/pdf")
        if not pdf_url.endswith(
            ".pdf"
        ):  # Sometimes pdf link needs .pdf but arxiv works without usually
            # arXiv pdf links usually don't need .pdf suffix but let's be safe if redirection handles it
            pass
        return download_file(pdf_url, save_path)
    return False


def download_acm(cit, save_path):
    """Download from ACM Digital Library."""
    url = cit.get("link", "")
    pdf_url = None
    if "dl.acm.org/doi/abs" in url:
        pdf_url = url.replace("dl.acm.org/doi/abs", "dl.acm.org/doi/pdf")
    elif "dl.acm.org/doi/pdf" in url:
        pdf_url = url

    if pdf_url:
        return download_file(pdf_url, save_path)
    return False


def download_ieee(cit, save_path):
    """Download from IEEE Xplore."""
    url = cit.get("link", "")
    if (
        "ieeexplore.ieee.org/abstract/document/" not in url
        and "ieeexplore.ieee.org/document/" not in url
    ):
        return False

    match = re.search(r"document/(\d+)", url)
    if not match:
        return False

    ieee_number = match.group(1)
    pdf_url = (
        f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={ieee_number}"
    )
    return download_file(pdf_url, save_path)


def download_springer(cit, save_path):
    """Download from Springer (Article or Chapter)."""
    url = cit.get("link", "")
    if "link.springer.com" not in url:
        return False

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "html.parser")

        # Try finding PDF link in different common Springer layouts
        pdf_link = None

        # Method 1: c-pdf-container
        div_tag = soup.find("div", class_="c-pdf-container")
        if div_tag:
            a_tag = div_tag.find("a", href=True)
            if a_tag:
                pdf_link = a_tag["href"]

        # Method 2: c-article-access-provider (Chapters)
        if not pdf_link:
            div_tag = soup.find("div", class_="c-article-access-provider")
            if div_tag:
                a_tag = div_tag.find("a", href=True)
                if a_tag:
                    pdf_link = a_tag["href"]

        if pdf_link:
            if not pdf_link.startswith("http"):
                pdf_link = "http://link.springer.com" + pdf_link
            return download_file(pdf_link, save_path)

    except Exception as e:
        logging.info(f"[FAILED] Error parsing Springer page: {e}")

    return False


def download_pdf_in_arxiv_search(title, abstract, save_path):
    """Search and download PDF from arXiv (Fallback)."""
    client = arxiv.Client()

    try:
        # Enclose title in quotes to perform an exact phrase search for the title
        search = arxiv.Search(query=f'ti:"{title}"', max_results=3)
        # Handle empty iterator safely
        results = list(client.results(search))
        if not results:
            logging.info(f"[FAILED] find nothing in arXiv search for {title}.")
            return False
        result = results[0]
    except Exception as e:
        logging.error(f"[FAILED] Error searching arXiv: {e}")
        return False

    ismatch = are_strings_almost_matching(title, result.title, 85)

    if ismatch:
        try:
            result.download_pdf(
                dirpath=os.path.dirname(save_path), filename=os.path.basename(save_path)
            )
            logging.info(
                f"[SUCCESS] PDF has been downloaded from arXiv search: {save_path}"
            )
            return True
        except Exception as e:
            logging.info(f"[FAILED] Network error downloading from arXiv search: {e}")
            return False
    else:
        logging.info("[FAILED] Found result in arXiv but title mismatch.")
        return False


def get_pdf(cit, pth):
    """Try to get PDF from various sources."""

    # 1. Try explicit PDF link provided in citation
    link = cit.get("PDF", "")
    if link:
        logging.info(
            "+==============try to get pdf from provided PDF link=============+"
        )
        if download_file(link, pth):
            logging.info(f"[SUCCESS] Success with provided PDF link")
            return True
        else:
            logging.info(f"[FAILED] Failed with provided PDF link")

    # 2. Try specialized downloaders based on the 'link' (Page Link)
    logging.info("+==============try to get pdf from page link=============+")

    downloaders = [
        download_arxiv_direct,  # Fast check if link is arxiv abs
        download_acm,
        download_ieee,
        download_springer,
    ]

    for downloader in downloaders:
        try:
            if downloader(cit, pth):
                logging.info(f"[SUCCESS] Success with {downloader.__name__}")
                return True
            else:
                logging.info(f"[FAILED] Failed with {downloader.__name__}")
        except Exception as e:
            logging.info(f"[FAILED] {downloader.__name__} failed: {e}")

    # 3. Fallback: Try general link as a direct PDF download (sometimes link is a PDF)
    page_link = cit.get("link", "")
    if page_link and page_link != link:
        logging.info("+==============try to download page link as PDF=============+")
        if download_file(page_link, pth):
            return True

    # 4. Fallback: Search arXiv
    logging.info("+==============search pdf in arxiv=============+")
    title = cit.get("title", "")
    abstract = cit.get("abstract", "")
    if title:
        if download_pdf_in_arxiv_search(title, abstract, pth):
            return True
    else:
        logging.warning("No title provided for citation, skipping arXiv search.")

    return False

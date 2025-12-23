import logging
import json
import pdb
import time
import os
import pickle
import re
import shutil
import urllib3
from datetime import datetime
from serpapi import GoogleSearch

import config



class Citation:
    def __init__(
        self, title="", info="", abstract="", PDF="", filename="", link=""
    ) -> None:
        self.title = title
        self.info = info
        self.abstract = abstract
        self.PDF = PDF
        self.filename = filename
        self.link = link

    def display(self):
        print(
            "+++===================================================================================================+++"
        )
        print(f"title: {self.title}")
        print(f"filename: {self.filename}")
        print(f"info: {self.info}")
        print(f"abstract: {self.abstract}")
        if self.PDF == "":
            print("no PDF resource.")
        else:
            print(f"PDF: {self.PDF}")
        print(f"paper_link: {self.link}")


def display_paper(paper):
    logging.info(
        "+++===================================================================================================+++"
    )
    logging.info(f"title: {paper.title}")
    logging.info(f"filename: {paper.filename}")
    logging.info(f"info: {paper.info}")
    logging.info(f"abstract: {paper.abstract}")
    if paper.PDF == "":
        logging.info("no PDF resource.")
    else:
        logging.info(f"PDF: {paper.PDF}")
    logging.info(f"paper_link: {paper.link}")


# 访问尝试三次，以防出现问题
def google_search(para):
    attempts = 0
    max_attempts = 5  # 增加重试次数
    while attempts < max_attempts:
        try:
            return GoogleSearch(para)
        except (urllib3.exceptions.ProtocolError, ConnectionResetError) as e:
            attempts += 1
            logging.info(
                f"Attempt {attempts} failed with error: {e}. Retrying in 10 seconds..."
            )
            time.sleep(10)  # 增加间隔时间
        except Exception as e:
            attempts += 1
            logging.info(
                f"Attempt {attempts} failed with error: {e}. Retrying in 5 seconds..."
            )
            time.sleep(5)
    logging.info("All attempts failed.")
    print("!!!Network error. Please check the log file for more information.")
    print("para")
    return False


def get_filename(paper_title):
    words = paper_title.split()
    if len(words) <= config.NUM_WORDS_IN_FILENAME:
        fn = paper_title
    else:
        fn = " ".join(words[: config.NUM_WORDS_IN_FILENAME])
    fn = fn.replace(":", "")
    fn = fn.replace("?", "")
    return fn


# 无须处理publication_str，留下版本号等信息
def get_info(chicago_str, pro_str):
    publication_str = chicago_str

    first_quot_index = chicago_str.find('"')
    name_str = chicago_str[:first_quot_index]
    second_quot_index = chicago_str.find('"', first_quot_index + 1)
    publication_str = chicago_str[(second_quot_index + 2) :]

    # 处理 name_str
    first_comma_index = name_str.find(",")
    if first_comma_index != -1:
        second_comma_index = name_str.find(",", first_comma_index + 1)
        name_1 = name_str[:second_comma_index]
        name_str = name_str[second_comma_index:]

        comma_1 = name_1.find(",")
        last_name = name_1[:comma_1]
        first_name = name_1[(comma_1 + 2) :]
        name_1 = first_name + " " + last_name
        name_str = name_1 + name_str

    # 处理 pro_str
    url_index = pro_str.rfind(" - ")
    if url_index == -1:
        pro_str = ""
    else:
        pro_str = pro_str[url_index:]
    info_str = name_str[:-2] + " - " + publication_str[:-1] + pro_str
    return info_str


def contains_cjk(text):
    # 使用正则表达式匹配中文、日文、韩文字符
    pattern = re.compile(r"[\u4e00-\u9fff\u3040-\u30FF\uAC00-\uD7AF]+")
    return bool(pattern.search(text))


def get_citation(paper_div):
    paper = Citation()
    paper.title = paper_div["title"]
    paper.filename = get_filename(paper.title)
    paper.abstract = paper_div["snippet"]
    if "resources" in paper_div:
        if "file_format" in paper_div["resources"][0]:
            if paper_div["resources"][0]["file_format"] == "PDF":
                paper.PDF = paper_div["resources"][0]["link"]
    if "link" in paper_div:
        paper.link = paper_div["link"]

    pro_info = paper_div["publication_info"]["summary"]
    result_id = paper_div["result_id"]

    if contains_cjk(pro_info):
        paper.info = pro_info
    else:
        chicago = get_chicago(result_id)
        paper.info = get_info(chicago, pro_info)
    return paper


def save_citation(dir_name, cit_list):
    with open(
        os.path.join("paper_list", dir_name, "citation_info.json"),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(cit_list, f, ensure_ascii=False, indent=4)


def get_citation_info(index, paper):
    index = str(index).zfill(3)
    cit_dict = {
        "index": index,
        "title": paper.title,
        "info": paper.info,
        "abstract": paper.abstract,
        "PDF": paper.PDF,
        "filename": paper.filename,
        "link": paper.link,
    }
    return cit_dict


def get_chicago(qkey):
    params = {
        "engine": "google_scholar_cite",
        "api_key": config.API_KEY,
        "q": qkey,
    }

    search = google_search(params)
    results = search.get_dict()
    citations = results["citations"]
    chicago = citations[2]["snippet"]
    return chicago


def get_position(paper_list):
    folder_path = f"./paper_list/"
    paper_processed = [
        d
        for d in os.listdir(folder_path)
        if os.path.isdir(os.path.join(folder_path, d))
    ]
    if not paper_processed:
        return 0
    c_ind = 0
    for ind, paper in enumerate(paper_list):
        if isinstance(paper, dict):
            current = get_filename(paper["title"])
        else:
            current = get_filename(paper)
        if current in paper_processed:
            c_ind = ind
    return c_ind


def paper_worker(paper):
    dir_name = get_filename(paper["title"])
    os.makedirs(f"./paper_list/{dir_name}/", exist_ok=True)
    print(
        f"***++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***"
    )
    print(f"Start crawling the citations of the paper: [{dir_name}]")
    print(
        f"***++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***"
    )
    print()

    logging.info(
        f"\n***++++++++++++++++++++++++++++++++++crawling Paper: [{dir_name}] {datetime.now().strftime('%Y%m%d%H%M%S')}++++++++++++++++++++++++++++++++++***\n"
    )
    cites_id = paper["cite_id"]
    if cites_id == "no citation":
        logging.info(f"Paper: [{dir_name}] has no citation")
        shutil.rmtree(f"./paper_list/{dir_name}/")
        print(f"Empty folder [{dir_name}] has been deleted.")
        logging.info(f"Empty folder [{dir_name}] has been deleted.")
        logging.info(
            "+++===================================================================================================+++\n"
        )
        print(
            f"***++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***"
        )
        print(f"Paper: [{dir_name}] has no citation")
        print(
            f"***++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***"
        )
        print()
        return

    params = {
        "engine": "google_scholar",
        "api_key": config.API_KEY,
        "cites": cites_id,
        "as_ylo": str(config.start_year),
        "as_yhi": str(config.end_year),
        "num": str(config.num_ls),  # limited to 20
        "start": "0",
    }
    search = google_search(params)
    results = search.get_dict()

    if (
        "search_information" not in results
        or "total_results" not in results["search_information"]
    ):
        logging.info(f"Paper: [{dir_name}] has no citation")
        shutil.rmtree(f"./paper_list/{dir_name}/")
        print(f"Empty folder [{dir_name}] has been deleted.")
        logging.info(f"Empty folder [{dir_name}] has been deleted.")
        logging.info(
            "+++===================================================================================================+++\n"
        )
        print(
            f"***++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***"
        )
        print(f"Paper: [{dir_name}] has no citation")
        print(
            f"***++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***"
        )
        print()
        return
    num_str = results["search_information"]["total_results"]
    num = int(num_str)
    if num == 0:
        shutil.rmtree(f"./paper_list/{dir_name}/")
        print(f"Empty folder [{dir_name}] has been deleted.")
        logging.info(f"Empty folder [{dir_name}] has been deleted.")
        logging.info(
            "+++===================================================================================================+++\n"
        )
        return

    citation_list = [Citation() for i in range(num)]

    # 如果之前爬过，则从之前的位置开始
    if os.path.exists(f"./paper_list/{dir_name}/citation_info.json"):
        with open(f"./paper_list/{dir_name}/citation_info.json", "r") as file:
            cit_list = json.load(file)
    else:
        cit_list = []
    start_pos = len(cit_list)

    logging.info(f"num of citations: {str(num)}")
    logging.info("+================================================+\n")

    for i in range(start_pos, num, config.num_ls):
        params["start"] = str(i)
        search = google_search(params)
        results = search.get_dict()
        if "organic_results" not in results:
            logging.info(f"No organic results for the {i} start_pos of [{dir_name}]")
            continue
        organic_results = results["organic_results"]
        for element in organic_results:
            index = i + int(element["position"])
            if index > num:
                break
            # Ensure citation_list is large enough if num increased or index is out of bounds
            if index - 1 >= len(citation_list):
                citation_list.extend([Citation()] * (index - len(citation_list)))

            citation_list[index - 1] = get_citation(element)
            display_paper(citation_list[index - 1])
            logging.info(f"paper_index: {str(index)}")
            logging.info(
                "+++===================================================================================================+++\n"
            )
            cit_dict = get_citation_info(index, citation_list[index - 1])
            cit_list.append(cit_dict)
            save_citation(dir_name, cit_list)

    print(
        f"***++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***"
    )
    print(f"Paper: [{dir_name}] has been crawled successfully")
    print(
        f"***++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***"
    )
    print()


# 专用于single_paper，获取相关信息
def get_paper_info(title):
    query = title
    params = {"engine": "google_scholar", "api_key": config.API_KEY, "q": query}
    search = google_search(params)
    results = search.get_dict()

    if "organic_results" not in results:
        return "no citation"
    organic_results = results["organic_results"]

    if (
        "cited_by" in organic_results[0]["inline_links"]
        and "cites_id" in organic_results[0]["inline_links"]["cited_by"]
    ):
        cites_id = organic_results[0]["inline_links"]["cited_by"]["cites_id"]
    else:
        cites_id = "no citation"
    link = organic_results[0].get("link", "")
    authors = organic_results[0].get("authors", "")
    publication = organic_results[0].get("publication_info", "")
    data = {
        "title": title,
        "authors": authors,
        "publication": publication,
        "link": link,
        "cite_id": cites_id,
    }
    return data


def paper_crawler(paper_list):

    current_ind = get_position(paper_list)
    paper_ls = paper_list[current_ind:]

    tmp_list = []
    if paper_ls and isinstance(paper_ls[0], str):
        for paper in paper_ls:
            info = get_paper_info(paper)
            if info != "no citation":
                tmp_list.append(info)
        paper_ls = tmp_list

    print()
    print(f"{len(paper_ls)} papers to be crawled:")
    print(
        "+++===================================================================================================+++"
    )
    print()

    logging.info("\n\n\n")
    logging.info(
        "#####***+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***#####"
    )
    title_ls = [paper["title"] for paper in paper_ls]
    logging.info(
        f"The {len(paper_ls)} paper list should be crawled:\n\n" + "\n".join(title_ls)
    )
    logging.info(
        "#####***+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***#####"
    )
    logging.info("\n\n\n")

    for paper in paper_ls:
        paper_worker(paper)
    print("All papers have been crawled successfully.")
    print("\n\n")

    logging.info("\n\n\n")
    logging.info(
        "#####***+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***#####"
    )
    logging.info(f"All papers have been crawled successfully.")
    logging.info(
        "#####***+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++***#####"
    )
    logging.info("\n\n\n")


if __name__ == "__main__":

    if not os.path.exists("./paper_list"):
        os.makedirs("./paper_list")

    paper_crawler(config.paper_list)

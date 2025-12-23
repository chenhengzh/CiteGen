import streamlit as st
import os
import json
import shutil
import time
import glob
from config import PAPER_LIST_DIR
from utils import get_filename

# ================= 配置区域 =================
# 尝试自动猜测下载路径 (Windows/Mac/Linux)
if os.name == "nt":  # Windows
    DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
else:  # Mac / Linux
    DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
# ===========================================

st.set_page_config(layout="wide", page_title="论文手动下载助手")

# 初始化 session state
if "latest_pdf_path" not in st.session_state:
    st.session_state.latest_pdf_path = None
    st.session_state.latest_pdf_time = 0
if "monitored_folder" not in st.session_state:
    st.session_state.monitored_folder = None
if "archive_message" not in st.session_state:
    st.session_state.archive_message = None
# 选中的论文文件夹
if "selected_paper" not in st.session_state:
    st.session_state.selected_paper = None

st.title("📥 论文手动下载助手")

# 显示归档消息（如果有）
if st.session_state.archive_message:
    st.success(st.session_state.archive_message)
    if st.button("清除消息", key="clear_message"):
        st.session_state.archive_message = None
        st.rerun()

st.markdown(
    """
**使用说明：**
1. 在左侧选择要处理的论文项目，并设置浏览器默认下载路径。
2. 页面会列出缺失 PDF 的引用。
3. 点击列表中的链接下载 PDF。
4. 下载完成后，点击对应条目的 **"⬅️ 归档最近下载"** 按钮，工具会自动将你刚刚下载的文件（Downloads文件夹中最新的PDF）移动并重命名。
"""
)

# 1. 获取项目列表
if not os.path.exists(PAPER_LIST_DIR):
    st.error(f"找不到 {PAPER_LIST_DIR} 目录")
    st.stop()

paper_dirs = [
    d
    for d in os.listdir(PAPER_LIST_DIR)
    if os.path.isdir(os.path.join(PAPER_LIST_DIR, d))
]
paper_dirs.sort()

st.sidebar.header("设置")

selected_paper_name = st.sidebar.selectbox(
    "选择论文项目", paper_dirs, index=0 if paper_dirs else None
)
st.session_state.selected_paper = selected_paper_name

# 下载路径设置
download_folder = st.sidebar.text_input("浏览器下载路径", value=DEFAULT_DOWNLOAD_DIR)


# 2. 辅助函数：获取文件夹中最新的PDF
def get_latest_pdf(folder):
    if not os.path.exists(folder):
        return None, 0

    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".pdf")
    ]
    if not files:
        return None, 0

    # 按修改时间排序
    latest_file = max(files, key=os.path.getmtime)
    return latest_file, os.path.getmtime(latest_file)


# 3. 扫描缺失 PDF 的引用
def get_missing_citations(paper_name):
    if not paper_name:
        return []

    paper_path = os.path.join(PAPER_LIST_DIR, paper_name)
    json_path = os.path.join(paper_path, "citation_info.json")

    if not os.path.exists(json_path):
        st.warning(f"在 {paper_name} 中找不到 citation_info.json")
        return []

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            citations = json.load(f)
    except Exception as e:
        st.error(f"读取 citation_info.json 失败: {e}")
        return []

    missing_list = []

    for cit in citations:
        filename = cit.get("filename")
        if not filename:
            continue

        pdf_path = os.path.join(paper_path, f"{filename}.pdf")

        # Check if PDF exists
        if not os.path.exists(pdf_path):
            missing_list.append(
                {
                    "index": cit.get("index", "N/A"),
                    "title": cit.get("title", "Unknown Title"),
                    "filename": filename,
                    "pdf_url": cit.get("PDF", ""),
                    "page_link": cit.get("link", ""),
                    "target_path": pdf_path,
                }
            )

    return missing_list


# 4. 定时检测最新文件（自动监控）
def update_latest_pdf():
    """定期更新最新的 PDF 文件信息"""
    latest_pdf_path, latest_pdf_time = get_latest_pdf(download_folder)
    st.session_state.latest_pdf_path = latest_pdf_path
    st.session_state.latest_pdf_time = latest_pdf_time


# 首次初始化或文件夹改变时更新
if st.session_state.monitored_folder != download_folder:
    st.session_state.monitored_folder = download_folder
    update_latest_pdf()

# 在侧边栏显示当前探测到的文件
st.sidebar.markdown("---")
st.sidebar.subheader("🕵️ 实时监控")

# 自动刷新机制：使用 Streamlit 的 auto-rerun
if st.sidebar.button("🔄 手动刷新"):
    update_latest_pdf()
    st.rerun()

# 显示监控信息
latest_pdf_path = st.session_state.latest_pdf_path
latest_pdf_time = st.session_state.latest_pdf_time

if latest_pdf_path:
    latest_pdf_name = os.path.basename(latest_pdf_path)
    # 计算是多久前下载的
    time_diff = time.time() - latest_pdf_time
    if time_diff < 60:
        st.sidebar.success(f"✅ 检测到新文件 (刚刚):\n**{latest_pdf_name}**")
    else:
        st.sidebar.info(
            f"📄 最新文件 ({int(time_diff/60)}分钟前):\n**{latest_pdf_name}**"
        )
else:
    st.sidebar.warning("⚠️ 下载文件夹中没有 PDF")

# 添加自动刷新的 interval 显示
st.sidebar.markdown("---")
st.sidebar.caption("💡 手动刷新来获取最新的下载文件")

# 5. 主界面列表
missing_papers = get_missing_citations(st.session_state.selected_paper)

st.subheader(f"项目: {st.session_state.selected_paper}")

if not missing_papers:
    st.success("🎉 恭喜！该项目下所有引用论文的 PDF 都已存在。")
else:
    st.write(f"共缺失 {len(missing_papers)} 篇论文")

    for paper in missing_papers:
        # 使用容器把每一行框起来
        with st.container():
            col1, col2, col3 = st.columns([4, 1, 1.5])

            with col1:
                st.markdown(f"**[{paper['index']}] {paper['title']}**")
                links = []
                if paper["pdf_url"]:
                    links.append(f"[直接下载链接]({paper['pdf_url']})")
                if paper["page_link"]:
                    links.append(f"[论文详情页]({paper['page_link']})")
                if not links:
                    st.write("无可用链接")
                else:
                    st.markdown(" | ".join(links))

            with col2:
                # 占位，美观
                pass

            with col3:
                # 核心逻辑：一键归档 - 简化按钮显示
                btn_label = "⬅️ 归档最近下载"

                # Use filename as unique key part
                btn_key = f"move_{paper['filename']}_{paper['index']}"

                if st.button(
                    btn_label,
                    key=btn_key,
                    help="将下载文件夹中最新的PDF移动并重命名为当前论文",
                ):
                    update_latest_pdf()
                    if not st.session_state.latest_pdf_path:
                        st.error("下载文件夹里没有PDF！")
                    else:
                        try:
                            # 保存原始文件名
                            original_filename = os.path.basename(
                                st.session_state.latest_pdf_path
                            )

                            # 移动并重命名
                            # Ensure target directory exists
                            os.makedirs(
                                os.path.dirname(paper["target_path"]), exist_ok=True
                            )
                            shutil.move(
                                st.session_state.latest_pdf_path, paper["target_path"]
                            )

                            # 保存成功消息到 session state
                            st.session_state.archive_message = f"✅ 成功归档: {original_filename} → {os.path.basename(paper['target_path'])}"

                            # 更新最新文件
                            update_latest_pdf()
                            st.rerun()
                        except Exception as e:
                            st.error(f"移动失败: {e}")

            st.divider()

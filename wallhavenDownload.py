r"""
File: \wallhavenDownload.py
Project: wallpaper
Version: 0.10.5
File Created: Friday, 2021-11-05 23:10:20
Author: vanton
-----
Last Modified: Friday, 2024-11-29 16:27:54
Modified By: vanton
-----
Copyright  2021-2024
License: MIT License
"""

import asyncio
import json
import logging
import os
import signal
import time
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Event
from turtle import color
from typing import Any

import aiofiles
import aiohttp
import requests
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Column

from APIKey import APIKey


@dataclass(frozen=True)
class Args:
    """需要时请修改此参数

    See: https://wallhaven.cc/help/api#search

    Attributes:
        categories (str): = `100`/`101`/`111`*/etc (general/anime/people) - Turn categories on(1) or off(0)
        purity (str): = `100`*/`110`/`111`/etc (sfw/sketchy/nsfw) - Turn purities on(1) or off(0) - NSFW requires a valid API key
        ai_art_filter (str): = `0`/`1` - AI art filter - off(0) allow AI
        sorting (str): = "hot" `date_added`*, `relevance`, `random`, `views`, `favorites`, `toplist`- Method of sorting results
        order (str): = `desc`*, `asc` - Sorting order
        topRange (str): = `1d`, `3d`, `1w`, `1M`*, `3M`, `6M`, `1y` - Sorting MUST be set to 'toplist'
        ratios (str): = 16x9,16x10,`landscape`,`portrait`,`square` - List of aspect ratios - Single ratio allowed
        atleast (str): = `1920x1080` - Minimum resolution allowed

        SAVE_PATH (str): Where images are saved
        MAX_PAGE (int): Maximum pages to download
    """

    categories: str = "110"
    purity: str = "100"
    ai_art_filter: str = "0"
    sorting: str = "hot"
    order: str = "desc"
    topRange: str = "1w"
    ratios: str = "landscape"
    atleast: str = "1000x1000"

    SAVE_PATH: str = "./Pic"
    MAX_PAGE: int = 4


"""
: command: python3 wallhavenDownload.py - m toplist - s./Pic - p 1
: command: python3 wallhavenDownload.py - m latest - s./Pic - p 1
: command: python3 wallhavenDownload.py - m hot - s ./Pic - p 1

参数说明:
--categories 110
-c 110
爬取图片分类 General, Anime, People:
    110 -> General+Anime,
    111 -> General+Anime+People, (默认)
    100 -> General
--mode {toplist, latest, hot}
-m hot
爬取图片模式，{toplist, latest, hot} 三种模式，默认为 hot
--savePath savePath
-s ./Pic
图片保存路径，默认 ./Pic
--maxPage maxPage
-p 1
最大页数, 默认 1
"""

#!##############################################################################
# 配置
max_files = 24 * Args.MAX_PAGE + 4
"""max_files (int): 要保留的最大文件数量，默认为 24 * Args.MAX_PAGE + 4。
- 理论上是 Args.MAX_PAGE 页的数量; 如果一次下载图片过多, 会发生重复下载图片然后重复删除。
- 建议保存图片数应大于 单页数量 * 下载页数。"""
wallhaven_url_base = "https://wallhaven.cc/api/v1/search?"
pic_type_map = {
    "image/png": "png",
    "image/jpeg": "jpg",
}
DEBUG: bool = True

# 参数解析
# parser = argparse.ArgumentParser()
# # General, Anime, People: 110 - General+Anime, 111 - General+Anime+People
# parser.add_argument('--categories', '-c', default='100', help='爬取图片分类 General, Anime, People: 110 - General+Anime, 111 - General+Anime+People')
# parser.add_argument('--mode', '-m', default='hot', choices=['toplist', 'latest', 'hot'], help='爬取图片模式')
# parser.add_argument('--savePath', '-s', default='./Pic', help='图片保存路径')
# parser.add_argument('--maxPage', '-p', default=2, help='最大页数')
# args = parser.parse_args()

#!##############################################################################


class AdvProgress(Progress):
    def get_renderables(self):
        title = "Progress"
        if hasattr(self, "title"):
            title = self.title
        yield Panel(renderable=self.make_tasks_table(tasks=self.tasks), title=title)

    def set_title(self, title):
        self.title = title


progress = AdvProgress(
    TextColumn(text_format="[bold blue]{task.fields[filename]}", justify="right"),
    "{task.fields[colors]}",
    BarColumn(),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(table_column=Column(justify="center")),
    "•",
    TransferSpeedColumn(table_column=Column(justify="right")),
    "•",
    TimeRemainingColumn(),
    TextColumn(text_format="[gray]{task.description}"),
    auto_refresh=False,
)
console = progress.console
"""`logging` 与 `progress` 输出使用同一个 `console` 实例，以防止输出冲突"""
window_width, window_height = console.size
done_event = Event()


def handle_sigint(signum, frame):
    done_event.set()


signal.signal(signal.SIGINT, handle_sigint)
# socks5_proxy = ""
# proxies = dict(http=socks5_proxy, https=socks5_proxy)


class Log:
    """日志类

    see the :mod:`logging` module

    Attributes:
        self.logger: same as :class:`logging.Logger`
    """

    def __init__(
        self,
        logPath="./log/wallhavenDownload.log",
        when="D",  # 按天轮换日志
        maxBytes=1024 * 64,  # 轮换日志大小
        backupCount=5,  # 保留日志文件数量
    ):
        # 文件不存在则创建
        if not os.path.exists(os.path.dirname(logPath)):
            os.makedirs(os.path.dirname(logPath))
        if not os.path.exists(logPath):
            with open(logPath, "w", encoding="UTF-8") as f:
                f.write("")

        # 重命名备份日志文件
        def custom_namer(default_name: str) -> str:
            base_filename, ext, date = default_name.split(".")
            return f"{base_filename}.{date}.{ext}"

        log_level = logging.DEBUG if DEBUG else logging.INFO
        # handler = TimedRotatingFileHandler(
        #     logPath, when=when, backupCount=backupCount, encoding="UTF-8"
        # )
        handler = RotatingFileHandler(
            logPath, maxBytes=maxBytes, backupCount=backupCount, encoding="UTF-8"
        )
        handler.setLevel(log_level)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
        )
        handler.namer = custom_namer

        rich_handler = RichHandler(console=console)
        rich_handler.setLevel(logging.INFO)
        rich_handler.setFormatter(logging.Formatter("%(message)s"))

        logging.basicConfig(
            level=logging.NOTSET,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[rich_handler, handler],
        )
        self.logger = logging.getLogger(__name__)


log = Log().logger


def init_download():
    global wallhaven_url_base
    # https://wallhaven.cc/search?categories=110&purity=100&sorting=hot&order=desc
    # sorting=toplist toplist
    # sorting=hot 最热
    # sorting=latest 最新
    # atleast=1000x1000 最小尺寸 1000x1000
    # topRange=1w 一周

    wallhaven_url_base += (
        f"apikey={APIKey}&categories={Args.categories}&order=desc&topRange={Args.topRange}&atleast={Args.atleast}"
        f"&sorting={Args.sorting}&ratios={Args.ratios}&purity={Args.purity}&ai_art_filter={Args.ai_art_filter}&page="
    )
    log.info(wallhaven_url_base.split("&", 1)[1])
    # log.info(wallhaven_url_base)
    # 创建文件保存目录
    os.makedirs(Args.SAVE_PATH, exist_ok=True)


def format_time(atime: float | None = None) -> str:
    """格式化时间
    Args:
        atime: 时间戳秒数，或为 None 以格式化当前时间。

    Returns:
        格式为 "YYYY-MM-DD HH:MM:SS" 的字符串。
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(atime))


def format_size(size_bytes: int) -> str:
    """Convert file size in bytes to human readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size string (e.g. "1.23 MB")
    """
    size_mb = size_bytes / (1024 * 1024)
    return f"{round(size_mb, 2)} MB"


@lru_cache(maxsize=128)
def calculate_dir_size(path: str | Path) -> int:
    """Calculate total size of directory contents in bytes.

    Args:
        path: Directory path

    Returns:
        int: Total size in bytes
    """
    path = Path(path)
    if not path.is_dir():
        return 0

    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except Exception as e:
        log.error(f"Error calculating directory size for {path}: {e}")
        return 0


def get_dir_info(path: str | Path):
    """Get directory information including size and file count.

    Args:
        path: Directory path

    Returns:
        dict: Directory information containing size and file count
    """
    path = Path(path)
    if not path.exists():
        log.error(f"Directory does not exist: {path}")
        return {"exists": False, "is_dir": False, "size": 0, "file_count": 0}

    if not path.is_dir():
        log.error(f"Path is not a directory: {path}")
        return {"exists": True, "is_dir": False, "size": 0, "file_count": 0}

    size_bytes = calculate_dir_size(path)
    file_count = sum(1 for _ in path.rglob("*") if _.is_file())

    info = {
        "exists": True,
        "is_dir": True,
        "size_bytes": size_bytes,
        "size_formatted": format_size(size_bytes),
        "file_count": file_count,
    }

    log.info(f"Directory {path}: {info['size_formatted']}, {info['file_count']} files")
    return info


def remove_file(file_path: str | Path) -> bool:
    """Safely remove a file.

    Args:
        file_path: Path to file to remove

    Returns:
        bool: True if file was successfully removed
    """
    file_path = Path(file_path)
    if not file_path.exists():
        log.error(f"File does not exist: {file_path}")
        return False

    if not file_path.is_file():
        log.warning(f"Path is not a file: {file_path}")
        return False

    try:
        file_path.unlink()
        log.info(f"Successfully removed file: {file_path}")
        return True
    except Exception as e:
        log.error(f"Failed to remove file {file_path}: {e}")
        return False


def clean_directory(
    directory=Args.SAVE_PATH, max_files=max_files, sort_key: str = "created"
) -> dict:
    """Clean directory by removing oldest files while keeping specified number of newest files.

    Args:
        directory: Directory path to clean
        max_files: Maximum number of files to keep
        sort_key: Key to sort files by ('created', 'modified', or 'accessed')

    Returns:
        dict: Summary of cleaning operation
    """
    directory = Path(directory)
    if not directory.exists():
        log.error(f"Directory does not exist: {directory}")
        return {"success": False, "files_removed": 0, "errors": 1}

    if not directory.is_dir():
        log.error(f"Path is not a directory: {directory}")
        return {"success": False, "files_removed": 0, "errors": 1}

    # Get all files with their stats
    try:
        files_info = []
        for file_path in directory.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                timestamp = {
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "accessed": stat.st_atime,
                }.get(sort_key, stat.st_ctime)

                files_info.append((file_path, timestamp))
    except Exception as e:
        log.error(f"Error reading directory contents: {e}")
        return {"success": False, "files_removed": 0, "errors": 1}

    # Sort files by timestamp
    files_info.sort(key=lambda x: x[1])

    # Calculate files to remove
    files_to_remove = files_info[:-max_files:] if len(files_info) > max_files else []

    # Remove files
    removed_count = 0
    errors = 0

    for file_path, _ in files_to_remove:
        if remove_file(file_path):
            removed_count += 1
        else:
            errors += 1

    # Get directory info after cleaning
    final_info = get_dir_info(directory)

    summary = {
        "success": errors == 0,
        "files_removed": removed_count,
        "errors": errors,
        "remaining_files": final_info["file_count"],
        "final_size": final_info["size_formatted"],
    }

    log.info(f"Directory cleaning complete: {summary}")
    return summary


@dataclass
class DownloadTask:
    """Represents a download task with its metadata"""

    task_id: TaskID
    url: str
    path: Path
    chunk_size: int = 64 * 1024  # 64KB chunks
    timeout: int = 20
    headers: dict[str, str] | None = None

    def __post_init__(self):
        self.headers = self.headers or {"User-Agent": "Magic Browser"}
        self.path.parent.mkdir(parents=True, exist_ok=True)


done_list: deque[TaskID] = deque()
count = 0
all = 0


async def copy_url_async(task: DownloadTask) -> None | TaskID:
    """Asynchronously copy data from a URL to a local file.
    Args:
        task: DownloadTask containing download parameters

    Returns:
        Task ID if successful, None if failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                task.url, headers=task.headers, timeout=task.timeout
            ) as response:
                if response.status != 200:
                    log.error(f"HTTP {response.status} for {task.url}")
                    return None
                total_size = int(response.headers.get("Content-Length", 0))
                progress.update(task_id=task.task_id, total=total_size)
                async with aiofiles.open(task.path, "wb") as dest_file:
                    progress.start_task(task.task_id)
                    progress.update(task.task_id, visible=True)
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(task.chunk_size):
                        if done_event.is_set():
                            return task.task_id
                        await dest_file.write(chunk)
                        downloaded += len(chunk)
                        progress.update(task.task_id, advance=len(chunk), refresh=True)
                    if downloaded == total_size:
                        progress.update(
                            task.task_id, description="[green]", refresh=True
                        )
                        return task.task_id
                    else:
                        log.warning(f"Incomplete download for {task.url}")
                        progress.update(
                            task.task_id, description="[red]", refresh=True
                        )
    except KeyboardInterrupt:
        log.info("Download interrupted by user")
        done_event.set()
    except asyncio.TimeoutError:
        log.error(f"Timeout downloading {task.url}")
    except aiohttp.ClientError as e:
        log.error(f"Network error for {task.url}: {e}")
    except Exception as e:
        log.error(f"Unexpected error downloading {task.url}: {e}")


def set_done(task_id: TaskID):
    """Mark a task as done and update the progress bar."""
    global done_list, count, all
    if task_id not in done_list:
        done_list.append(task_id)
        count += 1
    _length = len(done_list)
    if (_length > window_height - 15 and _length > 10) or _length > 24:
        progress.remove_task(done_list.popleft())  # cspell:words popleft

    progress.set_title(f"Progress: {count}/{all}")


async def download_with_retries(task: DownloadTask, max_retries=3) -> TaskID | None:
    """Attempt to download with retries on failure"""
    for attempt in range(max_retries):
        if attempt > 0:
            await asyncio.sleep(2**attempt)  # Exponential backoff
            log.warning(f"retry {attempt + 1}/{max_retries} for {task.url}")
            progress.reset(task_id=task.task_id, start=True)
            progress.update(
                task.task_id,
                description=f" {attempt + 1}/{max_retries}",
            )
        result = await copy_url_async(task)
        if result != None:
            set_done(task_id=task.task_id)
            return result
    progress.update(task.task_id, description="[red]", refresh=True)
    set_done(task_id=task.task_id)


@dataclass
class TargetPic:
    id: str  # "7p86x9"
    file_size: int  # 2305231
    path: str  # "https://w.wallhaven.cc/full/7p/wallhaven-7p86x9.jpg"
    resolution: str  # "1600x1074"
    purity: str  # "sfw"
    colors: list[str]  # ["#424153","#ff9900","#000000","#ff6600","#999999"]


async def download_async(
    pics: list[tuple[TargetPic, bool]], dest_dir=Args.SAVE_PATH, max_concurrent=4
):
    """Download multiple files concurrently to the given directory.
    Args:
        urls: Iterable of URLs to download
        dest_dir: Destination directory
        max_concurrent: Maximum number of concurrent downloads
    """
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []

    async def bounded_download(task: DownloadTask) -> TaskID | None:
        async with semaphore:
            return await download_with_retries(task=task)

    with progress:
        for pic, again in pics:
            filename = pic.path.split("/")[-1]
            # colors = "[#990033]█[#339966]█[#993366]█[#FF9933]█[#6666FF]█"
            colors = "".join([f"[{color}]██" for color in pic.colors])
            description = "" if again else ""
            task_id: TaskID = progress.add_task(
                description=description,
                filename=filename,
                colors=colors,
                start=False,
                visible=False,
            )
            download_task = DownloadTask(
                task_id=task_id, url=pic.path, path=dest_path / filename
            )
            tasks.append(bounded_download(download_task))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Handle any exceptions that occurred
        for pic, result in zip(pics, results):
            if isinstance(result, Exception):
                log.error(f"Failed to download {pic}: {result}")


def download(pics: list[tuple[TargetPic, bool]], dest_dir=Args.SAVE_PATH):
    """Entry point for downloads - runs async code in event loop"""
    try:
        asyncio.run(download_async(pics, dest_dir))
    except KeyboardInterrupt:
        log.info("Download interrupted by user")
        done_event.set()
    except Exception as e:
        log.error(f"Download failed: {e}")
        done_event.set()


def download_one_pic(target_pic: TargetPic) -> None | tuple[TargetPic, bool]:
    """下载指定 URL 的单张图片到指定路径。
    Args:
        target_pic:
    """
    url = target_pic.path
    filename = url.split("/")[-1]
    filesize = target_pic.file_size
    pic_path = f"{Args.SAVE_PATH}/{filename}"
    # log.debug(f"<{pic_id}> <{resolution}> {url}")
    again = False
    if os.path.isfile(pic_path):
        file_info = os.stat(pic_path)
        log.debug(
            f"图片已存在 <{filename}> <{format_size(file_info.st_size)}> <{format_time(file_info.st_atime)}>"
        )
        if file_info.st_size == filesize:
            return
        else:
            log.debug(
                f"图片不完整，重新下载 <{filename}> <{file_info.st_size} -> {filesize}>"
            )
            again = True
    return target_pic, again


def handle_server_response(response_bytes) -> Any:
    """处理来自服务器的响应。
    Args:
        response_bytes: 服务器返回的字节数据。

    Returns:
        如果解码和解析成功则返回解析后的 JSON 对象，否则返回 None。
    """
    try:
        response_str = response_bytes.decode("utf-8")
        response_dict = json.loads(response_str)
        return response_dict
    except json.JSONDecodeError as e:
        log.critical(f"结果转化错误: {e}")


def get_pending_pic_url(wallhaven_url: str) -> list[TargetPic]:
    """从 Wallhaven API 检索待处理的图片 URL 列表。
    Args:
        wallhaven_url: 查询图片数据的 URL。

    Returns:
        list: 包含图片元数据(ID、分辨率、URL 和文件类型)的字典列表。
    """
    # response_res = requests.get(wallhaven_url, proxies=proxies).content
    response_res = requests.get(url=wallhaven_url).content
    response_res_dict = handle_server_response(response_bytes=response_res)
    if not response_res_dict.get("data"):
        log.critical("获取图片列表失败")
        raise Exception("获取图片列表失败")
    target_pics_list = []
    for pic in response_res_dict.get("data"):
        target_pics_list.append(
            TargetPic(
                id=pic.get("id"),
                file_size=pic.get("file_size"),
                path=pic.get("path"),
                resolution=pic.get("resolution"),
                purity=pic.get("purity"),
                colors=pic.get("colors"),
            )
        )
    return target_pics_list


def download_all_pics():
    """从 Wallhaven 下载指定页面范围的所有图像。"""
    global all
    pics = []
    for page_num in range(1, int(Args.MAX_PAGE) + 1):
        wallhaven_url = wallhaven_url_base + str(page_num)
        pending_pic_list: list[TargetPic] = get_pending_pic_url(wallhaven_url)
        num = 0
        for target_pic in pending_pic_list:
            pic: None | tuple[TargetPic, bool] = download_one_pic(target_pic)
            if pic:
                pics.append(pic)
                num += 1
        log.info(f"下载第{page_num}页图片: {num}/{len(pending_pic_list)}")
    all = len(pics)
    download(pics)
    log.info("图片下载完成")


def wallhaven_download():
    init_download()
    download_all_pics()


if __name__ == "__main__":
    _sep = "-" * 15
    log.info(f"{_sep} START {_sep} >>> {format_time()}")
    wallhaven_download()
    clean_directory()
    log.info(f"{_sep}  END  {_sep} >>> {format_time()}\n")

"""
Filename: /wallhavenDownload.py
Project: wallpaper
Version: v0.9.3
File Created: Friday, 2021-11-05 23:10:20
Author: vanton
-----
Last Modified: Tuesday, 2024-11-08 16:40:36
Modified By: vanton
-----
Copyright (c) 2024
"""

import aiohttp
import aiofiles
import asyncio
import json
import logging
import os
import requests
import signal
import time
from typing import Iterable, Optional
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from threading import Event
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from APIKey import APIKey


@dataclass
class Args:
    """需要时请修改此参数"""

    CATEGORIES: str = "110"  # General + Anime + People
    MODE: str = "hot"  # Download mode (hot/latest/toplist)
    SAVE_PATH: str = "./Pic"  # Where images are saved
    MAX_PAGE: int = 2  # Maximum pages to download
    RATIOS: str = "landscape"  # Image aspect ratio filter


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
when = "D"  # 按天轮换日志
backup_count = 5  # 保留日志文件数量
log_path = "./log/wallhavenDownload.log"
wallhaven_url_base = ""
pic_type_map = {
    "image/png": "png",
    "image/jpeg": "jpg",
}

# 参数解析
# parser = argparse.ArgumentParser()
# # General, Anime, People: 110 - General+Anime, 111 - General+Anime+People
# parser.add_argument('--categories', '-c', default='100', help='爬取图片分类 General, Anime, People: 110 - General+Anime, 111 - General+Anime+People')
# parser.add_argument('--mode', '-m', default='hot', choices=['toplist', 'latest', 'hot'], help='爬取图片模式')
# parser.add_argument('--savePath', '-s', default='./Pic', help='图片保存路径')
# parser.add_argument('--maxPage', '-p', default=2, help='最大页数')
# args = parser.parse_args()

#!##############################################################################

console = Console()
progress = Progress(
    TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
    SpinnerColumn(),
    BarColumn(),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
)
done_event = Event()


def handle_sigint(signum, frame):
    done_event.set()


signal.signal(signal.SIGINT, handle_sigint)
# socks5_proxy = ""
# proxies = dict(http=socks5_proxy, https=socks5_proxy)


class Log:
    # when 轮换时间 S: 秒 M: 分 H: 小时 D: 天 W: 周

    def __init__(
        self,
        logPath=log_path,
        when=when,
        maxBytes=1024 * 1000,
        backupCount=backup_count,
    ):
        # 文件不存在则创建
        if not os.path.exists(os.path.dirname(logPath)):
            os.makedirs(os.path.dirname(logPath))
        if not os.path.exists(logPath):
            with open(logPath, "w", encoding="UTF-8") as f:
                f.write("")

        # _fmt = '%(asctime)s - [%(levelname)s] - %(message)s'
        _fmt = "%(message)s"

        def custom_namer(default_name) -> str:
            base_filename, ext, date = default_name.split(".")
            return f"{base_filename}.{date}.{ext}"

        handler = TimedRotatingFileHandler(
            logPath, when=when, backupCount=backupCount, encoding="UTF-8"
        )
        handler.namer = custom_namer

        logging.basicConfig(
            level=logging.INFO,
            format=_fmt,
            handlers=[RichHandler(console=console), handler],
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

    wallhaven_url_base = (
        f"https://wallhaven.cc/api/v1/search?apikey={APIKey}&categories={Args.CATEGORIES}"
        f"&sorting={Args.MODE}&ratios={Args.RATIOS}&purity=100&atleast=1000x1000&topRange=1w&page="
    )
    log.info(wallhaven_url_base.split("&", 1)[1])
    # log.info(wallhaven_url_base)
    # 创建文件保存目录
    os.makedirs(Args.SAVE_PATH, exist_ok=True)


def format_time(atime: Optional[float] = None) -> str:
    """
    Args:
        atime: 时间戳秒数，或为 None 以格式化当前时间。

    Returns:
        格式为 "YYYY-MM-DD HH:MM:SS" 的字符串。
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(atime))


def file_size(size_in_bytes: int) -> str:
    """
    计算文件大小并返回以MB为单位的字符串表示。

    Args:
        size_in_bytes: 文件大小（字节）

    Returns:
        以"X.XX MB"格式表示的文件大小
    """
    size_in_mb = size_in_bytes / float(1024 * 1024)
    return f"{round(size_in_mb, 2)} MB"


def dir_size(path: str | os.PathLike) -> str | int:
    """
    计算指定目录的大小。

    Args:
        path: 要计算大小的目录路径。

    Returns:
        表示目录大小的字符串，格式为 "X.XX MB"。
    """
    size = 0
    if os.path.isdir(path):
        try:
            size = sum(
                sum(
                    os.path.getsize(os.path.join(walk_result[0], element))
                    for element in walk_result[2]
                )
                for walk_result in os.walk(path)
            )
            size = file_size(size)
        except Exception as e:
            log.error(f"发生错误: {e}")
    return size


def dir_info(path: str | os.PathLike):
    """
    记录目录的信息。

    Args:
        path: 要记录信息的目录路径。
    """
    if os.path.exists(path):
        if os.path.isdir(path):
            log.info(f"<图片目录:{path}> <大小:{dir_size(path)}>")
        else:
            log.error(f"目标不是目录: {path}")
    else:
        log.error(f"图片目录不存在: {path}")


def remove_file(file: str | os.PathLike):
    """
    移除文件。

    Args:
        file: 要移除的文件路径。
    """
    if os.path.exists(file):
        if os.path.isfile(file):
            os.remove(file)
            log.info(f"文件删除成功: {file}")
        else:
            log.warning(f"目录不可删除: {file}")
    else:
        log.error(f"文件不存在: {file}")


def clean_up(path=Args.SAVE_PATH, max_files=96):
    """
    清理目录中的文件，移除旧文件。

    Args:
        path: 要清理的目录路径，默认为 args.savePath。
        max_files: 要保留的最大文件数量，默认为 96。
    """
    log.info("清理文件")
    if os.path.exists(path):
        dir_info(path)
        files = os.listdir(path)
        log.info(f"清理前文件数量: {len(files)}")
        old_pwd = os.getcwd()
        os.chdir(path)
        files.sort(key=os.path.getctime)
        del files[-max_files:]

        for file in files:
            remove_file(file)

        os.chdir(old_pwd)
        dir_info(path)
    else:
        log.error(f"文件不存在: {path}")


def handle_server_response(response_bytes) -> Optional[dict]:
    """
    处理来自服务器的响应。

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
        return None


@dataclass
class DownloadTask:
    """Represents a download task with its metadata"""

    task_id: str
    url: str
    path: Path
    chunk_size: int = 32 * 1024  # 32KB chunks
    timeout: int = 60
    headers: dict = None

    def __post_init__(self):
        self.headers = self.headers or {"User-Agent": "Magic Browser"}
        self.path.parent.mkdir(parents=True, exist_ok=True)


async def copy_url_async(task: DownloadTask) -> Optional[str]:
    """
    Asynchronously copy data from a URL to a local file.

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
                progress.update(task.task_id, total=total_size)
                async with aiofiles.open(task.path, "wb") as dest_file:
                    progress.start_task(task.task_id)
                    progress.update(task.task_id, visible=True)
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(task.chunk_size):
                        if done_event.is_set():
                            return task.task_id
                        await dest_file.write(chunk)
                        downloaded += len(chunk)
                        progress.update(task.task_id, advance=len(chunk))
                    if downloaded == total_size:
                        return task.task_id
                    else:
                        log.warning(f"Incomplete download for {task.url}")
                        return None
    except asyncio.TimeoutError:
        log.error(f"Timeout downloading {task.url}")
    except aiohttp.ClientError as e:
        log.error(f"Network error for {task.url}: {e}")
    except Exception as e:
        log.error(f"Unexpected error downloading {task.url}: {e}")
    return None


async def download_with_retries(task: DownloadTask, max_retries=3) -> Optional[str]:
    """Attempt to download with retries on failure"""
    for attempt in range(max_retries):
        if attempt > 0:
            await asyncio.sleep(2**attempt)  # Exponential backoff
            log.warning(f"Retry {attempt + 1}/{max_retries} for {task.url}")
            progress.reset(task.task_id, start=True)
        result = await copy_url_async(task)
        if result:
            return result
    return None


async def download_async(
    urls: Iterable[str], dest_dir=Args.SAVE_PATH, max_concurrent=4
):
    """
    Download multiple files concurrently to the given directory.

    Args:
        urls: Iterable of URLs to download
        dest_dir: Destination directory
        max_concurrent: Maximum number of concurrent downloads
    """
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []

    async def bounded_download(task: DownloadTask) -> Optional[str]:
        async with semaphore:
            return await download_with_retries(task)

    with progress:
        for url in urls:
            filename = url.split("/")[-1]
            task_id = progress.add_task(
                "download", filename=filename, start=False, visible=False
            )
            download_task = DownloadTask(
                task_id=task_id, url=url, path=dest_path / filename
            )
            tasks.append(bounded_download(download_task))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Handle any exceptions that occurred
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                log.error(f"Failed to download {url}: {result}")


def download(urls: Iterable[str], dest_dir=Args.SAVE_PATH):
    """
    Entry point for downloads - runs async code in event loop
    """
    try:
        asyncio.run(download_async(urls, dest_dir))
    except KeyboardInterrupt:
        log.info("Download interrupted by user")
        done_event.set()
    except Exception as e:
        log.error(f"Download failed: {e}")
        done_event.set()


@dataclass
class TargetPic:
    id: str
    resolution: str
    url: str
    file_size: int


def download_one_pic(target_pic: TargetPic) -> Optional[str]:
    """
    下载指定 URL 的单张图片到指定路径。

    Args:
        target_pic: 包含图片 ID、分辨率、URL 和文件类型的字典。
    """
    pic_id = target_pic.id
    resolution = target_pic.resolution
    url = target_pic.url
    filename = url.split("/")[-1]
    filesize = target_pic.file_size
    pic_path = f"{Args.SAVE_PATH}/{filename}"
    log.debug(f"<{pic_id}> <{resolution}> {url}")
    if os.path.isfile(pic_path):
        file_info = os.stat(pic_path)
        log.debug(
            f"图片已存在 <{filename}> <{file_size(file_info.st_size)}> <{format_time(file_info.st_atime)}>"
        )
        if file_info.st_size == filesize:
            return
        else:
            log.warning(
                f"图片不完整，重新下载 <{filename}> <{file_info.st_size} -> {filesize}>"
            )
        # if is_valid_image(pic_path):
        #     return
    # wget(url, pic_path)
    return url


def get_pending_pic_url(wallhaven_url: str) -> list:
    """
    从 Wallhaven API 检索待处理的图片 URL 列表。

    Args:
        wallhaven_url: 查询图片数据的 URL。

    Returns:
        list: 包含图片元数据（ID、分辨率、URL 和文件类型）的字典列表。
    """
    # response_res = requests.get(wallhaven_url, proxies=proxies).content
    response_res = requests.get(wallhaven_url).content
    response_res_dict = handle_server_response(response_res)
    pending_pic_url_list = []
    if not response_res_dict.get("data"):
        log.critical("获取图片列表失败")
        raise Exception("获取图片列表失败")  # 使用异常处理代替 exit(1)
    for pic_msg in response_res_dict["data"]:
        pic_msg_main = TargetPic(
            id=pic_msg["id"],
            resolution=pic_msg["resolution"],
            url=pic_msg["path"],
            file_size=pic_msg["file_size"],
        )
        pending_pic_url_list.append(pic_msg_main)
    return pending_pic_url_list


def download_all_pics():
    """从 Wallhaven 下载指定页面范围的所有图像。"""
    urls = []
    for page_num in range(1, int(Args.MAX_PAGE) + 1):
        wallhaven_url = wallhaven_url_base + str(page_num)
        pending_pic_url_list: list[TargetPic] = get_pending_pic_url(wallhaven_url)
        num = 0
        for target_pic in pending_pic_url_list:
            url = download_one_pic(target_pic)
            if url:
                urls.append(url)
                num += 1
        log.info(f"下载第{page_num}页图片: {num}/{len(pending_pic_url_list)}")
    download(urls)
    # log.debug(f"{page_num}页图片下载完成")


def wallhaven_download():
    init_download()
    download_all_pics()


if __name__ == "__main__":
    _sep = "-" * 15
    log.info(f"{_sep} START {_sep} >>> {format_time()}")
    wallhaven_download()
    clean_up()
    log.info(f"{_sep}  END  {_sep} >>> {format_time()}\n")

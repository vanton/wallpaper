'''
Filename: \wallhavenDownload.py
Project: wallpaper
Version: v0.8.2
File Created: Friday, 2021-11-05 23:10:20
Author: vanton
-----
Last Modified: Tuesday, 2024-11-08 16:40:36
Modified By: vanton
-----
Copyright (c) 2024
'''

import json
import logging
import os
import subprocess
import time
from colorama import init, Fore, Back, Style
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from APIKey import APIKey


class Args():
    ''' 需要时请修改此参数
    '''
    CATEGORIES = '111'    # General + Anime + People
    MODE = 'hot'          # Download mode (hot/latest/toplist)
    SAVE_PATH = './Pic'   # Where images are saved
    MAX_PAGE = 2          # Maximum pages to download
    RATIOS = 'landscape'  # Image aspect ratio filter


'''
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
'''

#!##############################################################################
# 配置
when = 'H'  # 按小时日志
backup_count = 5  # 保留日志文件数量
log_path = './log/wallhavenDownload.log'

wallhaven_url_base = ""

pic_type_map = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
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

init(autoreset=True)


class MyFormatter(logging.Formatter):
    '''自定义日志格式
    '''

    def format(self, record: logging.LogRecord) -> str:
        '''自定义日志格式

        :param record: 日志记录
        :return: 格式化后的字符串
        '''
        record.message = record.getMessage()
        # 这里的字典可以简化，不需要重复使用 record.levelname
        log_level_colors = {
            logging.INFO:     f"{Fore.GREEN}INFO{Style.RESET_ALL}",
            logging.WARNING:  f"{Fore.RED}WARNING{Style.RESET_ALL}",
            logging.ERROR:    f"{Fore.RED + Back.WHITE}ERROR{Style.RESET_ALL}",
            logging.CRITICAL: f"{Fore.WHITE + Back.RED}CRITICAL{Style.RESET_ALL}",
            logging.DEBUG:    f"{Fore.BLUE}DEBUG{Style.RESET_ALL}"
        }
        record.levelname = log_level_colors.get(
            record.levelno, record.levelname)
        return super().format(record)


class Log:
    # when 轮换时间 S: 秒 M: 分 H: 小时 D: 天 W: 周

    def __init__(self, logPath=log_path, when=when, maxBytes=1024*1000, backupCount=backup_count):
        '''
        :param logPath: The path where the log file will be stored.
        :param when: The interval for rotating the log file (e.g., 'H' for hourly).
        :param maxBytes: The maximum file size for log rotation by size (unused in current implementation).
        :param backupCount: The number of backup log files to keep.
        '''
        # 文件不存在则创建
        if not os.path.exists(os.path.dirname(logPath)):
            os.makedirs(os.path.dirname(logPath))
        if not os.path.exists(logPath):
            with open(logPath, 'w', encoding='UTF-8') as f:
                f.write('')

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self._fmt = '%(asctime)s - [%(levelname)s] - %(message)s'

        self.formatter = logging.Formatter(self._fmt)

        # 输出到文件
        # 按日期轮换

        def namer(name: str) -> str:
            '''
            :param name: The original log filename with a date suffix before ".log".
            :return: The modified log filename with the date suffix repositioned.
            '''
            # xxx.log.2021-11-05 -> xxx.2021-11-05.log`
            return name.replace(".log", "") + ".log"

        self.fileHandler = TimedRotatingFileHandler(
            logPath, when=when, backupCount=backupCount, encoding='UTF-8')
        self.fileHandler.namer = namer
        # self.fileHandler.suffix = "%Y-%m-%d_%H-%M.log"
        # self.fileHandler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}")

        # 按文件大小轮换
        # self.fileHandler = RotatingFileHandler(
        #     logPath, maxBytes=maxBytes, backupCount=backupCount, encoding='UTF-8')

        self.fileHandler.setFormatter(self.formatter)
        self.logger.addHandler(self.fileHandler)

        # 输出到控制台
        self.streamFormatter = MyFormatter(self._fmt)
        self.streamHandler = logging.StreamHandler()
        self.streamHandler.setFormatter(self.streamFormatter)
        self.logger.addHandler(self.streamHandler)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def critical(self, msg):
        self.logger.critical(msg)

    def exception(self, msg):
        self.logger.exception(msg)


log = Log()


def init():
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
    log.info(wallhaven_url_base.split('&', 1)[1])
    # log.info(wallhaven_url_base)
    # 创建文件保存目录
    os.makedirs(Args.SAVE_PATH, exist_ok=True)


def format_time(atime: float = None) -> str:
    '''
    :param atime: 时间戳秒数，或为 None 以格式化当前时间。
    :return: 格式为 "YYYY-MM-DD HH:MM:SS" 的字符串。
    '''
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(atime))


def file_size(size_in_bytes: int) -> str:
    '''
    计算文件大小并返回以MB为单位的字符串表示。

    :param size_in_bytes: 文件大小（字节）
    :return: 以"X.XX MB"格式表示的文件大小
    '''
    size_in_mb = size_in_bytes / float(1024 * 1024)
    return f"{round(size_in_mb, 2)} MB"


def dir_size(path: str) -> str | int:
    '''
    计算指定目录的大小。

    :param path: 要计算大小的目录路径。
    :return: 表示目录大小的字符串，格式为 "X.XX MB"。
    '''
    size = 0
    if os.path.exists(path):
        try:
            process = subprocess.Popen(
                ['du', '-s', path], stdout=subprocess.PIPE)
            process_output = process.communicate()[0]
            if process_output:
                size = int(process_output.split()[0]) * 1024  # 转换为字节
                size = file_size(size)
        except Exception as e:
            print(f"发生错误: {e}")
    return size


def dir_info(path: str):
    '''
    记录目录的信息。

    :param path: 要记录信息的目录路径。
    '''
    if os.path.exists(path):
        if os.path.isdir(path):
            log.info(f"<图片目录:{path}> <大小:{dir_size(path)}>")
        else:
            log.error(f"目标不是目录: {path}")
    else:
        log.error(f"图片目录不存在: {path}")


def remove_file(file: str):
    '''
    移除文件。

    :param file: 要移除的文件路径。
    '''
    if os.path.exists(file):
        if os.path.isfile(file):
            os.remove(file)
            log.info(f"文件删除成功: {file}")
        else:
            log.warning(f"目录不可删除: {file}")
    else:
        log.error(f"文件不存在: {file}")


def clean_up(path=Args.SAVE_PATH, max_files=96):
    '''
    清理目录中的文件，移除旧文件。

    :param path: 要清理的目录路径，默认为 args.savePath。
    :param max_files: 要保留的最大文件数量，默认为 96。
    '''
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


def wget(url: str, savePath: Optional[str]):
    '''
    使用 wget 下载指定的 URL 并将其保存到指定路径。

    :param url: 要下载的 URL。
    :param savePath: 保存下载文件的路径。可以为 None。

    :raises ValueError: 如果 URL 或 savePath 无效。
    :raises subprocess.CalledProcessError: 如果 wget 命令执行失败。
    '''
    if not url or not savePath:
        raise ValueError("URL 和 savePath 不能为空。")
    try:
        subprocess.run(["wget", "-O", savePath, url], check=True)
    except subprocess.CalledProcessError as e:
        print(f"下载失败: {e}")


def curl_get(url: str) -> bytes:
    '''
    使用 curl 对指定的 URL 执行 GET 请求。

    :param url: 要发送 GET 请求的 URL。
    :return: 响应体，类型为 bytes。
    '''
    command = ["curl", "-X", "GET", "-L", url,
               "--max-time", "60", "--retry", "3"]
    result = subprocess.run(command, stdout=subprocess.PIPE).stdout
    return result


def handle_server_response(response_bytes) -> dict | None:
    '''
    处理来自服务器的响应。
    :param response_bytes: 服务器返回的字节数据。
    :return: 如果解码和解析成功则返回解析后的 JSON 对象，否则返回 None。
    '''
    try:
        response_str = response_bytes.decode("utf-8")
        response_dict = json.loads(response_str)
        return response_dict
    except json.JSONDecodeError as e:
        log.critical(f"结果转化错误: {e}")
        return None


def download_one_pic(target_pic: dict):
    '''
    下载指定 URL 的单张图片到指定路径。

    :param target_pic: 包含图片 ID、分辨率、URL 和文件类型的字典。
    '''
    pic_id = target_pic['id']
    resolution = target_pic['resolution']
    url = target_pic['url']
    pic_type = target_pic['file_type']
    pic_path = f"{Args.SAVE_PATH}/{resolution}_{pic_id}.{pic_type_map[pic_type]}"
    log.info(f"正在下载图片 <ID:{pic_id}> <规格:{resolution}> {url} -> {pic_path}")
    if os.path.isfile(pic_path):
        file_info = os.stat(pic_path)
        log.warning(
            f"图片已存在 <文件大小: {file_size(file_info.st_size)}> <时间: {format_time(file_info.st_atime)}>")
        return
    wget(url, pic_path)
    log.info("图片下载成功")


def get_pending_pic_url(wallhaven_url: str) -> list:
    '''
    从 Wallhaven API 检索待处理的图片 URL 列表。

    :param wallhaven_url: 查询图片数据的 URL。
    :return: 包含图片元数据（ID、分辨率、URL 和文件类型）的字典列表。
    '''
    response_res = curl_get(wallhaven_url)
    response_res_dict = handle_server_response(response_res)
    pending_pic_url_list = []
    if not response_res_dict.get("data"):
        log.critical("获取图片列表失败")
        raise Exception("获取图片列表失败")  # 使用异常处理代替 exit(1)
    for pic_msg in response_res_dict["data"]:
        pic_msg_main = {
            'id': pic_msg['id'],
            'resolution': pic_msg['resolution'],
            'url': pic_msg['path'],
            'file_type': pic_msg['file_type'],    # image/png image/jpeg
        }
        pending_pic_url_list.append(pic_msg_main)
    return pending_pic_url_list


def download_all_pic_in_one_page(page_num):
    '''
    从 Wallhaven 下载单个页面上的所有图像。

    :param pageNum: 下载图像的页码。
    '''
    log.info(f"正在下载第{page_num}页图片")
    wallhaven_url = wallhaven_url_base + str(page_num)
    pending_pic_url_list = get_pending_pic_url(wallhaven_url)

    for target_pic in pending_pic_url_list:
        download_one_pic(target_pic)

    log.info(f"第{page_num}页图片下载完成")


def wallhaven_download():
    init()

    for pageNum in range(1, int(Args.MAX_PAGE)+1):
        download_all_pic_in_one_page(pageNum)


if __name__ == "__main__":
    _sep = "-" * 15
    log.info(_sep + "START" + _sep)
    wallhaven_download()
    clean_up()
    log.info(_sep + "END" + _sep + "\n")

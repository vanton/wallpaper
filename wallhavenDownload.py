'''
Filename: \wallhavenDownload.py
Project: wallpaper
Version: v0.8
File Created: Friday, 2021-11-05 23:10:20
Author: vanton
-----
Last Modified: Tuesday, 2024-11-05 00:31:09
Modified By: vanton
-----
Copyright (c) 2024
'''


import json
import logging
import os
import subprocess
import time
from logging.handlers import TimedRotatingFileHandler

from APIKey import APIKey

#!##############################################################################
# 常量配置
when = 'H'  # 按小时日志
backupCount = 5  # 保留日志文件数量
logPath = './log/wallhavenDownload.log'

wallHavenUrlBase = ""

picTypeMap = {
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


class args:
    ''' 需要时请修改此参数
    '''
    categories = '111'
    mode = 'hot'
    savePath = './Pic'
    maxPage = 2
    ratios = 'landscape'


#!##############################################################################


class MyFormatter(logging.Formatter):
    '''自定义日志格式
    '''

    def format(self, record: logging.LogRecord) -> str:
        '''Customize the log format

        :param record: The log record
        :return: The formatted string
        '''
        record.message = record.getMessage()
        log_level_colors = {
            logging.INFO: record.levelname,
            logging.WARNING: record.levelname,
            logging.ERROR: record.levelname,
            logging.CRITICAL: record.levelname,
            logging.DEBUG: record.levelname
        }
        record.levelname = log_level_colors.get(
            record.levelno, record.levelname)
        return super().format(record)


class Log:
    # when 轮换时间 S: 秒 M: 分 H: 小时 D: 天 W: 周

    def __init__(self, logPath=logPath, when=when, maxBytes=1024*1000, backupCount=backupCount):
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
        self._fmt = '%(asctime)s\t-\t[%(levelname)s]\t-\t%(message)s'

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
    global wallHavenUrlBase
    # https://wallhaven.cc/search?categories=110&purity=100&sorting=hot&order=desc
    # sorting=toplist toplist
    # sorting=hot 最热
    # sorting=latest 最新
    # atleast=1000x1000 最小尺寸 1000x1000
    # topRange=1w 一周

    wallHavenUrlBase = "https://wallhaven.cc/api/v1/search?apikey={}&categories={}&sorting={}&ratios={}&purity=100&atleast=1000x1000&topRange=1w&page=".format(
        APIKey, args.categories, args.mode, args.ratios)
    log.info(wallHavenUrlBase)
    # 创建文件保存目录
    os.makedirs(args.savePath, exist_ok=True)


def formatTime(atime=None) -> str:
    '''
    :param atime: The time in seconds since the epoch, or None to format the current time.
    :return: A string of the form "YYYY-MM-DD HH:MM:SS".
    '''
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(atime))


def fileSize(filesize: int) -> str:
    '''
    :param filesize: The size of the file in bytes.
    :return: A string of the form "X.XX MB" representing the size of the file in megabytes.
    '''
    filesize = filesize/float(1024*1024)
    return str(round(filesize, 2)) + ' MB'


def dirSize(path: str) -> str:
    '''
    :param path: The path to the directory to calculate the size of.
    :return: A string of the form "X.XX MB" representing the size of the directory in megabytes.
    '''
    size = 0
    if os.path.exists(path):
        output = subprocess.Popen(['du', '-s', path], stdout=subprocess.PIPE)
        output = output.communicate()[0]
        if output:
            size = output.split()[0]
        size = fileSize(int(size) * 1024)
    return size


def dirInfo(path: str):
    '''
    Log information about a directory.

    :param path: The path to the directory to log information about.
    '''
    if os.path.exists(path):
        if os.path.isdir(path):
            log.info("<图片目录:{}> <大小:{}>".format(
                path, dirSize(path)))
        else:
            log.error("目标不是目录:{}".format(path))
    else:
        log.error("图片目录不存在:{}".format(path))


def fileRemove(file: str):
    '''
    Remove a file.

    :param file: The path to the file to remove.
    '''
    if os.path.exists(file):
        if os.path.isfile(file):
            os.remove(file)
            log.info("文件删除成功:{}".format(file))
        else:
            log.warning("目录不可删除:{}".format(file))
    else:
        log.error("文件不存在:{}".format(file))


def cleanUp(path=args.savePath, max=96):
    '''
    Clean up files in a directory by removing older files.

    :param path: The path to the directory to clean up. Defaults to args.savePath.
    :param max: The maximum number of files to retain in the directory. Defaults to 96.
    '''
    log.info("清理文件")
    if os.path.exists(path):
        dirInfo(path)
        files = os.listdir(path)
        log.info("清理前文件数量:{}".format(len(files)))
        oldPwd = os.getcwd()
        os.chdir(path)
        files.sort(key=os.path.getctime)
        del files[-max:]
        for file in files:
            fileRemove(file)
        os.chdir(oldPwd)
        dirInfo(path)
    else:
        log.error("文件不存在:{}".format(path))


def wget(url, savePath: str):
    '''
    Use wget to download a URL and save it to the specified path.

    :param url: The URL to download.
    :param savePath: The path to save the downloaded file to.
    '''
    subprocess.run(["wget", "-O", savePath, url])


def curlGet(url) -> bytes:
    '''
    Perform a GET request to the specified URL using curl.

    :param url: The URL to send the GET request to.
    :return: The response body as bytes.
    '''
    command = ["curl", "-XGET", "-L", url, "--max-time", "60", "--retry", "3"]
    result = subprocess.run(command, stdout=subprocess.PIPE).stdout
    return result


def handleResponseRes(responseResBytes) -> dict:
    '''
    Handle the response from the server.

    :param responseResBytes: The response from the server as bytes.
    :return: The parsed JSON object if the decoding and parsing succeed, otherwise None.
    '''
    try:
        responseResStr = str(responseResBytes, encoding="utf-8")
        responseResDict = json.loads(responseResStr)
        return responseResDict
    except Exception as e:
        log.critical("结果转化错误: {}".format(e))
        return


def downloadOnePic(targetPic: map):
    '''
    Download a single image from the specified URL to the specified path.

    :param targetPic: A map with the image's ID, resolution, URL, and file type.
    '''
    id = targetPic['id']
    resolution = targetPic['resolution']
    url = targetPic['url']
    picType = targetPic['fileType']
    picPath = "{}/{}_{}.{}".format(args.savePath,
                                   resolution, id, picTypeMap[picType])

    log.info("正在下载图片 <ID:{}> <规格:{}> {} -> {}".format(id, resolution, url, picPath))
    if os.path.isfile(picPath):
        fileInfo = os.stat(picPath)
        log.warning("图片已存在 <文件大小: {}> <时间: {}>".format(
            fileSize(fileInfo.st_size), formatTime(fileInfo.st_atime)))
        return

    wget(url, picPath)
    log.info("图片下载成功")


def getPendingPicUrl(wallHavenUrl: str) -> list:
    '''
    Retrieve a list of pending picture URLs from the Wallhaven API.

    :param wallHavenUrl: The URL to query for image data.
    :return: A list of dictionaries containing image metadata (ID, resolution, URL, and file type).
    '''
    responseRes = curlGet(wallHavenUrl)
    responseResDict = handleResponseRes(responseRes)

    pendingPicUrlList = []
    if not responseResDict.get("data"):
        log.critical("获取图片列表失败")
        exit(1)

    for PicMsg in responseResDict["data"]:
        PicMsgMain = {
            'id': PicMsg['id'],
            'resolution': PicMsg['resolution'],
            'url': PicMsg['path'],
            'fileType': PicMsg['file_type'],    # image/png image/jpeg
        }
        pendingPicUrlList.append(PicMsgMain)

    return pendingPicUrlList


def downloadAllPicInOnePage(pageNum):
    '''
    Download all images on a single page from Wallhaven.

    :param pageNum: The page number to download images from.
    '''
    log.info("正在下载第{}页图片".format(str(pageNum)))
    wallHavenUrl = wallHavenUrlBase + str(pageNum)
    pendingPicUrlList = getPendingPicUrl(wallHavenUrl)

    for targetPic in pendingPicUrlList:
        downloadOnePic(targetPic)

    log.info("第{}页图片下载完成".format(str(pageNum)))


def WallhavenDownload():
    init()

    for pageNum in range(1, int(args.maxPage)+1):
        downloadAllPicInOnePage(pageNum)


if __name__ == "__main__":
    _sep = "-" * 15
    log.info(_sep + "START" + _sep)
    WallhavenDownload()
    cleanUp()
    log.info(_sep + "END" + _sep + "\n")

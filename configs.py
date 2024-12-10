from dataclasses import dataclass

# 填写自己的 APIKey
# Fill in your APIKey
APIKey = ""

"""
打开以下页面获取APIKey。必须先登录。
APIKey 可以为空, 为空时 NSFW 内容无法下载。
Open the following page to obtain the APIKey. Must log in first.
APIKey can be empty, and NSFW content cannot be downloaded when it is empty.
https://wallhaven.cc/settings/account

API Key
Your API key can be used to grant other apps access to some of your account settings.
See our API documentation for more.
"""


@dataclass
class Args:
    """Please modify this parameter if necessary

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
: command: python wallhavenDownload.py --categories 100 --sorting hot --maxPage 4
: command: python wallhavenDownload.py --categories 110 --purity 100
: command: python wallhavenDownload.py --sorting toplist --maxPage 2

Parameter description:
--categories 110
-c 110
Crawl image classification General, Anime, People:
    110 -> General+Anime,
    111 -> General+Anime+People, (默认)
    100 -> General
--sorting {toplist, latest, hot}
-s hot
Crawling image mode, {toplist, latest, hot} 3 modes, default is hot
--maxPage maxPage
-m 4
Maximum number of pages, default 4
"""

#!##############################################################################
# 其他配置，非必要不要修改
# Other configurations should not be modified unless necessary.

max_files: int = 24 * Args.MAX_PAGE + 10
"""max_files (int):
Maximum number of files to retain, defaults to 24 *Args.MAX_PAGE + 4.
-Theoretically, it is the number of max_files; if too many pictures are downloaded at one time, the pictures will be downloaded and then deleted repeatedly.
-It is recommended that the number of saved pictures should be greater than the number of single pages *the number of downloaded pages.
"""
DEBUG: bool = True

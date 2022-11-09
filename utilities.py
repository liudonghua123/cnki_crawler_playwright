
# some help functions
from dataclasses import dataclass
import sys
from os.path import dirname, join, realpath
from playwright.sync_api._generated import Page

#%%
# In order to run this script directly, you need to add the parent directory to the sys.path
# Or you need to run this script in the parent directory using the command: python -m client.algorithm
sys.path.append(dirname(realpath(".")))
from common.config_logging import init_logging

logger = init_logging(join(dirname(realpath(__file__)), "main.log"))

def selector_exists(element, selector):
    exists = False
    locator = None
    try:
        locator = element.locator(selector)
        exists = True
    except:
        exists = False
    return exists, locator

def focus_and_click(page: Page, selector: str):
    result = True
    try:
        page.focus(selector)
        page.click(selector)
    except:
        logger.error(f"failed to focus_and_click {selector}")
        result = False
    return result

@dataclass
class Link:
    title: str
    url: str

    def __str__(self):
        return "{}-{}".format(self.title, self.url)

def format_link(value: Link) -> str:
    return f"{value.title},{value.url}"   

def format_links(values: list[Link]) -> str:
    return "|".join([f"{link.title}->{link.url}" for link in values])     
    
@dataclass
class  SearchResult:
    # 篇名					
    paper_name: Link
    # 作者
    authors: list[Link]
    # 刊名
    publication: Link
    # 发表时间
    publish_datetime: str
    # 被引
    back_reference: Link
    # 被引详情
    back_reference_details: list[Link]
    # 下载
    download_count: Link
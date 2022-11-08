#%%
import sys
from os.path import dirname, join, realpath
from time import sleep

import yaml
import asyncio
from dataclasses import dataclass
from dataclass_csv import DataclassWriter
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import Page

#%%
# In order to run this script directly, you need to add the parent directory to the sys.path
# Or you need to run this script in the parent directory using the command: python -m client.algorithm
sys.path.append(dirname(realpath(".")))
from common.config_logging import init_logging

logger = init_logging(join(dirname(realpath(__file__)), "main.log"))

#%%
# some configurations or constants
a_bit_waiting_time = 1
result_file = "search_results.csv"

#%%
# read config.yml file using yaml
with open(
    join(dirname(realpath(__file__)), "config.yml"),
    mode="r",
    encoding="utf-8",
) as file:
    config = yaml.safe_load(file)

logger.info(f"load config: {config}")
search_author: str = config['search_settings']['search_author']
same_name_selection: list[int] = config['search_settings']['same_name_selection']

#%%
# some help functions
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
    # 下载
    download_count: Link
    

#%%
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://cnki.net/")
        # Get page after a specific action (e.g. clicking a link)
        with context.expect_page() as new_page_info:
            # 点击 高级检索
            # page.click("#highSearch")
            focus_and_click(page, "#highSearch")
        page.close()
        page = new_page_info.value
        
        # 点击 学术期刊
        logger.info(f'click 学术期刊')
        sleep(a_bit_waiting_time) # TODO: wait for the page to load completely? otherwise the click will fail
        focus_and_click(page, "ul.doctype-menus.keji > li[data-id=xsqk] a")
        # 等待点击后的页面加载完成
        logger.info(f'wait_for_selector 学术期刊')
        page.wait_for_selector("ul.doctype-menus.keji > li.cur[data-id=xsqk]")
        
        # 输入作者
        logger.info(f'input 输入作者 {search_author}')
        page.focus("#gradetxt > dd:nth-child(3) > div.input-box > input[type=text]")
        page.locator("#gradetxt > dd:nth-child(3) > div.input-box > input[type=text]").fill(search_author)
        # 选择右边弹窗里面的前两项
        logger.info(f'wait_for_selector {search_author} 同名作者列表')
        page.wait_for_selector("#gradetxt-2 > ul > li")
        # document.querySelector("#gradetxt-2 > ul > li:nth-child(2) label").click()
        logger.info(f'check {search_author} 同名作者')
        for i in same_name_selection:
            page.click(f"#gradetxt-2 > ul > li:nth-child({i}) label")
        
        # 勾选上 CSSCI
        # document.querySelector("#JournalSourceType input[type=checkbox][key=CSI]").click()
        logger.info(f'check CSSCI')
        page.click("#JournalSourceType input[type=checkbox][key=CSI]")
        # 输入主题
        # page.locator("#gradetxt > dd:nth-child(2) > div.input-box > input[type=text]").fill('?')
        
        # 点击 检索
        # document.querySelector("div.search-buttons > input[type=button][value=检索]").click()
        page.click("div.search-buttons > input[type=button][value=检索]")
        
        # 处理搜索结果
        assert selector_exists(page, "#countPageDiv > span.pagerTitleCell > em")[0]
        # 获取搜索结果数量
        # document.querySelector("#countPageDiv > span.pagerTitleCell > em").textContent
        search_results_count = page.locator("#countPageDiv > span.pagerTitleCell > em").inner_text()
        # 获取当前页/总页数
        # document.querySelector("#countPageDiv > span.countPageMark").textContent
        current_page, total_page = map(int, page.locator("#countPageDiv > span.countPageMark").inner_text().split('/'))
        logger.info(f"search_results_count: {search_results_count}, current_page: {current_page}, total_page: {total_page}")
        
        # 获取搜索结果
        search_results = []
        for page_num in range(1, total_page+1):
            # document.querySelectorAll('#gridTable > table > tbody > tr')
            rows = page.locator('#gridTable > table > tbody > tr')
            rows_count = rows.count()
            logger.info(f"process page: {page_num}, current rows count: {rows_count}")
            for i in range(rows_count):
                row = rows.nth(i)
                # 篇名
                paper_name = Link(row.locator('td.name > a').inner_text(), row.locator('td.name > a').evaluate('a => a.href'))
                # 作者
                authors_links = row.locator('td.author > a')
                authors_links_count = authors_links.count()
                authors = [Link(authors_links.nth(author_index).inner_text(), authors_links.nth(author_index).evaluate('a => a.href')) for author_index in range(authors_links_count)]
                # 刊名
                publication = Link(row.locator('td.source > a').inner_text(), row.locator('td.source > a').evaluate('a => a.href'))
                # 发表时间
                publish_datetime = row.locator('td.date').inner_text()
                # 被引，可能为空
                back_reference = None
                if len(row.locator('td.quote').inner_text()) > 0:
                    back_reference_locator = row.locator('td.quote > a')
                    back_reference = Link(back_reference_locator.inner_text(), back_reference_locator.evaluate('a => a.href'))
                # 下载
                download_count = Link(row.locator('td.download > a').inner_text(), row.locator('td.download > a').evaluate('a => a.href'))
                
                # 保存搜索结果
                search_result = SearchResult(
                    paper_name,
                    authors,
                    publication,
                    publish_datetime,
                    back_reference,
                    download_count,
                )
                logger.info(f'page {page_num}, {i:>02}/{rows_count}, search_result: {search_result}')
                search_results.append(search_result)
            # 点击下一页
            focus_and_click(page, "#Page_next_top")
            # 增量保存每页结果
            with open(result_file, "w", encoding='utf-8') as f:
                w = DataclassWriter(f, search_results, SearchResult)
                # https://github.com/dfurtado/dataclass-csv/issues/33#issuecomment-1307545091
                # w.map("paper_name").using(format_link)
                # w.map("authors").using(format_links)
                # w.map("publication").using(format_link)
                # w.map("back_reference").using(format_link)
                # w.map("download_count").using(format_link)
                w.write()
        logger.info(f"saved {len(search_results)} search_results to {result_file}")
        # # 保存所有的结果
        # with open(result_file, "w", encoding='utf-8') as f:
        #     w = DataclassWriter(f, search_results, SearchResult)
        #     w.write()
        
        browser.close()

main()

# %%

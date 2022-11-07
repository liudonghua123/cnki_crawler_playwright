#%%
import sys
from os.path import dirname, join, realpath
from time import sleep

import yaml
import asyncio
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

#%%
# read config.yml file using yaml
with open(
    join(dirname(realpath(__file__)), "config.yml"),
    mode="r",
    encoding="utf-8",
) as file:
    config = yaml.safe_load(file)

logger.info(f"load config: {config}")

#%%
# some help functions
def selector_exists(page, selector):
    exists = False
    locator = None
    try:
        locator = page.locator(selector)
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
        
        # 输入作者 胡鞍钢
        logger.info(f'input 输入作者 胡鞍钢')
        page.focus("#gradetxt > dd:nth-child(3) > div.input-box > input[type=text]")
        page.locator("#gradetxt > dd:nth-child(3) > div.input-box > input[type=text]").fill('胡鞍钢')
        # 选择右边弹窗里面的前两项
        logger.info(f'wait_for_selector 作者列表')
        page.wait_for_selector("#gradetxt-2 > ul > li")
        # document.querySelector("#gradetxt-2 > ul > li:nth-child(2) label").click()
        logger.info(f'check 作者 胡鞍钢')
        page.click("#gradetxt-2 > ul > li:nth-child(1) label")
        page.click("#gradetxt-2 > ul > li:nth-child(2) label")
        
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
        browser.close()

main()

# %%

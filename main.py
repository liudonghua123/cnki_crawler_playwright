#%%
from os.path import dirname, join, realpath
from time import sleep
import re
import yaml
import asyncio
from dataclass_csv import DataclassWriter
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import Page
from utilities import logger, selector_exists, focus_and_click, Link, SearchResult, format_link, format_links



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
headless: bool = config['playwright']['headless']
slow_mo: int = config['playwright']['slow_mo']
  

def get_back_reference_details(context, link_url: str) -> list[Link]:
    # 获取被引详情信息，获取文章名称、链接
    # https://kns.cnki.net/kcms/detail/search.aspx?sfield=cite&code=BGYS202103001&dbcode=CJFD&sKey=%e4%b8%ad%e5%9b%bd%e5%ae%9e%e7%8e%b02030%e5%b9%b4%e5%89%8d%e7%a2%b3%e8%be%be%e5%b3%b0%e7%9b%ae%e6%a0%87%e5%8f%8a%e4%b8%bb%e8%a6%81%e9%80%94%e5%be%84
    back_references_details = []
    page: Page = context.new_page()
    page.goto(link_url)
    # 获取总的分类数
    section_count = page.locator('div#divResult > div.essayBox').count()
    logger.info(f"url {link_url}, section_count: {section_count}")
    for i in range(1, section_count + 1):
        section = page.locator(f'div#divResult > div.essayBox:nth-child({i})')
        section_name = section.locator('div.dbTitle').inner_text().split(' ')[0]
        section_total_count = section.locator('span[name=pcount]').inner_text()
        logger.info(f"section_name: {section_name}, section_total_count: {section_total_count}")
        # 初始化该分类页数为1页，如果有多页，会有pageBar
        section_page_count = 1
        page_bar_exits, _ = selector_exists(section, 'div.pageBar')
        if page_bar_exits:
          # 获取该分类下的总页数，结果类似于 '共2页      1 2 下一页 末页 '
          page_bar_text = section.locator('div.pageBar > span').inner_text()
          # section_page_count = int(page_bar_text.split('共')[1].split('页')[0])
          section_page_count = int(re.search('共(?P<count>\d+)页', page_bar_text).group('count'))
        # 获取每个分类下的文章数
        for j in range(1, section_page_count + 1):
          # article_count 有时候可能还没有更新，导致获取的数据还是上一次的，所以这里等待一下
          sleep(a_bit_waiting_time)
          article_count = section.locator('ul > li').count()
          for k in range(1, article_count + 1):
              # 一些文章没有链接，只有标题，例如 图书 分类下的文章
              # 这里限定a:nth-child(2)，否则会有多个结果，例如 https://kns.cnki.net/kcms/detail/search.aspx?sfield=cite&code=BGYS202103001&dbcode=CJFD&sKey=%e4%b8%ad%e5%9b%bd%e5%ae%9e%e7%8e%b02030%e5%b9%b4%e5%89%8d%e7%a2%b3%e8%be%be%e5%b3%b0%e7%9b%ae%e6%a0%87%e5%8f%8a%e4%b8%bb%e8%a6%81%e9%80%94%e5%be%84
              # 中硕士第1页的第5篇文章
              article_exists, article = selector_exists(section, f'ul > li:nth-child({k}) a:nth-child(2)')
              if article_exists:
                article_link = Link(article.inner_text(), article.evaluate('a => a.href'))
                back_references_details.append(article_link)
                logger.info(f"section_name: {section_name}, page {j:>02}, {k:>02}/{article_count} article_link: {article_link}")
              else:
                logger.warn(f"section_name: {section_name}, page {j:>02}, {k:>02}/{article_count} does not have link")
          # 点击下一页，下一页按钮比较难定位，从pagebar中的倒数第二个链接中获取
          section.locator('div.pageBar > span > a:nth-last-child(2)').click()
    # 关闭页面
    page.close()
    return back_references_details

#%%
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=headless, slow_mo=slow_mo)
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
        page.wait_for_selector("ul.doctype-menus.keji > li[data-id=xsqk] a")
        focus_and_click(page, "ul.doctype-menus.keji > li[data-id=xsqk] a")
        # 等待点击后的页面加载完成
        logger.info(f'wait_for_selector 学术期刊')
        page.wait_for_selector("ul.doctype-menus.keji > li.cur[data-id=xsqk]")
        
        # 输入作者
        logger.info(f'input 输入作者 {search_author}')
        # 有时候会出现输入框没有获取到焦点的情况，所以这里先点击一下
        page.locator("#gradetxt > dd:nth-child(3) > div.input-box > input[type=text]").fill(search_author)
        sleep(a_bit_waiting_time)
        page.click("#gradetxt > dd:nth-child(3) > div.input-box > input[type=text]")
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
                back_references_details = None
                if len(row.locator('td.quote').inner_text()) > 0:
                    back_reference_locator = row.locator('td.quote > a')
                    back_reference = Link(back_reference_locator.inner_text(), back_reference_locator.evaluate('a => a.href'))
                    # TODO: 获取被引详情
                    back_references_details = get_back_reference_details(context, back_reference.url)
                
                # 下载
                download_count = Link(row.locator('td.download > a').inner_text(), row.locator('td.download > a').evaluate('a => a.href'))
                
                # 保存搜索结果
                search_result = SearchResult(
                    paper_name,
                    authors,
                    publication,
                    publish_datetime,
                    back_reference,
                    back_references_details,
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

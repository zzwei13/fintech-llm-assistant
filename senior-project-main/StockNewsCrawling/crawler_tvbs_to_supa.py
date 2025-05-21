import time
import os
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 定义要爬取的股票ID和关键词
stocks = [
    # {"stock_id": "2330", "keyword": "台積電"},v
    # {"stock_id": "3443", "keyword": "創意"},v
    # {"stock_id": "2002", "keyword": "中鋼"},v
    # {"stock_id": "2317", "keyword": "鴻海"},v
    # {"stock_id": "2731", "keyword": "雄獅"}v
]
add_page = 2
# 指定要爬取的日期范围
start_date = datetime.strptime("20220101", "%Y%m%d")
end_date = datetime.strptime("20240801", "%Y%m%d")

# 遍历每个股票
for stock in stocks:
    stock_id = stock["stock_id"]
    keyword = stock["keyword"]
    glob_url = f"https://news.tvbs.com.tw/news/searchresult/{keyword}/news/"

    page = 1
    if(stock_id == '2330'):
        add_page = 8
    elif stock_id == '2002':
        add_page = 3
    elif stock_id == '2317':
        add_page = 5
    else:
        add_page = 2

    while True:
        # 请求网页内容
        url = glob_url + str(page)
        response = requests.get(url)

        # 解析网页内容
        soup = BeautifulSoup(response.content, "html.parser")

        # 找到所有的 <li> 元素
        elements = soup.find_all("li")

        # 提取每个元素的文字内容
        news_found = False  # 标记是否找到了符合条件的新闻

        for e in elements:
            try:
                # 找到时间元素
                time_element = e.find("div", class_="time")
                if time_element is None:
                    continue

                time_text = time_element.text.strip()
                time_datetime = datetime.strptime(time_text, "%Y/%m/%d %H:%M")
                formatted_date = time_datetime.strftime("%Y-%m-%d")

                # 判断新闻日期是否在指定范围内
                if time_datetime < start_date:
                    # 如果新闻日期早于开始日期，停止爬虫
                    print(
                        f"{keyword} - 发现日期早于{start_date.strftime('%Y-%m-%d')}的新闻，停止爬虫..."
                    )
                    news_found = False
                    break
                elif time_datetime > end_date:
                    # 如果新闻日期晚于结束日期，跳过这条新闻
                    continue

                news_found = True

                # 找到摘要元素
                summary_element = e.find("div", class_="summary")
                if summary_element is None:
                    continue

                # 拼接新闻内容
                content = summary_element.text.strip()

                # 打印爬取进度
                print(f"{keyword} - Date:{formatted_date}, link:{url}")

                # 将数据插入 Supabase
                record = {
                    "stockID": int(stock_id),
                    "date": formatted_date,
                    "content": content,
                }
                supabase.table("news_content").insert(record).execute()

            except Exception as ex:
                print(f"{keyword} - 爬取失败", ex)
                print(f"link:{url}")
                pass

        if not news_found:
            # 如果在这个页面没有找到符合条件的新闻，停止爬虫
            break

        page += add_page
        time.sleep(2)

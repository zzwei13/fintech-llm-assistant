# tvbs_scraper.py
import time
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def scrape_tvbs(stocks, start_date, end_date):
    for stock in stocks:
        stock_id = stock["stockID"]
        keyword = stock["stock_name"]
        glob_url = f"https://news.tvbs.com.tw/news/searchresult/{keyword}/news/"

        page = 1
        add_page = 3 if stock_id in ['2330', '2002', '2317'] else 1

        while True:
            url = glob_url + str(page)
            response = requests.get(url)
            soup = BeautifulSoup(response.content, "html.parser")
            elements = soup.find_all("li")
            news_found = False

            for e in elements:
                try:
                    time_element = e.find("div", class_="time")
                    if time_element is None:
                        continue
                    time_text = time_element.text.strip()
                    time_datetime = datetime.strptime(time_text, "%Y/%m/%d %H:%M")
                    formatted_date = time_datetime.strftime("%Y-%m-%d")

                    if time_datetime < start_date:
                        print(f"{keyword} - 发现日期早于{start_date.strftime('%Y-%m-%d')}的新闻，停止爬虫...")
                        news_found = False
                        break
                    elif time_datetime > end_date:
                        continue

                    news_found = True
                    summary_element = e.find("div", class_="summary")
                    if summary_element is None:
                        continue

                    content = summary_element.text.strip()
                    print(f"{keyword} - Date:{formatted_date}, link:{url}")

                    record = {
                        "stockID": int(stock_id),
                        "date": formatted_date,
                        "content": content,
                    }
                    supabase.table("news_test").insert(record).execute()

                except Exception as ex:
                    print(f"{keyword} - 爬取失败", ex)
                    print(f"link:{url}")
                    pass

            if not news_found:
                break

            page += add_page
            time.sleep(2)

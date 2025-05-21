import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import re
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
    # {"stock_id": "2330", "keyword": "台積電"},
    {"stock_id": "3443", "keyword": "創意"},
    # {"stock_id": "2002", "keyword": "中鋼"},
    # {"stock_id": "2317", "keyword": "鴻海"},
    # {"stock_id": "2731", "keyword": "雄獅"}
]

# 指定要爬取的日期范围
start_date = datetime.strptime("20220101", "%Y%m%d")
end_date = datetime.strptime("20240801", "%Y%m%d")

# 遍历每个股票
for stock in stocks:
    stock_id = stock["stock_id"]
    keyword = stock["keyword"]
    url = f"https://www.cnyes.com/search/news?keyword={keyword}"
    driver = webdriver.Chrome()
    driver.get(url)
    news_url_l = []

    for i in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        elements = driver.find_elements(
            By.XPATH,
            '//a[contains(@class, "jsx-1986041679") and contains(@class, "news")]',
        )
        for e in elements:
            href = e.get_attribute("href")
            if href not in news_url_l:  # 避免重复添加
                news_url_l.append(href)
                print(f"目標元素的網址: {href}")

    driver.quit()

    # Requests 和 BeautifulSoup 進行網頁解析
    content = ""
    date_last = ""
    article = ""

    for index, link in enumerate(news_url_l):
        try:
            response = requests.get(link)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # 找到時間元素 #2024-07-26 09:04
            time_text = soup.find("p", class_="alr4vq1").text.strip()
            match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", time_text)

            if match:
                time_string = match.group()
                time_datetime = datetime.strptime(time_string, "%Y-%m-%d %H:%M")
                formatted_date = time_datetime.strftime("%Y%m%d")
                supabase_date_format = time_datetime.strftime("%Y-%m-%d")

            print("supabase_date_format:", supabase_date_format)

            if date_last != formatted_date:
                article = ""
            date_last = formatted_date

            p = soup.find("main", class_="c1tt5pk2")
            contents = p.find_all("p")

            for content in contents:
                article += content.text.strip()

            # Write data to Supabase
            data = {
                "stockID": int(stock_id),
                "date": supabase_date_format,
                "content": article,
                "gemini_signal": None,  # Assuming this is to be filled later
                "emotion": None,  # Assuming this is to be filled later
                "arousal": None,
            }
            response = supabase.table("news_content").insert(data).execute()
            if response.data:
                print(
                    f"[{index+1}/{len(news_url_l)}], Date:{formatted_date}, link:{link} - Inserted into Supabase"
                )
            else:
                print(f"Failed to insert into Supabase: {response.error}")

        except requests.exceptions.Timeout:
            print(f"Request timed out for link: {link}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed for link: {link}, Error: {e}")
        except Exception as e:
            print(f"爬取失敗 {e}")
            print("link", link)
        time.sleep(1)
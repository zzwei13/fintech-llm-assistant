import time
import os
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import re
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 設定股票要抓的區間
stocks = (
    supabase
    .table("stock")
    .select("stockID, stock_name")
    .gte("stockID", 2486)
    .lte("stockID", 9999)
    .execute()
    .data
)

# Specify the date range
start_date = datetime.strptime("20241018", "%Y%m%d")
end_date = datetime.strptime("20241118", "%Y%m%d")

# CSV file setup for appending data
csv_file = "cnye_news.csv"
file_exists = os.path.isfile(csv_file)

with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(["StockID", "Date", "Content", "Link"])

# Iterate over each stock from Supabase
for stock in stocks:
    stock_id = stock["stockID"]
    keyword = stock["stock_name"]
    url = f"https://www.cnyes.com/search/news?keyword={keyword}"
    driver = webdriver.Chrome()
    driver.get(url)
    news_url_l = []

    # Scroll and gather news links
    for i in range(2):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        #time.sleep(1)
        
        # Retry fetching elements to avoid StaleElementReferenceException
        try:
            elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@class, "jsx-1986041679") and contains(@class, "news")]'))
            )
            for e in elements:
                try:
                    href = e.get_attribute("href")
                    if href not in news_url_l:
                        news_url_l.append(href)
                        print(f"News URL: {href}")
                except StaleElementReferenceException:
                    print("Stale element, skipping this href.")
        except TimeoutException:
            print("Timeout while waiting for elements.")
            
    driver.quit()

    # Parse news articles with BeautifulSoup
    date_last = ""
    for index, link in enumerate(news_url_l):
        try:
            response = requests.get(link)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Find and format the article date
            time_text = soup.find("p", class_="alr4vq1").text.strip()
            match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", time_text)
            if match:
                time_string = match.group()
                time_datetime = datetime.strptime(time_string, "%Y-%m-%d %H:%M")
                formatted_date = time_datetime.strftime("%Y%m%d")
                supabase_date_format = time_datetime.strftime("%Y-%m-%d")

            # Skip articles outside date range
            if not (start_date <= time_datetime <= end_date):
                continue

            print("Article Date:", supabase_date_format)

            # Clear article content for a new date
            if date_last != formatted_date:
                article = ""
            date_last = formatted_date

            # Extract article text
            p = soup.find("main", class_="c1tt5pk2")
            contents = p.find_all("p")
            for content in contents:
                article += content.text.strip()

            # Write data to Supabase
            data = {
                "stockID": stock_id,
                "date": supabase_date_format,
                "content": article,
                "gemini_signal": None,
                "emotion": None,
                "arousal": None,
            }
            response = supabase.table("news_content").insert(data).execute()
            if response.data:
                print(f"[{index + 1}/{len(news_url_l)}] Date:{formatted_date}, link:{link} - Inserted into Supabase")
            else:
                print(f"Failed to insert into Supabase: {response.error}")

            # Append data to CSV
            with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([stock_id, supabase_date_format, article, link])

        except requests.exceptions.Timeout:
            print(f"Request timed out for link: {link}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed for link: {link}, Error: {e}")
        except Exception as e:
            print(f"Scraping failed: {e}")
            print("link", link)
        #time.sleep(1)

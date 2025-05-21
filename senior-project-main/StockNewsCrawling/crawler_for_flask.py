import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote
import random
from selenium.webdriver.chrome.options import Options

# 設置 Chrome driver 的選項
options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--headless")

# 加载环境变量
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_news_batch_to_supabase(news_data):
    """Batch insert the news headlines into Supabase"""
    try:
        # 插入資料到 Supabase 的 news_test 表格
        response = supabase.table('news_test').insert(news_data).execute()
        
        # 檢查是否有錯誤
        if response.error:
            print(f"Failed to insert news batch: {response.error}")
        else:
            print(f"Successfully inserted {len(news_data)} news items.")
    
    except Exception as e:
        print(f"Error inserting news into Supabase: {e}")

def get_stock_name(stock_id):
    """Fetch stock name from Supabase using stock ID"""
    try:
        response = supabase.table('stock').select('stock_name').eq('stockID', stock_id).execute()
        stock_name = response.data[0]['stock_name'] if response.data else None
        return stock_name
    except Exception as e:
        print(f"Error fetching stock name for {stock_id}: {e}")
        return None

def fetch_news_ltn(stock_id, stock_name):
    """Fetch news from Liberty Times Net for the given stock name"""
    today = datetime.today().strftime('%Y%m%d')
    news_list = []

    url = f'https://search.ltn.com.tw/list?keyword={stock_name}&sort=date&start_time={today}&end_time={today}&type=business'

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        news_items = soup.find_all('div', class_='cont')

        if news_items:
            for item in news_items[:3]:  # 只返回前三條新聞
                headline = item.find('a').text.strip()
                link = item.find('a')['href']
                news_list.append({
                    'stockID': stock_id,
                    'date': datetime.today().strftime('%Y-%m-%d'),
                    'content': headline,
                    'gemini_signal': None,
                    'emotion': None,
                    'arousal': None
                })

    except Exception as e:
        print(f"Error fetching news from LTN for {stock_name}: {e}")

    return news_list

def fetch_news_tvbs(stock_id, stock_name):
    """Fetch news from TVBS for the given stock ID and name"""
    today = datetime.today().strftime('%Y/%m/%d')
    news_list = []
    keyword = f'{stock_id}{stock_name}'
    encoded_keyword = quote(keyword)
    base_url = f"https://news.tvbs.com.tw/news/searchresult/{encoded_keyword}/news/"
    
    url = base_url + "1"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching page 1 for {stock_id} {stock_name}: {response.status_code}")
            return news_list

        soup = BeautifulSoup(response.content, 'html.parser')
        elements = soup.find_all('li')

        for e in elements:
            link_element = e.find('a')
            if not link_element:
                continue
            link = link_element['href']
            
            title_element = e.find('h2', class_='txt')
            headline = title_element.text.strip() if title_element else "No title"
            
            if headline == "No title":
                continue
            
            news_list.append({
                'stockID': stock_id,
                'date': datetime.today().strftime('%Y-%m-%d'),
                'content': headline,
                'gemini_signal': None,
                'emotion': None,
                'arousal': None
            })

            if len(news_list) >= 3:
                break

    except Exception as e:
        print(f"Error fetching news from TVBS for {stock_id} {stock_name}: {e}")

    return news_list

def fetch_news_cnye(stock_id, stock_name):
    """Fetch news from CNYE for the given stock name"""
    url = f"https://www.cnyes.com/search/news?keyword={stock_name}"
    
    driver = webdriver.Chrome()
    driver.get(url)

    news_list = []
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[contains(@class, "jsx-1986041679") and contains(@class, "news")]'))
        )

        elements = driver.find_elements(By.XPATH, '//a[contains(@class, "jsx-1986041679") and contains(@class, "news")]')

        for e in elements[:3]:
            href = e.get_attribute("href")
            headline = e.text.strip()
            news_list.append({
                'stockID': stock_id,
                'date': datetime.today().strftime('%Y-%m-%d'),
                'content': headline,
                'gemini_signal': None,
                'emotion': None,
                'arousal': None
            })

    except Exception as e:
        print(f"Error fetching news from CNYE: {e}")
    
    finally:
        driver.quit()

    return news_list

def fetch_news_chinatime(stock_id, stock_name):
    """Fetch news from Chinatime for the given stock name"""
    keyword = f'{stock_id}{stock_name}'
    encoded_keyword = quote(keyword)
    base_url = f"https://www.chinatimes.com/search/{encoded_keyword}?page="

    news_list = []

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=options)

    try:
        for i in range(1, 4):
            url = base_url + str(i) + "&chdtv"
            driver.get(url)
            time.sleep(random.uniform(3, 6))

            try:
                article_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "article-list"))
                )
            except:
                print(f"Error: Article list not found on page {i}.")
                continue

            articles = article_list.find_elements(By.TAG_NAME, "li")

            for article in articles:
                try:
                    title_elements = article.find_elements(By.TAG_NAME, "h3")
                    if title_elements:
                        title_text = title_elements[0].text
                    else:
                        continue

                    link_element = article.find_element(By.TAG_NAME, "a")
                    link_url = link_element.get_attribute("href")

                    news_list.append({
                        'stockID': stock_id,
                        'date': datetime.today().strftime('%Y-%m-%d'),
                        'content': title_text,
                        'gemini_signal': None,
                        'emotion': None,
                        'arousal': None
                    })
                    
                    if len(news_list) >= 3:
                        driver.quit()
                        return news_list

                except Exception as e:
                    print(f"Error extracting article on page {i}: {e}")
    except Exception as e:
        print(f"Error accessing Chinatime: {e}")
    finally:
        driver.quit()

    return news_list

def print_news(news_list, source):
    """以統一格式輸出新聞標題和連結"""
    if news_list:
        print(f"\nNews from {source}:")
        for news in news_list:
            print(f"title: {news['content']}\n")
    else:
        print(f"No news available from {source}.")

def main():
    stock_id = input("Enter the stock ID: ")
    stock_name = get_stock_name(stock_id)

    if stock_name:
        print(f"\nFetching news for {stock_id} {stock_name}...\n")
        all_news = []
        
        news_ltn = fetch_news_ltn(stock_id, stock_name)
        all_news.extend(news_ltn)
        
        news_tvbs = fetch_news_tvbs(stock_id, stock_name)
        all_news.extend(news_tvbs)
        
        news_cnye = fetch_news_cnye(stock_id, stock_name)
        all_news.extend(news_cnye)
        
        news_chinatime = fetch_news_chinatime(stock_id, stock_name)
        all_news.extend(news_chinatime)
        
        print_news(all_news, "all sources")
        
        if all_news:
            insert_news_batch_to_supabase(all_news)
    else:
        print("Stock name not found in database.")

if __name__ == "__main__":
    main()

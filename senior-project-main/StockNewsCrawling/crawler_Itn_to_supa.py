import time
import os
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from supabase import create_client, Client
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 定义要爬取的股票ID和关键词
stocks = [
    {"stock_id": "2330", "keyword": "台積電"},
    # {"stock_id": "3443", "keyword": "創意"},
    # {"stock_id": "2002", "keyword": "中鋼"},
    # {"stock_id": "2317", "keyword": "鴻海"},
    # {"stock_id": "2731", "keyword": "雄獅"}
]

# 遍历每个股票
for stock in stocks:
    stock_id = stock["stock_id"]
    keyword = stock["keyword"]
    global_url = f'https://search.ltn.com.tw/list?keyword={keyword}&start_time=20220101&end_time=20230901&sort=date&type=all&page='

    page = 1
    news_url_l = []

    while True:
        url = global_url + str(page)
        
        # 创建 WebDriver 实例
        driver = webdriver.Chrome()
        
        # 设置隐式等待时间
        driver.implicitly_wait(10) # seconds
        
        # 载入网页
        driver.get(url)
        
        try:
            # 使用显式等待，等待特定元素出现
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "cont")]'))
            )
            
            # 获取所有元素
            elements = driver.find_elements(By.XPATH, '//div[contains(@class, "cont")]')
            
            # 如果元素数量少于10，停止爬虫
            if len(elements) < 10:
                print(f"{keyword} - 页面内容不足，停止爬虫...")
                break
            
            for e in elements:
                # 获取该元素的 href 属性
                href = e.get_attribute('href')
                if href:
                    print(f"{keyword} - 目标元素的网址:", href)
                    news_url_l.append(href)
                    
        except TimeoutException:
            print(f"{keyword} - 网页载入超时，重新载入...")
            # 关闭当前的 WebDriver 实例
            driver.quit()
            continue
        
        # 关闭 WebDriver 实例
        driver.quit()
        
        # 增加页数
        page += 8
        
        # 延时避免过快请求
        time.sleep(1)

    # 找到所有自由财经的网址
    news_url_l2 = [href for href in news_url_l if href.startswith("https://ec")]
    news_url_l2 = news_url_l2[:]

    # 爬取详细新闻内容并存储到 Supabase
    date_last = ''
    article = ''

    for index, link in enumerate(news_url_l2):
        # 请求网页内容
        response = requests.get(link)
        # 解析网页内容
        soup = BeautifulSoup(response.content, 'html.parser')

        try:
            time_element = soup.find_all('span', class_='time')
            time_text = time_element[1].text.strip()
            time_datetime = datetime.strptime(time_text, '%Y/%m/%d %H:%M')
            formatted_date = time_datetime.strftime('%Y-%m-%d')
            
            if date_last != formatted_date:
                article = ''
            date_last = formatted_date
            
            # 每次循环开始时清空 article 变量
            article = ''
            
            p = soup.find_all('div', class_="text")[1]
            contents = p.find_all('p')
            
            for content in contents:
                article = article + content.text.strip()
                
            # 打印爬取进度
            print(f'[{index+1}/{len(news_url_l2)}], {keyword} - Date:{formatted_date}, link:{link}')

            # 将数据插入 Supabase
            record = {
                'stockID': int(stock_id),
                'date': formatted_date,
                'content': article
            }
            supabase.table('news_content').insert(record).execute()
                
        except Exception as e:
            print(f"{keyword} - 爬取失败", e)
            print(f'[{index+1}/{len(news_url_l2)}], {keyword} - Date:{formatted_date}, link:{link}')
            pass
        time.sleep(1)

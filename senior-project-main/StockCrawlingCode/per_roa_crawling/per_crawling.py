#爬取上市股票的per(季度) 爬取網站:goodinfo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import csv
from supabase import create_client, Client

# Supabase setup
url = "https://ifdyheuivlbmhsbpuyqf.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlmZHloZXVpdmxibWhzYnB1eXFmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyMTMxMTU2OSwiZXhwIjoyMDM2ODg3NTY5fQ.c6DehH3cUJrjHa22_ps0w32xCLRhS5AAQUqc1sHqoI0"
supabase: Client = create_client(url, key)

# Fetch stock IDs from Supabase
response = supabase.table('stock').select('stockID').execute()
stock_ids = [item['stockID'] for item in response.data]

#爬到一半被阻擋 可以改stock_ids 繼續爬
#stock_ids = [item['stockID'] for item in response.data if int(item['stockID']) <= 2033] 

options = Options()
options.add_argument("--disable-notifications")

driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)

# Prepare the CSV file
with open('PER_results.csv', 'a', newline='', encoding='utf-8-sig') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['StockID', 'Year', 'PER'])

    for stock_id in stock_ids:
        url = f"https://goodinfo.tw/tw/ShowK_ChartFlow.asp?RPT_CAT=PER&STOCK_ID={stock_id}&CHT_CAT=QUAR&SCROLL2Y=111"
        driver.get(url)

        wait = WebDriverWait(driver, 10)
        element_present = wait.until(EC.presence_of_element_located((By.ID, "tblDetail")))

        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", {"class": "b1 p4_0 r0_10"})
        div_txtFinDetailData = soup.find("div", {"id": "divDetail"})

        if table and div_txtFinDetailData.text.strip() != "查無資料":
            trs = table.find_all("tr", {"align": "center"})
            for tr in trs:
                tds = tr.find_all("td")
                if len(tds) >= 5:
                    year = tds[0].text.strip()
                    per = tds[5].text.strip()
                    print(f"StockID: {stock_id}, Year: {year}, PER: {per}")
                    writer.writerow([stock_id, year, per])

        time.sleep(3)  # Delay to avoid being blocked

driver.quit()

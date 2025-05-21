from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import csv

options = Options()
options.add_argument("--disable-notifications")

driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)


stock_id='2330'
url = f"https://goodinfo.tw/tw/StockBzPerformance.asp?STOCK_ID={stock_id}"

driver.get(url)

# 'driver' 是您的 Selenium WebDriver 實例
wait = WebDriverWait(driver, 10)
# 等待元素 tblDetail 或 txtFinDetailData 顯示，
element_present = wait.until(
    EC.presence_of_element_located((By.ID, "tblDetail"))
    or soup.find("div", {"id": "txtFinDetailData"}) # type: ignore
)

html = driver.page_source
soup = BeautifulSoup(html, "lxml")

############# Find the main table #############
table = soup.find("table", {"id": "tblDetail"})
div_txtFinDetailData = soup.find("div", {"id": "txtFinDetailData"})

if table and div_txtFinDetailData.text.strip() != "查無資料":

    print("# " + str(stock_id))

    # Find the first th element with rowspan="2"
    first_row_th = (
        table.find("tr", {"class": "bg_h2"})
        .find("th", {"rowspan": "2"})
        .text.strip()
    )



    # Modify the title to include " BPS" after the first_row_th text
    title = f"{first_row_th} Share capital"
    print(title)

    time.sleep(1)

    # Find all tr elements with align="center"
    trs = table.find_all("tr", {"align": "center"})

    # Extract the text content of the first and twentieth td elements
    result = []
    for tr in trs:
        tds = tr.find_all("td")
        if len(tds) >= 20:  # Ensure there are at least 20 td elements
            result.append(
                f"{tds[0].text.strip()} {tds[1].text.strip()}"  # Adjusted index for the 20th element (19 in zero-based indexing)
            )


    # Output the result
    for item in result:
        print(item)

    print("\n")
    # 將資料寫入 CSV 檔案
    with open('year_Share_capital.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)

        # 寫入 CSV 表頭
        writer.writerow(['year', stock_id])
        
        # 寫入資料行
        for item in result:
            writer.writerow(item.split())  # Assuming each item in result is a string that can be split into the desired columns


    time.sleep(3)  # Add a delay between requests to avoid being blocked

driver.quit()
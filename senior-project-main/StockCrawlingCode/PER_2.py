# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 15:41:18 2024

@author: Chloe
"""

# crawler_bps.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import os

# Configure WebDriver options
options = Options()
options.add_argument("--disable-notifications")

driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)

stock_id = '2731'
url = f"https://goodinfo.tw/tw/ShowK_ChartFlow.asp?RPT_CAT=PER&STOCK_ID={stock_id}&CHT_CAT=QUAR&SCROLL2Y=111"

try:
    driver.get(url)

    # Wait for the button to be clickable and click it
    wait = WebDriverWait(driver, 10)
    button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='查60年']")))
    button.click()
    time.sleep(5)
    # Wait for the table to be present
    element_present = wait.until(EC.presence_of_element_located((By.ID, "tblDetail")))

    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    # Find the main table and div
    table = soup.find("table", {"id": "tblDetail"})
    div_txtFinDetailData = soup.find("div", {"id": "divDetail"})

    if table and div_txtFinDetailData.text.strip() != "查無資料":

        print("# " + str(stock_id))

        # Find the first th element with rowspan="2"
        #first_row_th = table.find("tr", {"id": "row0"}).find("th", {"rowspan": "2"}).text.strip()
        #title = f"{first_row_th} PER"
        #print(title)

        time.sleep(2)

        # Find all tr elements with align="center"
        trs = table.find_all("tr", {"align": "center"})

        # Extract the text content of the desired td elements
        result = []
        for tr in trs:
            tds = tr.find_all("td")
            if len(tds) >= 6:  # Ensure there are at least 6 td elements
                result.append(tds[5].text.strip())  # Adjusted index for the 6th element (5 in zero-based indexing)

        # Output the result
        for item in result:
            print(item)

        print("\n")

        # Check if the CSV file exists
        file_exists = os.path.isfile('PER.csv')

        if file_exists:
            # Read the existing CSV file into a DataFrame
            df_existing = pd.read_csv('PER.csv')
        else:
            # If the file does not exist, create an empty DataFrame
            df_existing = pd.DataFrame()

        # Create a DataFrame with the new data
        df_new = pd.DataFrame({stock_id: result})

        # Merge the new DataFrame with the existing one
        df_merged = pd.concat([df_existing, df_new], axis=1)

        # Output to CSV file (overwrite the original file)
        df_merged.to_csv('PER.csv', index=False, encoding='utf-8-sig')

        time.sleep(3)  # Add a delay between requests to avoid being blocked

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    driver.quit()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

def fetch_eps_data(driver, stock_id):
    url = f"https://goodinfo.tw/tw/StockBzPerformance.asp?STOCK_ID={stock_id}"
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    
    # 等待表格出现
    try:
        element_present = wait.until(EC.presence_of_element_located((By.ID, "tblDetail")))
    except:
        print(f"Data table not found for stock {stock_id}")
        return pd.DataFrame()  # 返回空的DataFrame

    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    # 查找主要表格
    table = soup.find("table", {"id": "tblDetail"})
    if not table:
        print(f"No data table found for stock {stock_id}")
        return pd.DataFrame()

    # 解析表格数据
    trs = table.find_all("tr", {"align": "center"})
    eps_data = []
    for tr in trs:
        tds = tr.find_all("td")
        if len(tds) >= 20:
            year = tds[0].text.strip()
            eps = tds[19].text.strip()
            eps_data.append([year, eps])

    return pd.DataFrame(eps_data, columns=[f'Year_{stock_id}', f'EPS_{stock_id}'])

# 配置Selenium WebDriver
options = Options()
options.add_argument("--disable-notifications")
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)

# 股票IDs
stock_ids = ['2330', '3443', '2002' , '2317','2731','3687']

# 收集所有股票的EPS数据
all_data_frames = []
for stock_id in stock_ids:
    eps_data = fetch_eps_data(driver, stock_id)
    all_data_frames.append(eps_data)

# 如果有多个DataFrame，将它们并列合并
if all_data_frames:
    combined_df = pd.concat(all_data_frames, axis=1)
    output_path = './StockData/year_eps.xlsx'
    combined_df.to_excel(output_path, index=False)
else:
    print("No data collected.")

driver.quit()

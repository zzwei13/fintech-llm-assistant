import os
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

# 定義一些常見的User-Agent
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
    # 添加更多User-Agent
]

# 將季度格式轉換為年份
def convert_season_to_year(season_str):
    if 'Q' in season_str:
        year, quarter = season_str.split('Q')
        year = f"20{year.zfill(2)}"
        return f"{year}{quarter}"
    return season_str

# 獲取財務數據並保存到 CSV 文件
def get_data(driver, stock_id, data_index, column_name, file_name):
    try:
        url = f"https://goodinfo.tw/tw/StockBzPerformance.asp?STOCK_ID={stock_id}"
        driver.get(url)

        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", {"id": "tblDetail"})
        div_txtFinDetailData = soup.find("div", {"id": "txtFinDetailData"})

        if table and div_txtFinDetailData.text.strip() != "查無資料":
            trs = table.find_all("tr", {"align": "center"})
            result = [
                [stock_id, convert_season_to_year(tds[0].text.strip()), tds[data_index].text.strip()]
                for tr in trs if (tds := tr.find_all("td")) and len(tds) >= data_index
            ]

            file_exists = os.path.isfile(file_name)
            df_existing = pd.read_csv(file_name) if file_exists else pd.DataFrame(columns=["stockID", "year", column_name])
            df_new = pd.DataFrame(result, columns=["stockID", "year", column_name])
            df_merged = pd.concat([df_existing, df_new], ignore_index=True)
            df_merged.to_csv(file_name, index=False, encoding='utf-8-sig')
            return True
        else:
            print(f"查無資料 for stock {stock_id}")
            return False

    except Exception as e:
        print(f"Error processing stock {stock_id}: {e}")
        return False

# 通用數據獲取函數
def fetch_data(driver, stock_id, column_name, data_index, file_name, page="StockBzPerformance"):
    try:
        url = f"https://goodinfo.tw/tw/{page}.asp?STOCK_ID={stock_id}"
        driver.get(url)

        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", {"id": "tblDetail"})

        if table:
            trs = table.find_all("tr", {"align": "center"})
            result = [
                [stock_id, convert_season_to_year(tds[0].text.strip()), tds[data_index].text.strip()]
                for tr in trs if (tds := tr.find_all("td")) and len(tds) >= data_index
            ]
            if result:
                file_exists = os.path.isfile(file_name)
                df_existing = pd.read_csv(file_name) if file_exists else pd.DataFrame(columns=["stockID", "year", column_name])
                df_new = pd.DataFrame(result, columns=["stockID", "year", column_name])
                df_merged = pd.concat([df_existing, df_new], ignore_index=True)
                df_merged.to_csv(file_name, index=False, encoding='utf-8-sig')
                return True
            else:
                print(f"查無資料 for stock {stock_id}")
                return False
        else:
            print(f"查無資料 for stock {stock_id}")
            return False
    except Exception as e:
        print(f"Error fetching {column_name} data for stock {stock_id}: {e}")
        return False

# 獲取 EPS 數據
def fetch_eps_data(driver, stock_id):
    return fetch_data(driver, stock_id, "EPS", 19, 'year_eps.csv')

# 獲取 DBR 數據
def fetch_dbr_data(driver, stock_id):
    return fetch_data(driver, stock_id, "DBR", 19, 'year_dbr.csv', page="StockAssetsStatus")

# 獲取 GM 數據
def fetch_gm_data(driver, stock_id):
    return fetch_data(driver, stock_id, "GM", 12, 'year_gm.csv')

# 獲取 OPM 數據
def fetch_opm_data(driver, stock_id):
    return fetch_data(driver, stock_id, "OPM", 13, 'year_opm.csv')

# 處理單個股票數據
def process_stock_data(stock_id):
    options = Options()
    user_agent = random.choice(user_agents)
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--disable-notifications")
    options.add_argument("--headless")  # 無頭模式
    options.add_argument("--disable-gpu")  # 禁用GPU，對於無頭模式下的穩定性有幫助
    options.add_argument("--no-sandbox")  # 對於某些系統，這個選項可以提高穩定性
    options.add_argument("--window-size=1920,1080")  # 設定窗口大小
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)

    stock_id = str(stock_id)
    
    if not get_data(driver, stock_id, 20, "BPS", 'year_bps.csv'):
        driver.quit()
        return
    if not get_data(driver, stock_id, 16, "ROE", 'year_roe.csv'):
        driver.quit()
        return
    if not get_data(driver, stock_id, 1, "Share_Capital", 'year_Share_capital.csv'):
        driver.quit()
        return

    if not fetch_eps_data(driver, stock_id):
        driver.quit()
        return
    if not fetch_dbr_data(driver, stock_id):
        driver.quit()
        return
    if not fetch_gm_data(driver, stock_id):
        driver.quit()
        return
    if not fetch_opm_data(driver, stock_id):
        driver.quit()
        return

    driver.quit()
    print(f"success to process stock {stock_id}")
    # 隨機等待5到15秒，模擬人工操作
    time.sleep(random.uniform(5, 8))


# 主函數
def main():
    for stock_id in range(1187, 10000):
        try:
            process_stock_data(stock_id)
        except Exception as e:
            print(f"Error processing stock {stock_id}: {e}")

if __name__ == "__main__":
    main()
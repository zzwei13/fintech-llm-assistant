import os
import time
from multiprocessing import Pool, Manager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 初始化 Supabase 客戶端
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 設定ChromeDriver
def setup_driver():
    options = Options()

    # 設定下載路徑
    download_dir = "D:\\twii\\stock_price"
    prefs = {"download.default_directory": download_dir, 
             "directory_upgrade": True,
             "safebrowsing.enabled": True}
    options.add_experimental_option("prefs", prefs)

    options.add_argument("--disable-gpu")  # 禁用GPU
    options.add_argument("--headless")  # 無頭模式
    options.add_argument("--disable-extensions")  # 禁用擴展
    options.add_argument("--disable-blink-features=AutomationControlled")  # 禁用自動化標識

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(3)  # 減少隱式等待時間
    return driver

# 處理單個股票數據
def process_stock_data(stock_id, lock):
    download_dir = "D:\\twii\\stock_price"
    download_file_path = os.path.join(download_dir, f"{stock_id}.TW.csv")

    # 如果檔案已存在，則跳過
    if os.path.exists(download_file_path):
        print(f"{stock_id}.TW.csv 已存在，跳過下載")
        return

    driver = setup_driver()
    try:
        url = f"https://hk.finance.yahoo.com/quote/{stock_id}.TW/history/"
        driver.get(url)

        wait = WebDriverWait(driver, 3)

        # 點擊日期選擇按鈕中的SVG圖標
        date_button_svg = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.Pos\(r\).D\(ib\).Va\(m\).Mstart\(8px\) div.Pos\(r\).D\(ib\).C\(\$linkColor\).Cur\(p\) svg")))
        date_button_svg.click()

        # 點擊最大日期按鈕
        max_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-value="MAX"]')))
        max_button.click()

        # 點擊下載按鈕
        download_svg = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'svg[data-icon="download"]')))
        download_svg.click()

        # 等待文件下載完成
        wait.until(lambda driver: os.path.exists(download_file_path))

        # 僅在 lock 不為 None 時使用 lock
        if lock:
            with lock:
                print(f"成功下載 {stock_id} 的數據")
        else:
            print(f"成功下載 {stock_id} 的數據")

    except Exception as e:
        if lock:
            with lock:
                print(f"處理股票代號 {stock_id} 時發生錯誤: {e}")
        else:
            print(f"處理股票代號 {stock_id} 時發生錯誤: {e}")

    finally:
        driver.quit()


# 主函數
def main():
    try:
        # 設定 stockID 的最小值
        min_stock_id = int(input("請輸入需要處理的最小 stockID: "))

        # 選擇模式：單進程或多進程
        mode = input("請選擇模式 (1: 單進程, 2: 多進程): ").strip()
        num_processes = 4  # 可根據需要調整進程數量

        # 從 Supabase 讀取所有 stockID
        response = supabase.table('stock').select('stockID').execute()
        stock_ids = response.data

        if stock_ids:
            stock_ids = [int(stock['stockID']) for stock in stock_ids if int(stock['stockID']) >= min_stock_id]

            if mode == '2':  # 多進程模式
                # 創建多進程管理器
                with Manager() as manager:
                    # 創建可以在多進程之間共享的鎖
                    lock = manager.Lock()

                    # 使用進程池並行處理
                    with Pool(processes=num_processes) as pool:
                        pool.starmap(process_stock_data, [(stock_id, lock) for stock_id in stock_ids])
            elif mode == '1':  # 單進程模式
                for stock_id in stock_ids:
                    process_stock_data(stock_id, None)
            else:
                print("無效的模式選擇。")
        else:
            print("No stock IDs found.")
    except Exception as e:
        print(f"Error retrieving stock data: {e}")

if __name__ == "__main__":
    main()

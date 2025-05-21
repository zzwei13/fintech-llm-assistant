from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import pandas as pd
import re
from selenium.common.exceptions import TimeoutException
def fetch_stock_data(stock_id):
    base_url = f'https://pchome.megatime.com.tw/stock/sto2/ock1/20183/sid{stock_id}.html'
    driver.get(base_url)

    try:
        # 明確等待，直到 'select' 元素可見
        select_tag = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "select[onchange*='sid{}']".format(stock_id)))
        )
        soup = BeautifulSoup(select_tag.get_attribute('innerHTML'), 'lxml')
        option_values = [option.get('value') for option in soup.find_all('option')]

        stock_data = []

        for value in option_values:
            driver.get(f'https://pchome.megatime.com.tw/stock/sto2/ock1/' + value + f'/sid{stock_id}.html')
            try:
                # 等待 bttb div 出現
                bttb_div = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "bttb"))
                )
                page_soup = BeautifulSoup(bttb_div.get_attribute('innerHTML'), 'html.parser')
                ct16_elements = page_soup.find_all(class_="ct16")

                if ct16_elements:
                    season_eps = ct16_elements[len(ct16_elements) - 6].text.strip()
                    stock_data.append([value, season_eps])
                else:
                    print(f"No data found for season {value} on stock {stock_id}.")
            except Exception as e:
                print(f"Error while fetching data for season {value} on stock {stock_id}: {e}")
            time.sleep(4)

        return pd.DataFrame(stock_data, columns=['season_' + stock_id, 'EPS_' + stock_id])

    except TimeoutException:
        print(f"Timeout occurred while trying to fetch data for stock {stock_id}")
        return pd.DataFrame(columns=['season_' + stock_id, 'EPS_' + stock_id])

# Selenium configuration and driver setup
options = Options()
options.add_argument("--disable-notifications")
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)

# Stock IDs to fetch data for
stocks = ['2330', '3443', '2002' , '2317','2731','3687']

# Fetch data for each stock and store in list of DataFrames
all_data_frames = [fetch_stock_data(stock_id) for stock_id in stocks]

# Concatenate all DataFrames horizontally
final_df = pd.concat(all_data_frames, axis=1)

# Write to Excel file
output_path = './StockData/season_eps.xlsx'
final_df.to_excel(output_path, index=False)

driver.quit()
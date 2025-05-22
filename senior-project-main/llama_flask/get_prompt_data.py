# 獲取所有prompt需要的股市資料
import asyncio
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import csv
from dotenv import load_dotenv
from supabase import create_client, Client
from ollama import AsyncClient

# 載入環境變數
load_dotenv()
# 初始化 Supabase 客戶端
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


# 获取公司背景资料
def get_company_background(stock_id):
    url = f"https://tw.stock.yahoo.com/quote/{stock_id}/profile"
    web = requests.get(url)
    soup = BeautifulSoup(web.text, "html.parser")

    # 查找第一个 section
    first_section = soup.find("section")

    # 查找第一个 section 中的最后一个 div
    if first_section:
        background_div = first_section.find_all("div")[-1]
        if background_div:
            return background_div.get_text().strip()

    return "无法取得公司背景资料"


# 汇总股票数据
def summarize_stock_data(stock_id, end_year):
    # 設定開始年份（過去五年）
    start_year = end_year - 4

    # 從 Supabase 中獲取指定年份範圍內的日價格資料
    response = (
        supabase.table("daily_price")
        .select("date", "adj_price")
        .eq("stockID", stock_id)
        .gte("date", f"{start_year}-01-01")
        .lte("date", f"{end_year}-12-31")
        .execute()
    )

    # 將資料轉換為 DataFrame
    df = pd.DataFrame(response.data)

    # 確保 'date' 欄位為日期格式，並設為索引
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)

    # 按年份進行重采樣並計算統計資料
    yearly_summary = df["adj_price"].resample("Y").agg(["first", "last", "max", "min"])
    yearly_summary.columns = ["Open", "Close", "High", "Low"]

    return yearly_summary


# 將彙總資料轉換為string格式
def get_stock_summary_string(summary):
    summary_str = "\n".join(
        [
            f"{year.strftime('%Y')}: Open={row['Open']}, Close={row['Close']}, High={row['High']}, Low={row['Low']}"
            for year, row in summary.iterrows()
        ]
    )
    return summary_str


# 確保資料安全取值
def safe_get_value(data, year, column_name):
    if data is None:
        print(f"Data is None, cannot retrieve {column_name} for year {year}.")
        return "NA"
    try:
        value = data.loc[year, column_name]
        print(f"Retrieved {column_name} for year {year}: {value}")
        if column_name == "share_capital":
            return str(value)  # 對於 capital_value，返回字符串
        else:
            return float(value)  # 對於其他指標，返回浮點數
    except KeyError:
        print(f"KeyError: Unable to find {column_name} data for year {year}")
        return "NA"
    except ValueError:
        print(f"ValueError: Unable to convert {column_name} data for year {year}")
        return "NA"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "NA"


# supabase資料存取
def select_supabase_data(stock_id, date):

    end_year = int(date[:4])
    # 使用過去五年的資料
    start_year = end_year - 4
    date_obj = datetime.strptime(date, "%Y-%m-%d")

    # 從 Supabase 獲取資料
    data_bps = get_data_from_supabase(
        "year_bps", int(stock_id), int(start_year), int(end_year)
    )
    data_roe = get_data_from_supabase(
        "year_roe", int(stock_id), int(start_year), int(end_year)
    )
    data_Share_capital = get_data_from_supabase(
        "year_share_capital", int(stock_id), int(start_year), int(end_year)
    )
    data_roa = get_data_from_supabase(
        "year_roa", int(stock_id), int(start_year), int(end_year)
    )
    data_eps = get_data_from_supabase(
        "year_eps", int(stock_id), int(start_year), int(end_year)
    )
    data_per = get_data_from_supabase(
        "year_per", int(stock_id), int(start_year), int(end_year)
    )
    data_GM = get_data_from_supabase(
        "year_gm", int(stock_id), int(start_year), int(end_year)
    )
    data_OPM = get_data_from_supabase(
        "year_opm", int(stock_id), int(start_year), int(end_year)
    )
    data_DBR = get_data_from_supabase(
        "year_dbr", int(stock_id), int(start_year), int(end_year)
    )

    stock_price = get_stock_price(stock_id, date)

    # 返回所有数据作为字典
    return {
        "data_bps": data_bps,
        "data_roe": data_roe,
        "data_Share_capital": data_Share_capital,
        "data_eps": data_eps,
        "data_GM": data_GM,
        "data_OPM": data_OPM,
        "data_DBR": data_DBR,
        "data_roa": data_roa,
        "data_per": data_per,
        "stock_price": stock_price,
    }


def get_data_from_supabase(table_name, stock_id, start_year, end_year):
    print(f"Fetching data from table: {table_name}")
    response = (
        supabase.table(table_name)
        .select("*")
        .eq("stockID", stock_id)
        .gte("year", start_year)
        .lte("year", end_year)
        .execute()
    )

    print(f"Response data: {response.data}")
    df = pd.DataFrame(response.data)
    if df.empty:
        print(f"No data found for {table_name}")
    else:
        print(f"Data fetched for {table_name}: {df}")
    if "year" not in df.columns:
        print("No 'year' column found in the returned data.")
        return None
    df.set_index("year", inplace=True)
    return df


def get_stock_price(stock_id, date):
    # 將輸入的日期字串轉換為 datetime 物件
    date_obj = pd.to_datetime(date).date()

    # 從 Supabase 中抓取價格資料
    response = (
        supabase.table("daily_price")
        .select("adj_price")
        .eq("stockID", stock_id)
        .eq("date", date_obj)
        .execute()
    )

    # 如果找到匹配的價格，則返回價格，否則返回 None 或其他合適的預設值
    if response.data:
        price = response.data[0]["adj_price"]
        return price
    else:
        return None


def get_stock_price_from_yahoo(stock_id):

    url = f"https://tw.stock.yahoo.com/quote/{stock_id}"  # Yahoo Finance stock URL
    web = requests.get(url)  # 獲取網頁內容
    soup = BeautifulSoup(web.text, "html.parser")  # 解析網頁內容
    title = soup.find("h1").get_text()  # 獲取股票名稱
    current_price = soup.select(".Fz\(32px\)")[0].get_text()  # 獲取當前價格
    change = soup.select(".Fz\(20px\)")[0].get_text()  # Get price change
    status = ""  # 設置狀態：上漲、下跌或持平

    try:
        if soup.select("#main-0-QuoteHeader-Proxy")[0].select(".C($c-trend-down)")[0]:
            status = "-"  # 下跌
    except:
        try:
            if soup.select("#main-0-QuoteHeader-Proxy")[0].select(".C($c-trend-up)")[0]:
                status = "+"  # 上漲
        except:
            status = "▬"  # 持平

    return (
        f"{title} : {current_price} ( {status}{change} )"  # Return the formatted string
    )

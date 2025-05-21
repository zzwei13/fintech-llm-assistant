import asyncio
import os
import csv
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from together import Together
from app.services.get_prompt_data import *
from app.services.prompt_generater import *

# 獲取腳本所在目錄
script_dir = os.path.dirname(os.path.abspath(__file__))

# 設置結果資料相對路徑
result_data_dir = os.path.join(script_dir, "..", "test result")
if not os.path.exists(result_data_dir):
    os.makedirs(result_data_dir)

# 載入環境變數
load_dotenv()

# 初始化 Supabase 客戶端
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 初始化 Together 客戶端
together_client = Together(api_key=os.environ.get("TOGETHER_API_KEY2"))

# 解析模型輸出結果
import re


def parse_output(output):
    result = {}
    # 使用正則表達式來匹配每個問題的答案
    bullish_match = re.search(
        r"1\. Is the next one year bullish or bearish\?:(.*)", output
    )
    buy_recommendation_match = re.search(
        r"2\. Based on the current price, is it recommended to buy\?\s*:(.*)", output
    )
    sell_price_match = re.search(
        r"3\. Based on the current price, assuming the maximum loss of the stop loss strategy is 10%, what is the recommended selling price\?\s*:(.*)",
        output,
    )
    holding_period_match = re.search(
        r"4\. What is the recommended holding period for this investment\?\s*:(.*)",
        output,
    )
    stop_loss_strategy_match = re.search(
        r"5\. Suggested stop loss strategy\? What are your criteria for triggering a sell order\?\s*:(.*)",
        output,
    )

    if bullish_match:
        result["Bullish/Bearish"] = bullish_match.group(1).strip()
    if buy_recommendation_match:
        result["Recommend buy or not"] = buy_recommendation_match.group(1).strip()
    if sell_price_match:
        result["Recommended selling price"] = sell_price_match.group(1).strip()
    if holding_period_match:
        result["Recommended holding period"] = holding_period_match.group(1).strip()
    if stop_loss_strategy_match:
        result["Stop-loss strategy"] = stop_loss_strategy_match.group(1).strip()

    return result


# 獲取所有 stock_id
def get_all_stock_ids():
    response = supabase.table("stock").select("stockID").execute()
    # 将 stockID 转换为字符串类型
    stock_ids = [str(item["stockID"]) for item in response.data]
    return stock_ids


# 只取部分 stock_id
def get_some_stock_ids(begin, end):
    response = (
        supabase.table("stock")
        .select("stockID")
        .gte("stockID", begin)
        .lte("stockID", end)
        .execute()
    )
    stock_ids = [str(item["stockID"]) for item in response.data]
    return stock_ids


# dates = ["2019-12-31"]
# stock_ids = get_some_stock_ids(4106, 4119)  # 只分析部分 stock_id


async def chat(dates, stocks):
    for stock in stocks:
        stock_id = stock.get("stock_id")
        for date in dates:
            print("today date :", date)
            print(f"Processing stock: {stock_id}")
            end_year = int(date[:4])
            start_year = end_year - 4

            # 取得 prompt 需要的股票資料
            result = select_supabase_data(stock_id, date)
            required_fields = [
                "data_bps",
                "data_roe",
                "data_Share_capital",
                "data_eps",
                "data_GM",
                "data_OPM",
                "data_DBR",
                "data_roa",
                "data_per",
                "stock_price",
            ]
            if not all(field in result for field in required_fields):
                print(f"Skipping stock {stock_id} due to incomplete data.")
                continue

            data_bps = result["data_bps"]
            data_roe = result["data_roe"]
            data_Share_capital = result["data_Share_capital"]
            data_eps = result["data_eps"]
            data_GM = result["data_GM"]
            data_OPM = result["data_OPM"]
            data_DBR = result["data_DBR"]
            data_roa = result["data_roa"]
            data_per = result["data_per"]
            stock_price = result["stock_price"]

            # Summarize historical stock data
            yearly_summary = summarize_stock_data(stock_id, end_year)
            summary_str = get_stock_summary_string(yearly_summary)

            # 取得公司背景資料
            company_background = get_company_background(stock_id)

            # 處理數據
            bps_values = [
                safe_get_value(data_bps, year, "BPS")
                for year in range(start_year, end_year + 1)
            ]
            roe_values = [
                safe_get_value(data_roe, year, "ROE")
                for year in range(start_year, end_year + 1)
            ]
            capital_values = [
                safe_get_value(data_Share_capital, year, "Share_Capital")
                for year in range(start_year, end_year + 1)
            ]
            roa_values = [
                safe_get_value(data_roa, year, "roa")
                for year in range(start_year, end_year + 1)
            ]
            eps_values = [
                safe_get_value(data_eps, year, "EPS")
                for year in range(start_year, end_year + 1)
            ]
            per_values = [
                safe_get_value(data_per, year, "per")
                for year in range(start_year, end_year + 1)
            ]
            GM_values = [
                safe_get_value(data_GM, year, "GM")
                for year in range(start_year, end_year + 1)
            ]
            OPM_values = [
                safe_get_value(data_OPM, year, "OPM")
                for year in range(start_year, end_year + 1)
            ]
            DBR_values = [
                safe_get_value(data_DBR, year, "DBR")
                for year in range(start_year, end_year + 1)
            ]

            # 把五年的資料變成字串格式
            bps_str = ", ".join(map(str, bps_values))
            roe_str = ", ".join(map(str, roe_values))
            capital_str = ", ".join(map(str, capital_values))
            roa_str = ", ".join(map(str, roa_values))
            eps_str = ", ".join(map(str, eps_values))
            per_str = ", ".join(map(str, per_values))
            GM_str = ", ".join(map(str, GM_values))
            OPM_str = ", ".join(map(str, OPM_values))
            DBR_str = ", ".join(map(str, DBR_values))

            print("bps_str:", bps_str)
            print("roe_str:", roe_str)
            print("capital_str:", capital_str)
            print("roa_str:", roa_str)
            print("eps_str:", eps_str)
            print("per_str:", per_str)
            print("GM_str:", GM_str)
            print("OPM_str:", OPM_str)
            print("DBR_str:", DBR_str)
            print("summary_str:", summary_str)
            print("current price:", stock_price)
            print("company background:", company_background)

            # --------------------------------循環次數------------------------------------ #
            for _ in range(1):
                stock_price = get_stock_price_from_yahoo(stock_id)

                # 使用 generate_message_content 生成 message_content
                message_content = generate_message_content(
                    stock_id,
                    bps_str,
                    capital_str,
                    roe_str,
                    eps_str,
                    GM_str,
                    OPM_str,
                    DBR_str,
                    summary_str,
                    stock_price,
                    company_background,
                    roa_str,
                    per_str,
                )

                # 保存每次的 input message 到 log 檔案
                input_log_path = os.path.join(
                    result_data_dir, str(stock_id), f"input_log_{stock_id}.txt"
                )

                # 確保目錄存在
                os.makedirs(os.path.dirname(input_log_path), exist_ok=True)

                with open(input_log_path, "a", encoding="utf-8") as input_log_f:
                    input_log_f.write(f"no.{_} === {datetime.now()} ===\n")
                    input_log_f.write(message_content)
                    input_log_f.write("\n\n")

                message = {"role": "user", "content": message_content}

                # 修改路徑
                result_path = os.path.join(
                    result_data_dir, str(stock_id), f"output_{stock_id}.txt"
                )
                log_path = os.path.join(
                    result_data_dir, str(stock_id), f"output_log_{stock_id}.txt"
                )
                csv_path = os.path.join(
                    result_data_dir, str(stock_id), f"output_{stock_id}.csv"
                )

                # 確保目錄存在
                os.makedirs(os.path.dirname(result_path), exist_ok=True)

                fieldnames = [
                    "Date",
                    "Bullish/Bearish",
                    "Recommend buy or not",
                    "Recommended selling price",
                    "Recommended holding period",
                    "Stop-loss strategy",
                ]

                # 將輸出存成 txt 檔案
                with open(result_path, "w", encoding="utf-8") as f:
                    response = together_client.chat.completions.create(
                        model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                        messages=[message],
                        max_tokens=512,
                        temperature=0.7,
                        top_p=0.7,
                        top_k=50,
                        repetition_penalty=1,
                        stop=["<|eot_id|>", "<|eom_id|>"],
                        stream=True,
                    )

                    accumulated_text = ""  # 用於累積生成的文本
                    for part in response:
                        for choice in part.choices:
                            accumulated_text += choice.delta.content  # 累積內容
                    f.write(accumulated_text)

                # 解析輸出結果
                with open(result_path, "r", encoding="utf-8") as f:
                    output = f.read()
                    parsed_result = parse_output(output)

                # 將結果寫入 CSV 檔案
                try:
                    with open(csv_path, "x", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                except FileExistsError:
                    pass

                with open(csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    parsed_result["Date"] = date  # 新增 date 欄位
                    writer.writerow(parsed_result)

                # 保存歷史紀錄到 log 檔案
                with open(log_path, "a", encoding="utf-8") as log_f:
                    log_f.write(f"no.{_} === {datetime.now()} ===\n")
                    log_f.write(output)
                    log_f.write("\n\n")

                # 輸出結果到終端
                print(_)
                print(parsed_result)

    return parsed_result


def get_stock_predictions(dates, stocks):
    return asyncio.run(chat(dates, stocks))

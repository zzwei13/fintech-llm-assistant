import asyncio
import os
import csv
import re
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from together import Together
from get_prompt_data import *
from prompt_generater import *
from functools import lru_cache

# 獲取腳本所在目錄
script_dir = os.path.dirname(os.path.abspath(__file__))

# 設置結果資料相對路徑
result_data_dir = os.path.join(script_dir, "..", "test_result")
os.makedirs(result_data_dir, exist_ok=True)

# 載入環境變數
load_dotenv()

# 初始化 Supabase 客戶端
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 初始化 Together 客戶端
together_client = Together(api_key=os.getenv("TOGETHER_API_KEY"))

# 使用 LRU 快取來儲存重複查詢的股票資料
@lru_cache(maxsize=128)
def fetch_stock_data(stock_id, date):
    result = select_supabase_data(stock_id, date)
    return result if result else None

def parse_output(output):
    # 使用正則表達式群組一次性匹配所有答案
    pattern = (
        r"1\. Is the next one year bullish or bearish\?:\s*(.*?)\n"
        r"2\. Based on the current price, is it recommended to buy\?\s*:\s*(.*?)\n"
        r"3\. Based on the current price, assuming the maximum loss of the stop loss strategy is 10%, what is the recommended selling price\?\s*:\s*(.*?)\n"
        r"4\. What is the recommended holding period for this investment\?\s*:\s*(.*?)\n"
        r"5\. Suggested stop loss strategy\? What are your criteria for triggering a sell order\?\s*:\s*(.*?)\n"
    )
    matches = re.search(pattern, output, re.DOTALL)
    if matches:
        return {
            "Bullish/Bearish": matches.group(1).strip(),
            "Recommend buy or not": matches.group(2).strip(),
            "Recommended selling price": matches.group(3).strip(),
            "Recommended holding period": matches.group(4).strip(),
            "Stop-loss strategy": matches.group(5).strip(),
        }
    return {}

async def process_stock(stock_id, date):
    print(f"Processing stock: {stock_id} on date: {date}")

    # 取得 prompt 需要的股票資料
    result = fetch_stock_data(stock_id, date)
    required_fields = [
        "data_bps", "data_roe", "data_Share_capital", "data_eps", "data_GM",
        "data_OPM", "data_DBR", "data_roa", "data_per", "stock_price"
    ]
    if not result or not all(field in result for field in required_fields):
        print(f"Skipping stock {stock_id} due to incomplete data.")
        return

    data_values = {field: result[field] for field in required_fields}

    # 將數據轉為字串格式
    data_strings = {
        key: ", ".join(map(str, [safe_get_value(data_values[key], year, key.upper()) 
                                 for year in range(int(date[:4]) - 4, int(date[:4]) + 1)]))
        for key in data_values if key != "stock_price"
    }
    summary_str = get_stock_summary_string(summarize_stock_data(stock_id, int(date[:4])))
    company_background = get_company_background(stock_id)

    print(f"Data summary for stock {stock_id}: {summary_str}")

    # 生成 message_content
    message_content = generate_message_content(
        stock_id,
        **data_strings,
        summary_str=summary_str,
        stock_price=data_values["stock_price"],
        company_background=company_background
    )

    # 確保日誌目錄存在
    input_log_path = os.path.join(result_data_dir, stock_id, f"input_log_{stock_id}.txt")
    os.makedirs(os.path.dirname(input_log_path), exist_ok=True)

    # 寫入日誌
    async with open(input_log_path, "a", encoding="utf-8") as input_log_f:
        input_log_f.write(f"{datetime.now()}:\n{message_content}\n\n")

    # 取得模型回應並解析
    response = await together_client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        messages=[{"role": "user", "content": message_content}],
        max_tokens=512,
        temperature=0.7,
        top_p=0.7,
        top_k=50,
        repetition_penalty=1,
        stop=["<|eot_id|>", "<|eom_id|>"],
        stream=True,
    )
    
    # 收集輸出並解析
    accumulated_text = "".join(choice.delta.content for part in response for choice in part.choices)
    parsed_result = parse_output(accumulated_text)

    # 寫入 CSV 檔案
    csv_path = os.path.join(result_data_dir, stock_id, f"output_{stock_id}.csv")
    async with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Date", "Bullish/Bearish", "Recommend buy or not",
            "Recommended selling price", "Recommended holding period", "Stop-loss strategy"
        ])
        if f.tell() == 0:
            writer.writeheader()  # 新建檔案時寫入標題
        parsed_result["Date"] = date
        writer.writerow(parsed_result)

    return parsed_result

async def chat(dates, stock_ids):
    results = []
    for stock_id in stock_ids:
        for date in dates:
            result = await process_stock(stock_id, date)
            results.append(result)
    return results

def get_stock_predictions(dates, stock_ids):
    return asyncio.run(chat(dates, stock_ids))

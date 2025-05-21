# main.py
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import tvbs,cnye,ltn  # 导入 TVBS 爬虫模块

# 加载环境变量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 设置股票和日期范围
def get_stocks():
    return supabase.table("stock").select("stockID, stock_name").gte("stockID", 1217).lte("stockID", 1300).execute().data

def main():
    stocks = get_stocks()
    start = "20241008"
    end = "20241108"
    start_date = datetime.strptime(start, "%Y%m%d")
    end_date = datetime.strptime(end, "%Y%m%d")

    # 调用 TVBS 爬虫
    tvbs.scrape_tvbs(stocks, start_date, end_date)
    cnye.scrape_cnye(stocks, start_date, end_date)
    ltn.scrape_ltn(stocks, start, end)

if __name__ == "__main__":
    main()

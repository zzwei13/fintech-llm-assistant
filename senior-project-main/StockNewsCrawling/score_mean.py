from supabase import create_client, Client
import pandas as pd
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

"""
todo :
新增emotion平均


"""
# 加載環境變量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def scoreMean(date, stocks):

    mean_data = {}  # 改變為字典來儲存結果，而不是列表

    # 逐個處理每個股票和日期
    for stock in stocks:
        stock_id = stock.get("stock_id")
        stock_name = stock.get("stock_name")

        # 解析日期
        end_date = datetime.strptime(date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=30)

        # 從 Supabase 讀取新聞數據
        news_response = (
            supabase.table("news_test").select("*").eq("stockID", stock_id).execute()
        )

        if news_response.data:
            news_data = news_response.data
            news = pd.DataFrame(news_data)
        else:
            print(
                f"Failed to fetch data from Supabase for stock_id {stock_id}: data={news_response.data}, count={news_response.count}"
            )
            continue  # 跳過該股票ID，繼續處理下一個

        # 將日期列轉換為 datetime 類型
        news["date"] = pd.to_datetime(news["date"])

        # 過濾數據，只包含過去30天內的行
        recent_news = news[(news["date"] >= start_date) & (news["date"] <= end_date)]

        # 計算 arousal 列的總和和總數
        total_arousal = recent_news["arousal"].sum()
        total_emotion = recent_news["emotion"].sum()
        news_count = len(recent_news)

        if news_count > 0:
            # 計算過去30天的平均 arousal
            mean_arousal = round(total_arousal / news_count, 5)
            mean_emotion = round(total_emotion / news_count, 5)
        else:
            mean_arousal = 0
            mean_emotion = 0

        # 構建用來存儲的數據結構，使用 stockID 和日期作為索引
        if stock_id not in mean_data:
            mean_data[stock_id] = (
                {}
            )  # 如果該股票ID不在 mean_data 中，則初始化它為空字典

        mean_data[stock_id][date] = {
            "date": end_date.strftime("%Y-%m-%d"),
            "arousal_mean": mean_arousal,
            "emotion_mean": mean_emotion,
            "stockID": stock_id,
            "count": news_count,
        }

        # 檢查是否已存在該日期和股票ID的資料
        check_response = (
            supabase.table("stock_news_summary_30")
            .select("id")
            .eq("stockID", stock_id)
            .eq("date", end_date.strftime("%Y-%m-%d"))
            .execute()
        )

        if check_response.data:
            # 資料存在，更新該筆資料的 arousal_mean 欄位
            update_response = (
                supabase.table("stock_news_summary_30")
                .update(
                    {
                        "arousal_mean": mean_arousal,
                        "emotion_mean": mean_emotion,
                        "count": news_count,
                    }
                )  # 更新 count 和 arousal_mean
                .eq("stockID", stock_id)
                .eq("date", end_date.strftime("%Y-%m-%d"))
                .execute()
            )
            if update_response.data is None:
                print(
                    f"Failed to update data for stock_id {stock_id}: {update_response}"
                )
                raise Exception("Data update failed")
            else:
                print(f"Data for stock_id {stock_id} updated successfully.")
        print("total arousal:", total_arousal)
        print("total emotion:", total_emotion)
        print("mean_data:", mean_data)
    print(f"{stock_id}30日的新聞分數平均計算完成\n")

    # 返回將要插入的字典列表
    return mean_data


# test
if __name__ == "__main__":
    # Define a test date as a single string
    test_date = "2024-10-19"

    # 測試传入股票的 stocks 列表格式
    test_stocks = [{"stock_id": "2330", "stock_name": "台積電"}]
    try:
        print("Testing with keyword '台積電'...")
        mean_result = scoreMean(test_date, test_stocks)  # 傳入單個日期字串
        print("Inserted data:", mean_result)
    except Exception as e:
        print(f"Error testing with keyword '台積電': {e}")

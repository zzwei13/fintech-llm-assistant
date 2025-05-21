# cvaw3 + NTUD
import jieba
import jieba.analyse
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def load_data_from_supabase():
    """Load the necessary data from Supabase and return dataframes."""

    # Load CVAW3 sentiment words
    response = supabase.table("cvaw3").select("*").execute()
    if response.data:
        cvaw3 = pd.DataFrame(response.data).set_index("Word")
        print("CVAW3 loaded")
    else:
        print(f"Failed to load CVAW3: data={response.data}, count={response.count}")
        raise Exception("Cannot load CVAW3 data")

    # Load positive words
    pos_response = supabase.table("positive_word").select("*").execute()
    if pos_response.data:
        positive_words = set(pd.DataFrame(pos_response.data)["text"])
        print("Positive words loaded")
    else:
        print(
            f"Failed to load positive words: data={pos_response.data}, count={pos_response.count}"
        )
        raise Exception("Cannot load positive words")

    # Load negative words
    neg_response = supabase.table("negative_word").select("*").execute()
    if neg_response.data:
        negative_words = set(pd.DataFrame(neg_response.data)["text"])
        print("Negative words loaded\n")
    else:
        print(
            f"Failed to load negative words: data={neg_response.data}, count={neg_response.count}"
        )
        raise Exception("Cannot load negative words")

    return cvaw3, positive_words, negative_words


# 特定日期範圍來篩選新聞
def load_news_data(date, stock_id):
    """Load news data from Supabase based on a stock ID."""
    end_date = datetime.strptime(date, "%Y-%m-%d")
    start_date = end_date - timedelta(days=30)

    # Query for news within the date range
    news_response = (
        supabase.table("news_content")
        .select("*")
        .eq("stockID", stock_id)
        .gte("date", start_date)  # Filter for news on or after start_date
        .lte("date", end_date)  # Filter for news on or before end_date
        .execute()
    )

    if news_response.data:
        news = pd.DataFrame(news_response.data)
        return news
    else:
        print(
            f"從 Supabase 獲取資料失敗: data={news_response.data}, count={news_response.count}"
        )
        raise Exception("無法從 Supabase 獲取資料")


def analyze_sentiment(news, cvaw3, positive_words, negative_words):
    """Perform sentiment analysis on the news data and add relevant columns."""

    # Initialize new columns
    news["CVAW3_Valence_Avg"] = float("nan")
    news["CVAW3_Valence_Total"] = float("nan")
    news["CVAW3_Arousal_Avg"] = float("nan")
    news["CVAW3_Arousal_Total"] = float("nan")
    news["NTUD_Valence_Avg"] = float("nan")
    news["NTUD_Valence_Total"] = float("nan")
    news["NTUD_Valence_Percentage"] = float("nan")

    # Analyze each news content
    for i in range(len(news["content"])):
        seg_list = jieba.cut(news["content"][i])
        cvaw3_sum_V, cvaw3_sum_A, cvaw3_count = 0, 0, 0
        ntud_sum_V, ntud_count = 0, 0

        for w in seg_list:
            if w in cvaw3.index:
                cvaw3_sum_V += cvaw3["Valence_Mean"][w] - 5
                cvaw3_sum_A += cvaw3["Arousal_Mean"][w] - 5
                cvaw3_count += 1
            elif w in negative_words:
                ntud_sum_V -= 1
                ntud_count += 1
            elif w in positive_words:
                ntud_sum_V += 1
                ntud_count += 1

        # Update news dataframe with computed values
        if cvaw3_count > 0:
            news.at[i, "CVAW3_Valence_Avg"] = round(cvaw3_sum_V / cvaw3_count, 6)
            news.at[i, "CVAW3_Valence_Total"] = round(cvaw3_sum_V, 6)
            news.at[i, "CVAW3_Arousal_Avg"] = round(cvaw3_sum_A / cvaw3_count, 6)
            news.at[i, "CVAW3_Arousal_Total"] = round(cvaw3_sum_A, 6)
        else:
            news.at[i, "CVAW3_Valence_Avg"] = round(0, 6)
            news.at[i, "CVAW3_Valence_Total"] = round(cvaw3_sum_V, 6)
            news.at[i, "CVAW3_Arousal_Avg"] = round(0, 6)
            news.at[i, "CVAW3_Arousal_Total"] = round(cvaw3_sum_A, 6)

        if ntud_count > 0:
            news.at[i, "NTUD_Valence_Avg"] = ntud_sum_V / ntud_count
            news.at[i, "NTUD_Valence_Total"] = ntud_sum_V
            news.at[i, "NTUD_Valence_Percentage"] = (ntud_sum_V / ntud_count) * 100
        else:
            news.at[i, "NTUD_Valence_Avg"] = 0
            news.at[i, "NTUD_Valence_Total"] = ntud_sum_V
            news.at[i, "NTUD_Valence_Percentage"] = 0

        # Print result
        print(
            f"id: {news['id'][i]}, CVAW3_Valence_Avg: {news['CVAW3_Valence_Avg'][i]}, "
            f"CVAW3_Arousal_Avg: {news['CVAW3_Arousal_Avg'][i]}, NTUD_Valence_Total: {news['NTUD_Valence_Total'][i]}, "
            f"NTUD_Valence_Percentage: {news['NTUD_Valence_Percentage'][i]} %"
        )

    return news


# 更新Supabase中的對應欄位
def update_news_to_supabase(news):
    """Update the processed sentiment analysis back to Supabase."""
    for i in range(len(news)):
        supabase.table("news_content").update(
            {
                "arousal": news.at[i, "CVAW3_Arousal_Avg"],
                "emotion": news.at[i, "NTUD_Valence_Percentage"],
            }
        ).eq("id", news.at[i, "id"]).execute()


# Main function to handle the entire process
def get_sentiment_score(date, stocks):
    # Load all necessary data
    cvaw3, positive_words, negative_words = load_data_from_supabase()

    # Iterate over all stock IDs in the stocks dictionary
    for stock in stocks:
        stock_id = stock.get("stock_id")
        # stock_name = stock.get("stock_name")

        # Load news data for the specific stock and date
        news = load_news_data(date, stock_id)

        # Perform sentiment analysis
        news = analyze_sentiment(news, cvaw3, positive_words, negative_words)

        # Update news with sentiment scores back to Supabase
        update_news_to_supabase(news)

    print("正負情緒分數計算完成\n")


"""test
if __name__ == "__main__":
    # 測試日期和股票資料
    date = "2024-07-30"  # 你要測試的日期
    test_stocks = [
        {"stock_id": "3443", "stock_name": "創意"},
    ]

    try:
        get_sentiment_score(date, test_stocks)
        for stock in test_stocks:
            print(
                f"Sentiment analysis for stock ID {stock['stock_id']} on {date} completed."
            )
    except Exception as e:
        for stock in test_stocks:
            print(
                f"Error during sentiment analysis for stock {stock['stock_id']}: {str(e)}"
            )
"""

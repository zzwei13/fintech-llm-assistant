# cvaw3 + NTUD
import jieba
import jieba.analyse
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 從 Supabase 讀取cvaw3情感詞資料
response = supabase.table("cvaw3").select("*").execute()

if response.data:
    data = response.data
    cvaw3 = pd.DataFrame(data).set_index("Word")
    print("CVAW3 loaded")
else:
    # 打印更多的錯誤信息
    print(f"從 Supabase 獲取資料失敗: data={response.data}, count={response.count}")
    raise Exception("無法從 Supabase 獲取資料")


# 從 Supabase 讀取正面詞資料
pos_response = supabase.table("positive_word").select("*").execute()
if pos_response.data:
    positive_words = set(pd.DataFrame(pos_response.data)["text"])
    print("Positive words loaded")
else:
    print(
        f"從 Supabase 獲取資料失敗: data={pos_response.data}, count={pos_response.count}"
    )
    raise Exception("無法從 Supabase 獲取資料")

# 從 Supabase 讀取負面詞資料
neg_response = supabase.table("negative_word").select("*").execute()
if neg_response.data:
    negative_words = set(pd.DataFrame(neg_response.data)["text"])
    print("Negative words loaded")
else:
    print(
        f"從 Supabase 獲取資料失敗: data={neg_response.data}, count={neg_response.count}"
    )
    raise Exception("無法從 Supabase 獲取資料")

# Define the keyword for the news file
stock_id = "2330"  # Replace with your actual keyword

# Read news data from Supabasess
news_response = (
    supabase.table("news_test").select("*").eq("stockID", stock_id).execute()
)
if news_response.data:
    news_data = news_response.data
    news = pd.DataFrame(news_data)
else:
    print(
        f"從 Supabase 獲取資料失敗: data={news_response.data}, count={news_response.count}"
    )
    raise Exception("無法從 Supabase 獲取資料")

# Initialize columns for Valence and Arousal from CVAW3 and NTUD
news["CVAW3_Valence_Avg"] = float("nan")
news["CVAW3_Valence_Total"] = float("nan")
news["CVAW3_Arousal_Avg"] = float("nan")
news["CVAW3_Arousal_Total"] = float("nan")
news["NTUD_Valence_Avg"] = float("nan")
news["NTUD_Valence_Total"] = float("nan")
news["NTUD_Valence_Percentage"] = float("nan")  # For storing percentage values


# Compute Valence and Arousal values
for i in range(len(news["content"])):
    seg_list = jieba.cut(news["content"][i])  # 使用Jieba進行分詞，儲存分詞結果
    cvaw3_sum_V = 0  # CVAW3 情感價數的總和
    cvaw3_sum_A = 0  # CVAW3 喚起值的總和
    cvaw3_count = 0  # CVAW3 分詞後在詞彙庫中的詞彙數量

    ntud_sum_V = 0  # NTUD 情感價數的總和
    ntud_count = 0  # NTUD 分詞後在詞彙庫中的詞彙數量

    for w in seg_list:
        if w in cvaw3.index:
            cvaw3_sum_V += cvaw3["Valence_Mean"][w] - 5
            cvaw3_sum_A += cvaw3["Arousal_Mean"][w] - 5
            cvaw3_count += 1

        elif w in negative_words:
            ntud_sum_V -= 1  # Arbitrary adjustment for negative words
            ntud_count += 1
        elif w in positive_words:
            ntud_sum_V += 1  # Arbitrary adjustment for positive words
            ntud_count += 1

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
        # Calculate percentage for NTUD Valence
        news.at[i, "NTUD_Valence_Percentage"] = (ntud_sum_V / ntud_count) * 100
    else:
        news.at[i, "NTUD_Valence_Avg"] = 0
        news.at[i, "NTUD_Valence_Total"] = ntud_sum_V
        news.at[i, "NTUD_Valence_Percentage"] = 0

    # Print id and arousal of the news
    print(
        f"id: {news['id'][i]},CVAW3_Valence_Avg: {news['CVAW3_Valence_Avg'][i]}, CVAW3_Arousal_Avg: {news['CVAW3_Arousal_Avg'][i]}, NTUD_Valence_Total: {news['NTUD_Valence_Total'][i]}, NTUD_Valence_Percentage: {news['NTUD_Valence_Percentage'][i]} %"
    )

# 更新Supabase中的對應欄位
for i in range(len(news)):
    supabase.table("news_test").update(
        {
            "arousal": news.at[i, "CVAW3_Arousal_Avg"],
            "emotion": news.at[i, "NTUD_Valence_Percentage"],
        }
    ).eq("id", news.at[i, "id"]).execute()

"""
# Convert 'date' to datetime format
news["date"] = pd.to_datetime(news["date"])

# Create a date range from start to end date
date_range = pd.date_range(start="2024-01-01", end="2024-07-23", freq="D")
full_dates = pd.DataFrame({"date": date_range})

# Merge news data with the full date range
merged_data = pd.merge(full_dates, news, on="date", how="left")

# 绘制 'Valence_Avg' 随时间变化的图表
plt.figure(figsize=(12, 6))
plt.plot(
    merged_data["date"],
    merged_data["Valence_Avg"],
    label="Valence_Avg",
    color="orange",
)
plt.title("Valence Average Over Time")
plt.xlabel("Date")
plt.ylabel("Value")
plt.legend()
plt.show()
"""

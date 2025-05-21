import os
import jieba
import jieba.analyse
import re
import matplotlib.pyplot as plt
import pandas as pd

# 定義情感詞文件的完整路徑
base_dir = os.path.dirname(os.path.abspath(__file__))
positive_file_path = os.path.join(base_dir, "NTUSD_positive_unicode.txt")
negative_file_path = os.path.join(base_dir, "NTUSD_negative_unicode.txt")

# 載入和預處理 NTUSD 的正面和負面情感詞
def load_sentiment_words(file_path):
    encodings = ["utf-16", "utf-8", "utf-16-le", "utf-16-be"]
    for encoding in encodings:
        try:
            with open(file_path, encoding=encoding, mode="r") as f:
                lines = f.readlines()
            words = []
            for line in lines:
                clean_words = re.findall(r"\w+", line)
                words.extend(clean_words)
            return words
        except UnicodeError:
            print(f"Failed to decode {file_path} using {encoding}")
        except FileNotFoundError:
            print(f"Sentiment words file not found at: {file_path}")
            return []
    print(f"All encoding attempts failed for file: {file_path}")
    return []


# 載入正面和負面情感詞
positive_words = load_sentiment_words(positive_file_path)
negative_words = load_sentiment_words(negative_file_path)

# 設定股票代碼和名稱
stock_ids = ["2731"]
stock_names = ["雄獅"]
results = []

# 迭代處理每個股票代碼
for idx, stock_id in enumerate(stock_ids):
    # 換成相對路徑
    folderpath = os.path.join(base_dir, "stock_news", stock_id)

    # 檢查目錄是否存在
    if not os.path.exists(folderpath):
        print(f"Directory does not exist: {folderpath}")
        continue

    # 排序新聞文件
    sorted_news_files = sorted(os.listdir(folderpath))
    print("Sorted news files:", sorted_news_files)

    # 迭代處理每個子目錄
    for subdir in sorted_news_files:
        subdir_path = os.path.join(folderpath, subdir)
        if os.path.isdir(subdir_path):
            subdir_files = sorted(os.listdir(subdir_path))

            # 迭代處理每個新聞文件
            for file_name in subdir_files:
                date = file_name[-8:]  # 獲取文件名中的日期部分
                if date.startswith("2022") or date.startswith("2023"):
                    print(f"Stock&News: {subdir}, File: {file_name}, Date: {date}")
                    file_path = os.path.join(subdir_path, file_name)

                    try:
                        with open(file_path, encoding="utf-8") as file:
                            article = file.read()
                    except Exception as e:
                        print(f"Failed to read {file_path}: {e}")
                        continue

                    # 使用 jieba 分詞
                    jieba_result = list(jieba.cut(article, cut_all=False, HMM=True))

                    # 初始化計數
                    positive_count = 0
                    negative_count = 0
                    total_words = len(jieba_result)

                    # 分析情感
                    for word in jieba_result:
                        if word in positive_words:
                            positive_count += 1
                        elif word in negative_words:
                            negative_count += 1

                    # 計算情感分數百分比並四捨五入到兩位小數
                    if total_words > 0:
                        sentiment_weight = round(
                            (positive_count - negative_count) / total_words * 100, 2
                        )
                    else:
                        sentiment_weight = 0

                    # 存儲結果
                    results.append((date, sentiment_weight, article))

                    print(f"檔案: {file_path}, 總分: {sentiment_weight}")

# 定義保存 DataFrame 的相對路徑
output_dir = os.path.join(base_dir, "sentiment_data")
os.makedirs(output_dir, exist_ok=True)
output_file_path = os.path.join(output_dir, f"{stock_id}_sentiment_analysis_results.csv")

# 將結果轉換為 DataFrame
df = pd.DataFrame(results, columns=["Date", "Score(%)", "Article"])
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values(by="Date")

# 將 DataFrame 保存為 CSV 文件
df.to_csv(output_file_path, index=False, encoding="utf-8")

# 繪製結果圖表
plt.figure(figsize=(12, 5))
plt.plot(df["Date"], df["Score(%)"], marker="o", linestyle="-")
plt.xlabel("Date")
plt.ylabel("Sentiment Score")
plt.title("Sentiment Score Over Time")
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

# 定義保存圖表的相對路徑
save_path = os.path.join(base_dir, "sentiment_image")
os.makedirs(save_path, exist_ok=True)
plt.savefig(os.path.join(save_path, f"{stock_id}_sentiment_score_over_time.png"))

plt.show()

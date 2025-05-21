import asyncio
import os
import google.generativeai as genai
import settings
import csv

# 配置生成式 AI 模型
genai.configure(api_key=settings.api_key)

model = genai.GenerativeModel(
    "gemini-1.5-flash-001",
    generation_config=settings.generation_config,
    safety_settings=settings.safety_settings,
)
chat_model = model.start_chat(history=[])


def gemini_response(filepath, question):
    """
    filepath: string 檔案路徑
    question: string 問題指令

    return: string 回答
    """
    with open(filepath, "r", encoding="utf-8") as f:
        news = f.read()

    prompt = f"""
    以下是今天的新聞資訊。請根據這些資訊判斷一周內賣出是否可能獲利。請按照以下格式回答：

    1. 如果預測可以獲利，請回答：#好
    2. 如果預測不會獲利，請回答：#不好
    3. 如果資訊與股市無關，請回答：#無關

    請詳述您的理由。

    問題:
    {question}

    文章:
    {news}

    回答:
    """

    try:
        response = model.generate_content(prompt)
        print(prompt)
        return response.text.strip()
    except Exception as e:
        print(e)
        return "exception"


def response_to_signal(text):
    """
    text: string 回答訊息

    return: int 回答訊號
    """
    if "不好" in text:
        signal = -1
    elif "好" in text:
        signal = 1
    elif "無關" in text:
        signal = 0
    else:
        signal = None  # 處理未知情況
    return signal


async def chat():
    stock_ids = ["2731"]
    stock_names = ["雄獅"]
    results = []
    for idx, stock_id in enumerate(stock_ids):
        folderpath = os.path.join(
            os.path.dirname(os.path.abspath(os.getcwd())),
            "senior-project-main",
            "StockNewsCrawling",
            "stock_news",
            stock_id,
        )

        if not os.path.exists(folderpath):
            print(f"Directory does not exist: {folderpath}")
            continue

        write_folder = os.path.join("StockNewsCrawling", "news_grade", stock_id)
        if not os.path.exists(write_folder):
            os.makedirs(write_folder)
            print("建立資料夾 " + write_folder)

        sorted_news_files = sorted(os.listdir(folderpath))
        print("Sorted news files:", sorted_news_files)

        query = (
            f"請找出對{stock_id}{stock_names[idx]}股票的建議投資策略有影響的新聞資料"
        )
        signals = []

        for subdir in sorted_news_files:
            subdir_path = os.path.join(folderpath, subdir)
            if os.path.isdir(subdir_path):
                subdir_files = sorted(os.listdir(subdir_path))

                for file_name in subdir_files:
                    date = file_name[-8:]
                    if date.startswith("2022") or date.startswith("2023"):
                        print(f"Stock&News: {subdir},File: {file_name}, Date: {date}")
                        file_path = os.path.join(subdir_path, file_name)

                        ans = gemini_response(file_path, query)
                        print(ans)
                        sig = response_to_signal(ans)
                        if sig is None:
                            continue  # 跳過未知情況

                        if sig == 0:
                            os.remove(file_path)
                            print("成功刪除 #無關 資料" + file_path)
                        else:
                            signals.append([subdir, file_name, sig])
                            result = f"Stock&News: {subdir}, Date: {date}, Signal: {sig}\n,Answer: {ans}\n"
                            results.append(result)

                            with open(
                                os.path.join(write_folder, f"{subdir}_{date}.txt"),
                                "a",
                                encoding="UTF-8",
                            ) as f:
                                f.write(result)
                                print(
                                    "寫入 "
                                    + os.path.join(write_folder, f"{subdir}_{date}.txt")
                                )

        csv_file_path = os.path.join(write_folder, "signal.csv")
        with open(csv_file_path, "a", encoding="UTF-8", newline="") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerows(signals)
            print("寫入 " + csv_file_path)


asyncio.run(chat())

import asyncio
from datetime import datetime, timedelta
import google.generativeai as genai
from supabase import create_client, Client
from app.services import settings
import os

# 配置生成式 AI 模型
genai.configure(api_key=settings.api_key)

model = genai.GenerativeModel(
    "gemini-1.5-flash-001",
    generation_config=settings.generation_config,
    safety_settings=settings.safety_settings,
)
chat_model = model.start_chat(history=[])


# Supabase 資訊
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


def gemini_response(news, question):
    """
    filepath: string 檔案路徑
    question: string 問題指令

    return: string 回答
    """

    prompt = f"""
    以下是今天的新聞資訊。請根據這些資訊判斷一周內賣出是否可能獲利。請按照以下格式回答：

    1. 如果預測可以獲利，請回答：#好
    2. 如果預測不會獲利，請回答：#不好
    3. 如果資訊與股市無關，請回答：#無關

    請詳述您的理由，請用**理由**作為回答格式。

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


# 解析 AI 回應的文字
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


# title media date link article time
async def chat(date, stocks):

    end_date = datetime.strptime(date, "%Y-%m-%d")
    start_date = end_date - timedelta(days=30)

    results = []

    for stock in stocks:
        stock_id = stock.get("stock_id")
        stock_name = stock.get("stock_name")
        query = f"請找出對{stock_id}{stock_name}股票的建議投資策略有影響的新聞資料"
        signals = []

        # 從 Supabase 中提取數據
        response = (
            supabase.from_("news_content").select("*").eq("stockID", stock_id).execute()
        )
        news_data = response.data

        if not news_data:
            print(f"No news found for stockID: {stock_id}")
            continue

        for news in news_data:
            date_obj = news["date"]  # Directly using the date from the database

            # 確保 date_obj 是 date type
            if isinstance(date_obj, str):
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()

            if start_date.date() <= date_obj <= end_date.date():
                print(f"Stock&News: {stock_name}, Date: {date_obj}")

                ans = gemini_response(news["content"], query)
                print(ans)
                sig = response_to_signal(ans)

                if sig is None:
                    continue  # 跳過未知情況

                if sig == 0:
                    # 刪除該筆資料
                    supabase.from_("news_content").delete().eq(
                        "id",
                        news["id"],
                    ).execute()
                    print("Deleted #無關 資料")
                else:
                    """
                    # 更新 Supabase 中的數據
                    supabase.from_("news_content").update({"gemini_signal": sig}).eq(
                        "id", news["id"]
                    ).execute()"""
                    signals.append([stock_name, news["id"], sig])
                    result = f"Stock&News: {stock_name}\nDate: {date_obj}\nSignal: {sig}\nAnswer: {ans}\n"
                    results.append(result)
        print("gemini評分更新完成")


def get_gemini_response(date, stocks):
    return asyncio.run(chat(date, stocks))

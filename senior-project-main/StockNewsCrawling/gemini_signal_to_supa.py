import asyncio
from datetime import datetime
import google.generativeai as genai
from supabase import create_client, Client
import settings

# 配置生成式 AI 模型
genai.configure(api_key=settings.api_key)

model = genai.GenerativeModel(
    "gemini-1.5-flash-001",
    generation_config=settings.generation_config,
    safety_settings=settings.safety_settings,
)
chat_model = model.start_chat(history=[])


# Supabase 資訊
url = "https://ifdyheuivlbmhsbpuyqf.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlmZHloZXVpdmxibWhzYnB1eXFmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyMTMxMTU2OSwiZXhwIjoyMDM2ODg3NTY5fQ.c6DehH3cUJrjHa22_ps0w32xCLRhS5AAQUqc1sHqoI0"
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
async def chat(start_date, end_date, stock_id=None, keyword=None):
    # 確保至少 stock_id 或 keyword 其中一個有值
    if not stock_id and not keyword:
        raise ValueError("At least one of stock_id or keyword must be provided.")

    # 如果只有 keyword 沒有 stock_id，從 Supabase 查詢 stockID
    if not stock_id and keyword:
        stock_response = (
            supabase.from_("stock")
            .select("stockID")
            .eq("stock_name", keyword)
            .execute()
        )
        stock_data = stock_response.data

        if not stock_data or len(stock_data) == 0:
            raise ValueError(f"No stockID found for keyword: {keyword}")

        # 獲取 stockID
        stock_id = stock_data[0]["stockID"]

    # 如果只有 stock_id 沒有 keyword，從 Supabase 查詢 stock_name
    if not keyword and stock_id:
        stock_response = (
            supabase.from_("stock")
            .select("stock_name")
            .eq("stockID", stock_id)
            .execute()
        )
        stock_data = stock_response.data

        if not stock_data or len(stock_data) == 0:
            raise ValueError(f"No keyword (stock_name) found for stockID: {stock_id}")

        # 獲取 stock_name
        keyword = stock_data[0]["stock_name"]

    stocks = [{"stock_id": stock_id, "keyword": keyword}]
    results = []

    for stock in stocks:
        stock_id = stock["stock_id"]
        stock_name = stock["keyword"]
        query = f"請找出對{stock_id}{stock_name}股票的建議投資策略有影響的新聞資料"
        signals = []

        # 從 Supabase 中提取數據
        response = (
            supabase.from_("news_test").select("*").eq("stockID", stock_id).execute()
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

            if start_date <= date_obj <= end_date:
                print(f"Stock&News: {stock_name}, Date: {date_obj}")

                ans = gemini_response(news["content"], query)
                print(ans)
                sig = response_to_signal(ans)

                if sig is None:
                    continue  # 跳過未知情況

                # 更新 Supabase 中的數據
                supabase.from_("news_test").update({"gemini_signal": sig}).eq(
                    "id", news["id"]
                ).execute()

                if sig == 0:
                    # 刪除該筆資料
                    supabase.from_("news_test").delete().eq(
                        "id",
                        news["id"],
                    ).execute()
                    print("Deleted #無關 資料")
                else:
                    # 更新 Supabase 中的數據
                    supabase.from_("news_test").update({"gemini_signal": sig}).eq(
                        "id", news["id"]
                    ).execute()
                    signals.append([stock_name, news["id"], sig])
                    result = f"Stock&News: {stock_name}\nDate: {date_obj}\nSignal: {sig}\nAnswer: {ans}\n"
                    results.append(result)
        print("更新完成")


# 設定起始與結束日期
start_date = datetime.strptime("20240101", "%Y%m%d").date()
end_date = datetime.strptime("20240731", "%Y%m%d").date()
stock_id = "2330"
keyword = "台積電"
asyncio.run(chat(start_date, end_date, stock_id, keyword))

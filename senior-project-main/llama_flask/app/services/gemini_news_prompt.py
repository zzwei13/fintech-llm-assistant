"""
從 Supabase 中提取過去30天的新聞資料，生成摘要，
並使用生成式AI模型分析股市情況，最後將結果儲存到資料庫。

"""

import asyncio
from datetime import datetime, timedelta
import google.generativeai as genai
from supabase import create_client, Client
from app.services import settings

from app.services import settings

# import settings
import os
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import jieba  # 導入 jieba

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


# 中文分詞器與句子分割器
class ChineseTokenizer:
    def tokenize(self, text):
        return list(jieba.cut(text))  # 分詞

    def to_sentences(self, text):
        delimiters = ["。", "！", "？"]
        sentences = []
        start = 0
        for i, char in enumerate(text):
            if char in delimiters:
                sentences.append(text[start : i + 1].strip())
                start = i + 1
        if start < len(text):  # 如果還有剩餘的文本
            sentences.append(text[start:].strip())
        return sentences

    def to_words(self, text):
        return self.tokenize(text)  # 实现 to_words 方法，调用 tokenize 方法


# 使用 Sumy 生成新闻摘要
def summarize_text(news, tokenizer, word_limit=512):
    """
    使用 Sumy 的 LSA 方法来生成摘要，限制摘要字數
    :param news: string, 原始新闻
    :param word_limit: int, 摘要的字數限制
    :return: string, 摘要后的新闻
    """
    sentences = tokenizer.to_sentences(news)
    parser = PlaintextParser.from_string(" ".join(sentences), tokenizer)
    summarizer = LsaSummarizer()

    # 初步生成較多的句子
    preliminary_summary = summarizer(parser.document, 10)  # 先生成 10 個句子的摘要
    summary_text = " ".join(str(sentence) for sentence in preliminary_summary)

    # 根據字數限制進行裁剪
    if len(summary_text) > word_limit:
        summary_text = summary_text[:word_limit] + "..."

    return summary_text


# 過去30天的新聞"內容"
def gemini_response(news):
    """
    news: string 新聞資訊

    return: string 回答
    """
    prompt = f"""
    你是一個厲害的投資分析助理，會根據新聞資料來判斷股市情況。

    以下是過去30天的新聞資訊摘要。請根據這些資訊判斷今日賣出是否可能獲利。請按照以下格式回答：

    1. 如果預測可以獲利，請回答：#好
    2. 如果預測不會獲利，請回答：#不好
    3. 如果資訊與股市無關，請回答：#無關

    請詳述您的理由，並用 **理由** 作為回答格式。

    文章摘要:
    {news}

    回答:
    """

    try:
        # 這裡假設 model 有一個 generate_content 方法，返回的是包含 text 屬性的物件
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"發生錯誤: {e}")
        return "exception"


"""
def response_to_signal(text):
    
    #text: string 回答訊息

    #return: int 回答訊號
    if "不好" in text:
        signal = -1
    elif "好" in text:
        signal = 1
    elif "無關" in text:
        signal = 0
    else:
        signal = None  # 處理未知情況
    return signal
"""


# title media date link article time
async def chat(date, stocks):
    # 解析單一股票 ID 和名稱
    stock_id = stocks.get("stock_id")
    stock_name = stocks.get("stock_name")

    end_date = datetime.strptime(date, "%Y-%m-%d")
    start_date = end_date - timedelta(days=30)

    # 從 Supabase 中提取指定日期範圍內的數據
    response = (
        supabase.from_("news_content")
        .select("*")
        .eq("stockID", stock_id)
        .gte("date", start_date.strftime("%Y-%m-%d"))
        .lte("date", end_date.strftime("%Y-%m-%d"))
        .execute()
    )
    news_data = response.data

    if not news_data:
        print(f"No news found for stockID: {stock_id}")
        return

    # 收集30天內的新聞摘要
    news_summaries = []
    tokenizer = ChineseTokenizer()  # 初始化一次分詞器
    for news in news_data:
        # 對每篇新聞進行摘要處理
        summary = summarize_text(news["content"], tokenizer, word_limit=512)
        print(f"Summary for article dated {news['date']}:\n{summary}\n")
        news_summaries.append(summary)

    # 合併所有的摘要成一篇文章
    combined_summary = "\n".join(news_summaries)
    print(f"Combined Summary for {stock_name}:\n{combined_summary}\n")

    # 將合併後的摘要傳入 Gemini
    if combined_summary:
        ans = gemini_response(combined_summary)
        print(f"Gemini 回答: {ans}")
        # signal = response_to_signal(ans)

        # 將 stock_id、ans、date、combined_summary 寫入到 stock_news_summary_30 表中
        supabase.from_("stock_news_summary_30").insert(
            {
                "stockID": stock_id,
                # "gemini_signal": signal,
                "gemini_ans": ans,
                "date": end_date.strftime("%Y-%m-%d"),  # 插入處理日期
                "summary": combined_summary,
            }
        ).execute()

        # 結果格式化，方便後續輸出
        result_out = (
            f"Stock: {stock_name}\nSummary: {combined_summary}\nAnswer: {ans}\n"
        )
        return ans

    print("gemini 完成分析30天內相關新聞。")


# 封裝 async chat 函數
def get_gemini_30dnews_response(date, stocks):
    return asyncio.run(chat(date, stocks))


"""
def test_get_gemini_response():
    date = "2024-07-20"  # 使用當前日期
    stocks = {"stock_id": "2330", "stock_name": "台積電"}  # 改為字典

    get_gemini_30dnews_response(date, stocks)


#跳用測試函数
test_get_gemini_response()

"""

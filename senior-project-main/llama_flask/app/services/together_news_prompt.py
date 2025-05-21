import asyncio
from datetime import datetime, timedelta
from together import Together
from supabase import create_client, Client
from dotenv import load_dotenv

# Import other libraries
import os
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import jieba  # 导入 jieba
import re

# 載入環境變數
load_dotenv()

# Supabase client configuration
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Together API client
together_client = Together(api_key=os.environ.get("TOGETHER_API_KEY"))


# Chinese tokenizer
class ChineseTokenizer:
    def tokenize(self, text):
        return list(jieba.cut(text))  # 分词

    def to_sentences(self, text):
        delimiters = ["。", "！", "？"]
        sentences = []
        start = 0
        for i, char in enumerate(text):
            if char in delimiters:
                sentences.append(text[start : i + 1].strip())
                start = i + 1
        if start < len(text):  # 如果还有剩余的文本
            sentences.append(text[start:].strip())
        return sentences

    def to_words(self, text):
        return self.tokenize(text)  # 实现 to_words 方法，调用 tokenize 方法


# Summarize news using Sumy
def summarize_text(news, tokenizer, word_limit=512):
    """
    使用 Sumy 的 LSA 方法生成摘要，限制摘要字数
    :param news: string, 原始新闻
    :param word_limit: int, 摘要的字数限制
    :return: string, 摘要后的新闻
    """
    sentences = tokenizer.to_sentences(news)
    parser = PlaintextParser.from_string(" ".join(sentences), tokenizer)
    summarizer = LsaSummarizer()

    # 初步生成较多的句子
    preliminary_summary = summarizer(parser.document, 10)  # 先生成 10 个句子的摘要
    summary_text = " ".join(str(sentence) for sentence in preliminary_summary)

    # 根据字数限制进行裁剪
    if len(summary_text) > word_limit:
        summary_text = summary_text[:word_limit] + "..."

    return summary_text


# Generate a response using Together API
def together_response(news):
    """
    news: string 新闻信息
    return: string 回答
    """
    messages = [
        {
            "role": "system",
            "content": "你是一個厲害的投資分析助理，會根據新聞資料來判斷股市情況。",
        },
        {
            "role": "user",
            "content": f"""
        以下是過去30天的新聞資訊摘要。請根據這些資訊判斷今日賣出是否可能獲利。請按照以下格式回答：

        1. 如果預測可以獲利，請回答：#好
        2. 如果預測不會獲利，請回答：#不好
        3. 如果資訊與股市無關，請回答：#無關

        請詳述您的理由，並用 **理由** 作為回答格式。

        文章摘要:
        {news}
        """,
        },
    ]

    try:
        response = together_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )
        print("Together Response:", response)

        # 改为访问 message.content
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"发生错误: {e}")
        return "exception"


# Async chat function
async def chat(date, stocks):
    stock_id = stocks.get("stock_id")
    stock_name = stocks.get("stock_name")

    end_date = datetime.strptime(date, "%Y-%m-%d")
    start_date = end_date - timedelta(days=30)

    # Fetch data from Supabase
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
        return "No news data available."

    # Summarize news for the past 30 days
    news_summaries = []
    tokenizer = ChineseTokenizer()  # Initialize tokenizer
    news_by_date = {}  # 用於計算每天的新聞數量
    total_length = 0  # 記錄 summaries 的總字數

    for news in news_data:

        news_date = news["date"]
        # 檢查此日期的新聞數量是否達到 2 篇
        if news_by_date.get(news_date, 0) >= 2:
            continue  # 當天新聞數量已滿，跳過此新聞

        summary = summarize_text(news["content"], tokenizer, word_limit=512)
        print(f"Summary for article dated {news['date']}:\n{summary}\n")
        news_summaries.append(summary)

        total_length += len(summary)  # 累加每次新增的摘要字數
        if total_length > 7500:
            break

    combined_summary = "\n".join(news_summaries)
    print(f"Combined Summary for {stock_name}:\n{combined_summary}\n")

    # Send combined summary to Together API
    if combined_summary:
        ans = together_response(combined_summary)
        print(f"Together API Answer: {ans}")

        # Save results to the database
        supabase.from_("stock_news_summary_30").insert(
            {
                "stockID": stock_id,
                "gemini_ans": ans,
                "date": end_date.strftime("%Y-%m-%d"),
                "summary": combined_summary,
            }
        ).execute()

        result_out = (
            f"Stock: {stock_name}\nSummary: {combined_summary}\nAnswer: {ans}\n"
        )
        return ans

    print("Together 完成分析 30 天相關新闻。")


# Wrapper for the async chat function
def get_together_30dnews_response(date, stocks):
    return asyncio.run(chat(date, stocks))


"""
def test_get_gemini_response():
    date = "2024-07-20"  # 使用當前日期
    stocks = {"stock_id": "2330", "stock_name": "台積電"}  # 改為字典

    result = get_together_30dnews_response(date, stocks)
    print(result)


# 跳用測試函数
test_get_gemini_response()
"""

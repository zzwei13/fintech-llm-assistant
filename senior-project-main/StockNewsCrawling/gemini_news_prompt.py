import asyncio
from datetime import datetime, timedelta
import google.generativeai as genai
from supabase import create_client, Client
import settings
import os
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import jieba  # 导入 jieba

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
        return list(jieba.cut(text))  # 使用 jieba 進行中文分詞

    def to_sentences(self, text):
        # 使用常見的中文句子分隔符號來分割文本
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


# 中文分辭器与句子分割器
class ChineseTokenizer:
    def tokenize(self, text):
        return list(jieba.cut(text))  # 使用 jieba 進行中文分辭

    def to_sentences(self, text):
        # 使用常見的中文句子分隔符號来分割文本
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

    def to_words(self, sentence):
        # 使用 jieba 分词
        return list(jieba.cut(sentence))  # 返回分词后的列表


# 使用 Sumy 生成新闻摘要
def summarize_text(news, sentence_count=7):
    """
    使用 Sumy 的 LSA 方法来生成摘要
    :param news: string, 原始新闻
    :param sentence_count: int, 摘要的句子数量限制
    :return: string, 摘要后的新闻
    """
    tokenizer = ChineseTokenizer()  # 使用中文分词器
    sentences = tokenizer.to_sentences(news)  # 分割为句子
    parser = PlaintextParser.from_string(" ".join(sentences), tokenizer)
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, sentence_count)
    return " ".join(str(sentence) for sentence in summary)


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

        # 從 Supabase 中提取數據
        response = (
            supabase.from_("news_test").select("*").eq("stockID", stock_id).execute()
        )
        news_data = response.data

        if not news_data:
            print(f"No news found for stockID: {stock_id}")
            continue

        # 收集30天內的新聞摘要
        news_summaries = []
        for news in news_data:
            date_obj = news["date"]  # Directly using the date from the database

            # 確保 date_obj 是 date type
            if isinstance(date_obj, str):
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()

            if start_date.date() <= date_obj <= end_date.date():
                print(f"Processing stock: {stock_name}, Date: {date_obj}")

                # 對每篇新聞進行摘要處理
                summary = summarize_text(news["content"], sentence_count=7)
                print(
                    f"Summary for article dated {date_obj}:\n{summary}\n"
                )  # 打印每篇新闻的摘要
                news_summaries.append(summary)

        # 合併所有的摘要成一篇文章
        combined_summary = "\n".join(news_summaries)
        print(
            f"Combined Summary for {stock_name}:\n{combined_summary}\n"
        )  # 輸出合併後的摘要

        # 將合併後的摘要傳入 Gemini
        if combined_summary:
            ans = gemini_response(combined_summary)
            print(f"Gemini 回答: {ans}")
            signal = response_to_signal(ans)

            # 將 stock_id、ans、date、combined_summary 寫入到 stock_news_summary_30 table 中
            supabase.from_("stock_news_summary_30").insert(
                {
                    "stockID": stock_id,
                    "gemini_signal": signal,
                    "gemini_ans": ans,
                    "date": end_date.strftime("%Y-%m-%d"),  # 插入當前處理的日期
                    "summary": combined_summary,
                }
            ).execute()

            # for flask
            result = (
                f"Stock: {stock_name}\nSummary: {combined_summary}\nAnswer: {ans}\n"
            )
            results.append(result)

    print("gemini評分更新完成")


# 封裝 async chat 函數
def get_gemini_30dnews_response(date, stocks):
    return asyncio.run(chat(date, stocks))


"""test
def test_get_gemini_response():
    date = "2024-10-20"  # 使用当前日期
    stocks = [
        {"stock_id": "2330", "stock_name": "台積電"},
    ]

    get_gemini_30dnews_response(date, stocks)


# 跳用測試函数
test_get_gemini_response()
"""

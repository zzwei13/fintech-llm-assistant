import asyncio
from datetime import datetime, timedelta
from supabase import create_client, Client
from together import Together
import os
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import jieba
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# Supabase client configuration
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Together API client
together_client = Together(api_key=os.environ.get("TOGETHER_API_KEY3"))


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


# 使用 Sumy 生成新聞摘要
def summarize_text(news, tokenizer, word_limit=512):
    """
    使用 Sumy 的 LSA 方法来生成摘要，限制摘要字數
    :param news: string, 原始新闻
    :param word_limit: int, 摘要的字數限制
    :return: string, 摘要后的新闻
    """
    sentences = tokenizer.to_sentences(news)
    if not sentences:
        return ""  # 若無有效句子，直接返回空字符串
    parser = PlaintextParser.from_string(" ".join(sentences), tokenizer)
    summarizer = LsaSummarizer()

    # 初步生成較多的句子
    preliminary_summary = summarizer(parser.document, 10)  # 先生成 10 個句子的摘要
    summary_text = " ".join(str(sentence) for sentence in preliminary_summary)

    # 根據字數限制進行裁剪
    if len(summary_text) > word_limit:
        summary_text = summary_text[:word_limit] + "..."

    return summary_text


async def together_response(news, question):
    """
    使用 Together API 生成回應

    :param news: string 新聞內容
    :param question: string 問題指令
    :return: string AI 回應
    """

    messages = [
        {
            "role": "system",
            "content": (
                "以下是今天的新聞資訊。請根據這些資訊判斷一周內賣出是否可能獲利。請按照以下格式回答：\n\n"
                "1. 如果預測可以獲利，請回答：#好\n"
                "2. 如果預測不會獲利，請回答：#不好\n"
                "3. 如果資訊與股市無關，請回答：#無關\n\n"
                "請詳述您的理由，請用**理由**作為回答格式。\n"
            ),
        },
        {
            "role": "user",
            "content": f"問題:\n{question}\n\n文章:\n{news}\n\n回答:",
        },
    ]

    try:
        # 呼叫 Together API
        response = together_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()
        # print(f"Together Response Content:\n{content}")  # 指印內容
        return content
    except Exception as e:
        print(f"Error with Together API: {e}")
        return "exception"


def response_to_signal(text):
    """
    解析 AI 回應的文字以生成訊號

    :param text: string 回應文字
    :return: int 回應訊號
    """
    if "不好" in text:
        return -1
    elif "好" in text:
        return 1
    elif "無關" in text:
        return 0
    else:
        return None  # 處理未知情況


async def chat(date, stocks):
    """
    從 Together API 獲取新聞訊號並更新 Supabase

    :param date: string 日期
    :param stocks: list 股票列表

    """
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
            print(f"No valid news content found for stockID: {stock_id}")
            continue

        tokenizer = ChineseTokenizer()  # 初始化一次分詞器

        for news in news_data:
            date_obj = news["date"]

            # 確保 date_obj 是 date 型別
            if isinstance(date_obj, str):
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()

            if start_date.date() <= date_obj <= end_date.date():
                print(f"Stock&News: {stock_name}, Date: {date_obj}")

                # 先進行摘要
                summary = summarize_text(news["content"], tokenizer, word_limit=512)
                if not summary.strip():
                    print(f"Skipping news ID {news['id']} due to empty summary.")
                    continue

                print("summary: ", summary)
                ans = await together_response(summary, query)
                print("answer:", ans)
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
                    signals.append([stock_name, news["id"], sig])
                    result = f"Stock&News: {stock_name}\nDate: {date_obj}\nSignal: {sig}\nAnswer: {ans}\n"
                    results.append(result)

        print("\n無關新聞過濾完成。")


def get_together_response(date, stocks):
    asyncio.run(chat(date, stocks))


"""
# 示例日期
test_date = "2024-11-01"

# 示例股票数据
test_stocks = [
    {"stock_id": "1504", "stock_name": "東元"},
]

# 调用测试函数
get_together_response(test_date, test_stocks)
"""

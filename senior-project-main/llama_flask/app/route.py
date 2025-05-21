# 建立網頁的後端函數。
import re
from flask import (
    render_template,
    request,
    jsonify,
    Blueprint,
    Response,
    stream_with_context,
    session,
    redirect,
    url_for,
)
import app.services.llama_main_TogetherFlask as llama_main_TogetherFlask
import app.services.crawler_for_flask as crawler_for_flask  # 引入crawler_for_flask模塊
import app.services.gemini_signal_to_supa as gemini_signal_to_supa  # 引入gemini_signal模塊
import app.services.news_transformer as news_transformer
import app.services.gemini_news_prompt as gemini_news_prompt
import app.services.together_news_prompt as together_news_prompt
import app.services.together_filter as together_filter
from dotenv import load_dotenv
from supabase import create_client, Client
import os
from datetime import datetime
import time
import asyncio

# 加載環境變量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# 建立 Blueprint
app = Blueprint("app", __name__)

"""
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")  # 渲染出 html 檔，使用 render_template 函數
"""


@app.route("/")
def index():
    # 清空 session
    session.clear()
    # 從 session 獲取 sentiment_mean 和 result
    sentiment_mean = session.get("sentiment_mean")
    result = session.get("result")
    chart_filename = session.get("chart_filename")

    # 返回 index.html 並傳遞這些數據
    return render_template(
        "index.html",
        sentiment_mean=sentiment_mean,
        result=result,
        chart_filename=chart_filename,
    )


@app.route("/predict", methods=["POST"])
def predict():
    # 從請求中獲取 stock_data
    stock_data = request.form["stock_data"]
    stock_id = None
    stock_name = None

    # 檢查 stock_data 是否是四位數字
    if re.match(r"^\d{4}$", stock_data):
        stock_id = stock_data
    # 檢查 stock_data 是否是中文
    elif re.match(r"[\u4e00-\u9fff]+", stock_data):
        stock_name = stock_data
    else:
        return jsonify({"error": "Invalid stock data format"}), 400  # 返回錯誤訊息

    # 確保至少 stock_id 或 stock_name 其中一個有值
    if not stock_id and not stock_name:
        return (
            jsonify(
                {"error": "At least one of stock_id or stock_name must be provided."}
            ),
            400,
        )

    # 如果只有 stock_name 沒有 stock_id，從 Supabase 查詢 stockID
    if not stock_id and stock_name:
        stock_response = (
            supabase.from_("stock")
            .select("stockID")
            .eq("stock_name", stock_name)
            .execute()
        )
        stock_data = stock_response.data

        if not stock_data or len(stock_data) == 0:
            return (
                jsonify({"error": f"No stockID found for stock_name: {stock_name}"}),
                404,
            )

        # 獲取 stockID
        stock_id = stock_data[0]["stockID"]

    # 如果只有 stock_id 沒有 stock_name，從 Supabase 查詢 stock_name
    if not stock_name and stock_id:
        stock_response = (
            supabase.from_("stock")
            .select("stock_name")
            .eq("stockID", stock_id)
            .execute()
        )
        stock_data = stock_response.data

        if not stock_data or len(stock_data) == 0:
            return (
                jsonify({"error": f"No stock_name found for stockID: {stock_id}"}),
                404,
            )

        # 獲取 stock_name
        stock_name = stock_data[0]["stock_name"]

    # 構建 stocks 列表
    stocks = [{"stock_id": stock_id, "stock_name": stock_name}]
    # 輸出 stocks 列表
    print("Stocks list:", stocks)

    # 確保 stocks 列表不為空
    if not stocks:
        return jsonify({"error": "Stocks list cannot be empty."}), 400

    # (op.1)指定 date 為當日
    # date = datetime.today().strftime("%Y-%m-%d")
    # (op.2)自由指定 date
    date = datetime.today().strftime("%Y-%m-%d")
    print("Today Date:", date)

    # 日期放入 dates 列表
    dates = [date]  # 假設你需要處理的日期，這可以根據需求動態獲取

    # 獲取股票預測結果
    result = llama_main_TogetherFlask.get_stock_predictions(dates, stocks)

    # 刪除無關新聞，標記好、不好
    # gemini_score = gemini_signal_to_supa.get_gemini_response(date, stocks)
    # together_filter 刪除無關新聞
    together_filter.get_together_response(date, stocks)

    stocks = {"stock_id": stock_id, "stock_name": stock_name}  # 字典型態
    # 輸出 stocks 列表
    print("Stocks data:", stocks)

    # 30天的新聞summary+分析_together(llama)
    print("======together(llama)開始分析30天的新聞summary======")
    try:
        thirtydnews_response = together_news_prompt.get_together_30dnews_response(
            date, stocks
        )
        with open("together_output.log", "w", encoding="utf-8") as f:
            f.write(str(thirtydnews_response))
    except Exception as e:
        print(f"Failed to get thirty days news response. Error: {str(e)}")
        thirtydnews_response = "No data available."  # 設置默認值

    # 30天transformer情緒分數平均
    print("Starting sentiment analysis...")
    try:
        sentiment_mean, news_with_sentiment = asyncio.run(
            news_transformer.analyze_and_store_sentiments(date, stocks)
        )
        if sentiment_mean is None:
            raise ValueError("No valid sentiment data available.")
    except Exception as e:
        print(f"Sentiment analysis failed. Error: {str(e)}")
        sentiment_mean = None
        news_with_sentiment = []

    # 30天情緒趨勢圖表-> 生成 html
    print("準備產生圖表...")
    if news_with_sentiment:
        try:
            # 生成情绪趋势图表并保存为 HTML 文件
            chart_html = news_transformer.plot_sentiment_timeseries(news_with_sentiment)
            if chart_html is None:
                raise ValueError("Chart HTML generation failed.")

            # 設定 charts 資料夾路徑
            charts_dir = os.path.join(app.root_path, "static", "chart")

            # 檢查 charts 資料夾是否存在，若不存在則創建
            if not os.path.exists(charts_dir):
                os.makedirs(charts_dir)

            # 使用 f-string 格式化生成圖表的檔名
            chart_filename = f"sentiment_chart_{stocks['stock_id']}_{date}.html"

            # 保存圖表文件到 static/chart 資料夾
            with open(
                os.path.join(charts_dir, chart_filename), "w", encoding="utf-8"
            ) as f:
                f.write(chart_html)

        except Exception as e:
            print(f"Chart generation failed. Error: {str(e)}")
            chart_filename = None
    else:
        print("No sentiment data available for generating chart.")
        chart_filename = "No sentiment data for chart."

    # 保存結果到 session
    session["result"] = result if "result" in locals() else "No result available."
    session["chart_filename"] = (
        chart_filename if chart_filename is not None else "No chart available."
    )
    session["sentiment_mean"] = (
        sentiment_mean if sentiment_mean is not None else "No sentiment data available."
    )

    print("llama_result: ", session["result"])
    print("chart_filename: ", session["chart_filename"])
    print("sentiment_mean: ", session["sentiment_mean"])

    # 返回 JSON 格式的響應
    return jsonify(
        {
            "result": session["result"],
            "sentiment_mean": session["sentiment_mean"],
            "chart_filename": session["chart_filename"],
            "thirtydnews_response": thirtydnews_response,
        }
    )


@app.route("/sentiment-chart")
def sentiment_chart():
    # Fetch stored data from session
    chart_filename = session.get("chart_filename")

    # Read the HTML file contents
    if chart_filename and os.path.exists(chart_filename):
        return render_template("chart.html", chart_filename=chart_filename)
    else:
        return "Chart not available."


# 用來做前端的 SSE 股票分析跑馬燈
@app.route("/sse_stock_analysis")
def sse_stock_analysis():
    def generate_stock_data():
        # 模擬股票分析數據的逐步生成
        analysis_steps = [
            "Fetching stock data...",
            "Analyzing trends...",
            "Calculating metrics...",
            "Generating predictions...",
        ]
        for step in analysis_steps:
            yield f"data: {step}\n\n"  # SSE 格式
            time.sleep(1)  # 模擬延遲

        yield "data: 分析完成!\n\n"  # 最終消息

    return Response(
        stream_with_context(generate_stock_data()), content_type="text/event-stream"
    )


@app.route("/news", methods=["POST"])
def news():
    # Fetch stock ID from form data
    stock_data = request.form.get("stock_data")
    stock_id = None
    stock_name = None
    # if not stock_id:
    #     return jsonify({"error": "Stock ID is required"}), 400
    if re.match(r"[\u4e00-\u9fff]+", stock_data):
        stock_name = stock_data
    else:
        stock_id = stock_data

    # 如果只有 stock_name 沒有 stock_id，從 Supabase 查詢 stockID
    if not stock_id:
        stock_response = (
            supabase.from_("stock")
            .select("stockID")
            .eq("stock_name", stock_name)
            .execute()
        )
        stock_data = stock_response.data

        if not stock_data or len(stock_data) == 0:
            return (
                jsonify({"error": f"No stockID found for stock_name: {stock_name}"}),
                404,
            )

        # 獲取 stockID
        stock_id = stock_data[0]["stockID"]

    try:
        # Get stock name from Supabase
        stock_name = crawler_for_flask.get_stock_name(stock_id)

        if not stock_name:
            return jsonify({"error": f"Stock name for ID {stock_id} not found"}), 404

        # Fetch news from various sources
        news_ltn = crawler_for_flask.fetch_news_ltn(stock_id, stock_name)
        news_tvbs = crawler_for_flask.fetch_news_tvbs(stock_id, stock_name)
        news_cnye = crawler_for_flask.fetch_news_cnye(stock_id, stock_name)
        news_chinatime = crawler_for_flask.fetch_news_chinatime(stock_id, stock_name)

        # Log the fetched news data
        print("News data:", news_ltn, news_tvbs, news_cnye, news_chinatime)

        # Return news data as JSON response
        return jsonify(
            {
                "ltn": news_ltn,
                "tvbs": news_tvbs,
                "cnye": news_cnye,
                "chinatime": news_chinatime,
            }
        )

    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return jsonify({"error": "Failed to fetch news"}), 500

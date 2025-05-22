增強情緒分析與圖表生成的錯誤處理，防止應用程式崩潰

以下是此次修改的完整提交，包含 `analyze_and_store_sentiments()` 函數的修改部分，供團隊參考：

---

**提交訊息**：增強情緒分析與圖表生成的錯誤處理，防止應用程式崩潰

**修改檔案**：
1. `app/route.py`
2. `app/services/news_transformer.py`

---

### 修改摘要：

1. **為三十天新聞分析新增錯誤處理**：
    - 檔案：`app/route.py`
    - 函數：`predict()`
    - 修改說明：
        - 將 `together_news_prompt.get_together_30dnews_response()` 呼叫包裹在 `try...except` 區塊中，以處理新聞分析過程中可能發生的錯誤。
        - 如果分析失敗，將 `thirtydnews_response` 設定為默認訊息 `"No data available."`。

2. **增強情緒分析的錯誤處理**：
    - 檔案：`app/route.py`
    - 函數：`predict()`
    - 修改說明：
        - 將 `news_transformer.analyze_and_store_sentiments()` 包裹在 `try...except` 區塊中。
        - 如果情緒分析失敗或返回 `None`，則將 `sentiment_mean` 和 `news_with_sentiment` 設置為默認值（`None` 或空列表）。
        - 在繼續流程之前，新增檢查，確保 `sentiment_mean` 不為 `None`。

3. **防止圖表生成的錯誤**：
    - 檔案：`app/route.py`
    - 函數：`predict()`
    - 修改說明：
        - 增加條件檢查，確保 `news_with_sentiment` 包含數據後再嘗試生成圖表。
        - 將圖表生成（`news_transformer.plot_sentiment_timeseries()`）包裹在 `try...except` 區塊中。
        - 如果圖表生成失敗，則將 `chart_filename` 設置為 `None`。

4. **更新 Session 數據處理**：
    - 檔案：`app/route.py`
    - 函數：`predict()`
    - 修改說明：
        - 將 session 變數（`result`、`chart_filename`、`sentiment_mean`）設置為默認值，如果其相對應的操作失敗。
        - 這樣可以防止 `None` 值導致後續流程中的應用崩潰。

5. **增強 `analyze_and_store_sentiments()` 的錯誤處理與返回值檢查**：
    - 檔案：`app/services/news_transformer.py`
    - 函數：`analyze_and_store_sentiments()`
    - 修改說明：
        - 增加了檢查，確保在沒有情緒分析數據的情況下能正確返回。
        - 在執行更新或計算平均值之前，確保 `total_sentiment_score` 和 `count` 具有有效數據。
        - 在沒有有效情緒數據的情況下，返回 `None` 以便上層處理。

### 具體代碼修改：

- **三十天新聞分析部分** (`route.py`)：
    ```python
    try:
        thirtydnews_response = together_news_prompt.get_together_30dnews_response(date, stocks)
        with open("together_output.log", "w", encoding="utf-8") as f:
            f.write(str(thirtydnews_response))
    except Exception as e:
        print(f"Failed to get thirty days news response. Error: {str(e)}")
        thirtydnews_response = "No data available."
    ```

- **情緒分析部分** (`route.py`)：
    ```python
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
    ```

- **圖表生成部分** (`route.py`)：
    ```python
    if news_with_sentiment:
        try:
            chart_html = news_transformer.plot_sentiment_timeseries(news_with_sentiment)
            if chart_html is None:
                raise ValueError("Chart HTML generation failed.")
            
            charts_dir = os.path.join(app.root_path, "static", "chart")
            if not os.path.exists(charts_dir):
                os.makedirs(charts_dir)

            chart_filename = f"sentiment_chart_{stocks['stock_id']}_{date}.html"
            with open(os.path.join(charts_dir, chart_filename), "w", encoding="utf-8") as f:
                f.write(chart_html)
        except Exception as e:
            print(f"Chart generation failed. Error: {str(e)}")
            chart_filename = None
    else:
        print("No sentiment data available for generating chart.")
        chart_filename = None
    ```

- **Session 數據處理部分** (`route.py`)：
    ```python
    session["result"] = result if 'result' in locals() else "No result available."
    session["chart_filename"] = chart_filename if chart_filename else "No chart available."
    session["sentiment_mean"] = sentiment_mean if sentiment_mean is not None else "No sentiment data available."
    ```

- **`analyze_and_store_sentiments()` 修改部分** (`news_transformer.py`)：
    ```python
    async def analyze_and_store_sentiments(date, stock):
        stock_id = stock.get("stock_id")
        end_date = datetime.strptime(date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=30)

        print("date:", date)

        existing_summary = (
            supabase.from_("stock_news_summary_30")
            .select("transformer_mean")
            .eq("stockID", stock_id)
            .eq("date", date)
            .execute()
        )

        if existing_summary.data and existing_summary.data[0]["transformer_mean"] is not None:
            print(f"Data already exists for stockID {stock_id} on date {date}. Skipping...")
            return None, []  # 修改為返回 None, 以方便後續檢查

        response = (
            supabase.from_("news_test")
            .select("*")
            .gte("date", start_date)
            .lte("date", end_date)
            .eq("stockID", stock_id)
            .execute()
        )
        news_data = response.data

        if not news_data:
            print(f"No news data found for stock_id {stock_id} within the specified date range.")
            return None, []  # 修改為返回 None, 以方便後續檢查

        total_sentiment_score = 0
        count = 0
        new_with_sentiment = []

        for news in news_data:
            try:
                print(f"Processing news ID: {news['id']} for stock_id: {stock_id}")

                sentiment_result = bert_sentiment_analysis(news["content"])
                sentiment_score = sentiment_result["score"]

                total_sentiment_score += sentiment_score
                count += 1
                news["sentiment"] = sentiment_score
                new_with_sentiment.append(news)

            except Exception as e:
                print(f"Failed to process news ID {news['id']}. Error: {str(e)}")

        if count > 0:
            average_sentiment = total_sentiment_score / count

            if existing_summary.data:
                update_response = (
                    supabase.from_("stock_news_summary_30")
                    .update({"transformer_mean": average_sentiment, "count": count})
                    .eq("stockID", stock_id)
                    .eq("date", date)
                    .execute()
                )

                if update_response.data:
                    print(f"Updated transformer_mean and count for stockID {stock_id} on date {date}.")
                else:
                    print(f"Failed to update transformer_mean. Response: {update_response}")

            average_sentiment = round(average_sentiment, 4)
            return average_sentiment, new_with_sentiment
        else:
            print(f"No valid sentiment data found for stockID {stock_id} on date {date}.")
            return None, []  # 修改為返回 None, 以方便後續檢查
    ```



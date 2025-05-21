def generate_message_content(stock_id, bps_str, capital_str, roe_str, eps_str, GM_str, OPM_str, DBR_str, summary_str, stock_price, company_background, roa_str, per_str,bullish_threshold=15, bearish_threshold=15):
    return f'''Evaluate the share price of Taiwan Stock Exchange {stock_id} based on the following data:
*The following data is from left to right, with the year from the furthest to the most recent.
* BPS (book value per share) over the past 5 years: {bps_str}
* Capital over the past 5 years: {capital_str} * 100 million
* ROE (return on equity) over the past 5 years: {roe_str}(%)
* ROA (return on assets) over the past 5 years: {roa_str}(%)
* peratio (price to earnings ratio) over the past 5 years: {per_str}(%)
* EPS (earnings per share) over the past 5 years: {eps_str}

* Gross profit margin over the past 5 years: {GM_str}(%)
* OPM (Operating Margin) over the past 5 years: {OPM_str}(%)
*DBR (debt-to-asset ratio) over the past 5 years: {DBR_str}(%)
*Reference historical prices:
{summary_str}
* !!!Current price: {stock_price}

Provide additional background information about the company, industry, and market trends.

* Company background:
{company_background}

Assuming you are a stock analyst, please conduct a long-term (over 12 months) prediction analysis and answer the following questions (only answer the following questions, do not give recommendations or analysis):

1. Is the next one year bullish or bearish?
2. Based on the current price, is it recommended to buy?
3. Based on the current price, assuming the maximum loss of the stop loss strategy is {bearish_threshold}%, what is the recommended selling price?
4. What is the recommended holding period for this investment? (at least 12 months)
5. Suggested stop loss strategy? What are your criteria for triggering a sell order?
6. Please give specific reasons why you think it is bullish or bearish.

Evaluation criteria:

* A "bullish" market is defined as a stock price increase of at least {bullish_threshold}% over the next one year, but avoid being overly conservative; consider the potential for a stronger performance if indicators suggest growth.
* A "bearish" market is defined as a stock price decline of at least {bearish_threshold}% over the next one year, but ensure that a reasonable margin for error is accounted for, especially if the stock has stable fundamentals.
* If bullish, the selling price will usually be higher than the buying price, but aim for a balanced target that captures potential gains without excessive risk.
* If it is bearish, no need to answer question 2.3.4.5.
* It is recommended that the selling price should be the take profit price when bullish. If the former is bearish, you can skip it directly.

*When evaluating, focus on long-term potential growth trends such as market expansion, rising industry demand, and technological innovation, and maintain a moderately optimistic outlook when making predictions.

Answer according to the sample format without explanation.
Answer sample format:
1. Is the next one year bullish or bearish?: [bullish/bearish]
2. Based on the current price, is it recommended to buy?: [Yes/No/later]
3. Based on the current price, assuming the maximum loss of the stop loss strategy is {bearish_threshold}%, what is the recommended selling price?: [a integer] NTD
4. What is the recommended holding period for this investment?: [a integer] months
5. Suggested stop loss strategy? What are your criteria for triggering a sell order?: [strategy]
6. Please give specific reasons why you think it is bullish or bearish.: [reason]
'''
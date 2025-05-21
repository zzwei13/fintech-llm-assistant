import os
import pandas as pd
from supabase import create_client, Client
import datetime
import re  

# 初始化 supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def get_historical_prices(stock_symbol, start_date, end_date):
    # 從 supabase 抓 adj_price (調整後股價)
    response = supabase.table('daily_price').select('date, adj_price').eq('stockID', stock_symbol).gte('date', start_date).lte('date', end_date).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df['adj_price']
    else:
        return pd.Series(dtype='float64')  

def is_float(value):
    try:
        float(value.replace(',', ''))  # 移除逗號來處理數字格式
        return True
    except ValueError:
        return False

# analyze result 的 路徑
analyze_result_path = '../senior_project/llama_analyze/analyze result'
correct_count = 0  # CORRECT 的數量
total_count = 0  # 驗證總數

for stock_dir in os.listdir(analyze_result_path):
    try:
        stock_id = int(stock_dir)
        if 2000 <= stock_id <= 4000:  # 只處理股票代號在 xxxx 到 xxxx 之間的
            stock_symbol = stock_dir  
            print(stock_symbol)
            stock_folder_path = os.path.join(analyze_result_path, stock_dir)
            
            csv_file = os.path.join(stock_folder_path, f'output_{stock_symbol}.csv')
            
            # 檢查檔案是否存在
            if not os.path.isfile(csv_file):
                print(f"File not found: {csv_file}. Skipping...")
                continue
            
            data = pd.read_csv(csv_file)
            
            result_file_path = os.path.join(stock_folder_path, f'{stock_symbol}_results.txt')
            
            with open(result_file_path, 'w', encoding='utf-8') as result_file:
                for index, row in data.iterrows():
                    if pd.isna(row['Recommended holding period']):
                        result_file.write(f"Skipping entry {index} due to missing holding period.\n")
                        continue
                    # 清理中括弧
                    holding_period_str = re.sub(r'\[|\]', '', str(row['Recommended holding period']))
                    bullish_bearish = re.sub(r'\[|\]', '', str(row['Bullish/Bearish']))
                    recommended_selling_price = re.sub(r'\[|\]', '', str(row['Recommended selling price']))
                    recommend_buy_or_not = re.sub(r'\[|\]', '', str(row['Recommend buy or not']))
                    
                    if 'month' in holding_period_str: 
                        holding_period = int(holding_period_str.split()[0].split('-')[0])
                        result_file.write(f"股票代碼 : {stock_symbol} \n")
                        result_file.write(f"持有時間 : {holding_period} 個月\n")
                    else:
                        result_file.write(f"Skipping entry {index} due to invalid holding period format: {holding_period_str}\n")
                        continue

                    start_date = pd.Timestamp(row['Date'])  # 使用 CSV 中的日期作為開始日期
                    print("start : ", start_date)

                    # Calculate the three selling dates
                    sell_dates = [
                        start_date + pd.DateOffset(months=holding_period - 2),
                        start_date + pd.DateOffset(months=holding_period - 1),
                        start_date + pd.DateOffset(months=holding_period)
                    ]
                    print("sell_dates: ", sell_dates)

                    # Get historical prices up to the last sell date
                    historical_prices = get_historical_prices(stock_symbol, start_date, sell_dates[-1])

                    initial_price = historical_prices.loc[start_date] if start_date in historical_prices.index else None  # 當天股價
                    
                    result_file.write(f"開始日期 : {start_date}\n")
                    result_file.write(f"初始股價 : {initial_price}\n")
                    # Calculate profits for each sell
                    profits = []
                    percentage_profits= []
                    for i, sell_date in enumerate(sell_dates):
                        final_price = historical_prices.loc[sell_date] if sell_date in historical_prices.index else None
                        
                        if final_price is not None and initial_price is not None:
                            # 獲利
                            profit = final_price - initial_price 
                            profits.append(profit)
                            # 報酬率
                            percentage_profit = profit / initial_price
                            percentage_profits.append(percentage_profit)
                            result_file.write(f"賣出日期 {sell_date} : 獲利 {profit if profit is not None else 'N/A'} 報酬率 {percentage_profit if percentage_profit is not None else 'N/A' }\n")
                        else:
                            result_file.write(f"賣出日期 {sell_date} : 獲利 N/A\n")
                    
                    # Average profit across the three sell dates
                    if profits:
                        #平均獲利
                        average_profit = sum(profits) / len(profits)
                        #平均報酬率
                        average_percentage_profit = sum(percentage_profits) / len(percentage_profits) 
                    else:
                        average_profit = None
                        average_percentage_profit = None
                    
                    #result_file.write(f"第 {index+1} 筆驗證資料:\n")
                    result_file.write(f"看漲或看跌 : {bullish_bearish} \n")
                    #result_file.write(f"賣出日期 : {sell_dates}\n")
                    result_file.write(f"平均獲利 : {average_profit if average_profit is not None else 'N/A'}\n")
                    result_file.write(f"平均報酬率 : {average_percentage_profit if average_percentage_profit is not None else 'N/A'}\n")
                        
                    total_count += 1  # 總驗證數
                    if bullish_bearish.lower() == 'bullish':
                        if average_profit is not None and average_profit > 0:
                            result_file.write("=> CORRECT!\n")
                            correct_count += 1  
                        else:
                            result_file.write("=> INCORRECT!\n")
                    else:  # Bearish
                        if average_profit is not None and average_profit > 0:
                            result_file.write("=> INCORRECT!\n")
                        else:
                            result_file.write("=> CORRECT!\n")
                            correct_count += 1  

                    result_file.write("==============================\n")
    except ValueError:
        print(f"Skipping invalid directory name: {stock_dir}")

correct_percentage = (correct_count / total_count) * 100 if total_count > 0 else 0
print(f"\n總驗證數: {total_count}\n")
print(f"正確數: {correct_count}\n")
print(f"正確率: {correct_percentage:.2f}%\n")

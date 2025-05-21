import os
import pandas as pd
from supabase import create_client, Client
import datetime
import re  

# 初始化 Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def get_historical_prices(stock_symbol, start_date, end_date):
    # 抓調整後股價
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
        float(value.replace(',', ''))  # Remove commas to handle numeric format
        return True
    except ValueError:
        return False

# analyze result 的路徑
analyze_result_path = '../senior_project/llama_analyze/analyze result'
correct_count = 0  # 正確數
total_count = 0  # bullish + bearish 總數
bullish_count = 0  # bullish 總數

# Initialize variables for calculating total average return rate
total_average_percentage_profit = 0
valid_stock_count = 0
correct_stock_details = []  # To store details of correct stocks

for stock_dir in os.listdir(analyze_result_path):
    try:
        stock_id = int(stock_dir)
        if 1000 <= stock_id <= 4306:  # 驗證 股票代碼 xxxx ~ xxxx
            stock_symbol = stock_dir  
            print(stock_symbol)
            stock_folder_path = os.path.join(analyze_result_path, stock_dir)
            
            csv_file = os.path.join(stock_folder_path, f'output_{stock_symbol}.csv')
            
            # 檢查csv檔是否存在
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
                    
                    # 清除中括弧和 **
                    holding_period_str = re.sub(r'\[|\]|\*\*', '', str(row['Recommended holding period']))
                    bullish_bearish = re.sub(r'\[|\]|\*\*', '', str(row['Bullish/Bearish']))
                    recommended_selling_price = re.sub(r'\[|\]|\*\*', '', str(row['Recommended selling price']))
                    recommend_buy_or_not = re.sub(r'\[|\]|\*\*', '', str(row['Recommend buy or not']))

                    
                    # 計算總數 (bullish + bearish)
                    total_count += 1

                    # 若是看跌 跳過
                    if bullish_bearish.lower() == 'bearish':
                        result_file.write(f"'{stock_symbol} skip...BEARISH'\n")
                        result_file.write("==============================\n")
                        continue  # Skip to the next entry

                    # 計算 bullish 總數
                    bullish_count += 1

                    if 'month' in holding_period_str: 
                        holding_period = int(holding_period_str.split()[0].split('-')[0])
                        result_file.write(f"股票代碼 : {stock_symbol} \n")
                        result_file.write(f"持有時間 : {holding_period} 個月\n")
                    else:
                        result_file.write(f"Skipping entry {index} due to invalid holding period format: {holding_period_str}\n")
                        continue

                    start_date = pd.Timestamp(row['Date'])  # Use the date from the CSV as the start date
                    print("start : ", start_date)

                    # Calculate the holding period end date
                    end_date = start_date + pd.DateOffset(months=holding_period)

                    # Get historical prices up to the holding period end date
                    historical_prices = get_historical_prices(stock_symbol, start_date, end_date)

                    initial_price = historical_prices.loc[start_date] if start_date in historical_prices.index else None  # Initial price on the start date
                    
                    result_file.write(f"開始日期 : {start_date}\n")
                    result_file.write(f"初始股價 : {initial_price}\n")
                    
                    # 停利設在30%
                    target_price = initial_price * 1.3 if initial_price is not None else None
                    reached_stop_profit = False

                    if target_price is not None:
                        # Check daily prices within the holding period
                        for current_date in pd.date_range(start=start_date, end=end_date):
                            if current_date in historical_prices.index:
                                current_price = historical_prices.loc[current_date]
                                if current_price >= target_price:
                                    reached_stop_profit = True
                                    # 計算報酬率
                                    profit = current_price - initial_price  # 計算獲利
                                    percentage_profit = profit / initial_price  # 計算報酬率
                                    
                                    result_file.write(f"賣出日期 {current_date} 達到停利條件（股價超過 {target_price}），實際股價為 {current_price}。\n")
                                    print(f"達到停利條件: 日期 {current_date}, 股價 {current_price}, ")  # Print to console
                                    result_file.write(f"獲利 {profit}, 報酬率 {percentage_profit}\n")
                                    result_file.write("=> CORRECT!\n")
                                    result_file.write("==============================\n")

                                    # 將報酬率納入總報酬率計算
                                    total_average_percentage_profit += percentage_profit
                                    valid_stock_count += 1  # Count of valid stocks processed

                                    correct_count += 1  
                                    correct_stock_details.append((stock_symbol, start_date))  # Save the correct stock symbol and date
                                    break  # Stop further checking since stop profit was reached


                    if reached_stop_profit:
                        continue  # Skip to the next entry if stop profit was reached

                    
                    profits = [] #獲利
                    percentage_profits = [] #報酬率
                    
                    adjusted_sell_dates = [
                        start_date + pd.DateOffset(months=holding_period - 2),
                        start_date + pd.DateOffset(months=holding_period - 1),
                        end_date
                    ]

                    for i in range(len(adjusted_sell_dates)):
                        sell_date = adjusted_sell_dates[i]
                        final_price = historical_prices.loc[sell_date] if sell_date in historical_prices.index else None
                        
                        # 若賣出的當天獲利為空值 往前一天找
                        while final_price is None:
                            sell_date -= pd.DateOffset(days=1)  # Move back by one day
                            final_price = historical_prices.loc[sell_date] if sell_date in historical_prices.index else None
                            result_file.write(f"賣出日期 {sell_date + pd.DateOffset(days=1)} 的獲利為 N/A，將日期調回一天至 {sell_date}。\n")

                        # Calculate profit and percentage profit
                        profit = final_price - initial_price if initial_price is not None else None
                        percentage_profit = profit / initial_price if initial_price is not None else None

                        profits.append(profit)
                        percentage_profits.append(percentage_profit)

                        result_file.write(f"賣出日期 {sell_date} : 獲利 {profit if profit is not None else 'N/A'} 報酬率 {percentage_profit if percentage_profit is not None else 'N/A'}\n")

                    # Average profit and percentage profit calculation
                    if profits:
                        average_profit = sum(profits) / len(profits) #平均獲利
                        average_percentage_profit = sum(percentage_profits) / len(percentage_profits) #平均報酬
                        
                        # Add to total for overall average calculation
                        total_average_percentage_profit += average_percentage_profit
                        valid_stock_count += 1  # Count of valid stocks processed
                    else:
                        average_profit = None
                        average_percentage_profit = None
                    
                    result_file.write(f"看漲或看跌 : {bullish_bearish} \n")
                    result_file.write(f"平均獲利 : {average_profit if average_profit is not None else 'N/A'}\n")
                    result_file.write(f"平均報酬率 : {average_percentage_profit if average_percentage_profit is not None else 'N/A'}\n")
                    
                    # Check for "correct" condition if stop profit was not reached
                    correct_condition = False
                    if average_profit is not None and average_profit > 0:
                        correct_condition = True  # Correct if average profit is positive
                    
                    if correct_condition:
                        result_file.write("=> CORRECT!\n")
                        result_file.write("==============================\n")
                        correct_count += 1  
                        correct_stock_details.append((stock_symbol, start_date))  # Save the correct stock symbol and date
                    else:
                        result_file.write("=> NOT CORRECT!\n")
                        result_file.write("==============================\n")

    except Exception as e:
        print(f"Error processing stock {stock_symbol}: {e}")

correct_percentage = (correct_count / bullish_count) * 100 if total_count > 0 else 0
overall_average_return = (total_average_percentage_profit / valid_stock_count) * 100 if valid_stock_count > 0 else 0  # Overall average return in percentage
# Final summary
print(f"\n資料總數: {total_count}\n")
print(f"正確數量: {correct_count}\n")
print(f"bullish 數量: {bullish_count}\n")
print(f"正確率: {correct_percentage:.2f}%\n")
print(f"總報酬率: {overall_average_return:.2f}%\n") 

print("Correct stock symbols and dates:")
for symbol, date in correct_stock_details:
    print(f"股票代碼: {symbol}, 日期: {date}")
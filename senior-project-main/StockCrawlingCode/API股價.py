import yfinance as yf
import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Supabase 配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 获取股票数据
date = '2010-01-01'
# stocks = ['2330.TW', '3443.TW', '2002.TW', '2317.TW', '2731.TW']
stocks = ['3443.TW', '2002.TW', '2317.TW', '2731.TW']
# 创建一个空的 DataFrame 来存储股票数据
all_stock_data = pd.DataFrame()

for stock_no in stocks:
    stock = yf.Ticker(stock_no)
    stock_data = stock.history(start=date)
    
    # 检查 stock_data 是否为空或缺少数据
    if stock_data.empty or 'Close' not in stock_data.columns:
        print(f"Data for {stock_no} not found or possibly delisted.")
        stock_data = pd.DataFrame(index=pd.date_range(start=date, periods=1), columns=[stock_no])
    else:
        stock_data = stock_data[['Close']]  # 仅选择 'Close' 列
        stock_data.rename(columns={'Close': stock_no}, inplace=True)  # 重命名列为股票编号
    
    # 移除 datetime 索引中的时区信息
    stock_data.index = stock_data.index.tz_localize(None)
    
    # 合并数据
    if all_stock_data.empty:
        all_stock_data = stock_data
    else:
        all_stock_data = all_stock_data.join(stock_data, how='outer')

# 移除 datetime 索引中的时区信息
all_stock_data.index = all_stock_data.index.tz_localize(None)

# 重整数据格式
all_stock_data.reset_index(inplace=True)
all_stock_data = all_stock_data.melt(id_vars=['Date'], var_name='stockID', value_name='price')
all_stock_data.dropna(inplace=True)
all_stock_data['stockID'] = all_stock_data['stockID'].str.extract(r'(\d+)').astype(int)

# 将日期列转换为字符串格式
all_stock_data['Date'] = all_stock_data['Date'].astype(str)

# 重命名列以匹配数据库表结构
all_stock_data.rename(columns={'Date': 'date'}, inplace=True)

# 插入或更新数据到 Supabase
for record in all_stock_data.to_dict(orient='records'):
    # 检查记录是否已经存在
    existing_record = supabase.table('daily_price').select('*').eq('date', record['date']).eq('stockID', record['stockID']).execute()
    if existing_record.data:
        # 更新现有记录
        supabase.table('daily_price').update(record).eq('date', record['date']).eq('stockID', record['stockID']).execute()
    else:
        # 插入新记录
        supabase.table('daily_price').insert(record).execute()

print("Data inserted/updated successfully!")

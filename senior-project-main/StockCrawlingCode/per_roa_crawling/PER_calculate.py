# per爬下來是季度，此code將計算成年度並匯出新的csv
import pandas as pd

# 讀取CSV文件
df = pd.read_csv('PER_cleaned.csv')

# 提取 Year 的前兩位數字，創建 YearGroup 列
print(df['Year'].str[:2])
df['year'] = '20' + df['Year'].str[:2]

# 按照 StockID 和 YearGroup 分組，計算平均 PER
result = df.groupby(['StockID', 'year']).agg({'PER': 'mean'}).reset_index()

# 保存結果到新的CSV文件
result.to_csv('average_per.csv', index=False)

print("結果已經保存到 'average_per.csv'")

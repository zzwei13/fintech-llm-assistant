# 看要刪 空值 或 - 或 某些字串，自行註解掉來做使用
import pandas as pd

file_path = '____.csv'  # 要清除的檔案名稱
df = pd.read_csv(file_path)

# 刪除 'PER' 欄位是空值的資料
#df_cleaned = df.dropna(subset=['PER']) 

# 刪除 'PER' 欄位是 '-' 的資料
df_cleaned = df[df['PER'] != "-"]

# 刪除 'YEAR' 欄位中值為 '24Q1' 的資料
df_cleaned = df[df['year'] != '24Q1']

# 將清理後的資料儲存回一個新的 CSV 檔案
cleaned_file_path = 'PER_cleaned.csv'  # 修改為你想要儲存的檔案路徑
df_cleaned.to_csv(cleaned_file_path, index=False)

print("資料已成功清理並儲存到", cleaned_file_path)
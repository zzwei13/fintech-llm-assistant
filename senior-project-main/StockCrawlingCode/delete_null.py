import pandas as pd
import os

# 設定檔案目錄
directory = ""
output_directory = "C:/Github repository/senior-project/"  # 儲存修改後檔案的目錄

# 如果目錄不存在，創建一個新目錄
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# 取得目錄下所有 CSV 檔案
csv_files = [
    "year_bps.csv",
    "year_dbr.csv",
    "year_eps.csv",
    "year_gm.csv",
    "year_opm.csv",
    "year_roe.csv",
    "year_Share_capital.csv",
]

# 遍歷每個 CSV 檔案進行處理
for file_name in csv_files:
    file_path = os.path.join(directory, file_name)
    # 讀取 CSV 檔案
    df = pd.read_csv(file_path)

    # 替換單純的 "-" 為 NaN (空值)
    df.replace("-", pd.NA, inplace=True)

    # 刪除包含任何空值的行
    df.dropna(inplace=True)

    # 將處理後的資料保存為新的 CSV 檔案
    new_file_path = os.path.join(output_directory, file_name)
    df.to_csv(new_file_path, index=False)
    print(f"已處理並保存為: {new_file_path}")

print("所有檔案處理完成。")

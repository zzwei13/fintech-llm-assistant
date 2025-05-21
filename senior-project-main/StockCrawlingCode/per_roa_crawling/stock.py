#爬所有台股上市股票代碼與名稱
import requests
from bs4 import BeautifulSoup
import csv

# 目標網址
url = "https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=1&issuetype=1&industry_code=&Page=1&chklike=Y"

# 發送請求
response = requests.get(url)

# 解析 HTML
soup = BeautifulSoup(response.text, 'html.parser')

# 找到目標表格
table = soup.find('table', {'class': 'h4'})

# 提取表格中的所有行
rows = table.find_all('tr')[1:]  # 排除表頭

# 開啟 CSV 文件，準備寫入
with open('stock.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # 寫入欄位名稱
    writer.writerow(['stockID', 'stock_name'])

    # 循環提取每行的有價證券代號和名稱，並寫入 CSV
    for row in rows:
        columns = row.find_all('td')
        code = columns[2].text.strip()  # 有價證券代號
        name = columns[3].text.strip()  # 有價證券名稱
        writer.writerow([code, name])

print("資料已成功寫入 stock_data.csv")

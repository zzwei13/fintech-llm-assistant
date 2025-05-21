# StockNewsCrawling

此專案主要用於爬取不同新聞來源的股票相關新聞，並對其進行情緒分析。專案包含多個爬蟲程式及分析工具，可將資料匯入到資料庫中進行後續處理。

## 專案結構

- `crawler_chinatime_to_supa.py` - 爬取《中國時報》股票相關新聞並儲存到資料庫。
- `crawler_cnye_to_supa.py` - 爬取《中時電子報》股票相關新聞並儲存到資料庫。
- `crawler_Itn_to_supa.py` - 爬取《自由時報》股票相關新聞並儲存到資料庫。
- `crawler_tvbs_to_supa.py` - 爬取《TVBS》股票相關新聞並儲存到資料庫。
- `sentiment_analysis_to_supa.py` - 整合 CVAW3 與 NTUD 的情緒分析字典，對新聞進行情緒分析並將結果匯入資料庫。
- `gemini_signal_to_supa.py` - 進行股市信號分析的模型程式碼，將分析結果匯入資料庫。
- `settings.py` - 設定檔案，包含各種爬蟲與分析模型的配置選項。

## 安裝與使用

1. 請確保已安裝 Python 3.7 或更新版本。
2. 配置 `settings.py` 中的參數，設定資料庫連接資訊以及爬蟲相關的設定。

## 注意事項

- 爬蟲程式運行時可能會受到新聞網站的反爬蟲機制影響，建議適當調整抓取頻率。
- 在使用情緒分析模型時，請確保情緒字典的版本與模型相容。

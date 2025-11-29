# 台指期貨資料抓取工具 (TAIFEX Futures Data Fetcher)

抓取台灣期貨交易所 (TAIFEX) 的台指期貨行情資料，支援每日行情、歷史資料下載等功能。

## 安裝依賴

```bash
pip install requests pandas
```

## 快速開始

### 命令列使用

```bash
# 抓取今日台指期貨行情
python3 taifex_futures.py

# 抓取指定日期的行情
python3 taifex_futures.py --date 2024/11/22

# 抓取小型台指期貨 (MTX)
python3 taifex_futures.py --product MTX --date 2024/11/22

# 抓取最近 30 天歷史資料
python3 taifex_futures.py --historical --days 30

# 抓取三大法人籌碼
python3 taifex_futures.py --institutional --date 2024/11/22

# 儲存為 JSON 格式
python3 taifex_futures.py --date 2024/11/22 --output json

# 同時儲存 CSV 和 JSON
python3 taifex_futures.py --date 2024/11/22 --output both
```

### Python 程式碼使用

```python
from taifex_futures import TAIFEXFetcher

# 建立抓取器
fetcher = TAIFEXFetcher()

# 抓取每日行情
data = fetcher.fetch_daily_market(date="2024/11/22", product_id="TX")

# 顯示行情摘要
fetcher.print_market_summary(data)

# 取得近月合約
near_month = fetcher.get_near_month_contract(data)
print(f"近月收盤價: {near_month['收盤價']}")

# 抓取歷史資料
historical = fetcher.fetch_historical_data(product_id="TX", days=30)

# 儲存資料
fetcher.save_to_csv(data, "my_data.csv")
fetcher.save_to_json(data, "my_data.json")

# 抓取三大法人資料
institutional = fetcher.fetch_institutional_trading(date="2024/11/22")
print(f"外資淨部位: {institutional['外資']['淨部位']}")
```

## 支援的期貨商品

| 代碼 | 名稱 |
|------|------|
| TX   | 臺股期貨 |
| MTX  | 小型臺指期貨 |
| TE   | 電子期貨 |
| TF   | 金融期貨 |
| XIF  | 非金電期貨 |

## 資料欄位說明

### 每日行情資料

| 欄位 | 說明 |
|------|------|
| 日期 | 交易日期 |
| 商品代碼 | 期貨商品代碼 |
| 商品名稱 | 期貨商品名稱 |
| 契約月份 | 到期月份 (YYYYMM) |
| 開盤價 | 當日開盤價 |
| 最高價 | 當日最高價 |
| 最低價 | 當日最低價 |
| 收盤價 | 當日收盤價 |
| 漲跌 | 漲跌點數 |
| 漲跌% | 漲跌幅度 |
| 結算價 | 當日結算價 |
| 未平倉量 | 未沖銷契約數 |
| 最佳買價 | 最後最佳買價 |
| 最佳賣價 | 最後最佳賣價 |
| 歷史最高價 | 該契約歷史最高價 |
| 歷史最低價 | 該契約歷史最低價 |

### 三大法人資料

| 欄位 | 說明 |
|------|------|
| 外資 | 外資及陸資 |
| 投信 | 投信 |
| 自營商 | 自營商 |
| 多單 | 多方未平倉口數 |
| 空單 | 空方未平倉口數 |
| 淨部位 | 多空淨額 (多單 - 空單) |

## 命令列參數

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--date, -d` | 指定日期 (YYYY/MM/DD) | 今日 |
| `--product, -p` | 商品代碼 | TX |
| `--historical, -H` | 抓取歷史資料 | - |
| `--days` | 歷史資料天數 | 30 |
| `--institutional, -i` | 抓取三大法人資料 | - |
| `--output, -o` | 輸出格式 (csv/json/both) | csv |
| `--data-dir` | 資料儲存目錄 | ./taifex_data |

## 資料來源

- [台灣期貨交易所 TAIFEX](https://www.taifex.com.tw/)

## 注意事項

1. 資料僅供參考，投資決策請自行判斷
2. 避免頻繁抓取以免對伺服器造成負擔
3. 週末及國定假日無交易資料
4. 盤中時段資料可能尚未更新完整

## License

MIT License

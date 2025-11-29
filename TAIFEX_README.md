# 台指期貨資料擷取工具

這個腳本可以用來擷取台灣期貨交易所 (TAIFEX) 的台指期貨資料。

## 功能

- 擷取指定日期的台指期貨資料
- 擷取歷史區間資料
- 支援 JSON 和 CSV 輸出格式

## 安裝需求

```bash
pip install aiohttp
```

（專案已包含在 requirements.txt 中）

## 使用方法

### 1. 擷取今天的資料

```bash
python fetch_taifex_futures.py
```

### 2. 擷取指定日期的資料

```bash
python fetch_taifex_futures.py --date 20240101
```

### 3. 擷取歷史區間資料

```bash
python fetch_taifex_futures.py --start-date 20240101 --end-date 20240131
```

### 4. 指定輸出檔案和格式

```bash
# 輸出為 JSON
python fetch_taifex_futures.py --date 20240101 --output data.json --format json

# 輸出為 CSV
python fetch_taifex_futures.py --date 20240101 --output data.csv --format csv
```

## 輸出資料格式

每筆資料包含以下欄位：

- `date`: 日期
- `contract`: 契約代碼
- `expiry_month`: 到期月份
- `open`: 開盤價
- `high`: 最高價
- `low`: 最低價
- `close`: 收盤價
- `volume`: 成交量
- `open_interest`: 未平倉量

## 注意事項

1. TAIFEX 網站可能有存取限制，請適度控制請求頻率
2. 歷史資料擷取會自動在每次請求間加入 0.5 秒延遲
3. 如果遇到存取問題，可能需要調整請求標頭或使用其他資料來源

## 範例輸出

```json
[
  {
    "date": "20240101",
    "contract": "TX",
    "expiry_month": "202401",
    "open": 17500.0,
    "high": 17550.0,
    "low": 17480.0,
    "close": 17520.0,
    "volume": 50000,
    "open_interest": 300000
  }
]
```

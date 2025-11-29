#!/usr/bin/env python3
"""
台指期貨資料抓取工具 (TAIFEX Futures Data Fetcher)

抓取台灣期貨交易所 (TAIFEX) 的台指期貨行情資料
支援每日行情、歷史資料下載、三大法人籌碼等功能

Author: AI Assistant
"""

import csv
import json
import os
import re
import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# TAIFEX API URLs
TAIFEX_BASE_URL = "https://www.taifex.com.tw"
DAILY_MARKET_URL = f"{TAIFEX_BASE_URL}/cht/3/futDailyMarketReport"
DAILY_MARKET_CSV_URL = f"{TAIFEX_BASE_URL}/cht/3/dlFutDataDown"
FUTURES_CONTRACT_URL = f"{TAIFEX_BASE_URL}/cht/3/futContractsDate"
INSTITUTIONAL_URL = f"{TAIFEX_BASE_URL}/cht/3/futContractsDateDown"
OPEN_INTEREST_URL = f"{TAIFEX_BASE_URL}/cht/3/largeTraderFutQry"

# 期貨商品代碼
FUTURES_CODES = {
    "TX": "臺股期貨",
    "MTX": "小型臺指期貨", 
    "TE": "電子期貨",
    "TF": "金融期貨",
    "XIF": "非金電期貨",
}

# 預設資料儲存路徑
DEFAULT_DATA_DIR = Path("./taifex_data")


class TAIFEXFetcher:
    """台灣期貨交易所資料抓取器"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化抓取器
        
        Args:
            data_dir: 資料儲存目錄，預設為 ./taifex_data
        """
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        })
    
    def _parse_date(self, date_str: str) -> str:
        """
        解析日期字串，支援多種格式
        
        Args:
            date_str: 日期字串 (YYYY/MM/DD, YYYY-MM-DD, YYYYMMDD)
            
        Returns:
            標準化日期字串 YYYY/MM/DD
        """
        date_str = date_str.strip().replace("-", "/")
        if "/" not in date_str and len(date_str) == 8:
            date_str = f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"
        return date_str
    
    def _date_to_roc(self, date_str: str) -> str:
        """
        將西元年轉換為民國年
        
        Args:
            date_str: 西元日期 YYYY/MM/DD
            
        Returns:
            民國日期 YYY/MM/DD
        """
        parts = date_str.split("/")
        roc_year = int(parts[0]) - 1911
        return f"{roc_year}/{parts[1]}/{parts[2]}"
    
    def fetch_daily_market(self, date: str = None, product_id: str = "TX") -> List[Dict]:
        """
        抓取每日期貨行情資料
        
        Args:
            date: 日期 (YYYY/MM/DD 或 YYYY-MM-DD)，預設為今日
            product_id: 商品代碼，預設為 TX (臺股期貨)
            
        Returns:
            期貨行情資料列表
        """
        if date is None:
            date = datetime.now().strftime("%Y/%m/%d")
        else:
            date = self._parse_date(date)
        
        print(f"📊 抓取 {date} {product_id} 期貨行情資料...")
        
        # 使用網頁 HTML 解析方式
        params = {
            "queryType": "1",
            "marketCode": "0",
            "commodity_id": product_id,
            "queryDate": date,
        }
        
        try:
            self.session.headers.update({
                "Referer": DAILY_MARKET_URL,
            })
            response = self.session.get(DAILY_MARKET_URL, params=params, timeout=30)
            response.raise_for_status()
            response.encoding = "utf-8"
            
            # 解析 HTML 表格
            data = self._parse_daily_market_html(response.text, date, product_id)
            
            if data:
                print(f"✅ 成功抓取 {len(data)} 筆資料")
            else:
                print(f"⚠️ 無資料 (可能是假日或尚未開盤)")
                
            return data
            
        except requests.RequestException as e:
            print(f"❌ 抓取失敗: {e}")
            return []
    
    def _parse_daily_market_html(self, html: str, date: str, product_id: str) -> List[Dict]:
        """解析每日行情 HTML 表格"""
        data = []
        
        try:
            # 找到 table_f 表格
            table_match = re.search(r'<table[^>]*class="table_f[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL)
            if not table_match:
                return data
            
            table_html = table_match.group(1)
            
            # 找出所有 tr
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
            
            for row in rows:
                # 抓取 td 內容
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                # 清理 HTML 標籤
                cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                
                # 檢查是否為有效資料行 (第一欄應該是商品代碼，第二欄是契約月份)
                if len(cells) < 10:
                    continue
                
                # 跳過標題行
                if cells[0] == product_id or cells[0] in FUTURES_CODES:
                    try:
                        # 清理漲跌符號
                        change_str = cells[6].replace("▲", "").replace("▼", "-").replace(",", "")
                        change_pct_str = cells[7].replace("▲", "").replace("▼", "-").replace("%", "").replace(",", "")
                        
                        record = {
                            "日期": date,
                            "商品代碼": cells[0],
                            "商品名稱": FUTURES_CODES.get(cells[0], cells[0]),
                            "契約月份": cells[1],
                            "開盤價": self._safe_float(cells[2].replace(",", "")),
                            "最高價": self._safe_float(cells[3].replace(",", "")),
                            "最低價": self._safe_float(cells[4].replace(",", "")),
                            "收盤價": self._safe_float(cells[5].replace(",", "")),
                            "漲跌": self._safe_float(change_str),
                            "漲跌%": self._safe_float(change_pct_str),
                            "結算價": self._safe_float(cells[8].replace(",", "")),
                            "未平倉量": self._safe_int(cells[9].replace(",", "")),
                            "最佳買價": self._safe_float(cells[10].replace(",", "")) if len(cells) > 10 else None,
                            "最佳賣價": self._safe_float(cells[11].replace(",", "")) if len(cells) > 11 else None,
                            "歷史最高價": self._safe_float(cells[12].replace(",", "")) if len(cells) > 12 else None,
                            "歷史最低價": self._safe_float(cells[13].replace(",", "")) if len(cells) > 13 else None,
                        }
                        data.append(record)
                        
                    except (IndexError, ValueError) as e:
                        continue
                        
        except Exception as e:
            print(f"解析錯誤: {e}")
            
        return data
    
    def _safe_float(self, value: str) -> Optional[float]:
        """安全轉換為浮點數"""
        try:
            return float(value) if value else None
        except ValueError:
            return None
    
    def _safe_int(self, value: str) -> Optional[int]:
        """安全轉換為整數"""
        try:
            return int(value) if value else None
        except ValueError:
            return None
    
    def fetch_institutional_trading(self, date: str = None) -> Dict:
        """
        抓取三大法人期貨交易資訊
        
        Args:
            date: 日期 (YYYY/MM/DD)，預設為今日
            
        Returns:
            三大法人交易資訊
        """
        if date is None:
            date = datetime.now().strftime("%Y/%m/%d")
        else:
            date = self._parse_date(date)
        
        print(f"📈 抓取 {date} 三大法人期貨交易資訊...")
        
        # 使用 HTML 解析方式抓取三大法人資料
        url = f"{TAIFEX_BASE_URL}/cht/3/totalTableDate"
        
        params = {
            "queryDate": date,
        }
        
        try:
            self.session.headers.update({
                "Referer": url,
            })
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            response.encoding = "utf-8"
            
            data = self._parse_institutional_html(response.text, date)
            
            if data and any(data[k]["多單"] != 0 for k in ["外資", "投信", "自營商"]):
                print(f"✅ 成功抓取三大法人資料")
            else:
                print(f"⚠️ 無資料或解析失敗")
                
            return data
            
        except requests.RequestException as e:
            print(f"❌ 抓取失敗: {e}")
            return {}
    
    def _parse_institutional_html(self, html: str, date: str) -> Dict:
        """解析三大法人 HTML"""
        result = {
            "日期": date,
            "外資": {"多單": 0, "空單": 0, "淨部位": 0},
            "投信": {"多單": 0, "空單": 0, "淨部位": 0},
            "自營商": {"多單": 0, "空單": 0, "淨部位": 0},
        }
        
        try:
            # 尋找臺股期貨區塊的三大法人資料
            # 表格結構: 商品 | 身份 | 多方口數 | 多方金額 | 空方口數 | 空方金額 | 淨口數 | 淨金額
            
            # 找所有表格
            tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
            
            for table in tables:
                # 找包含臺股期貨的表格
                if '臺股期貨' not in table and '股價指數期貨' not in table:
                    continue
                
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
                
                for row in rows:
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                    cells = [re.sub(r'<[^>]+>', '', c).strip().replace(",", "").replace("\r", "").replace("\n", "") for c in cells]
                    
                    if len(cells) < 5:
                        continue
                    
                    # 檢查身份別
                    for i, cell in enumerate(cells):
                        if "外資" in cell or "外資及陸資" in cell:
                            if i + 2 < len(cells):
                                result["外資"]["多單"] = self._safe_int(cells[i+1]) or 0
                                result["外資"]["空單"] = self._safe_int(cells[i+3]) or 0 if i+3 < len(cells) else 0
                                result["外資"]["淨部位"] = result["外資"]["多單"] - result["外資"]["空單"]
                        elif "投信" in cell:
                            if i + 2 < len(cells):
                                result["投信"]["多單"] = self._safe_int(cells[i+1]) or 0
                                result["投信"]["空單"] = self._safe_int(cells[i+3]) or 0 if i+3 < len(cells) else 0
                                result["投信"]["淨部位"] = result["投信"]["多單"] - result["投信"]["空單"]
                        elif "自營商" in cell:
                            if i + 2 < len(cells):
                                result["自營商"]["多單"] = self._safe_int(cells[i+1]) or 0
                                result["自營商"]["空單"] = self._safe_int(cells[i+3]) or 0 if i+3 < len(cells) else 0
                                result["自營商"]["淨部位"] = result["自營商"]["多單"] - result["自營商"]["空單"]
                    
        except Exception as e:
            print(f"解析錯誤: {e}")
            
        return result
    
    def fetch_historical_data(
        self, 
        product_id: str = "TX",
        start_date: str = None,
        end_date: str = None,
        days: int = 30
    ) -> List[Dict]:
        """
        抓取歷史行情資料
        
        Args:
            product_id: 商品代碼
            start_date: 開始日期
            end_date: 結束日期
            days: 若未指定日期，抓取最近幾天的資料
            
        Returns:
            歷史行情資料列表
        """
        if end_date is None:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(self._parse_date(end_date).replace("/", "-"), "%Y-%m-%d")
            
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        else:
            start_date = datetime.strptime(self._parse_date(start_date).replace("/", "-"), "%Y-%m-%d")
        
        print(f"📅 抓取 {start_date.strftime('%Y/%m/%d')} ~ {end_date.strftime('%Y/%m/%d')} {product_id} 歷史資料...")
        
        all_data = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y/%m/%d")
            
            # 跳過週末
            if current_date.weekday() < 5:
                data = self.fetch_daily_market(date_str, product_id)
                all_data.extend(data)
                time.sleep(0.5)  # 避免請求過快
            
            current_date += timedelta(days=1)
        
        print(f"✅ 總共抓取 {len(all_data)} 筆歷史資料")
        return all_data
    
    def save_to_csv(self, data: List[Dict], filename: str = None) -> str:
        """
        將資料儲存為 CSV 檔案
        
        Args:
            data: 資料列表
            filename: 檔案名稱，預設自動產生
            
        Returns:
            儲存的檔案路徑
        """
        if not data:
            print("⚠️ 無資料可儲存")
            return ""
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"taifex_futures_{timestamp}.csv"
        
        filepath = self.data_dir / filename
        
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        print(f"💾 資料已儲存至 {filepath}")
        return str(filepath)
    
    def save_to_json(self, data: List[Dict], filename: str = None) -> str:
        """
        將資料儲存為 JSON 檔案
        
        Args:
            data: 資料列表
            filename: 檔案名稱，預設自動產生
            
        Returns:
            儲存的檔案路徑
        """
        if not data:
            print("⚠️ 無資料可儲存")
            return ""
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"taifex_futures_{timestamp}.json"
        
        filepath = self.data_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 資料已儲存至 {filepath}")
        return str(filepath)
    
    def get_near_month_contract(self, data: List[Dict]) -> Optional[Dict]:
        """
        取得近月合約資料
        
        Args:
            data: 行情資料列表
            
        Returns:
            近月合約資料
        """
        if not data:
            return None
            
        # 依契約月份排序，取最近的
        sorted_data = sorted(data, key=lambda x: x.get("契約月份", "999999"))
        return sorted_data[0] if sorted_data else None
    
    def print_market_summary(self, data: List[Dict]):
        """
        印出行情摘要
        
        Args:
            data: 行情資料列表
        """
        if not data:
            print("⚠️ 無資料可顯示")
            return
        
        near_month = self.get_near_month_contract(data)
        
        if near_month:
            print("\n" + "=" * 50)
            print(f"📊 {near_month['商品名稱']} ({near_month['商品代碼']}) 行情摘要")
            print("=" * 50)
            print(f"📅 日期: {near_month['日期']}")
            print(f"📋 契約月份: {near_month['契約月份']}")
            print(f"💰 開盤價: {near_month['開盤價']}")
            print(f"📈 最高價: {near_month['最高價']}")
            print(f"📉 最低價: {near_month['最低價']}")
            print(f"🏷️ 收盤價: {near_month['收盤價']}")
            
            change = near_month.get('漲跌', 0) or 0
            change_symbol = "🔺" if change > 0 else ("🔻" if change < 0 else "➖")
            print(f"{change_symbol} 漲跌: {change}")
            
            open_interest = near_month.get('未平倉量', 0) or 0
            print(f"📦 未平倉量: {open_interest:,}")
            print(f"💹 結算價: {near_month.get('結算價', 'N/A')}")
            print("=" * 50)


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description="台指期貨資料抓取工具")
    parser.add_argument("--date", "-d", help="指定日期 (YYYY/MM/DD)")
    parser.add_argument("--product", "-p", default="TX", help="商品代碼 (TX, MTX, TE, TF)")
    parser.add_argument("--historical", "-H", action="store_true", help="抓取歷史資料")
    parser.add_argument("--days", type=int, default=30, help="歷史資料天數")
    parser.add_argument("--institutional", "-i", action="store_true", help="抓取三大法人資料")
    parser.add_argument("--output", "-o", choices=["csv", "json", "both"], default="csv", help="輸出格式")
    parser.add_argument("--data-dir", help="資料儲存目錄")
    
    args = parser.parse_args()
    
    fetcher = TAIFEXFetcher(data_dir=args.data_dir)
    
    if args.institutional:
        # 抓取三大法人資料
        data = fetcher.fetch_institutional_trading(args.date)
        if data:
            print(f"\n📊 三大法人期貨交易資訊 ({data['日期']})")
            print("-" * 40)
            for name in ["外資", "投信", "自營商"]:
                info = data[name]
                net = info["淨部位"]
                symbol = "📈" if net > 0 else ("📉" if net < 0 else "➖")
                print(f"{name}: 多單 {info['多單']:,} | 空單 {info['空單']:,} | {symbol} 淨部位 {net:,}")
    
    elif args.historical:
        # 抓取歷史資料
        data = fetcher.fetch_historical_data(
            product_id=args.product,
            days=args.days
        )
        
        if data:
            if args.output in ["csv", "both"]:
                fetcher.save_to_csv(data)
            if args.output in ["json", "both"]:
                fetcher.save_to_json(data)
    
    else:
        # 抓取每日行情
        data = fetcher.fetch_daily_market(args.date, args.product)
        
        if data:
            fetcher.print_market_summary(data)
            
            if args.output in ["csv", "both"]:
                fetcher.save_to_csv(data)
            if args.output in ["json", "both"]:
                fetcher.save_to_json(data)


if __name__ == "__main__":
    main()

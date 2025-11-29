"""
台指期貨資料擷取腳本
Fetch Taiwan Stock Index Futures (TAIFEX) data
"""

import aiohttp
import asyncio
import json
import csv
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import os


class TAIFEXFuturesFetcher:
    """台指期貨資料擷取器"""
    
    def __init__(self):
        self.base_url = "https://www.taifex.com.tw"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_daily_data(self, date: Optional[str] = None) -> List[Dict]:
        """
        擷取指定日期的台指期貨資料
        
        Args:
            date: 日期字串，格式為 YYYYMMDD，如果為 None 則使用今天
        
        Returns:
            期貨資料列表
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        # TAIFEX 每日行情查詢 API
        url = f"{self.base_url}/cht/3/futDataDown"
        
        # 設定查詢參數
        params = {
            "down_type": "1",  # 1: 期貨, 2: 選擇權
            "commodity_id": "TX",  # TX: 台指期貨
            "dateaddcnt": "0",
            "queryDate": date
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    # TAIFEX 通常返回 CSV 格式
                    text = await response.text()
                    return self._parse_csv_data(text)
                else:
                    print(f"請求失敗，狀態碼: {response.status}")
                    return []
        except Exception as e:
            print(f"擷取資料時發生錯誤: {e}")
            return []
    
    def _parse_csv_data(self, csv_text: str) -> List[Dict]:
        """解析 CSV 格式的資料"""
        data = []
        lines = csv_text.strip().split('\n')
        
        # 跳過標題行，從資料行開始解析
        for line in lines[1:]:
            if not line.strip():
                continue
            
            # TAIFEX CSV 格式通常為: 日期,契約,到期月份,開盤,最高,最低,收盤,成交量等
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 7:
                try:
                    record = {
                        'date': parts[0],
                        'contract': parts[1],
                        'expiry_month': parts[2],
                        'open': float(parts[3]) if parts[3] else None,
                        'high': float(parts[4]) if parts[4] else None,
                        'low': float(parts[5]) if parts[5] else None,
                        'close': float(parts[6]) if parts[6] else None,
                        'volume': int(parts[7]) if len(parts) > 7 and parts[7] else 0,
                        'open_interest': int(parts[8]) if len(parts) > 8 and parts[8] else 0,
                    }
                    data.append(record)
                except (ValueError, IndexError) as e:
                    print(f"解析資料行時發生錯誤: {e}, 行內容: {line}")
                    continue
        
        return data
    
    async def fetch_historical_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        擷取歷史資料
        
        Args:
            start_date: 開始日期 YYYYMMDD
            end_date: 結束日期 YYYYMMDD
        
        Returns:
            歷史資料列表
        """
        all_data = []
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        
        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            print(f"正在擷取 {date_str} 的資料...")
            daily_data = await self.fetch_daily_data(date_str)
            all_data.extend(daily_data)
            current += timedelta(days=1)
            # 避免請求過於頻繁
            await asyncio.sleep(0.5)
        
        return all_data
    
    def save_to_json(self, data: List[Dict], filename: str):
        """儲存資料為 JSON 格式"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"資料已儲存至 {filename}")
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """儲存資料為 CSV 格式"""
        if not data:
            print("沒有資料可儲存")
            return
        
        fieldnames = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"資料已儲存至 {filename}")


async def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='擷取台指期貨資料')
    parser.add_argument('--date', type=str, help='指定日期 (YYYYMMDD)，預設為今天')
    parser.add_argument('--start-date', type=str, help='開始日期 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, help='結束日期 (YYYYMMDD)')
    parser.add_argument('--output', type=str, default='taifex_futures_data.json', 
                       help='輸出檔案名稱')
    parser.add_argument('--format', type=str, choices=['json', 'csv'], default='json',
                       help='輸出格式')
    
    args = parser.parse_args()
    
    async with TAIFEXFuturesFetcher() as fetcher:
        if args.start_date and args.end_date:
            # 擷取歷史資料
            data = await fetcher.fetch_historical_data(args.start_date, args.end_date)
        else:
            # 擷取單日資料
            data = await fetcher.fetch_daily_data(args.date)
        
        if data:
            if args.format == 'json':
                fetcher.save_to_json(data, args.output)
            else:
                # 將 .json 改為 .csv
                csv_filename = args.output.replace('.json', '.csv')
                fetcher.save_to_csv(data, csv_filename)
            
            print(f"\n成功擷取 {len(data)} 筆資料")
            if data:
                print("\n前 5 筆資料預覽:")
                for i, record in enumerate(data[:5], 1):
                    print(f"{i}. {record}")
        else:
            print("未擷取到任何資料")


if __name__ == '__main__':
    asyncio.run(main())

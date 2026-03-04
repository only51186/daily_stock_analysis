# -*- coding: utf-8 -*-
"""
===================================
OpenBB Data Source Test
===================================

[Purpose]
Verify OpenBB data source availability with multi-source fallback

[Usage]
python scripts/test_openbb_data.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_openbb_data_source():
    """Test OpenBB data source"""
    print("\n" + "=" * 60)
    print("Test 1: OpenBB Data Source")
    print("=" * 60)
    
    try:
        from openbb import obb
        
        print("Fetching stock data from OpenBB...")
        
        try:
            df = obb.equity.price.historical(
                "000001.SZ",
                provider="yfinance",
                start_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d')
            )
            
            if df is not None and not df.empty:
                print(f"SUCCESS: Fetched {len(df)} rows from OpenBB")
                print(f"Columns: {list(df.columns)}")
                return True, "OpenBB"
            else:
                print("WARNING: No data from OpenBB, trying fallback...")
                return False, "OpenBB"
        except Exception as e:
            print(f"WARNING: OpenBB fetch failed: {e}")
            return False, "OpenBB"
            
    except ImportError:
        print("FAILED: OpenBB not installed")
        return False, "OpenBB"


def test_tushare_data_source():
    """Test Tushare data source"""
    print("\n" + "=" * 60)
    print("Test 2: Tushare Data Source")
    print("=" * 60)
    
    try:
        import tushare as ts
        from dotenv import load_dotenv
        
        load_dotenv()
        token = os.getenv('TUSHARE_TOKEN')
        
        if not token:
            print("WARNING: TUSHARE_TOKEN not configured")
            return False, "Tushare"
        
        pro = ts.pro_api(token)
        
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        
        df = pro.daily(ts_code='000001.SZ', start_date=start_date, end_date=end_date)
        
        if df is not None and not df.empty:
            print(f"SUCCESS: Fetched {len(df)} rows from Tushare")
            print(f"Columns: {list(df.columns)}")
            return True, "Tushare"
        else:
            print("WARNING: No data from Tushare")
            return False, "Tushare"
            
    except Exception as e:
        print(f"WARNING: Tushare fetch failed: {e}")
        return False, "Tushare"


def test_akshare_data_source():
    """Test Akshare data source"""
    print("\n" + "=" * 60)
    print("Test 3: Akshare Data Source")
    print("=" * 60)
    
    try:
        import akshare as ak
        
        print("Fetching stock data from Akshare...")
        
        df = ak.stock_zh_a_hist(symbol="000001", period="daily", adjust="")
        
        if df is not None and not df.empty:
            print(f"SUCCESS: Fetched {len(df)} rows from Akshare")
            print(f"Columns: {list(df.columns)}")
            return True, "Akshare"
        else:
            print("WARNING: No data from Akshare")
            return False, "Akshare"
            
    except Exception as e:
        print(f"WARNING: Akshare fetch failed: {e}")
        return False, "Akshare"


def test_integrated_fetcher():
    """Test integrated OpenBB fetcher with fallback"""
    print("\n" + "=" * 60)
    print("Test 4: Integrated Data Fetcher (Multi-Source Fallback)")
    print("=" * 60)
    
    try:
        from src.openbb_data import get_openbb_stock_data
        
        print("Testing integrated data fetcher...")
        
        data, source = get_openbb_stock_data(
            symbol='000001.SZ',
            start_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d')
        )
        
        if data is not None and not data.empty:
            print(f"SUCCESS: Fetched {len(data)} rows from {source}")
            print(f"Columns: {list(data.columns)}")
            return True, source
        else:
            print("FAILED: No data from any source")
            return False, "None"
            
    except Exception as e:
        print(f"FAILED: Integrated fetcher test failed: {e}")
        return False, "Error"


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("OpenBB Data Source Availability Test")
    print("=" * 60)
    
    results = []
    
    success, source = test_openbb_data_source()
    results.append(("OpenBB", success, source))
    
    success, source = test_tushare_data_source()
    results.append(("Tushare", success, source))
    
    success, source = test_akshare_data_source()
    results.append(("Akshare", success, source))
    
    success, source = test_integrated_fetcher()
    results.append(("Integrated", success, source))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    available_sources = []
    for test_name, success, source in results:
        status = "AVAILABLE" if success else "UNAVAILABLE"
        print(f"  {test_name}: {status} (Source: {source})")
        if success:
            available_sources.append(source)
    
    print("\n" + "=" * 60)
    if available_sources:
        print(f"AVAILABLE DATA SOURCES: {', '.join(available_sources)}")
        print("DATA FETCH: OPERATIONAL")
    else:
        print("WARNING: No data sources available")
    print("=" * 60)
    
    return len(available_sources) > 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

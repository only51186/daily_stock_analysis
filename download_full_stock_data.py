# -*- coding: utf-8 -*-
"""
下载完整的沪深主板股票数据
"""

import sys
import os
import time
import akshare as ak
import pandas as pd
from datetime import datetime
from src.data.data_manager import DataManager

class FullStockDataDownloader:
    """完整股票数据下载器"""
    
    def __init__(self):
        self.dm = DataManager()
        self.stock_list_file = os.path.join(os.path.dirname(__file__), 'data', 'stock_list.csv')
        
    def download_full_data(self):
        """下载完整股票数据"""
        print("=" * 80)
        print("开始下载完整的沪深主板股票数据")
        print("=" * 80)
        
        # 1. 读取股票列表
        print("\n1. 读取股票列表...")
        stock_list = self._read_stock_list()
        
        if stock_list.empty:
            print("❌ 无法读取股票列表")
            return False
        
        print(f"   股票列表: {len(stock_list)} 只")
        
        # 2. 清空现有数据
        print("\n2. 清空现有数据...")
        self._clear_existing_data()
        
        # 3. 分批下载股票数据
        print("\n3. 分批下载股票数据...")
        all_stock_data = []
        
        # 分批处理，避免请求过多
        batch_size = 100
        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(stock_list))
            batch_stocks = stock_list.iloc[start_idx:end_idx]
            
            print(f"   下载批次 {batch_num + 1}/{total_batches}: {start_idx+1}-{end_idx}")
            
            batch_data = self._download_batch_data(batch_stocks)
            if not batch_data.empty:
                all_stock_data.append(batch_data)
            
            # 添加延迟，避免请求过快
            time.sleep(1)
        
        if not all_stock_data:
            print("❌ 没有下载到任何数据")
            return False
        
        # 合并所有数据
        full_data = pd.concat(all_stock_data, ignore_index=True)
        print(f"   合并数据: {len(full_data)} 只股票")
        
        # 4. 处理日K数据
        print("\n4. 处理日K数据...")
        processed_data = self._process_daily_k_data(full_data)
        
        # 5. 保存到数据库
        print("\n5. 保存到数据库...")
        success = self._save_to_database(processed_data)
        
        # 6. 保存到CSV备份
        print("\n6. 保存到CSV备份...")
        self._save_to_csv_backup(processed_data)
        
        return success
    
    def _read_stock_list(self):
        """读取股票列表"""
        try:
            if os.path.exists(self.stock_list_file):
                stock_list = pd.read_csv(self.stock_list_file)
                print(f"   从文件读取: {len(stock_list)} 只股票")
                return stock_list
            else:
                # 如果没有文件，重新获取
                print("   重新获取股票列表...")
                stock_info = ak.stock_info_a_code_name()
                main_board = stock_info[stock_info['code'].str.startswith(('60', '00'))]
                
                # 保存股票列表
                os.makedirs(os.path.dirname(self.stock_list_file), exist_ok=True)
                main_board.to_csv(self.stock_list_file, index=False, encoding='utf-8-sig')
                
                print(f"   重新获取: {len(main_board)} 只股票")
                return main_board
                
        except Exception as e:
            print(f"❌ 读取股票列表失败: {e}")
            return pd.DataFrame()
    
    def _clear_existing_data(self):
        """清空现有数据"""
        try:
            self.dm.connect()
            cursor = self.dm.conn.cursor()
            
            tables = ['stock_daily', 'factor_data', 'selection_results', 'backtest_results', 'review_data']
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
                print(f"   清空表: {table}")
            
            self.dm.conn.commit()
            
            # 删除CSV缓存文件
            cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'cache')
            if os.path.exists(cache_dir):
                for file in os.listdir(cache_dir):
                    if file.endswith('.csv'):
                        os.remove(os.path.join(cache_dir, file))
                        print(f"   删除缓存文件: {file}")
                        
        except Exception as e:
            print(f"❌ 清空数据失败: {e}")
    
    def _download_batch_data(self, batch_stocks):
        """分批下载股票数据"""
        try:
            # 使用实时行情接口
            stock_zh_a_spot_df = ak.stock_zh_a_spot()
            
            if stock_zh_a_spot_df.empty:
                print("   实时行情数据为空")
                return pd.DataFrame()
            
            # 标准化列名
            column_mapping = {
                'symbol': 'code',
                'name': 'name',
                'trade': 'close',
                'settlement': 'pre_close',
                'changepercent': 'pct_chg',
                'change': 'change',
                'volume': 'volume',
                'amount': 'amount',
                'turnoverratio': 'turnover',
                'amplitude': 'amplitude',
                'high': 'high',
                'low': 'low',
                'open': 'open',
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in stock_zh_a_spot_df.columns:
                    stock_zh_a_spot_df[new_col] = stock_zh_a_spot_df[old_col]
            
            # 添加日期列
            stock_zh_a_spot_df['date'] = datetime.now().strftime('%Y-%m-%d')
            
            # 筛选主板股票
            batch_codes = batch_stocks['code'].tolist()
            filtered_data = stock_zh_a_spot_df[stock_zh_a_spot_df['code'].isin(batch_codes)]
            
            print(f"   下载成功: {len(filtered_data)} 只")
            return filtered_data
            
        except Exception as e:
            print(f"❌ 下载批次数据失败: {e}")
            return pd.DataFrame()
    
    def _process_daily_k_data(self, stock_data):
        """处理日K数据"""
        if stock_data.empty:
            return pd.DataFrame()
        
        print("   处理日K数据...")
        
        # 确保数值类型正确
        numeric_columns = ['open', 'high', 'low', 'close', 'pre_close', 
                         'change', 'pct_chg', 'volume', 'amount', 
                         'turnover', 'volume_ratio', 'amplitude']
        
        for col in numeric_columns:
            if col in stock_data.columns:
                stock_data[col] = pd.to_numeric(stock_data[col], errors='coerce')
        
        # 计算流通市值（估算）
        if 'amount' in stock_data.columns and 'turnover' in stock_data.columns:
            # 流通市值 = 成交额 / 换手率
            stock_data['circ_mv'] = stock_data['amount'] / (stock_data['turnover'] / 100)
            stock_data['circ_mv'] = stock_data['circ_mv'].fillna(0)
        
        # 计算总市值（估算为流通市值的1.5倍）
        if 'circ_mv' in stock_data.columns:
            stock_data['total_mv'] = stock_data['circ_mv'] * 1.5
        
        print(f"   处理完成: {len(stock_data)} 只股票")
        
        return stock_data
    
    def _save_to_database(self, processed_data):
        """保存到数据库"""
        if processed_data.empty:
            print("❌ 没有数据需要保存")
            return False
        
        try:
            # 保存股票日线数据
            result = self.dm.save_stock_daily(processed_data)
            
            if result['success']:
                print(f"✅ 数据库保存成功: {result['count']} 条记录")
                return True
            else:
                print(f"❌ 数据库保存失败: {result['message']}")
                return False
                
        except Exception as e:
            print(f"❌ 数据库保存异常: {e}")
            return False
    
    def _save_to_csv_backup(self, processed_data):
        """保存到CSV备份"""
        if processed_data.empty:
            return
        
        try:
            # 创建备份目录
            backup_dir = os.path.join(os.path.dirname(__file__), 'data', 'backup')
            os.makedirs(backup_dir, exist_ok=True)
            
            # 保存文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'full_stock_data_{timestamp}.csv'
            filepath = os.path.join(backup_dir, filename)
            
            # 保存数据
            processed_data.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            print(f"✅ CSV备份保存成功: {filepath}")
            
        except Exception as e:
            print(f"❌ CSV备份保存失败: {e}")
    
    def verify_download(self):
        """验证下载结果"""
        print("\n" + "=" * 80)
        print("验证下载结果")
        print("=" * 80)
        
        # 检查数据库数据
        data = self.dm.get_stock_daily()
        
        if data.empty:
            print("❌ 数据库中没有数据")
            return False
        
        print(f"✅ 数据库数据量: {len(data)} 条")
        print(f"📅 最新数据日期: {data['date'].iloc[0]}")
        
        # 分类统计
        print("\n📊 数据分类统计:")
        
        main_board = data[data['code'].str.startswith(('60', '00'), na=False)]
        gem_board = data[data['code'].str.startswith('30', na=False)]
        star_board = data[data['code'].str.startswith('68', na=False)]
        
        print(f"   沪深主板A股: {len(main_board)} 只")
        print(f"   创业板: {len(gem_board)} 只")
        print(f"   科创板: {len(star_board)} 只")
        
        # 检查数据质量
        print("\n📈 数据质量检查:")
        
        if 'turnover' in data.columns:
            valid_turnover = data['turnover'].notna().sum()
            print(f"   有效换手率数据: {valid_turnover}/{len(data)}")
        
        if 'volume_ratio' in data.columns:
            valid_volume_ratio = data['volume_ratio'].notna().sum()
            print(f"   有效量比数据: {valid_volume_ratio}/{len(data)}")
        
        if 'circ_mv' in data.columns:
            valid_circ_mv = data['circ_mv'].notna().sum()
            print(f"   有效流通市值: {valid_circ_mv}/{len(data)}")
        
        # 显示前10只股票
        print("\n📋 前10只股票详情:")
        for i, (_, stock) in enumerate(data.head(10).iterrows(), 1):
            print(f"   {i}. {stock['code']} {stock.get('name', 'N/A')} "
                  f"涨幅: {stock.get('pct_chg', 0):.2f}% "
                  f"换手: {stock.get('turnover', 0):.2f}% "
                  f"量比: {stock.get('volume_ratio', 0):.2f}")
        
        return True

def main():
    """主函数"""
    print("开始下载完整的沪深主板股票数据...")
    print(f"下载时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    downloader = FullStockDataDownloader()
    
    # 下载数据
    success = downloader.download_full_data()
    
    if success:
        # 验证结果
        verification = downloader.verify_download()
        
        if verification:
            print("\n🎉 完整股票数据下载成功！")
            print("✅ 沪深主板股票数据已更新")
            print("✅ 日K数据已处理并保存")
            print("✅ 数据库和CSV备份已更新")
        else:
            print("\n⚠️ 数据下载完成但验证失败")
    else:
        print("\n❌ 数据下载失败")

if __name__ == "__main__":
    main()
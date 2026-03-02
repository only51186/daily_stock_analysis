import argparse
import requests
import json
import logging
import os
import pandas as pd
from datetime import datetime
import random

# ====================== 1. 日志配置 ======================
def setup_logger():
    """配置日志系统"""
    # 创建logs目录
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 主日志
    main_logger = logging.getLogger('stock_analysis')
    main_logger.setLevel(logging.INFO)
    main_handler = logging.FileHandler(f'logs/stock_analysis_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    main_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    main_logger.addHandler(main_handler)
    
    # 调试日志
    debug_logger = logging.getLogger('stock_analysis_debug')
    debug_logger.setLevel(logging.DEBUG)
    debug_handler = logging.FileHandler(f'logs/stock_analysis_debug_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    debug_handler.setFormatter(logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'))
    debug_logger.addHandler(debug_handler)
    
    return main_logger, debug_logger

# 初始化日志
logger, debug_logger = setup_logger()

# ====================== 2. 股票数据获取 ======================
def get_stock_info(stock_code):
    """获取股票基本信息和行情数据"""
    try:
        # 东方财富接口（兼容指数/板块/个股）
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={get_secid(stock_code)}&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f27,f28,f30,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data['data']:
            stock_data = {
                'code': stock_code,
                'name': data['data']['f14'],
                'price': data['data']['f2'],          # 当前价
                'change': data['data']['f3'],        # 涨跌幅(%)
                'change_amount': data['data']['f4'], # 涨跌额
                'volume': data['data']['f5'],        # 成交量
                'turnover': data['data']['f6'],      # 成交额
                'open': data['data']['f7'],          # 开盘价
                'high': data['data']['f8'],          # 最高价
                'low': data['data']['f9'],           # 最低价
                'prev_close': data['data']['f10'],   # 昨收价
                'market_cap': data['data']['f20'],   # 总市值
                'circulating_cap': data['data']['f21'] # 流通市值
            }
            debug_logger.debug(f"获取 {stock_code} 数据成功: {stock_data}")
            return stock_data
        else:
            logger.warning(f"未获取到 {stock_code} 的数据")
            return None
    except Exception as e:
        debug_logger.error(f"获取 {stock_code} 数据失败: {str(e)}")
        return None

def get_secid(stock_code):
    """转换为东方财富的secid格式"""
    if stock_code.startswith('60') or stock_code.startswith('90'):
        return f"1.{stock_code}"  # 沪市
    elif stock_code.startswith('00') or stock_code.startswith('30'):
        return f"0.{stock_code}"  # 深市
    elif stock_code.startswith('8'):
        return f"1.{stock_code}"  # 北交所
    else:
        return f"1.{stock_code}"  # 指数/板块默认

# ====================== 3. 股票分析逻辑 ======================
def analyze_stock(stock_data):
    """分析单只股票，生成评分和操作建议"""
    if not stock_data:
        return None
    
    try:
        # 基础评分（0-100）
        score = 50
        
        # 涨跌幅评分（±30分）
        change = stock_data['change']
        if change > 5:
            score += 30
        elif change > 2:
            score += 15
        elif change > 0:
            score += 5
        elif change < -5:
            score -= 30
        elif change < -2:
            score -= 15
        elif change < 0:
            score -= 5
        
        # 成交量评分（±10分）
        volume = stock_data['volume']
        if volume > 1e8:  # 成交量>1亿
            score += 10
        elif volume < 1e7:  # 成交量<1000万
            score -= 10
        
        # 限制评分范围0-100
        score = max(0, min(100, score))
        
        # 生成操作建议
        if score >= 80:
            advice = "买入"
            trend = "强势上涨"
        elif score >= 60:
            advice = "增持"
            trend = "震荡上行"
        elif score >= 40:
            advice = "持有"
            trend = "震荡"
        elif score >= 20:
            advice = "减持"
            trend = "震荡下行"
        else:
            advice = "卖出"
            trend = "弱势下跌"
        
        # 组装分析结果
        analysis_result = {
            'code': stock_data['code'],
            'name': stock_data['name'],
            'price': stock_data['price'],
            'change': stock_data['change'],
            'volume': stock_data['volume'],
            'score': score,
            'advice': advice,
            'trend': trend,
            'analysis_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.info(f"{stock_data['name']}({stock_data['code']}): {advice} 评分{score} {trend}")
        return analysis_result
    
    except Exception as e:
        debug_logger.error(f"分析 {stock_data['code']} 失败: {str(e)}")
        return None

# ====================== 4. 可视化网页生成（仅修复：移除echarts-python依赖，改用CDN） ======================
def generate_visual_report(analysis_results, output_path="stock_analysis_report.html"):
    """生成股票分析可视化网页"""
    if not analysis_results:
        logger.warning("无分析结果，跳过可视化网页生成")
        return
    
    try:
        # 整理数据
        df = pd.DataFrame(analysis_results)
        
        # 1. 准备图表数据
        # 评分TOP10
        top10_score = df.nlargest(10, 'score')[['name', 'score']].to_dict('records')
        # 操作建议统计
        advice_count = df['advice'].value_counts().to_dict()
        # 涨跌幅数据（过滤无效值）
        change_data = df[df['change'].notna()][['name', 'change']].to_dict('records')
        # 股票列表（用于表格）
        stock_table_data = df[['code', 'name', 'price', 'change', 'score', 'advice', 'trend']].to_dict('records')
        
        # 2. HTML模板（仅修改：使用ECharts CDN，无python包依赖）
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>每日股票分析报告 - {datetime.now().strftime('%Y-%m-%d')}</title>
    <!-- 引入ECharts和jQuery CDN（无需本地安装） -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: "Microsoft YaHei", Arial, sans-serif; 
            background-color: #f8f9fa; 
            padding: 20px;
            color: #333;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            box-shadow: 0 2px 20px rgba(0,0,0,0.08);
        }}
        h1 {{ 
            text-align: center; 
            color: #2c3e50; 
            margin-bottom: 30px;
            font-weight: 600;
        }}
        .summary {{ 
            background: #e8f4f8; 
            padding: 20px; 
            border-radius: 8px; 
            margin-bottom: 30px;
            border-left: 5px solid #3498db;
        }}
        .summary h3 {{ 
            color: #2c3e50; 
            margin-bottom: 10px;
        }}
        .chart-section {{ 
            margin-bottom: 40px;
        }}
        .chart-section h3 {{ 
            color: #2c3e50; 
            margin-bottom: 15px;
            font-weight: 500;
        }}
        .chart {{ 
            height: 400px; 
            border-radius: 8px;
            box-shadow: 0 1px 10px rgba(0,0,0,0.05);
        }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 10px rgba(0,0,0,0.05);
        }}
        th {{ 
            background-color: #3498db; 
            color: white; 
            padding: 12px; 
            text-align: left;
            font-weight: 500;
        }}
        td {{ 
            padding: 12px; 
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ 
            background-color: #f8f9fa;
        }}
        .buy {{ color: #e74c3c; font-weight: 600; }}
        .hold {{ color: #f39c12; font-weight: 600; }}
        .sell {{ color: #27ae60; font-weight: 600; }}
        .filter-box {{ 
            margin-bottom: 20px; 
            padding: 10px; 
            background: #f5f5f5; 
            border-radius: 8px;
        }}
        .filter-box select {{ 
            padding: 8px 12px; 
            margin-right: 10px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>每日股票分析报告 ({datetime.now().strftime('%Y-%m-%d')})</h1>
        
        <!-- 汇总信息 -->
        <div class="summary">
            <h3>📊 分析汇总</h3>
            <p>📈 共分析股票：<strong>{len(df)}</strong> 只</p>
            <p>🎯 操作建议分布：{json.dumps(advice_count, ensure_ascii=False)}</p>
            <p>⭐ 平均评分：<strong>{df['score'].mean():.1f}</strong> 分</p>
            <p>📊 平均涨跌幅：<strong>{df[df['change'].notna()]['change'].mean():.2f}%</strong></p>
        </div>

        <!-- 评分TOP10柱状图 -->
        <div class="chart-section">
            <h3>🏆 股票评分TOP10</h3>
            <div id="scoreChart" class="chart"></div>
        </div>
        
        <!-- 涨跌幅折线图 -->
        <div class="chart-section">
            <h3>📉 个股涨跌幅分布</h3>
            <div id="changeChart" class="chart"></div>
        </div>
        
        <!-- 操作建议饼图 -->
        <div class="chart-section">
            <h3>🎯 操作建议分布</h3>
            <div id="adviceChart" class="chart"></div>
        </div>
        
        <!-- 个股详情表格 -->
        <div class="chart-section">
            <h3>📋 个股详情</h3>
            <div class="filter-box">
                <label>筛选操作建议：</label>
                <select id="adviceFilter">
                    <option value="all">全部</option>
                    <option value="买入">买入</option>
                    <option value="增持">增持</option>
                    <option value="持有">持有</option>
                    <option value="减持">减持</option>
                    <option value="卖出">卖出</option>
                </select>
                <label>筛选评分：</label>
                <select id="scoreFilter">
                    <option value="all">全部</option>
                    <option value="high">高评分(≥80)</option>
                    <option value="medium">中评分(40-79)</option>
                    <option value="low">低评分(&lt;40)</option>
                </select>
            </div>
            <table id="stockTable">
                <thead>
                    <tr>
                        <th>股票代码</th>
                        <th>股票名称</th>
                        <th>当前价(元)</th>
                        <th>涨跌幅(%)</th>
                        <th>评分</th>
                        <th>操作建议</th>
                        <th>走势判断</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f"""
                    <tr>
                        <td>{item['code']}</td>
                        <td>{item['name']}</td>
                        <td>{item['price']:.2f}</td>
                        <td style="color: {'red' if item['change'] > 0 else 'green'}">{item['change']:.2f}</td>
                        <td>{item['score']}</td>
                        <td class="{'buy' if item['advice']=='买入' else 'hold' if item['advice'] in ['增持','持有'] else 'sell'}">{item['advice']}</td>
                        <td>{item['trend']}</td>
                    </tr>
                    """ for item in stock_table_data])}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // 初始化图表
        $(document).ready(function() {{
            // 1. 评分TOP10柱状图
            var scoreChart = echarts.init(document.getElementById('scoreChart'));
            scoreChart.setOption({{
                title: {{ text: '' }},
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
                xAxis: {{
                    type: 'category',
                    data: {[item['name'] for item in top10_score]},
                    axisLabel: {{ rotate: 30 }}
                }},
                yAxis: {{ type: 'value', name: '评分' }},
                series: [{{
                    name: '评分',
                    type: 'bar',
                    data: {[item['score'] for item in top10_score]},
                    itemStyle: {{
                        color: function(params) {{
                            var colorList = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e', '#27ae60', '#d35400'];
                            return colorList[params.dataIndex];
                        }}
                    }}
                }}]
            }});

            // 2. 涨跌幅折线图
            var changeChart = echarts.init(document.getElementById('changeChart'));
            changeChart.setOption({{
                title: {{ text: '' }},
                tooltip: {{ trigger: 'axis' }},
                grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
                xAxis: {{
                    type: 'category',
                    data: {[item['name'] for item in change_data[:20]]},
                    axisLabel: {{ rotate: 45 }}
                }},
                yAxis: {{ type: 'value', name: '涨跌幅(%)' }},
                series: [{{
                    name: '涨跌幅',
                    type: 'line',
                    data: {[item['change'] for item in change_data[:20]]},
                    markPoint: {{
                        data: [
                            {{type: 'max', name: '最大值'}},
                            {{type: 'min', name: '最小值'}}
                        ]
                    }},
                    markLine: {{
                        data: [{{type: 'average', name: '平均值'}}]
                    }}
                }}]
            }});

            // 3. 操作建议饼图
            var adviceChart = echarts.init(document.getElementById('adviceChart'));
            adviceChart.setOption({{
                title: {{ text: '' }},
                tooltip: {{ trigger: 'item' }},
                legend: {{
                    orient: 'vertical',
                    left: 'left'
                }},
                series: [{{
                    name: '操作建议',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    data: {[{{'name': k, 'value': v}} for k, v in advice_count.items()]},
                    emphasis: {{
                        itemStyle: {{
                            shadowBlur: 10,
                            shadowOffsetX: 0,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }}
                    }}
                }}]
            }});

            // 表格筛选功能
            $('#adviceFilter').change(function() {{
                filterTable();
            }});
            
            $('#scoreFilter').change(function() {{
                filterTable();
            }});
            
            function filterTable() {{
                var advice = $('#adviceFilter').val();
                var score = $('#scoreFilter').val();
                
                $('#stockTable tbody tr').each(function() {{
                    var rowAdvice = $(this).find('td:eq(5)').text();
                    var rowScore = parseInt($(this).find('td:eq(4)').text());
                    var show = true;
                    
                    // 筛选操作建议
                    if (advice !== 'all' && rowAdvice !== advice) {{
                        show = false;
                    }}
                    
                    // 筛选评分
                    if (score === 'high' && rowScore < 80) {{
                        show = false;
                    }} else if (score === 'medium' && (rowScore < 40 || rowScore >= 80)) {{
                        show = false;
                    }} else if (score === 'low' && rowScore >= 40) {{
                        show = false;
                    }}
                    
                    $(this).toggle(show);
                }});
            }}
            
            // 响应窗口大小变化
            window.addEventListener('resize', function() {{
                scoreChart.resize();
                changeChart.resize();
                adviceChart.resize();
            }});
        }});
    </script>
</body>
</html>
        """
        
        # 保存HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"可视化分析报告已生成：{output_path}")
        debug_logger.debug(f"可视化报告包含 {len(analysis_results)} 只股票数据")
        
    except Exception as e:
        debug_logger.error(f"生成可视化报告失败: {str(e)}")
        logger.error(f"可视化报告生成失败: {str(e)}")

# ====================== 5. 主程序 ======================
def main():
    """主程序入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='每日股票分析程序')
    parser.add_argument('--stocks', type=str, required=True, help='股票列表（逗号分隔）')
    args = parser.parse_args()
    
    # 拆分股票列表
    stock_codes = [code.strip() for code in args.stocks.split(',') if code.strip()]
    logger.info(f"开始分析 {len(stock_codes)} 只股票: {stock_codes}")
    
    # 存储所有分析结果
    all_analysis_results = []
    
    # 逐个分析股票
    for idx, stock_code in enumerate(stock_codes):
        logger.info(f"正在分析第 {idx+1}/{len(stock_codes)} 只股票: {stock_code}")
        
        # 获取股票数据
        stock_data = get_stock_info(stock_code)
        if not stock_data:
            continue
        
        # 分析股票
        analysis_result = analyze_stock(stock_data)
        if analysis_result:
            all_analysis_results.append(analysis_result)
        
        # 避免请求过快
        if idx % 10 == 0 and idx > 0:
            import time
            time.sleep(1)
    
    # 保存分析结果到CSV
    if all_analysis_results:
        df = pd.DataFrame(all_analysis_results)
        csv_path = f"stock_analysis_result_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"分析结果已保存到CSV: {csv_path}")
        
        # 生成可视化网页
        generate_visual_report(all_analysis_results)
    else:
        logger.warning("未生成任何分析结果")
    
    # 发送微信通知（如果配置了webhook）
    if os.getenv('WECHAT_WEBHOOK_URL'):
        try:
            send_wechat_notification(all_analysis_results)
        except Exception as e:
            logger.error(f"发送微信通知失败: {str(e)}")
    
    logger.info("程序执行完成")

def send_wechat_notification(analysis_results):
    """发送微信通知"""
    if not analysis_results:
        return
    
    # 筛选高评分股票（≥80）
    high_score_stocks = [r for r in analysis_results if r['score'] >= 80]
    
    # 组装消息
    msg = f"""
【每日股票分析报告】
分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
共分析股票：{len(analysis_results)} 只
高评分股票（≥80分）：{len(high_score_stocks)} 只

高评分股票列表：
{chr(10).join([f"• {r['name']}({r['code']}): 评分{r['score']} 建议{r['advice']}" for r in high_score_stocks[:10]])}
    """.strip()
    
    # 发送到企业微信/webhook
    requests.post(
        os.getenv('WECHAT_WEBHOOK_URL'),
        json={"msgtype": "text", "text": {"content": msg}},
        timeout=10
    )
    logger.info("微信通知发送成功")

# ====================== 6. 入口执行 ======================
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        debug_logger.exception("程序执行异常详情:")
        raise

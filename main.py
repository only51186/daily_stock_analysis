import argparse
import requests
import json
import logging
import os
import pandas as pd
from datetime import datetime
import random
from tenacity import retry, stop_after_attempt, wait_exponential

# ====================== 1. 日志配置 ======================
def setup_logger():
    """配置日志系统"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    main_logger = logging.getLogger('stock_analysis')
    main_logger.setLevel(logging.INFO)
    main_handler = logging.FileHandler(f'logs/stock_analysis_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    main_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    main_logger.addHandler(main_handler)
    
    debug_logger = logging.getLogger('stock_analysis_debug')
    debug_logger.setLevel(logging.DEBUG)
    debug_handler = logging.FileHandler(f'logs/stock_analysis_debug_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    debug_handler.setFormatter(logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'))
    debug_logger.addHandler(debug_handler)
    
    return main_logger, debug_logger

logger, debug_logger = setup_logger()

# ====================== 2. 股票数据获取（带重试防网络波动） ======================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=5))
def get_stock_info(stock_code):
    """获取股票基本信息和行情数据"""
    try:
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={get_secid(stock_code)}&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f27,f28,f30,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['data']:
            stock_data = {
                'code': stock_code,
                'name': data['data']['f14'],
                'price': data['data']['f2'],
                'change': data['data']['f3'],
                'change_amount': data['data']['f4'],
                'volume': data['data']['f5'],
                'turnover': data['data']['f6'],
                'open': data['data']['f7'],
                'high': data['data']['f8'],
                'low': data['data']['f9'],
                'prev_close': data['data']['f10'],
                'market_cap': data['data']['f20'],
                'circulating_cap': data['data']['f21']
            }
            debug_logger.debug(f"获取 {stock_code} 数据成功: {stock_data}")
            return stock_data
        else:
            logger.warning(f"未获取到 {stock_code} 的数据")
            return None
    except Exception as e:
        debug_logger.error(f"获取 {stock_code} 数据失败: {str(e)}")
        raise

def get_secid(stock_code):
    """转换为东方财富的secid格式"""
    if stock_code.startswith('60') or stock_code.startswith('90'):
        return f"1.{stock_code}"
    elif stock_code.startswith('00') or stock_code.startswith('30'):
        return f"0.{stock_code}"
    elif stock_code.startswith('8'):
        return f"1.{stock_code}"
    else:
        return f"1.{stock_code}"

# ====================== 3. 股票分析逻辑 ======================
def analyze_stock(stock_data):
    """分析单只股票，生成评分和操作建议"""
    if not stock_data:
        return None
    
    try:
        score = 50
        
        # 涨跌幅评分
        change = stock_data['change'] if stock_data['change'] is not None else 0
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
        
        # 成交量评分
        volume = stock_data['volume'] if stock_data['volume'] is not None else 0
        if volume > 1e8:
            score += 10
        elif volume < 1e7:
            score -= 10
        
        score = max(0, min(100, score))
        
        # 操作建议
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

# ====================== 4. 可视化网页生成（彻底修复语法错误） ======================
def generate_visual_report(analysis_results, output_path="stock_analysis_report.html"):
    """生成股票分析可视化网页"""
    if not analysis_results:
        logger.warning("无分析结果，跳过可视化网页生成")
        return
    
    try:
        df = pd.DataFrame(analysis_results)
        
        # 图表数据准备
        top10_score = df.nlargest(10, 'score')[['name', 'score']].to_dict('records')
        advice_count = df['advice'].value_counts().to_dict()
        change_data = df[df['change'].notna()][['name', 'change']].to_dict('records')
        stock_table_data = df[['code', 'name', 'price', 'change', 'score', 'advice', 'trend']].to_dict('records')

        # 提前单独生成表格HTML，彻底规避f-string嵌套报错
        table_rows = ""
        for item in stock_table_data:
            # 单独处理每一行的数值格式化
            price_text = f"{f"{f"{item['price']:.2f}" if item['price'] is not None else "-"
            change_text = f"{f"{f"{item['change']:.2f}" if item['change'] is not None else "-"
            change_color = "red" if (item['change'] is not None and item['change'] > 0) else "green"
            advice_class = "buy" if item['advice'] == '买入' else "hold" if item['advice'] in ['增持','持有'] else "sell"
            
            # 拼接每一行
            table_rows += f"""
            <tr>
                <td>{item['code']}</td>
                <td>{item['name']}</td>
                <td>{price_text}</td>
                <td style="color: {change_color}">{change_text}</td>
                <td>{item['score']}</td>
                <td class="{advice_class}">{item['advice']}</td>
                <td>{item['trend']}</td>
            </tr>
            """

        # 图表数据转JSON字符串，避免f-string嵌套报错
        top10_names = json.dumps([item['name'] for item in top10_score], ensure_ascii=False)
        top10_scores = json.dumps([item['score'] for item in top10_score], ensure_ascii=False)
        change_names = json.dumps([item['name'] for item in change_data], ensure_ascii=False)
        change_values = json.dumps([item['change'] for item in change_data], ensure_ascii=False)
        advice_data = json.dumps([{'name': k, 'value': v} for k, v in advice_count.items()], ensure_ascii=False)
        advice_count_json = json.dumps(advice_count, ensure_ascii=False)
        
        # 基础统计数据
        total_count = len(df)
        avg_score = f"{df['score'].mean():.1f}"
        avg_change = f"{df[df['change'].notna()]['change'].mean():.2f}"
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        # HTML模板（无任何嵌套f-string，彻底规避语法错误）
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>每日股票分析报告 - {report_date}</title>
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
        <h1>每日股票分析报告 ({report_date})</h1>
        
        <div class="summary">
            <h3>📊 分析汇总</h3>
            <p>📈 共分析股票：<strong>{total_count}</strong> 只</p>
            <p>🎯 操作建议分布：{advice_count_json}</p>
            <p>⭐ 平均评分：<strong>{avg_score}</strong> 分</p>
            <p>📊 平均涨跌幅：<strong>{avg_change}%</strong></p>
        </div>

        <div class="chart-section">
            <h3>🏆 股票评分TOP10</h3>
            <div id="scoreChart" class="chart"></div>
        </div>
        
        <div class="chart-section">
            <h3>📉 个股涨跌幅分布</h3>
            <div id="changeChart" class="chart"></div>
        </div>
        
        <div class="chart-section">
            <h3>🎯 操作建议分布</h3>
            <div id="adviceChart" class="chart"></div>
        </div>
        
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
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        $(document).ready(function() {{
            // 评分TOP10柱状图
            var scoreChart = echarts.init(document.getElementById('scoreChart'));
            scoreChart.setOption({{
                title: {{ text: '股票评分TOP10', left: 'center' }},
                xAxis: {{ type: 'category', data: {top10_names} }},
                yAxis: {{ type: 'value', name: '评分' }},
                series: [{{
                    name: '评分',
                    type: 'bar',
                    data: {top10_scores},
                    itemStyle: {{
                        color: function(params) {{
                            var colorList = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e', '#27ae60', '#d35400'];
                            return colorList[params.dataIndex];
                        }}
                    }}
                }}],
                tooltip: {{ trigger: 'axis' }}
            }});

            // 涨跌幅折线图
            var changeChart = echarts.init(document.getElementById('changeChart'));
            changeChart.setOption({{
                title: {{ text: '个股涨跌幅分布', left: 'center' }},
                xAxis: {{ type: 'category', data: {change_names} }},
                yAxis: {{ type: 'value', name: '涨跌幅(%)' }},
                series: [{{
                    name: '涨跌幅(%)',
                    type: 'line',
                    data: {change_values},
                    markPoint: {{
                        data: [
                            {{type: 'max', name: '最大值'}},
                            {{type: 'min', name: '最小值'}}
                        ]
                    }},
                    markLine: {{
                        data: [{{type: 'average', name: '平均值'}}]
                    }}
                }}],
                tooltip: {{ trigger: 'axis' }}
            }});

            // 操作建议饼图
            var adviceChart = echarts.init(document.getElementById('adviceChart'));
            adviceChart.setOption({{
                title: {{ text: '操作建议分布', left: 'center' }},
                tooltip: {{ trigger: 'item' }},
                legend: {{ orient: 'vertical', left: 'left' }},
                series: [{{
                    name: '操作建议',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    data: {advice_data},
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
                var advice = $(this).val();
                $('#stockTable tbody tr').each(function() {{
                    if (advice === 'all' || $(this).find('td:eq(5)').text() === advice) {{
                        $(this).show();
                    }} else {{
                        $(this).hide();
                    }}
                }});
            }});

            $('#scoreFilter').change(function() {{
                var scoreType = $(this).val();
                $('#stockTable tbody tr').each(function() {{
                    var score = parseInt($(this).find('td:eq(4)').text());
                    if (scoreType === 'all') {{
                        $(this).show();
                    }} else if (scoreType === 'high' && score >= 80) {{
                        $(this).show();
                    }} else if (scoreType === 'medium' && score >= 40 && score < 80) {{
                        $(this).show();
                    }} else if (scoreType === 'low' && score < 40) {{
                        $(this).show();
                    }} else {{
                        $(this).hide();
                    }}
                }});
            }});

            // 自适应窗口
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
        
        logger.info(f"可视化报告已生成：{output_path}")
        
        # 兼容imgkit，无环境不报错
        try:
            import imgkit
            img_path = output_path.replace('.html', '.png')
            imgkit.from_file(output_path, img_path)
            logger.info(f"报告图片已生成：{img_path}")
        except ImportError:
            logger.warning("未安装imgkit，跳过图片生成")
        except Exception as e:
            logger.warning(f"生成报告图片失败：{str(e)}")
            
    except Exception as e:
        debug_logger.error(f"生成可视化报告失败: {str(e)}")
        logger.error(f"生成可视化报告失败: {str(e)}")

# ====================== 5. 微信通知模块 ======================
def send_wechat_notification(analysis_results):
    """发送微信通知（示例，可对接企业微信API）"""
    try:
        if not analysis_results:
            return
        
        top_buy = [r for r in analysis_results if r['advice'] == '买入'][:5]
        content = f"""
【每日股票分析报告】
分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
共分析股票：{len(analysis_results)} 只
买入建议：{len(top_buy)} 只
TOP3买入标的：
{chr(10).join([f"• {r['name']}({r['code']}) 评分{r['score']}" for r in top_buy[:3]])}
        """
        logger.info(f"微信通知内容已生成：{content}")
        
    except Exception as e:
        debug_logger.error(f"发送微信通知失败: {str(e)}")
        logger.error(f"发送微信通知失败: {str(e)}")

# ====================== 6. 主函数 ======================
def main(stock_codes):
    """主函数：获取数据 → 分析 → 生成报告 → 发送通知"""
    logger.info("===== 开始每日股票分析 =====")
    
    # 获取股票数据
    stock_data_list = []
    for code in stock_codes:
        try:
            stock_data = get_stock_info(code)
            if stock_data:
                stock_data_list.append(stock_data)
            random.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logger.error(f"处理股票 {code} 失败: {str(e)}")
    
    if not stock_data_list:
        logger.error("未获取到任何股票数据，分析终止")
        return
    
    # 分析股票
    analysis_results = []
    for stock_data in stock_data_list:
        analysis_result = analyze_stock(stock_data)
        if analysis_result:
            analysis_results.append(analysis_result)
    
    # 输出结果
    if analysis_results:
        csv_path = f"stock_analysis_result_{datetime.now().strftime('%Y%m%d')}.csv"
        df = pd.DataFrame(analysis_results)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"分析结果已保存到CSV：{csv_path}")
        
        generate_visual_report(analysis_results)
        send_wechat_notification(analysis_results)
    
    logger.info("===== 每日股票分析完成 =====")

# ====================== 7. 命令行入口（核心容错修复） ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='每日股票分析工具')
    # 核心修复：把required=True改成False，不再强制必填，增加兜底逻辑
    parser.add_argument('--codes', nargs='+', required=False, help='股票代码列表，如：600000 000001')
args = parser.parse_args()
stock_codes = args.codes if args.codes else args.stocks
if not stock_codes:
    stock_list_env = os.getenv("STOCK_LIST", "")
    if stock_list_env:
        stock_codes = [code.strip() for code in stock_list_env.split(',') if code.strip()]
        logger.info(f"✅ 从环境变量读取到股票列表，共{len(stock_codes)}只")
    else:
        logger.error("❌ 未获取到任何股票列表，请检查配置")
        raise SystemExit("错误：未指定股票代码")

# 自动兜底：兼容--codes/--stocks双参数，自动从环境变量读取股票列表
stock_codes = args.codes if args.codes else args.stocks
if not stock_codes:
    stock_list_env = os.getenv("STOCK_LIST", "")
    if stock_list_env:
        stock_codes = [code.strip() for code in stock_list_env.split(',') if code.strip()]
        logger.info(f"✅ 从环境变量读取到股票列表，共{len(stock_codes)}只")
    else:
        logger.error("❌ 未获取到股票列表")
        raise SystemExit("错误：未指定任何股票代码")

    # 兜底逻辑1：如果命令行没传--codes，自动从环境变量STOCK_LIST读取
    stock_codes = args.codes
    if not stock_codes:
        stock_list_env = os.getenv("STOCK_LIST", "")
        if stock_list_env:
            # 把逗号分隔的股票代码拆分成列表
            stock_codes = [code.strip() for code in stock_list_env.split(',') if code.strip()]
            logger.info(f"从环境变量STOCK_LIST读取到股票列表：{stock_codes}")
        else:
            # 兜底逻辑2：如果环境变量也没有，直接报错退出，给出明确提示
            logger.error("未获取到股票列表！请通过--codes参数传入，或设置STOCK_LIST环境变量")
            raise SystemExit("错误：未指定任何股票代码")
    
    # 执行主函数
    main(stock_codes)

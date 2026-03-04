# -*- coding: utf-8 -*-
"""
===================================
统一配置文件
===================================

功能：
1. 合并重复的配置项（数据源、API、定时任务等）
2. 提供统一的配置管理接口
3. 支持环境变量覆盖

【配置优先级】
环境变量 > 配置文件 > 默认值
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path


@dataclass
class DataSourceConfig:
    """数据源配置"""
    # 优先级：akshare > efinance > tushare
    priority: List[str] = field(default_factory=lambda: ['akshare', 'efinance', 'tushare'])
    
    # 缓存配置
    cache_enabled: bool = True
    cache_dir: str = "data_cache"
    cache_ttl_hours: int = 1  # 缓存有效期1小时
    
    # 定时下载配置
    auto_download: bool = True
    download_times: List[str] = field(default_factory=lambda: ["09:30", "14:00"])
    
    # Tushare API Key（可选）
    tushare_token: str = ""


@dataclass
class DoubaoConfig:
    """豆包API配置"""
    api_key: str = ""  # 从环境变量读取，不硬编码
    model: str = "Doubao-Seedream-5.0-lite"
    api_url: str = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    # Token优化配置
    max_tokens: int = 1000
    temperature: float = 0.7
    
    # 推送配置
    push_enabled: bool = True
    retry_times: int = 3
    retry_delay: int = 5
    
    # Token监控
    token_monitor_enabled: bool = True
    token_threshold_percent: float = 10.0  # 剩余<10%时切换轻量化推理


@dataclass
class StrategyConfig:
    """策略配置"""
    # 股票筛选条件
    price_min: float = 5.0
    price_max: float = 35.0
    turnover_rate_min: float = 3.0
    turnover_rate_max: float = 10.0
    volume_ratio_threshold: float = 1.5
    
    # 持有时间
    hold_days: int = 2
    
    # 止损设置
    stop_loss_percent: float = 3.0
    
    # 定时运行配置
    selection_time: str = "14:30"  # 每日选股时间
    backtest_day: str = "Sunday"   # 每周回测日
    backtest_time: str = "20:00"   # 回测时间
    
    # 板块数量
    top_sectors_count: int = 10
    
    # 推荐股票数量
    max_recommendations: int = 10


@dataclass
class ScheduleConfig:
    """定时任务配置"""
    enabled: bool = True
    
    # 数据下载
    data_download_times: List[str] = field(default_factory=lambda: ["09:30", "14:00"])
    
    # 选股
    selection_time: str = "14:30"
    selection_days: List[str] = field(default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    
    # 回测
    backtest_time: str = "20:00"
    backtest_day: str = "Sunday"
    
    # 复盘
    review_time: str = "09:00"
    review_days: List[str] = field(default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])


@dataclass
class VisualizationConfig:
    """可视化配置"""
    # 界面配置
    ui_framework: str = "tkinter"  # tkinter 或 streamlit
    ui_title: str = "股票走势预测"
    ui_size: str = "1200x800"
    
    # 图表配置
    chart_style: str = "seaborn"
    prediction_days: int = 2
    history_days: int = 30
    
    # 情绪分析
    emotion_analysis_enabled: bool = True


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    log_dir: str = "logs"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # 日志文件
    strategy_log: str = "strategy.log"
    backtest_log: str = "backtest.log"
    data_log: str = "data.log"
    error_log: str = "error.log"


@dataclass
class Settings:
    """统一配置类"""
    
    # 项目根目录
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    
    # 各模块配置
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    doubao: DoubaoConfig = field(default_factory=DoubaoConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    def __post_init__(self):
        """初始化后处理：从环境变量读取配置"""
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # 数据源配置
        if os.getenv('DATA_CACHE_ENABLED'):
            self.data_source.cache_enabled = os.getenv('DATA_CACHE_ENABLED').lower() == 'true'
        if os.getenv('DATA_CACHE_TTL_HOURS'):
            self.data_source.cache_ttl_hours = int(os.getenv('DATA_CACHE_TTL_HOURS'))
        if os.getenv('TUSHARE_TOKEN'):
            self.data_source.tushare_token = os.getenv('TUSHARE_TOKEN')
        
        # 豆包API配置
        if os.getenv('DOUBAO_API_KEY'):
            self.doubao.api_key = os.getenv('DOUBAO_API_KEY')
        if os.getenv('DOUBAO_MODEL'):
            self.doubao.model = os.getenv('DOUBAO_MODEL')
        if os.getenv('DOUBAO_PUSH_ENABLED'):
            self.doubao.push_enabled = os.getenv('DOUBAO_PUSH_ENABLED').lower() == 'true'
        
        # 策略配置
        if os.getenv('STRATEGY_PRICE_MIN'):
            self.strategy.price_min = float(os.getenv('STRATEGY_PRICE_MIN'))
        if os.getenv('STRATEGY_PRICE_MAX'):
            self.strategy.price_max = float(os.getenv('STRATEGY_PRICE_MAX'))
        if os.getenv('STRATEGY_HOLD_DAYS'):
            self.strategy.hold_days = int(os.getenv('STRATEGY_HOLD_DAYS'))
        
        # 日志配置
        if os.getenv('LOG_LEVEL'):
            self.logging.level = os.getenv('LOG_LEVEL')
    
    def get_cache_dir(self) -> Path:
        """获取缓存目录"""
        return self.project_root / self.data_source.cache_dir
    
    def get_log_dir(self) -> Path:
        """获取日志目录"""
        return self.project_root / self.logging.log_dir
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'data_source': self.data_source.__dict__,
            'doubao': self.doubao.__dict__,
            'strategy': self.strategy.__dict__,
            'schedule': self.schedule.__dict__,
            'visualization': self.visualization.__dict__,
            'logging': self.logging.__dict__,
        }


# 全局配置实例
_settings = None


def get_settings() -> Settings:
    """
    获取配置实例（单例）
    
    Returns:
        Settings实例
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


if __name__ == "__main__":
    # 测试配置
    settings = get_settings()
    
    print("=== 统一配置测试 ===")
    print(f"\n项目根目录: {settings.project_root}")
    print(f"缓存目录: {settings.get_cache_dir()}")
    print(f"日志目录: {settings.get_log_dir()}")
    
    print(f"\n数据源配置:")
    print(f"  - 优先级: {settings.data_source.priority}")
    print(f"  - 缓存启用: {settings.data_source.cache_enabled}")
    print(f"  - 缓存有效期: {settings.data_source.cache_ttl_hours}小时")
    print(f"  - 自动下载时间: {settings.data_source.download_times}")
    
    print(f"\n豆包API配置:")
    print(f"  - API Key: {settings.doubao.api_key[:10]}...")
    print(f"  - 模型: {settings.doubao.model}")
    print(f"  - 最大Tokens: {settings.doubao.max_tokens}")
    print(f"  - 推送启用: {settings.doubao.push_enabled}")
    
    print(f"\n策略配置:")
    print(f"  - 价格范围: {settings.strategy.price_min}-{settings.strategy.price_max}元")
    print(f"  - 换手率范围: {settings.strategy.turnover_rate_min}-{settings.strategy.turnover_rate_max}%")
    print(f"  - 持有天数: {settings.strategy.hold_days}天")
    print(f"  - 选股时间: {settings.strategy.selection_time}")
    
    print(f"\n定时任务配置:")
    print(f"  - 数据下载: {settings.schedule.data_download_times}")
    print(f"  - 选股: {settings.schedule.selection_time} ({', '.join(settings.schedule.selection_days)})")
    print(f"  - 回测: {settings.schedule.backtest_time} on {settings.schedule.backtest_day}")

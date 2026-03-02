# -*- coding: utf-8 -*-
"""
===================================
日志配置模块
===================================

功能：
1. 统一日志配置，方便排查问题
2. 支持日志文件轮转，避免日志文件过大
3. 支持不同级别的日志输出
4. 记录每一步操作、错误信息
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(
    name: str = None,
    log_file: str = None,
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称，默认为调用模块的名称
        log_file: 日志文件路径，默认为 logs/strategy.log
        log_level: 日志级别
        log_to_console: 是否输出到控制台
        log_to_file: 是否输出到文件
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
        
    Returns:
        配置好的日志记录器
    """
    if name is None:
        name = __name__
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 文件处理器
    if log_to_file:
        if log_file is None:
            # 默认日志文件路径
            project_root = Path(__file__).parent.parent
            log_dir = project_root / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "strategy.log"
        else:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建轮转文件处理器
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    获取日志记录器（快捷方式）
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器
    """
    if name is None:
        name = __name__
    
    return logging.getLogger(name)


class LoggerMixin:
    """
    日志混入类
    
    为类提供日志功能
    """
    
    @property
    def logger(self) -> logging.Logger:
        """
        获取日志记录器
        
        Returns:
            日志记录器
        """
        if not hasattr(self, '_logger'):
            self._logger = setup_logger(self.__class__.__name__)
        return self._logger


def log_function_call(func):
    """
    函数调用日志装饰器
    
    记录函数的调用和返回值
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"调用函数: {func.__name__}，参数: args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"函数 {func.__name__} 执行成功，返回值: {result}")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败，错误: {e}", exc_info=True)
            raise
    
    return wrapper


def log_execution_time(func):
    """
    执行时间日志装饰器
    
    记录函数的执行时间
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        import time
        logger = get_logger(func.__module__)
        
        start_time = time.time()
        logger.debug(f"开始执行函数: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"函数 {func.__name__} 执行完成，耗时: {execution_time:.2f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.2f}秒，错误: {e}", exc_info=True)
            raise
    
    return wrapper


def log_error(logger: logging.Logger = None):
    """
    错误日志装饰器
    
    记录函数执行过程中的错误
    
    Args:
        logger: 日志记录器
        
    Returns:
        装饰器
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"函数 {func.__name__} 执行失败，错误: {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator


# 全局日志配置
def configure_global_logging(
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = True
):
    """
    配置全局日志
    
    Args:
        log_level: 日志级别
        log_to_console: 是否输出到控制台
        log_to_file: 是否输出到文件
    """
    project_root = Path(__file__).parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "strategy.log"
    
    # 创建日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 文件处理器
    if log_to_file:
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logging.info("全局日志配置完成")


if __name__ == "__main__":
    # 测试代码
    configure_global_logging()
    
    logger = setup_logger("test")
    
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    logger.critical("这是一条严重错误信息")
    
    @log_execution_time
    def test_function():
        import time
        time.sleep(1)
        return "测试完成"
    
    result = test_function()
    print(result)

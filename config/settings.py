#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统配置文件
"""

import os
from datetime import time
from typing import List, Dict, Any


class Settings:
    """系统配置类"""
    
    # 基础配置
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Web服务器配置
    WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
    WEB_PORT = int(os.getenv('WEB_PORT', 5000))
    
    # 数据库配置
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///atr.db')
    
    # 交易配置
    TRADING_INTERVAL = int(os.getenv('TRADING_INTERVAL', 300))  # 5分钟
    INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', 10000))  # $10,000
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', 0.1))  # 10%
    STOP_LOSS_PERCENTAGE = float(os.getenv('STOP_LOSS_PERCENTAGE', 0.05))  # 5%
    
    # 市场配置
    MARKET_OPEN_TIME = time(9, 30)  # 9:30 AM
    MARKET_CLOSE_TIME = time(16, 0)  # 4:00 PM
    TIMEZONE = 'US/Eastern'
    
    # 支持的股票列表 (NASDAQ 100 主要股票)
    SUPPORTED_SYMBOLS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
        'ADBE', 'CRM', 'ORCL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'TXN',
        'COST', 'SBUX', 'PYPL', 'ZOOM', 'DOCU', 'SHOP', 'SQ', 'ROKU'
    ]
    
    # AI模型配置
    AI_MODELS = {
        'gpt-4': {
            'enabled': False,
            'api_key_env': 'OPENAI_API_KEY',
            'model_name': 'gpt-4-turbo-preview',
            'max_tokens': 2000,
            'temperature': 0.1
        },
        'claude-3': {
            'enabled': False,
            'api_key_env': 'ANTHROPIC_API_KEY',
            'model_name': 'claude-3-opus-20240229',
            'max_tokens': 2000,
            'temperature': 0.1
        },
        'qwen-max': {
            'enabled': True,  # 通义千问模型已实现
            'api_key_env': 'QWEN_API_KEY',
            'model_name': 'qwen-max',
            'max_tokens': 2000,
            'temperature': 0.1
        },
        'deepseek-v3': {
            'enabled': True,  # DeepSeek v3.1模型已实现
            'api_key_env': 'DEEPSEEK_API_KEY',
            'model_name': 'deepseek-chat',
            'max_tokens': 2000,
            'temperature': 0.1
        }
    }
    
    # 数据源配置
    DATA_SOURCES = {
        'alpha_vantage': {
            'api_key_env': 'ALPHA_VANTAGE_API_KEY',
            'base_url': 'https://www.alphavantage.co/query'
        },
        'yahoo_finance': {
            'enabled': True
        },
        'news_api': {
            'api_key_env': 'NEWS_API_KEY',
            'base_url': 'https://newsapi.org/v2'
        }
    }
    
    # 风险管理配置
    RISK_MANAGEMENT = {
        'max_daily_loss': 0.05,  # 5% 最大日损失
        'max_portfolio_risk': 0.02,  # 2% 最大组合风险
        'position_sizing_method': 'kelly',  # kelly, fixed, volatility
        'rebalance_frequency': 'daily',  # daily, weekly, monthly
        'correlation_threshold': 0.7  # 相关性阈值
    }
    
    # 技术指标配置
    TECHNICAL_INDICATORS = {
        'sma_periods': [5, 10, 20, 50, 200],
        'ema_periods': [12, 26],
        'rsi_period': 14,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'bollinger_period': 20,
        'bollinger_std': 2
    }
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}'
    
    # 缓存配置
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TTL = int(os.getenv('CACHE_TTL', 300))  # 5分钟
    
    # 监控配置
    PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 8000))
    
    @classmethod
    def get_api_key(cls, key_name: str) -> str:
        """获取API密钥"""
        return os.getenv(key_name, '')
    
    @classmethod
    def is_model_enabled(cls, model_name: str) -> bool:
        """检查模型是否启用"""
        model_config = cls.AI_MODELS.get(model_name, {})
        if not model_config.get('enabled', False):
            return False
        
        api_key_env = model_config.get('api_key_env')
        if api_key_env and not cls.get_api_key(api_key_env):
            return False
        
        return True
    
    @classmethod
    def get_enabled_models(cls) -> List[str]:
        """获取启用的模型列表"""
        return [name for name in cls.AI_MODELS.keys() if cls.is_model_enabled(name)]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密钥配置模板
复制此文件为 api_keys.py 并填入你的API密钥
"""

import os

# OpenAI API配置
os.environ['OPENAI_API_KEY'] = 'your_openai_api_key_here'

# Anthropic Claude API配置
os.environ['ANTHROPIC_API_KEY'] = 'your_anthropic_api_key_here'

# 通义千问API配置
os.environ['QWEN_API_KEY'] = 'your_qwen_api_key_here'

# DeepSeek API配置
os.environ['DEEPSEEK_API_KEY'] = 'your_deepseek_api_key_here'

# Alpha Vantage API配置 (金融数据)
os.environ['ALPHA_VANTAGE_API_KEY'] = 'your_alpha_vantage_api_key_here'

# News API配置 (新闻数据)
os.environ['NEWS_API_KEY'] = 'your_news_api_key_here'

# 券商API配置 (如果使用真实交易)
# 注意: 建议先使用模拟交易进行测试
os.environ['BROKER_API_KEY'] = 'your_broker_api_key_here'
os.environ['BROKER_SECRET_KEY'] = 'your_broker_secret_key_here'

# Redis配置 (如果使用外部Redis)
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

# 数据库配置 (如果使用外部数据库)
os.environ['DATABASE_URL'] = 'sqlite:///atr.db'

# 其他配置
os.environ['DEBUG'] = 'True'  # 开发模式
os.environ['LOG_LEVEL'] = 'INFO'

# 交易配置
os.environ['INITIAL_CAPITAL'] = '10000'  # 初始资金
os.environ['TRADING_INTERVAL'] = '300'   # 交易间隔(秒)
os.environ['MAX_POSITION_SIZE'] = '0.1'  # 最大仓位比例

print("✅ API密钥配置已加载")
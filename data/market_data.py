#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据提供者
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
import json

try:
    import yfinance as yf
except ImportError:
    logger.warning("⚠️ yfinance库未安装，部分功能将不可用")
    yf = None

try:
    import pandas as pd
except ImportError:
    logger.warning("⚠️ pandas库未安装，部分功能将不可用")
    pd = None

from config.settings import Settings


@dataclass
class StockData:
    """股票数据"""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class MarketIndex:
    """市场指数数据"""
    symbol: str
    value: float
    change: float
    change_percent: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MarketDataProvider:
    """市场数据提供者"""
    
    def __init__(self):
        self.settings = Settings()
        self.data_sources = self.settings.DATA_SOURCES
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        self.session = None
        self.is_initialized = False
    
    async def initialize(self):
        """初始化数据提供者"""
        logger.info("📊 初始化市场数据提供者...")
        
        # 创建HTTP会话
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # 测试数据源连接
        await self._test_data_sources()
        
        self.is_initialized = True
        logger.info("✅ 市场数据提供者初始化完成")
    
    async def _test_data_sources(self):
        """测试数据源连接"""
        # 测试Yahoo Finance
        if yf is not None:
            try:
                # 简单测试
                test_ticker = yf.Ticker("AAPL")
                info = test_ticker.info
                if info:
                    logger.info("✅ Yahoo Finance连接正常")
            except Exception as e:
                logger.warning(f"⚠️ Yahoo Finance连接异常: {e}")
        
        # 测试Alpha Vantage
        alpha_vantage_key = Settings.get_api_key('ALPHA_VANTAGE_API_KEY')
        if alpha_vantage_key:
            try:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={alpha_vantage_key}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        logger.info("✅ Alpha Vantage连接正常")
                    else:
                        logger.warning(f"⚠️ Alpha Vantage响应异常: {response.status}")
            except Exception as e:
                logger.warning(f"⚠️ Alpha Vantage连接异常: {e}")
    
    async def get_real_time_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取实时数据"""
        try:
            # 检查缓存
            cache_key = f"realtime_{symbol}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]['data']
            
            # 尝试多个数据源
            data = None
            
            # 首先尝试Yahoo Finance
            if yf is not None:
                data = await self._get_yahoo_data(symbol)
            
            # 如果Yahoo Finance失败，尝试Alpha Vantage
            if not data:
                data = await self._get_alpha_vantage_data(symbol)
            
            # 如果都失败，使用模拟数据
            if not data:
                data = self._generate_mock_data(symbol)
            
            # 缓存数据
            if data:
                self.cache[cache_key] = {
                    'data': data,
                    'timestamp': datetime.now()
                }
            
            return data
            
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 实时数据失败: {e}")
            return None
    
    async def _get_yahoo_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从Yahoo Finance获取数据"""
        try:
            if yf is None:
                return None
            
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            
            # 获取基本信息
            info = await loop.run_in_executor(None, lambda: ticker.info)
            
            # 获取历史数据（最近1天）
            hist = await loop.run_in_executor(
                None, 
                lambda: ticker.history(period="1d", interval="1m")
            )
            
            if hist.empty:
                return None
            
            # 获取最新价格
            latest = hist.iloc[-1]
            previous_close = info.get('previousClose', latest['Close'])
            
            current_price = float(latest['Close'])
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close != 0 else 0
            
            data = {
                'symbol': symbol,
                'price': current_price,
                'change': change,
                'change_percent': change_percent,
                'volume': int(latest['Volume']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'open': float(latest['Open']),
                'previous_close': previous_close,
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'source': 'yahoo_finance',
                'timestamp': datetime.now().isoformat()
            }
            
            return data
            
        except Exception as e:
            logger.debug(f"Yahoo Finance获取 {symbol} 数据失败: {e}")
            return None
    
    async def _get_alpha_vantage_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从Alpha Vantage获取数据"""
        try:
            api_key = Settings.get_api_key('ALPHA_VANTAGE_API_KEY')
            if not api_key:
                return None
            
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                json_data = await response.json()
                quote = json_data.get('Global Quote', {})
                
                if not quote:
                    return None
                
                current_price = float(quote.get('05. price', 0))
                change = float(quote.get('09. change', 0))
                change_percent = float(quote.get('10. change percent', '0%').rstrip('%'))
                
                data = {
                    'symbol': symbol,
                    'price': current_price,
                    'change': change,
                    'change_percent': change_percent,
                    'volume': int(quote.get('06. volume', 0)),
                    'high': float(quote.get('03. high', 0)),
                    'low': float(quote.get('04. low', 0)),
                    'open': float(quote.get('02. open', 0)),
                    'previous_close': float(quote.get('08. previous close', 0)),
                    'source': 'alpha_vantage',
                    'timestamp': datetime.now().isoformat()
                }
                
                return data
                
        except Exception as e:
            logger.debug(f"Alpha Vantage获取 {symbol} 数据失败: {e}")
            return None
    
    def _generate_mock_data(self, symbol: str) -> Dict[str, Any]:
        """生成模拟数据"""
        import random
        
        # 基础价格映射
        base_prices = {
            'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 2500.0, 'AMZN': 3000.0,
            'TSLA': 200.0, 'META': 250.0, 'NVDA': 400.0, 'NFLX': 400.0,
            'QQQ': 350.0, 'SPY': 450.0, 'VIX': 20.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # 生成随机波动
        change_percent = random.uniform(-3.0, 3.0)
        current_price = base_price * (1 + change_percent / 100)
        change = current_price - base_price
        
        data = {
            'symbol': symbol,
            'price': round(current_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': random.randint(1000000, 50000000),
            'high': round(current_price * 1.02, 2),
            'low': round(current_price * 0.98, 2),
            'open': round(base_price, 2),
            'previous_close': base_price,
            'source': 'mock_data',
            'timestamp': datetime.now().isoformat()
        }
        
        return data
    
    async def get_historical_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        """获取历史数据"""
        try:
            if yf is None or pd is None:
                logger.warning("⚠️ 缺少必要的库，无法获取历史数据")
                return None
            
            # 检查缓存
            cache_key = f"historical_{symbol}_{period}_{interval}"
            if self._is_cache_valid(cache_key, ttl=3600):  # 1小时缓存
                return self.cache[cache_key]['data']
            
            # 在线程池中执行
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            hist = await loop.run_in_executor(
                None, 
                lambda: ticker.history(period=period, interval=interval)
            )
            
            if not hist.empty:
                # 缓存数据
                self.cache[cache_key] = {
                    'data': hist,
                    'timestamp': datetime.now()
                }
                
                return hist
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 历史数据失败: {e}")
            return None
    
    async def get_market_sentiment(self) -> Dict[str, Any]:
        """获取市场情绪数据"""
        try:
            # 检查缓存
            cache_key = "market_sentiment"
            if self._is_cache_valid(cache_key, ttl=1800):  # 30分钟缓存
                return self.cache[cache_key]['data']
            
            sentiment_data = {
                'vix_level': await self._get_vix_level(),
                'news_sentiment': await self._get_news_sentiment(),
                'social_sentiment': await self._get_social_sentiment(),
                'timestamp': datetime.now().isoformat()
            }
            
            # 计算综合情绪分数
            sentiment_data['composite_score'] = self._calculate_composite_sentiment(sentiment_data)
            
            # 缓存数据
            self.cache[cache_key] = {
                'data': sentiment_data,
                'timestamp': datetime.now()
            }
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"❌ 获取市场情绪数据失败: {e}")
            return {
                'composite_score': 0.0,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _get_vix_level(self) -> float:
        """获取VIX恐慌指数"""
        try:
            vix_data = await self.get_real_time_data('VIX')
            if vix_data:
                return vix_data.get('price', 20.0)
            return 20.0
        except:
            return 20.0
    
    async def _get_news_sentiment(self) -> Dict[str, Any]:
        """获取新闻情绪"""
        try:
            # 这里应该集成新闻API
            # 简化实现：返回模拟数据
            import random
            
            sentiment_score = random.uniform(-0.5, 0.5)
            
            return {
                'score': sentiment_score,
                'positive_count': random.randint(10, 50),
                'negative_count': random.randint(5, 30),
                'neutral_count': random.randint(20, 100)
            }
            
        except Exception as e:
            logger.debug(f"获取新闻情绪失败: {e}")
            return {'score': 0.0}
    
    async def _get_social_sentiment(self) -> Dict[str, Any]:
        """获取社交媒体情绪"""
        try:
            # 这里应该集成社交媒体API
            # 简化实现：返回模拟数据
            import random
            
            return {
                'twitter_sentiment': random.uniform(-0.3, 0.3),
                'reddit_sentiment': random.uniform(-0.2, 0.4),
                'mentions_count': random.randint(100, 1000)
            }
            
        except Exception as e:
            logger.debug(f"获取社交媒体情绪失败: {e}")
            return {'twitter_sentiment': 0.0, 'reddit_sentiment': 0.0}
    
    def _calculate_composite_sentiment(self, sentiment_data: Dict[str, Any]) -> float:
        """计算综合情绪分数"""
        try:
            # VIX影响（VIX越高，情绪越负面）
            vix_level = sentiment_data.get('vix_level', 20.0)
            vix_sentiment = max(-1.0, min(1.0, (25.0 - vix_level) / 10.0))
            
            # 新闻情绪
            news_sentiment = sentiment_data.get('news_sentiment', {}).get('score', 0.0)
            
            # 社交媒体情绪
            social_data = sentiment_data.get('social_sentiment', {})
            social_sentiment = (
                social_data.get('twitter_sentiment', 0.0) + 
                social_data.get('reddit_sentiment', 0.0)
            ) / 2
            
            # 加权平均
            composite = (
                vix_sentiment * 0.4 +
                news_sentiment * 0.35 +
                social_sentiment * 0.25
            )
            
            return max(-1.0, min(1.0, composite))
            
        except Exception as e:
            logger.debug(f"计算综合情绪分数失败: {e}")
            return 0.0
    
    async def get_batch_data(self, symbols: List[str]) -> Dict[str, Any]:
        """批量获取数据"""
        try:
            # 并行获取数据
            tasks = []
            for symbol in symbols:
                task = asyncio.create_task(self.get_real_time_data(symbol))
                tasks.append((symbol, task))
            
            # 等待所有任务完成
            results = {}
            for symbol, task in tasks:
                try:
                    data = await task
                    if data:
                        results[symbol] = data
                except Exception as e:
                    logger.error(f"❌ 获取 {symbol} 数据失败: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 批量获取数据失败: {e}")
            return {}
    
    def _is_cache_valid(self, cache_key: str, ttl: int = None) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache:
            return False
        
        cache_ttl = ttl or self.cache_ttl
        cache_time = self.cache[cache_key]['timestamp']
        
        return (datetime.now() - cache_time).seconds < cache_ttl
    
    def clear_cache(self):
        """清理缓存"""
        self.cache.clear()
        logger.info("🧹 市场数据缓存已清理")
    
    async def get_market_status(self) -> Dict[str, Any]:
        """获取市场状态"""
        try:
            now = datetime.now()
            
            # 简化的市场状态判断
            is_weekend = now.weekday() >= 5
            is_trading_hours = 9 <= now.hour <= 16
            
            market_status = {
                'is_open': not is_weekend and is_trading_hours,
                'current_time': now.isoformat(),
                'next_open': self._get_next_market_open(),
                'next_close': self._get_next_market_close(),
                'timezone': 'US/Eastern'
            }
            
            return market_status
            
        except Exception as e:
            logger.error(f"❌ 获取市场状态失败: {e}")
            return {'is_open': False}
    
    def _get_next_market_open(self) -> str:
        """获取下次开盘时间"""
        # 简化实现
        now = datetime.now()
        if now.weekday() < 5 and now.hour < 9:
            # 今天还没开盘
            next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        else:
            # 下一个工作日开盘
            days_ahead = 7 - now.weekday() if now.weekday() >= 5 else 1
            next_open = (now + timedelta(days=days_ahead)).replace(
                hour=9, minute=30, second=0, microsecond=0
            )
        
        return next_open.isoformat()
    
    def _get_next_market_close(self) -> str:
        """获取下次收盘时间"""
        # 简化实现
        now = datetime.now()
        if now.weekday() < 5 and now.hour < 16:
            # 今天还没收盘
            next_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        else:
            # 下一个工作日收盘
            days_ahead = 7 - now.weekday() if now.weekday() >= 5 else 1
            next_close = (now + timedelta(days=days_ahead)).replace(
                hour=16, minute=0, second=0, microsecond=0
            )
        
        return next_close.isoformat()
    
    async def shutdown(self):
        """关闭数据提供者"""
        logger.info("🛑 关闭市场数据提供者...")
        
        if self.session:
            await self.session.close()
        
        self.clear_cache()
        self.is_initialized = False
        
        logger.info("✅ 市场数据提供者已关闭")
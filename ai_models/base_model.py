#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI交易模型基类
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class TradingDecision:
    """交易决策"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    quantity: int
    confidence: float  # 0.0 - 1.0
    reason: str
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_level: str = "medium"  # low, medium, high


@dataclass
class MarketAnalysis:
    """市场分析结果"""
    symbol: str
    trend: str  # bullish, bearish, neutral
    strength: float  # 0.0 - 1.0
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    technical_indicators: Dict[str, float] = None
    sentiment_score: float = 0.0
    news_impact: str = "neutral"
    
    def __post_init__(self):
        if self.technical_indicators is None:
            self.technical_indicators = {}


class BaseAIModel(ABC):
    """AI交易模型基类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_active = False
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0
        }
        self.trade_history = []
        self.analysis_cache = {}
        self.last_analysis_time = None
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化模型"""
        pass
    
    @abstractmethod
    async def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, MarketAnalysis]:
        """分析市场数据"""
        pass
    
    @abstractmethod
    async def make_trading_decision(self, market_data: Dict[str, Any]) -> Optional[TradingDecision]:
        """做出交易决策"""
        pass
    
    async def get_portfolio_allocation(self, available_cash: float, current_positions: Dict) -> Dict[str, float]:
        """获取投资组合配置建议"""
        # 默认实现：等权重配置
        symbols = self.config.get('target_symbols', ['AAPL', 'MSFT', 'GOOGL'])
        allocation = {}
        
        weight_per_symbol = 1.0 / len(symbols)
        for symbol in symbols:
            allocation[symbol] = weight_per_symbol
        
        return allocation
    
    async def update_performance(self, trade_result: Dict[str, Any]):
        """更新性能指标"""
        self.performance_metrics['total_trades'] += 1
        
        if trade_result.get('pnl', 0) > 0:
            self.performance_metrics['winning_trades'] += 1
        
        self.performance_metrics['total_return'] += trade_result.get('pnl', 0)
        
        # 计算胜率
        if self.performance_metrics['total_trades'] > 0:
            win_rate = self.performance_metrics['winning_trades'] / self.performance_metrics['total_trades']
            self.performance_metrics['win_rate'] = win_rate
        
        # 记录交易历史
        self.trade_history.append({
            'timestamp': datetime.now().isoformat(),
            'symbol': trade_result.get('symbol'),
            'action': trade_result.get('action'),
            'quantity': trade_result.get('quantity'),
            'price': trade_result.get('price'),
            'pnl': trade_result.get('pnl', 0)
        })
        
        logger.info(
            f"📊 {self.name} 性能更新: 总交易 {self.performance_metrics['total_trades']}, "
            f"胜率 {self.performance_metrics.get('win_rate', 0):.1%}, "
            f"总收益 ${self.performance_metrics['total_return']:.2f}"
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.performance_metrics.copy()
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """获取交易历史"""
        return self.trade_history[-limit:]
    
    async def should_trade(self, market_data: Dict[str, Any]) -> bool:
        """判断是否应该交易"""
        # 基础检查
        if not self.is_active:
            return False
        
        # 检查市场数据是否充足
        if not market_data or len(market_data) < 3:
            logger.warning(f"⚠️ {self.name}: 市场数据不足")
            return False
        
        # 检查是否在交易时间
        now = datetime.now()
        if now.hour < 9 or now.hour > 16:  # 简化的交易时间检查
            return False
        
        return True
    
    def _calculate_position_size(self, symbol: str, confidence: float, available_cash: float, 
                               current_price: float, risk_level: str = "medium") -> int:
        """计算仓位大小"""
        # 基于Kelly公式的简化版本
        base_allocation = 0.1  # 基础配置10%
        
        # 根据置信度调整
        confidence_multiplier = confidence
        
        # 根据风险等级调整
        risk_multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5
        }
        risk_multiplier = risk_multipliers.get(risk_level, 1.0)
        
        # 计算投资金额
        investment_amount = available_cash * base_allocation * confidence_multiplier * risk_multiplier
        
        # 计算股数
        quantity = int(investment_amount / current_price)
        
        # 确保至少买1股，但不超过可用资金
        max_quantity = int(available_cash * 0.2 / current_price)  # 最多20%
        quantity = max(1, min(quantity, max_quantity))
        
        return quantity
    
    def _analyze_technical_indicators(self, price_data: List[float]) -> Dict[str, float]:
        """分析技术指标"""
        if len(price_data) < 20:
            return {}
        
        import numpy as np
        
        prices = np.array(price_data)
        
        indicators = {}
        
        # 简单移动平均线
        if len(prices) >= 5:
            indicators['sma_5'] = np.mean(prices[-5:])
        if len(prices) >= 10:
            indicators['sma_10'] = np.mean(prices[-10:])
        if len(prices) >= 20:
            indicators['sma_20'] = np.mean(prices[-20:])
        
        # RSI (简化版)
        if len(prices) >= 14:
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                indicators['rsi'] = rsi
        
        # 布林带
        if len(prices) >= 20:
            sma_20 = np.mean(prices[-20:])
            std_20 = np.std(prices[-20:])
            indicators['bollinger_upper'] = sma_20 + (2 * std_20)
            indicators['bollinger_lower'] = sma_20 - (2 * std_20)
            indicators['bollinger_middle'] = sma_20
        
        # 当前价格相对位置
        current_price = prices[-1]
        if 'bollinger_upper' in indicators and 'bollinger_lower' in indicators:
            bb_range = indicators['bollinger_upper'] - indicators['bollinger_lower']
            if bb_range > 0:
                bb_position = (current_price - indicators['bollinger_lower']) / bb_range
                indicators['bollinger_position'] = bb_position
        
        return indicators
    
    def _interpret_sentiment(self, sentiment_data: Dict[str, Any]) -> float:
        """解释情感分析数据"""
        if not sentiment_data:
            return 0.0
        
        # 简化的情感分析解释
        sentiment_score = sentiment_data.get('compound', 0.0)
        
        # 标准化到-1到1的范围
        normalized_score = max(-1.0, min(1.0, sentiment_score))
        
        return normalized_score
    
    async def cleanup(self):
        """清理资源"""
        self.is_active = False
        logger.info(f"🧹 {self.name} 模型已清理")
    
    def __str__(self):
        return f"{self.name} (活跃: {self.is_active}, 交易次数: {self.performance_metrics['total_trades']})"
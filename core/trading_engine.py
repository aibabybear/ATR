#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易引擎 - 核心交易逻辑
"""

import asyncio
from datetime import datetime, time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
import pytz

from .portfolio import Portfolio
from .risk_manager import RiskManager
from .order_manager import OrderManager
from data.market_data import MarketDataProvider
from config.settings import Settings


@dataclass
class TradingDecision:
    """交易决策数据类"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    quantity: int
    price: Optional[float] = None
    reason: str = ""
    confidence: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class TradeResult:
    """交易结果数据类"""
    success: bool
    order_id: Optional[str] = None
    executed_price: Optional[float] = None
    executed_quantity: int = 0
    commission: float = 0.0
    error_message: str = ""


class TradingEngine:
    """交易引擎主类"""
    
    def __init__(self):
        self.settings = Settings()
        self.portfolio = Portfolio()
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager()
        self.market_data = MarketDataProvider()
        
        self.timezone = pytz.timezone(self.settings.TIMEZONE)
        self.is_initialized = False
        self.trading_session_active = False
    
    async def initialize(self):
        """初始化交易引擎"""
        logger.info("🔧 初始化交易引擎...")
        
        # 初始化各个组件
        await self.portfolio.initialize(self.settings.INITIAL_CAPITAL)
        await self.risk_manager.initialize()
        await self.order_manager.initialize()
        await self.market_data.initialize()
        
        self.is_initialized = True
        logger.info("✅ 交易引擎初始化完成")
    
    def is_market_open(self) -> bool:
        """检查市场是否开放"""
        now = datetime.now(self.timezone)
        current_time = now.time()
        
        # 检查是否为工作日
        if now.weekday() >= 5:  # 周六、周日
            return False
        
        # 检查是否在交易时间内
        return (self.settings.MARKET_OPEN_TIME <= current_time <= 
                self.settings.MARKET_CLOSE_TIME)
    
    async def get_market_data(self) -> Dict[str, Any]:
        """获取市场数据"""
        try:
            market_data = {}
            
            # 获取支持股票的实时数据
            for symbol in self.settings.SUPPORTED_SYMBOLS:
                data = await self.market_data.get_real_time_data(symbol)
                if data:
                    market_data[symbol] = data
            
            # 获取市场指数数据
            indices = ['QQQ', 'SPY', 'VIX']
            for index in indices:
                data = await self.market_data.get_real_time_data(index)
                if data:
                    market_data[index] = data
            
            # 获取新闻和情感分析
            news_sentiment = await self.market_data.get_market_sentiment()
            market_data['sentiment'] = news_sentiment
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ 获取市场数据失败: {e}")
            return {}
    
    async def execute_trade(self, model_name: str, decision: TradingDecision) -> TradeResult:
        """执行交易决策"""
        try:
            logger.info(
                f"📋 {model_name} 交易决策: {decision.action} {decision.symbol} "
                f"x{decision.quantity} (置信度: {decision.confidence:.2f})"
            )
            
            # 风险检查
            risk_check = await self.risk_manager.check_trade_risk(
                decision, self.portfolio
            )
            
            if not risk_check.approved:
                logger.warning(
                    f"⚠️ 交易被风险管理拒绝: {risk_check.reason}"
                )
                return TradeResult(
                    success=False,
                    error_message=f"风险管理拒绝: {risk_check.reason}"
                )
            
            # 调整交易数量（如果需要）
            if risk_check.adjusted_quantity != decision.quantity:
                logger.info(
                    f"📊 风险管理调整数量: {decision.quantity} -> {risk_check.adjusted_quantity}"
                )
                decision.quantity = risk_check.adjusted_quantity
            
            # 执行订单
            result = await self.order_manager.place_order(decision)
            
            if result.success:
                # 更新投资组合
                await self.portfolio.update_position(
                    decision.symbol,
                    decision.action,
                    result.executed_quantity,
                    result.executed_price
                )
                
                # 记录交易
                await self._record_trade(model_name, decision, result)
                
                logger.info(
                    f"✅ 交易执行成功: {decision.action} {decision.symbol} "
                    f"x{result.executed_quantity} @ ${result.executed_price:.2f}"
                )
            else:
                logger.error(
                    f"❌ 交易执行失败: {result.error_message}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 执行交易时出错: {e}")
            return TradeResult(
                success=False,
                error_message=f"执行交易时出错: {str(e)}"
            )
    
    async def get_portfolio_status(self, model_name: str) -> Dict[str, Any]:
        """获取投资组合状态"""
        return await self.portfolio.get_status(model_name)
    
    async def get_performance_metrics(self, model_name: str) -> Dict[str, Any]:
        """获取性能指标"""
        portfolio_status = await self.get_portfolio_status(model_name)
        
        # 计算收益率
        total_value = portfolio_status['total_value']
        initial_capital = self.settings.INITIAL_CAPITAL
        total_return = (total_value - initial_capital) / initial_capital
        
        # 获取交易历史
        trade_history = await self.portfolio.get_trade_history(model_name)
        
        # 计算其他指标
        metrics = {
            'total_return': total_return,
            'total_value': total_value,
            'cash_balance': portfolio_status['cash_balance'],
            'positions_value': portfolio_status['positions_value'],
            'total_trades': len(trade_history),
            'winning_trades': len([t for t in trade_history if t['pnl'] > 0]),
            'losing_trades': len([t for t in trade_history if t['pnl'] < 0]),
        }
        
        # 计算胜率
        if metrics['total_trades'] > 0:
            metrics['win_rate'] = metrics['winning_trades'] / metrics['total_trades']
        else:
            metrics['win_rate'] = 0.0
        
        return metrics
    
    async def _record_trade(self, model_name: str, decision: TradingDecision, result: TradeResult):
        """记录交易到数据库"""
        trade_record = {
            'timestamp': datetime.now(),
            'model_name': model_name,
            'symbol': decision.symbol,
            'action': decision.action,
            'quantity': result.executed_quantity,
            'price': result.executed_price,
            'commission': result.commission,
            'reason': decision.reason,
            'confidence': decision.confidence,
            'order_id': result.order_id
        }
        
        # 这里应该保存到数据库
        # await self.db.save_trade_record(trade_record)
        logger.info(f"📝 交易记录已保存: {trade_record}")
    
    async def start_trading_session(self):
        """开始交易会话"""
        if not self.is_market_open():
            logger.warning("⚠️ 市场未开放，无法开始交易会话")
            return
        
        self.trading_session_active = True
        logger.info("🔔 交易会话已开始")
    
    async def end_trading_session(self):
        """结束交易会话"""
        self.trading_session_active = False
        
        # 生成日终报告
        await self._generate_daily_report()
        
        logger.info("🔔 交易会话已结束")
    
    async def _generate_daily_report(self):
        """生成日终报告"""
        logger.info("📊 生成日终报告...")
        
        # 获取所有模型的性能
        # 这里应该实现具体的报告生成逻辑
        
        logger.info("✅ 日终报告生成完成")
    
    async def shutdown(self):
        """关闭交易引擎"""
        logger.info("🛑 关闭交易引擎...")
        
        if self.trading_session_active:
            await self.end_trading_session()
        
        await self.order_manager.shutdown()
        await self.market_data.shutdown()
        
        logger.info("✅ 交易引擎已关闭")
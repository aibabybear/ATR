#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合管理模块
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from loguru import logger


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def market_value(self) -> float:
        """市场价值"""
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return (self.current_price - self.avg_cost) * self.quantity
    
    @property
    def unrealized_pnl_percent(self) -> float:
        """未实现盈亏百分比"""
        if self.avg_cost == 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost


@dataclass
class TradeRecord:
    """交易记录"""
    timestamp: datetime
    symbol: str
    action: str  # 'buy', 'sell'
    quantity: int
    price: float
    commission: float
    pnl: float = 0.0  # 已实现盈亏
    model_name: str = ""
    reason: str = ""


class Portfolio:
    """投资组合管理类"""
    
    def __init__(self):
        self.initial_capital = 0.0
        self.cash_balance = 0.0
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[TradeRecord] = []
        self.model_portfolios: Dict[str, Dict] = defaultdict(dict)
        self.is_initialized = False
    
    async def initialize(self, initial_capital: float):
        """初始化投资组合"""
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.is_initialized = True
        
        logger.info(f"💰 投资组合初始化完成，初始资金: ${initial_capital:,.2f}")
    
    async def update_position(self, symbol: str, action: str, quantity: int, price: float, model_name: str = ""):
        """更新持仓"""
        commission = self._calculate_commission(quantity, price)
        
        if action.lower() == 'buy':
            await self._buy_stock(symbol, quantity, price, commission, model_name)
        elif action.lower() == 'sell':
            await self._sell_stock(symbol, quantity, price, commission, model_name)
        
        # 记录交易
        trade_record = TradeRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            commission=commission,
            model_name=model_name
        )
        
        self.trade_history.append(trade_record)
        
        logger.info(
            f"📊 持仓更新: {action.upper()} {symbol} x{quantity} @ ${price:.2f} "
            f"(手续费: ${commission:.2f})"
        )
    
    async def _buy_stock(self, symbol: str, quantity: int, price: float, commission: float, model_name: str):
        """买入股票"""
        total_cost = quantity * price + commission
        
        if total_cost > self.cash_balance:
            raise ValueError(f"资金不足: 需要 ${total_cost:.2f}, 可用 ${self.cash_balance:.2f}")
        
        # 更新现金余额
        self.cash_balance -= total_cost
        
        # 更新持仓
        if symbol in self.positions:
            # 已有持仓，计算新的平均成本
            existing_pos = self.positions[symbol]
            total_quantity = existing_pos.quantity + quantity
            total_cost_basis = (existing_pos.quantity * existing_pos.avg_cost + 
                              quantity * price)
            new_avg_cost = total_cost_basis / total_quantity
            
            self.positions[symbol].quantity = total_quantity
            self.positions[symbol].avg_cost = new_avg_cost
        else:
            # 新建持仓
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=price,
                current_price=price
            )
    
    async def _sell_stock(self, symbol: str, quantity: int, price: float, commission: float, model_name: str):
        """卖出股票"""
        if symbol not in self.positions:
            raise ValueError(f"没有 {symbol} 的持仓")
        
        position = self.positions[symbol]
        if position.quantity < quantity:
            raise ValueError(
                f"持仓不足: 尝试卖出 {quantity} 股，但只有 {position.quantity} 股"
            )
        
        # 计算已实现盈亏
        realized_pnl = (price - position.avg_cost) * quantity - commission
        
        # 更新现金余额
        proceeds = quantity * price - commission
        self.cash_balance += proceeds
        
        # 更新持仓
        position.quantity -= quantity
        
        # 如果全部卖出，删除持仓
        if position.quantity == 0:
            del self.positions[symbol]
        
        # 更新交易记录的已实现盈亏
        if self.trade_history:
            self.trade_history[-1].pnl = realized_pnl
        
        logger.info(f"💰 已实现盈亏: ${realized_pnl:.2f}")
    
    async def update_market_prices(self, price_data: Dict[str, float]):
        """更新市场价格"""
        for symbol, position in self.positions.items():
            if symbol in price_data:
                position.current_price = price_data[symbol]
                position.last_updated = datetime.now()
    
    async def get_status(self, model_name: str = "") -> Dict[str, Any]:
        """获取投资组合状态"""
        # 计算持仓总价值
        positions_value = sum(pos.market_value for pos in self.positions.values())
        total_value = self.cash_balance + positions_value
        
        # 计算总收益
        total_return = (total_value - self.initial_capital) / self.initial_capital
        
        # 计算未实现盈亏
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        # 计算已实现盈亏
        realized_pnl = sum(trade.pnl for trade in self.trade_history)
        
        status = {
            'cash_balance': self.cash_balance,
            'positions_value': positions_value,
            'total_value': total_value,
            'total_return': total_return,
            'total_return_percent': total_return * 100,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': unrealized_pnl + realized_pnl,
            'positions_count': len(self.positions),
            'trades_count': len(self.trade_history)
        }
        
        return status
    
    async def get_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions.copy()
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """获取特定股票的持仓"""
        return self.positions.get(symbol)
    
    async def get_trade_history(self, model_name: str = "", limit: int = 100) -> List[Dict]:
        """获取交易历史"""
        trades = self.trade_history
        
        if model_name:
            trades = [t for t in trades if t.model_name == model_name]
        
        # 转换为字典格式
        trade_dicts = []
        for trade in trades[-limit:]:
            trade_dict = {
                'timestamp': trade.timestamp.isoformat(),
                'symbol': trade.symbol,
                'action': trade.action,
                'quantity': trade.quantity,
                'price': trade.price,
                'commission': trade.commission,
                'pnl': trade.pnl,
                'model_name': trade.model_name,
                'reason': trade.reason
            }
            trade_dicts.append(trade_dict)
        
        return trade_dicts
    
    async def get_top_positions(self, limit: int = 10) -> List[Dict]:
        """获取最大持仓"""
        positions = []
        
        for symbol, position in self.positions.items():
            pos_dict = {
                'symbol': symbol,
                'quantity': position.quantity,
                'avg_cost': position.avg_cost,
                'current_price': position.current_price,
                'market_value': position.market_value,
                'unrealized_pnl': position.unrealized_pnl,
                'unrealized_pnl_percent': position.unrealized_pnl_percent * 100
            }
            positions.append(pos_dict)
        
        # 按市场价值排序
        positions.sort(key=lambda x: x['market_value'], reverse=True)
        
        return positions[:limit]
    
    async def calculate_portfolio_metrics(self) -> Dict[str, float]:
        """计算投资组合指标"""
        if not self.trade_history:
            return {}
        
        # 计算日收益率序列
        daily_returns = self._calculate_daily_returns()
        
        if not daily_returns:
            return {}
        
        import numpy as np
        
        returns_array = np.array(daily_returns)
        
        # 计算各种指标
        metrics = {
            'volatility': np.std(returns_array) * np.sqrt(252),  # 年化波动率
            'sharpe_ratio': self._calculate_sharpe_ratio(returns_array),
            'max_drawdown': self._calculate_max_drawdown(),
            'win_rate': self._calculate_win_rate(),
            'avg_win': self._calculate_avg_win(),
            'avg_loss': self._calculate_avg_loss()
        }
        
        return metrics
    
    def _calculate_commission(self, quantity: int, price: float) -> float:
        """计算手续费"""
        # 简单的手续费模型：每股0.01美元，最低1美元
        commission = max(quantity * 0.01, 1.0)
        return commission
    
    def _calculate_daily_returns(self) -> List[float]:
        """计算日收益率"""
        # 这里应该实现基于交易历史的日收益率计算
        # 简化实现
        return []
    
    def _calculate_sharpe_ratio(self, returns: 'np.array') -> float:
        """计算夏普比率"""
        if len(returns) == 0:
            return 0.0
        
        import numpy as np
        
        excess_returns = returns - 0.02/252  # 假设无风险利率2%
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        # 简化实现
        return 0.0
    
    def _calculate_win_rate(self) -> float:
        """计算胜率"""
        profitable_trades = [t for t in self.trade_history if t.pnl > 0]
        total_trades = len([t for t in self.trade_history if t.pnl != 0])
        
        if total_trades == 0:
            return 0.0
        
        return len(profitable_trades) / total_trades
    
    def _calculate_avg_win(self) -> float:
        """计算平均盈利"""
        winning_trades = [t.pnl for t in self.trade_history if t.pnl > 0]
        
        if not winning_trades:
            return 0.0
        
        return sum(winning_trades) / len(winning_trades)
    
    def _calculate_avg_loss(self) -> float:
        """计算平均亏损"""
        losing_trades = [t.pnl for t in self.trade_history if t.pnl < 0]
        
        if not losing_trades:
            return 0.0
        
        return sum(losing_trades) / len(losing_trades)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理模块
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
import numpy as np

from config.settings import Settings


@dataclass
class RiskCheckResult:
    """风险检查结果"""
    approved: bool
    reason: str = ""
    adjusted_quantity: int = 0
    risk_score: float = 0.0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class RiskMetrics:
    """风险指标"""
    portfolio_var: float = 0.0  # 投资组合VaR
    portfolio_beta: float = 1.0  # 投资组合Beta
    concentration_risk: float = 0.0  # 集中度风险
    leverage_ratio: float = 0.0  # 杠杆比率
    max_drawdown: float = 0.0  # 最大回撤
    volatility: float = 0.0  # 波动率


class RiskManager:
    """风险管理器"""
    
    def __init__(self):
        self.settings = Settings()
        self.risk_limits = self.settings.RISK_MANAGEMENT
        self.daily_losses = {}
        self.position_limits = {}
        self.correlation_matrix = {}
        self.volatility_data = {}
        self.is_initialized = False
    
    async def initialize(self):
        """初始化风险管理器"""
        logger.info("🛡️ 初始化风险管理器...")
        
        # 初始化风险限制
        await self._load_risk_limits()
        
        # 初始化相关性矩阵
        await self._initialize_correlation_matrix()
        
        # 初始化波动率数据
        await self._initialize_volatility_data()
        
        self.is_initialized = True
        logger.info("✅ 风险管理器初始化完成")
    
    async def check_trade_risk(self, decision, portfolio) -> RiskCheckResult:
        """检查交易风险"""
        warnings = []
        risk_score = 0.0
        
        # 1. 检查资金充足性
        cash_check = await self._check_cash_availability(decision, portfolio)
        if not cash_check.approved:
            return cash_check
        
        # 2. 检查仓位限制
        position_check = await self._check_position_limits(decision, portfolio)
        if not position_check.approved:
            return position_check
        warnings.extend(position_check.warnings)
        risk_score += position_check.risk_score
        
        # 3. 检查日损失限制
        daily_loss_check = await self._check_daily_loss_limit(portfolio)
        if not daily_loss_check.approved:
            return daily_loss_check
        warnings.extend(daily_loss_check.warnings)
        
        # 4. 检查集中度风险
        concentration_check = await self._check_concentration_risk(decision, portfolio)
        warnings.extend(concentration_check.warnings)
        risk_score += concentration_check.risk_score
        
        # 5. 检查相关性风险
        correlation_check = await self._check_correlation_risk(decision, portfolio)
        warnings.extend(correlation_check.warnings)
        risk_score += correlation_check.risk_score
        
        # 6. 检查波动率风险
        volatility_check = await self._check_volatility_risk(decision, portfolio)
        warnings.extend(volatility_check.warnings)
        risk_score += volatility_check.risk_score
        
        # 7. 动态调整交易数量
        adjusted_quantity = await self._calculate_optimal_position_size(
            decision, portfolio, risk_score
        )
        
        return RiskCheckResult(
            approved=True,
            adjusted_quantity=adjusted_quantity,
            risk_score=risk_score,
            warnings=warnings,
            reason="风险检查通过"
        )
    
    async def _check_cash_availability(self, decision, portfolio) -> RiskCheckResult:
        """检查资金充足性"""
        if decision.action.lower() != 'buy':
            return RiskCheckResult(approved=True, adjusted_quantity=decision.quantity)
        
        # 估算交易成本
        estimated_price = decision.price or 100.0  # 如果没有指定价格，使用估算价格
        total_cost = decision.quantity * estimated_price * 1.01  # 加1%缓冲
        
        if total_cost > portfolio.cash_balance:
            # 计算最大可买数量
            max_quantity = int(portfolio.cash_balance / (estimated_price * 1.01))
            
            if max_quantity == 0:
                return RiskCheckResult(
                    approved=False,
                    reason=f"资金不足: 需要 ${total_cost:.2f}, 可用 ${portfolio.cash_balance:.2f}"
                )
            
            return RiskCheckResult(
                approved=True,
                adjusted_quantity=max_quantity,
                warnings=[f"资金不足，数量调整为 {max_quantity}"]
            )
        
        return RiskCheckResult(approved=True, adjusted_quantity=decision.quantity)
    
    async def _check_position_limits(self, decision, portfolio) -> RiskCheckResult:
        """检查仓位限制"""
        warnings = []
        risk_score = 0.0
        
        # 获取当前持仓
        current_position = await portfolio.get_position(decision.symbol)
        current_quantity = current_position.quantity if current_position else 0
        
        # 计算交易后的数量
        if decision.action.lower() == 'buy':
            new_quantity = current_quantity + decision.quantity
        else:
            new_quantity = current_quantity - decision.quantity
        
        # 检查单一股票仓位限制
        portfolio_status = await portfolio.get_status()
        total_value = portfolio_status['total_value']
        
        estimated_price = decision.price or 100.0
        position_value = new_quantity * estimated_price
        position_weight = position_value / total_value if total_value > 0 else 0
        
        max_position_size = self.settings.MAX_POSITION_SIZE
        
        if position_weight > max_position_size:
            # 计算最大允许数量
            max_value = total_value * max_position_size
            max_quantity = int(max_value / estimated_price)
            
            if decision.action.lower() == 'buy':
                adjusted_quantity = max(0, max_quantity - current_quantity)
            else:
                adjusted_quantity = decision.quantity
            
            warnings.append(
                f"单一股票仓位超限: {position_weight:.1%} > {max_position_size:.1%}, "
                f"调整数量为 {adjusted_quantity}"
            )
            risk_score += 0.3
            
            return RiskCheckResult(
                approved=True,
                adjusted_quantity=adjusted_quantity,
                warnings=warnings,
                risk_score=risk_score
            )
        
        return RiskCheckResult(
            approved=True,
            adjusted_quantity=decision.quantity,
            warnings=warnings,
            risk_score=risk_score
        )
    
    async def _check_daily_loss_limit(self, portfolio) -> RiskCheckResult:
        """检查日损失限制"""
        today = datetime.now().date()
        
        # 获取今日交易记录
        trade_history = await portfolio.get_trade_history()
        today_trades = [
            trade for trade in trade_history 
            if datetime.fromisoformat(trade['timestamp']).date() == today
        ]
        
        # 计算今日已实现损失
        today_pnl = sum(trade['pnl'] for trade in today_trades)
        
        # 计算未实现损失
        portfolio_status = await portfolio.get_status()
        unrealized_pnl = portfolio_status.get('unrealized_pnl', 0)
        
        total_daily_pnl = today_pnl + (unrealized_pnl if unrealized_pnl < 0 else 0)
        
        max_daily_loss = self.risk_limits['max_daily_loss']
        initial_capital = portfolio.initial_capital
        max_loss_amount = initial_capital * max_daily_loss
        
        if abs(total_daily_pnl) > max_loss_amount:
            return RiskCheckResult(
                approved=False,
                reason=f"超过日损失限制: ${abs(total_daily_pnl):.2f} > ${max_loss_amount:.2f}"
            )
        
        # 如果接近限制，发出警告
        if abs(total_daily_pnl) > max_loss_amount * 0.8:
            return RiskCheckResult(
                approved=True,
                warnings=[f"接近日损失限制: ${abs(total_daily_pnl):.2f} / ${max_loss_amount:.2f}"]
            )
        
        return RiskCheckResult(approved=True)
    
    async def _check_concentration_risk(self, decision, portfolio) -> RiskCheckResult:
        """检查集中度风险"""
        warnings = []
        risk_score = 0.0
        
        # 获取当前持仓分布
        positions = await portfolio.get_positions()
        
        if len(positions) < 5:  # 持仓过于集中
            warnings.append("持仓过于集中，建议增加多样化")
            risk_score += 0.2
        
        # 检查行业集中度（简化实现）
        # 这里应该根据股票的行业分类来计算
        
        return RiskCheckResult(
            approved=True,
            warnings=warnings,
            risk_score=risk_score
        )
    
    async def _check_correlation_risk(self, decision, portfolio) -> RiskCheckResult:
        """检查相关性风险"""
        warnings = []
        risk_score = 0.0
        
        # 获取当前持仓
        positions = await portfolio.get_positions()
        
        # 检查与现有持仓的相关性
        high_correlation_count = 0
        correlation_threshold = self.risk_limits.get('correlation_threshold', 0.7)
        
        for symbol in positions.keys():
            correlation = self._get_correlation(decision.symbol, symbol)
            if correlation > correlation_threshold:
                high_correlation_count += 1
        
        if high_correlation_count > 3:
            warnings.append(
                f"与 {high_correlation_count} 个持仓高度相关 (>{correlation_threshold:.1%})"
            )
            risk_score += 0.2
        
        return RiskCheckResult(
            approved=True,
            warnings=warnings,
            risk_score=risk_score
        )
    
    async def _check_volatility_risk(self, decision, portfolio) -> RiskCheckResult:
        """检查波动率风险"""
        warnings = []
        risk_score = 0.0
        
        # 获取股票的历史波动率
        volatility = self._get_volatility(decision.symbol)
        
        if volatility > 0.4:  # 年化波动率超过40%
            warnings.append(f"{decision.symbol} 波动率较高: {volatility:.1%}")
            risk_score += 0.1
        
        return RiskCheckResult(
            approved=True,
            warnings=warnings,
            risk_score=risk_score
        )
    
    async def _calculate_optimal_position_size(self, decision, portfolio, risk_score: float) -> int:
        """计算最优仓位大小"""
        base_quantity = decision.quantity
        
        # 根据风险评分调整仓位
        if risk_score > 0.5:
            # 高风险，减少仓位
            adjustment_factor = max(0.5, 1.0 - risk_score)
            adjusted_quantity = int(base_quantity * adjustment_factor)
        else:
            adjusted_quantity = base_quantity
        
        return max(1, adjusted_quantity)  # 至少1股
    
    async def calculate_portfolio_risk(self, portfolio) -> RiskMetrics:
        """计算投资组合风险指标"""
        positions = await portfolio.get_positions()
        
        if not positions:
            return RiskMetrics()
        
        # 计算投资组合VaR（简化实现）
        portfolio_var = await self._calculate_portfolio_var(positions)
        
        # 计算投资组合Beta
        portfolio_beta = await self._calculate_portfolio_beta(positions)
        
        # 计算集中度风险
        concentration_risk = await self._calculate_concentration_risk(positions)
        
        # 计算其他指标
        metrics = await portfolio.calculate_portfolio_metrics()
        
        return RiskMetrics(
            portfolio_var=portfolio_var,
            portfolio_beta=portfolio_beta,
            concentration_risk=concentration_risk,
            max_drawdown=metrics.get('max_drawdown', 0.0),
            volatility=metrics.get('volatility', 0.0)
        )
    
    async def _load_risk_limits(self):
        """加载风险限制"""
        # 这里可以从数据库或配置文件加载自定义风险限制
        pass
    
    async def _initialize_correlation_matrix(self):
        """初始化相关性矩阵"""
        # 这里应该加载历史相关性数据
        # 简化实现：使用随机相关性
        symbols = self.settings.SUPPORTED_SYMBOLS
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i != j:
                    # 简化：使用随机相关性
                    correlation = np.random.uniform(-0.5, 0.8)
                    self.correlation_matrix[f"{symbol1}_{symbol2}"] = correlation
    
    async def _initialize_volatility_data(self):
        """初始化波动率数据"""
        # 这里应该加载历史波动率数据
        # 简化实现：使用随机波动率
        for symbol in self.settings.SUPPORTED_SYMBOLS:
            self.volatility_data[symbol] = np.random.uniform(0.15, 0.6)
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """获取两个股票的相关性"""
        key = f"{symbol1}_{symbol2}"
        return self.correlation_matrix.get(key, 0.0)
    
    def _get_volatility(self, symbol: str) -> float:
        """获取股票的波动率"""
        return self.volatility_data.get(symbol, 0.3)
    
    async def _calculate_portfolio_var(self, positions) -> float:
        """计算投资组合VaR"""
        # 简化实现
        return 0.05
    
    async def _calculate_portfolio_beta(self, positions) -> float:
        """计算投资组合Beta"""
        # 简化实现
        return 1.0
    
    async def _calculate_concentration_risk(self, positions) -> float:
        """计算集中度风险"""
        if not positions:
            return 0.0
        
        # 计算赫芬达尔指数
        total_value = sum(pos.market_value for pos in positions.values())
        if total_value == 0:
            return 0.0
        
        hhi = sum((pos.market_value / total_value) ** 2 for pos in positions.values())
        return hhi
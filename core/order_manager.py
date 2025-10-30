#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单管理模块
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class Order:
    """订单数据类"""
    order_id: str
    symbol: str
    action: str  # 'buy', 'sell'
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    model_name: str = ""
    reason: str = ""
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class Fill:
    """成交记录"""
    fill_id: str
    order_id: str
    symbol: str
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.fills: List[Fill] = []
        self.is_initialized = False
        self.simulation_mode = True  # 默认模拟模式
        self.market_data_cache = {}
    
    async def initialize(self):
        """初始化订单管理器"""
        logger.info("📋 初始化订单管理器...")
        
        # 检查是否为模拟模式
        self.simulation_mode = True  # 暂时只支持模拟模式
        
        if self.simulation_mode:
            logger.info("🎮 运行在模拟交易模式")
        else:
            logger.info("💰 运行在真实交易模式")
        
        self.is_initialized = True
        logger.info("✅ 订单管理器初始化完成")
    
    async def place_order(self, decision) -> 'TradeResult':
        """下单"""
        from core.trading_engine import TradeResult
        
        try:
            # 创建订单
            order = await self._create_order(decision)
            
            # 提交订单
            result = await self._submit_order(order)
            
            if result.success:
                logger.info(
                    f"✅ 订单提交成功: {order.order_id} - {order.action} {order.symbol} x{order.quantity}"
                )
            else:
                logger.error(
                    f"❌ 订单提交失败: {result.error_message}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 下单过程出错: {e}")
            return TradeResult(
                success=False,
                error_message=f"下单过程出错: {str(e)}"
            )
    
    async def _create_order(self, decision) -> Order:
        """创建订单"""
        order_id = str(uuid.uuid4())
        
        # 确定订单类型
        if decision.price is None:
            order_type = OrderType.MARKET
        else:
            order_type = OrderType.LIMIT
        
        order = Order(
            order_id=order_id,
            symbol=decision.symbol,
            action=decision.action,
            quantity=decision.quantity,
            order_type=order_type,
            price=decision.price,
            stop_price=getattr(decision, 'stop_loss', None),
            model_name=getattr(decision, 'model_name', ''),
            reason=decision.reason
        )
        
        # 保存订单
        self.orders[order_id] = order
        
        return order
    
    async def _submit_order(self, order: Order) -> 'TradeResult':
        """提交订单"""
        from core.trading_engine import TradeResult
        
        try:
            if self.simulation_mode:
                return await self._simulate_order_execution(order)
            else:
                return await self._execute_real_order(order)
                
        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.updated_at = datetime.now()
            
            return TradeResult(
                success=False,
                error_message=f"订单执行失败: {str(e)}"
            )
    
    async def _simulate_order_execution(self, order: Order) -> 'TradeResult':
        """模拟订单执行"""
        from core.trading_engine import TradeResult
        
        # 获取当前市场价格
        current_price = await self._get_current_price(order.symbol)
        
        if current_price is None:
            order.status = OrderStatus.REJECTED
            return TradeResult(
                success=False,
                error_message=f"无法获取 {order.symbol} 的市场价格"
            )
        
        # 模拟订单执行逻辑
        if order.order_type == OrderType.MARKET:
            # 市价单立即成交
            execution_price = current_price
            
            # 添加一些滑点
            if order.action.lower() == 'buy':
                execution_price *= 1.001  # 买入时价格稍高
            else:
                execution_price *= 0.999  # 卖出时价格稍低
                
        elif order.order_type == OrderType.LIMIT:
            # 限价单检查是否能成交
            if order.action.lower() == 'buy' and current_price <= order.price:
                execution_price = order.price
            elif order.action.lower() == 'sell' and current_price >= order.price:
                execution_price = order.price
            else:
                # 限价单暂时无法成交
                order.status = OrderStatus.SUBMITTED
                return TradeResult(
                    success=True,
                    order_id=order.order_id,
                    executed_quantity=0,
                    error_message="限价单已提交，等待成交"
                )
        else:
            execution_price = current_price
        
        # 计算手续费
        commission = self._calculate_commission(order.quantity, execution_price)
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = execution_price
        order.commission = commission
        order.updated_at = datetime.now()
        
        # 创建成交记录
        fill = Fill(
            fill_id=str(uuid.uuid4()),
            order_id=order.order_id,
            symbol=order.symbol,
            quantity=order.quantity,
            price=execution_price,
            timestamp=datetime.now(),
            commission=commission
        )
        
        self.fills.append(fill)
        
        logger.info(
            f"🎯 模拟成交: {order.action} {order.symbol} x{order.quantity} @ ${execution_price:.2f}"
        )
        
        return TradeResult(
            success=True,
            order_id=order.order_id,
            executed_price=execution_price,
            executed_quantity=order.quantity,
            commission=commission
        )
    
    async def _execute_real_order(self, order: Order) -> 'TradeResult':
        """执行真实订单"""
        from core.trading_engine import TradeResult
        
        # 这里应该集成真实的券商API
        # 例如：Interactive Brokers, Alpaca, TD Ameritrade等
        
        logger.warning("⚠️ 真实交易模式尚未实现")
        
        return TradeResult(
            success=False,
            error_message="真实交易模式尚未实现"
        )
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        try:
            # 从缓存获取价格
            if symbol in self.market_data_cache:
                cache_data = self.market_data_cache[symbol]
                # 检查缓存是否过期（5分钟）
                if (datetime.now() - cache_data['timestamp']).seconds < 300:
                    return cache_data['price']
            
            # 这里应该调用市场数据API获取实时价格
            # 简化实现：使用随机价格模拟
            import random
            
            # 基础价格（根据股票设定）
            base_prices = {
                'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 2500.0, 'AMZN': 3000.0,
                'TSLA': 200.0, 'META': 250.0, 'NVDA': 400.0, 'NFLX': 400.0
            }
            
            base_price = base_prices.get(symbol, 100.0)
            
            # 添加随机波动（±2%）
            price = base_price * (1 + random.uniform(-0.02, 0.02))
            
            # 缓存价格
            self.market_data_cache[symbol] = {
                'price': price,
                'timestamp': datetime.now()
            }
            
            return price
            
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 价格失败: {e}")
            return None
    
    def _calculate_commission(self, quantity: int, price: float) -> float:
        """计算手续费"""
        # 简单的手续费模型
        # 每股$0.005，最低$1，最高交易金额的0.5%
        per_share_fee = quantity * 0.005
        min_fee = 1.0
        max_fee = quantity * price * 0.005
        
        commission = max(min_fee, min(per_share_fee, max_fee))
        return round(commission, 2)
    
    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if order_id not in self.orders:
            logger.warning(f"⚠️ 订单不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            logger.warning(f"⚠️ 订单无法取消，当前状态: {order.status.value}")
            return False
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        
        logger.info(f"✅ 订单已取消: {order_id}")
        return True
    
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """获取订单状态"""
        return self.orders.get(order_id)
    
    async def get_orders(self, symbol: str = None, status: OrderStatus = None) -> List[Order]:
        """获取订单列表"""
        orders = list(self.orders.values())
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        # 按创建时间倒序排列
        orders.sort(key=lambda x: x.created_at, reverse=True)
        
        return orders
    
    async def get_fills(self, symbol: str = None, limit: int = 100) -> List[Fill]:
        """获取成交记录"""
        fills = self.fills
        
        if symbol:
            fills = [f for f in fills if f.symbol == symbol]
        
        # 按时间倒序排列
        fills.sort(key=lambda x: x.timestamp, reverse=True)
        
        return fills[:limit]
    
    async def get_order_statistics(self) -> Dict[str, Any]:
        """获取订单统计信息"""
        total_orders = len(self.orders)
        
        if total_orders == 0:
            return {
                'total_orders': 0,
                'filled_orders': 0,
                'cancelled_orders': 0,
                'pending_orders': 0,
                'fill_rate': 0.0,
                'total_volume': 0.0,
                'total_commission': 0.0
            }
        
        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = len([
                o for o in self.orders.values() if o.status == status
            ])
        
        filled_orders = status_counts.get('filled', 0)
        fill_rate = filled_orders / total_orders if total_orders > 0 else 0.0
        
        total_volume = sum(
            f.quantity * f.price for f in self.fills
        )
        
        total_commission = sum(f.commission for f in self.fills)
        
        return {
            'total_orders': total_orders,
            'filled_orders': filled_orders,
            'cancelled_orders': status_counts.get('cancelled', 0),
            'pending_orders': status_counts.get('pending', 0) + status_counts.get('submitted', 0),
            'fill_rate': fill_rate,
            'total_volume': total_volume,
            'total_commission': total_commission,
            'status_breakdown': status_counts
        }
    
    async def process_pending_orders(self):
        """处理待成交订单"""
        pending_orders = await self.get_orders(status=OrderStatus.SUBMITTED)
        
        for order in pending_orders:
            if order.order_type == OrderType.LIMIT:
                # 检查限价单是否可以成交
                current_price = await self._get_current_price(order.symbol)
                
                if current_price is None:
                    continue
                
                can_fill = False
                if order.action.lower() == 'buy' and current_price <= order.price:
                    can_fill = True
                elif order.action.lower() == 'sell' and current_price >= order.price:
                    can_fill = True
                
                if can_fill:
                    # 执行成交
                    await self._fill_limit_order(order, order.price)
    
    async def _fill_limit_order(self, order: Order, fill_price: float):
        """执行限价单成交"""
        commission = self._calculate_commission(order.quantity, fill_price)
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price
        order.commission = commission
        order.updated_at = datetime.now()
        
        # 创建成交记录
        fill = Fill(
            fill_id=str(uuid.uuid4()),
            order_id=order.order_id,
            symbol=order.symbol,
            quantity=order.quantity,
            price=fill_price,
            timestamp=datetime.now(),
            commission=commission
        )
        
        self.fills.append(fill)
        
        logger.info(
            f"🎯 限价单成交: {order.action} {order.symbol} x{order.quantity} @ ${fill_price:.2f}"
        )
    
    async def shutdown(self):
        """关闭订单管理器"""
        logger.info("🛑 关闭订单管理器...")
        
        # 取消所有待处理订单
        pending_orders = await self.get_orders(status=OrderStatus.PENDING)
        for order in pending_orders:
            await self.cancel_order(order.order_id)
        
        logger.info("✅ 订单管理器已关闭")
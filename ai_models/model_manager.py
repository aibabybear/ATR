#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI模型管理器
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger

from .base_model import BaseAIModel
from .gpt_trader import GPTTrader
from .claude_trader import ClaudeTrader
from .qwen_trader import QwenTrader
from .deepseek_trader import DeepSeekTrader
from config.settings import Settings


class ModelManager:
    """AI模型管理器"""
    
    def __init__(self):
        self.models: Dict[str, BaseAIModel] = {}
        self.model_configs = Settings.AI_MODELS
        self.performance_history = {}
        self.is_initialized = False
        
        # 模型类映射
        self.model_classes = {
            'gpt-4': GPTTrader,
            'claude-3': ClaudeTrader,
            'qwen-max': QwenTrader,
            'deepseek-v3': DeepSeekTrader,
            # 可以添加更多模型
        }
    
    async def initialize(self):
        """初始化模型管理器"""
        logger.info("🤖 初始化AI模型管理器...")
        
        # 获取启用的模型列表
        enabled_models = Settings.get_enabled_models()
        
        if not enabled_models:
            logger.warning("⚠️ 没有启用的AI模型")
            return
        
        # 初始化每个启用的模型
        for model_key in enabled_models:
            await self._initialize_model(model_key)
        
        # 启动性能监控
        asyncio.create_task(self._performance_monitor())
        
        self.is_initialized = True
        logger.info(f"✅ AI模型管理器初始化完成，活跃模型: {len(self.get_active_models())}")
    
    async def _initialize_model(self, model_key: str):
        """初始化单个模型"""
        try:
            model_config = self.model_configs.get(model_key, {})
            model_class = self.model_classes.get(model_key)
            
            if not model_class:
                logger.warning(f"⚠️ 未找到模型类: {model_key}")
                return
            
            # 创建模型实例
            model_name = f"{model_key.upper()}-Trader"
            model = model_class(name=model_name, config=model_config)
            
            # 初始化模型
            success = await model.initialize()
            
            if success:
                self.models[model_key] = model
                self.performance_history[model_key] = []
                logger.info(f"✅ 模型 {model_name} 初始化成功")
            else:
                logger.error(f"❌ 模型 {model_name} 初始化失败")
                
        except Exception as e:
            logger.error(f"❌ 初始化模型 {model_key} 时出错: {e}")
    
    def get_active_models(self) -> List[BaseAIModel]:
        """获取活跃的模型列表"""
        return [model for model in self.models.values() if model.is_active]
    
    def get_model(self, model_key: str) -> Optional[BaseAIModel]:
        """获取指定模型"""
        return self.models.get(model_key)
    
    async def execute_parallel_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """并行执行所有模型的市场分析"""
        active_models = self.get_active_models()
        
        if not active_models:
            logger.warning("⚠️ 没有活跃的AI模型")
            return {}
        
        # 并行执行分析
        tasks = []
        for model in active_models:
            task = asyncio.create_task(
                self._safe_model_analysis(model, market_data)
            )
            tasks.append((model.name, task))
        
        # 等待所有分析完成
        results = {}
        for model_name, task in tasks:
            try:
                analysis_result = await task
                if analysis_result:
                    results[model_name] = analysis_result
            except Exception as e:
                logger.error(f"❌ 模型 {model_name} 分析失败: {e}")
        
        return results
    
    async def _safe_model_analysis(self, model: BaseAIModel, market_data: Dict[str, Any]) -> Optional[Dict]:
        """安全执行模型分析"""
        try:
            analysis = await model.analyze_market(market_data)
            return {
                'model_name': model.name,
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis,
                'performance': model.get_performance_metrics()
            }
        except Exception as e:
            logger.error(f"❌ 模型 {model.name} 分析出错: {e}")
            return None
    
    async def execute_parallel_decisions(self, market_data: Dict[str, Any]) -> List[Any]:
        """并行执行所有模型的交易决策"""
        active_models = self.get_active_models()
        
        if not active_models:
            return []
        
        # 并行执行决策
        tasks = []
        for model in active_models:
            task = asyncio.create_task(
                self._safe_model_decision(model, market_data)
            )
            tasks.append((model.name, task))
        
        # 收集决策结果
        decisions = []
        for model_name, task in tasks:
            try:
                decision = await task
                if decision:
                    decision.model_name = model_name  # 添加模型名称
                    decisions.append(decision)
            except Exception as e:
                logger.error(f"❌ 模型 {model_name} 决策失败: {e}")
        
        return decisions
    
    async def _safe_model_decision(self, model: BaseAIModel, market_data: Dict[str, Any]):
        """安全执行模型决策"""
        try:
            return await model.make_trading_decision(market_data)
        except Exception as e:
            logger.error(f"❌ 模型 {model.name} 决策出错: {e}")
            return None
    
    async def update_model_performance(self, model_key: str, trade_result: Dict[str, Any]):
        """更新模型性能"""
        model = self.models.get(model_key)
        if not model:
            return
        
        # 更新模型性能指标
        await model.update_performance(trade_result)
        
        # 记录性能历史
        performance_record = {
            'timestamp': datetime.now().isoformat(),
            'trade_result': trade_result,
            'metrics': model.get_performance_metrics()
        }
        
        if model_key not in self.performance_history:
            self.performance_history[model_key] = []
        
        self.performance_history[model_key].append(performance_record)
        
        # 限制历史记录数量
        if len(self.performance_history[model_key]) > 1000:
            self.performance_history[model_key] = self.performance_history[model_key][-1000:]
    
    def get_model_rankings(self) -> List[Dict[str, Any]]:
        """获取模型排名"""
        rankings = []
        
        for model_key, model in self.models.items():
            if not model.is_active:
                continue
            
            metrics = model.get_performance_metrics()
            
            ranking_data = {
                'model_key': model_key,
                'model_name': model.name,
                'total_return': metrics.get('total_return', 0.0),
                'total_trades': metrics.get('total_trades', 0),
                'win_rate': metrics.get('win_rate', 0.0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                'max_drawdown': metrics.get('max_drawdown', 0.0),
                'is_active': model.is_active
            }
            
            rankings.append(ranking_data)
        
        # 按总收益排序
        rankings.sort(key=lambda x: x['total_return'], reverse=True)
        
        # 添加排名
        for i, ranking in enumerate(rankings):
            ranking['rank'] = i + 1
        
        return rankings
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能汇总"""
        active_models = self.get_active_models()
        
        if not active_models:
            return {
                'total_models': 0,
                'active_models': 0,
                'total_trades': 0,
                'average_return': 0.0,
                'best_performer': None,
                'worst_performer': None
            }
        
        # 计算汇总统计
        total_trades = sum(m.performance_metrics.get('total_trades', 0) for m in active_models)
        total_returns = [m.performance_metrics.get('total_return', 0.0) for m in active_models]
        
        average_return = sum(total_returns) / len(total_returns) if total_returns else 0.0
        
        # 找出最佳和最差表现者
        rankings = self.get_model_rankings()
        best_performer = rankings[0] if rankings else None
        worst_performer = rankings[-1] if rankings else None
        
        return {
            'total_models': len(self.models),
            'active_models': len(active_models),
            'total_trades': total_trades,
            'average_return': average_return,
            'best_performer': best_performer,
            'worst_performer': worst_performer,
            'rankings': rankings
        }
    
    async def get_model_insights(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取所有模型的洞察"""
        insights = {}
        
        for model_key, model in self.models.items():
            if not model.is_active:
                continue
            
            try:
                # 尝试获取模型特定的洞察
                if hasattr(model, 'get_model_insights'):
                    model_insights = await model.get_model_insights(market_data)
                elif hasattr(model, 'get_market_outlook'):
                    model_insights = await model.get_market_outlook(market_data)
                else:
                    # 基础洞察
                    model_insights = {
                        'model_name': model.name,
                        'performance': model.get_performance_metrics(),
                        'status': 'active' if model.is_active else 'inactive'
                    }
                
                insights[model_key] = model_insights
                
            except Exception as e:
                logger.error(f"❌ 获取模型 {model.name} 洞察失败: {e}")
        
        return insights
    
    async def _performance_monitor(self):
        """性能监控循环"""
        while self.is_initialized:
            try:
                # 每小时记录一次性能快照
                await asyncio.sleep(3600)  # 1小时
                
                # 记录性能快照
                snapshot = {
                    'timestamp': datetime.now().isoformat(),
                    'models': {}
                }
                
                for model_key, model in self.models.items():
                    if model.is_active:
                        snapshot['models'][model_key] = model.get_performance_metrics()
                
                logger.info(f"📊 性能快照已记录: {len(snapshot['models'])} 个活跃模型")
                
            except Exception as e:
                logger.error(f"❌ 性能监控出错: {e}")
                await asyncio.sleep(300)  # 出错后等待5分钟
    
    async def rebalance_models(self, market_conditions: Dict[str, Any]):
        """根据市场条件重新平衡模型"""
        try:
            logger.info("⚖️ 开始模型重新平衡...")
            
            # 获取当前性能排名
            rankings = self.get_model_rankings()
            
            # 根据表现调整模型权重或状态
            for ranking in rankings:
                model_key = ranking['model_key']
                model = self.models.get(model_key)
                
                if not model:
                    continue
                
                # 如果模型表现持续不佳，可以考虑暂停
                if (ranking['total_trades'] > 10 and 
                    ranking['win_rate'] < 0.3 and 
                    ranking['total_return'] < -0.1):
                    
                    logger.warning(
                        f"⚠️ 模型 {model.name} 表现不佳，考虑调整策略"
                    )
                    # 这里可以实现模型调整逻辑
            
            logger.info("✅ 模型重新平衡完成")
            
        except Exception as e:
            logger.error(f"❌ 模型重新平衡失败: {e}")
    
    async def add_model(self, model_key: str, model_class, config: Dict[str, Any]):
        """动态添加新模型"""
        try:
            if model_key in self.models:
                logger.warning(f"⚠️ 模型 {model_key} 已存在")
                return False
            
            # 创建并初始化新模型
            model_name = f"{model_key.upper()}-Trader"
            model = model_class(name=model_name, config=config)
            
            success = await model.initialize()
            
            if success:
                self.models[model_key] = model
                self.performance_history[model_key] = []
                logger.info(f"✅ 动态添加模型 {model_name} 成功")
                return True
            else:
                logger.error(f"❌ 动态添加模型 {model_name} 失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 动态添加模型出错: {e}")
            return False
    
    async def remove_model(self, model_key: str):
        """移除模型"""
        try:
            model = self.models.get(model_key)
            if not model:
                logger.warning(f"⚠️ 模型 {model_key} 不存在")
                return False
            
            # 清理模型资源
            await model.cleanup()
            
            # 从管理器中移除
            del self.models[model_key]
            if model_key in self.performance_history:
                del self.performance_history[model_key]
            
            logger.info(f"✅ 模型 {model.name} 已移除")
            return True
            
        except Exception as e:
            logger.error(f"❌ 移除模型出错: {e}")
            return False
    
    async def shutdown(self):
        """关闭模型管理器"""
        logger.info("🛑 关闭AI模型管理器...")
        
        self.is_initialized = False
        
        # 清理所有模型
        for model in self.models.values():
            try:
                await model.cleanup()
            except Exception as e:
                logger.error(f"❌ 清理模型 {model.name} 失败: {e}")
        
        self.models.clear()
        self.performance_history.clear()
        
        logger.info("✅ AI模型管理器已关闭")
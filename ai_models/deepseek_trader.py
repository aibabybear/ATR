#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek v3.1交易模型实现
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    import requests
except ImportError:
    logger.warning("⚠️ requests库未安装，DeepSeek模型将无法使用")
    requests = None

from .base_model import BaseAIModel, TradingDecision, MarketAnalysis
from config.settings import Settings


class DeepSeekTrader(BaseAIModel):
    """基于DeepSeek v3.1的交易模型"""
    
    def __init__(self, name: str = "DeepSeek-Trader", config: Dict[str, Any] = None):
        if config is None:
            config = Settings.AI_MODELS.get('deepseek-v3', {})
        
        super().__init__(name, config)
        
        self.api_key = None
        self.model_name = config.get('model_name', 'deepseek-chat')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.1)
        
        # DeepSeek特有的交易策略参数
        self.trading_style = config.get('trading_style', 'quantitative')  # quantitative, fundamental, technical
        self.analysis_depth = config.get('analysis_depth', 'deep')  # shallow, medium, deep
        self.risk_tolerance = config.get('risk_tolerance', 'moderate')  # conservative, moderate, aggressive
        
        # API配置
        self.api_base_url = "https://api.deepseek.com/v1/chat/completions"
        
        # 系统提示词
        self.system_prompt = self._build_system_prompt()
    
    async def initialize(self) -> bool:
        """初始化DeepSeek模型"""
        try:
            if requests is None:
                logger.error("❌ requests库未安装")
                return False
            
            # 获取API密钥
            self.api_key = Settings.get_api_key('DEEPSEEK_API_KEY')
            if not self.api_key:
                logger.error("❌ 未找到DeepSeek API密钥")
                return False
            
            # 测试API连接
            await self._test_api_connection()
            
            self.is_active = True
            logger.info(f"✅ {self.name} 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ {self.name} 初始化失败: {e}")
            return False
    
    async def _test_api_connection(self):
        """测试API连接"""
        try:
            test_payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, test connection."
                    }
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 在线程池中执行同步请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.api_base_url,
                    headers=headers,
                    json=test_payload,
                    timeout=30
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('choices'):
                    logger.info(f"🔗 {self.name} API连接测试成功")
                else:
                    raise Exception("API响应格式异常")
            else:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"API连接测试失败: {e}")
    
    async def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, MarketAnalysis]:
        """分析市场数据"""
        try:
            analyses = {}
            
            # DeepSeek的策略：深度量化分析，数据驱动决策
            symbols_to_analyze = self._select_analysis_targets(market_data)
            
            for symbol in symbols_to_analyze:
                if symbol in ['sentiment', 'QQQ', 'SPY', 'VIX']:
                    continue
                
                stock_data = market_data.get(symbol, {})
                if not stock_data:
                    continue
                
                analysis = await self._analyze_single_stock(symbol, stock_data, market_data)
                if analysis:
                    analyses[symbol] = analysis
            
            return analyses
            
        except Exception as e:
            logger.error(f"❌ {self.name} 市场分析失败: {e}")
            return {}
    
    def _select_analysis_targets(self, market_data: Dict[str, Any]) -> List[str]:
        """选择分析目标股票"""
        # DeepSeek的策略：量化选股，关注数据质量和流动性
        priority_stocks = {
            'quantitative': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'QCOM'],
            'fundamental': ['AAPL', 'MSFT', 'GOOGL', 'BRK.B', 'JNJ', 'PG', 'KO', 'WMT'],
            'technical': ['TSLA', 'NVDA', 'AMD', 'NFLX', 'ZOOM', 'SQ', 'ROKU', 'SHOP']
        }
        
        target_stocks = priority_stocks.get(self.trading_style, priority_stocks['quantitative'])
        
        # 只选择有数据的股票
        available_stocks = [s for s in target_stocks if s in market_data]
        
        # 根据分析深度限制数量
        max_stocks = {
            'shallow': 8,
            'medium': 12,
            'deep': 16
        }
        
        limit = max_stocks.get(self.analysis_depth, 12)
        return available_stocks[:limit]
    
    async def _analyze_single_stock(self, symbol: str, stock_data: Dict, market_data: Dict) -> Optional[MarketAnalysis]:
        """分析单只股票"""
        try:
            # 构建深度分析提示
            analysis_prompt = self._build_analysis_prompt(symbol, stock_data, market_data)
            
            # 调用DeepSeek进行分析
            response_text = await self._call_deepseek_api(analysis_prompt)
            
            if not response_text:
                return None
            
            # 解析响应
            analysis = self._parse_analysis_response(symbol, response_text)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ 分析 {symbol} 失败: {e}")
            return None
    
    async def make_trading_decision(self, market_data: Dict[str, Any]) -> Optional[TradingDecision]:
        """做出交易决策"""
        try:
            if not await self.should_trade(market_data):
                return None
            
            # 进行市场分析
            market_analyses = await self.analyze_market(market_data)
            
            if not market_analyses:
                logger.warning(f"⚠️ {self.name}: 没有可用的市场分析")
                return None
            
            # 构建交易决策提示
            decision_prompt = self._build_decision_prompt(market_analyses, market_data)
            
            # 调用DeepSeek做出交易决策
            response_text = await self._call_deepseek_api(decision_prompt)
            
            if not response_text:
                return None
            
            # 解析交易决策
            decision = self._parse_decision_response(response_text, market_data)
            
            if decision:
                logger.info(
                    f"🤖 {self.name} 交易决策: {decision.action} {decision.symbol} "
                    f"x{decision.quantity} (置信度: {decision.confidence:.2f})"
                )
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ {self.name} 交易决策失败: {e}")
            return None
    
    async def _call_deepseek_api(self, prompt: str) -> Optional[str]:
        """调用DeepSeek API"""
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 在线程池中执行同步请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.api_base_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
            )
            
            if response.status_code == 200:
                result = response.json()
                choices = result.get('choices', [])
                if choices:
                    return choices[0].get('message', {}).get('content', '')
                else:
                    logger.error(f"❌ DeepSeek API响应格式异常: {result}")
                    return None
            else:
                logger.error(f"❌ DeepSeek API请求失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 调用DeepSeek API失败: {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""
你是{self.name}，一个基于DeepSeek v3.1的专业量化交易分析师。你以深度数据分析和量化建模著称。

你的特征：
- 交易风格: {self.trading_style}
- 分析深度: {self.analysis_depth}
- 风险容忍度: {self.risk_tolerance}
- 核心优势: 深度学习、量化分析、数据挖掘

分析方法：
1. 多维度量化分析
2. 深度学习模式识别
3. 统计套利机会发现
4. 高频数据处理分析
5. 机器学习预测建模

决策原则：
1. 数据驱动的量化决策
2. 统计显著性验证
3. 多因子模型分析
4. 动态风险调整
5. 算法化执行策略

技术特长：
1. 时间序列分析
2. 机器学习建模
3. 统计套利识别
4. 高频交易信号
5. 风险因子分解

响应要求：
- 使用精确的JSON格式
- 提供量化分析指标
- 包含统计置信度
- 给出概率化预测

记住：量化交易基于数据和统计，每个决策都要有数学依据。
"""
    
    def _build_analysis_prompt(self, symbol: str, stock_data: Dict, market_data: Dict) -> str:
        """构建分析提示"""
        # 获取相关数据
        sentiment = market_data.get('sentiment', {})
        market_indices = {
            'QQQ': market_data.get('QQQ', {}),
            'SPY': market_data.get('SPY', {}),
            'VIX': market_data.get('VIX', {})
        }
        
        prompt = f"""
请对股票 {symbol} 进行{self.analysis_depth}量化分析：

== 股票数据 ==
{json.dumps(stock_data, indent=2)}

== 市场情绪指标 ==
{json.dumps(sentiment, indent=2)}

== 基准指数数据 ==
{json.dumps(market_indices, indent=2)}

请从以下量化维度进行分析：

1. **技术量化指标**
   - 动量因子分析
   - 均值回归信号
   - 波动率模式识别
   - 成交量价格关系

2. **统计特征分析**
   - 价格分布特征
   - 收益率统计性质
   - 自相关性检验
   - 异常值检测

3. **市场微观结构**
   - 流动性指标
   - 买卖价差分析
   - 订单流特征
   - 市场冲击成本

4. **风险因子分解**
   - 系统性风险暴露
   - 特异性风险评估
   - 相关性分析
   - VaR计算

5. **预测模型输出**
   - 短期价格预测
   - 波动率预测
   - 趋势持续概率
   - 反转信号强度

请以JSON格式返回量化分析结果：
{{
    "symbol": "{symbol}",
    "quantitative_score": 0.0-10.0,
    "momentum_factor": -1.0到1.0,
    "mean_reversion_signal": -1.0到1.0,
    "volatility_regime": "low/medium/high",
    "liquidity_score": 0.0-10.0,
    "trend": "bullish/bearish/neutral",
    "strength": 0.0-1.0,
    "statistical_significance": 0.0-1.0,
    "support_level": 支撑价位,
    "resistance_level": 阻力价位,
    "expected_return": 预期收益率,
    "volatility_forecast": 波动率预测,
    "risk_metrics": {{
        "var_95": "95% VaR值",
        "max_drawdown_risk": "最大回撤风险",
        "beta": "市场Beta值"
    }},
    "trading_signals": {{
        "entry_signal": "strong/weak/none",
        "exit_signal": "strong/weak/none",
        "signal_confidence": 0.0-1.0
    }},
    "model_predictions": {{
        "price_target_1d": "1日价格目标",
        "price_target_5d": "5日价格目标",
        "trend_probability": "趋势持续概率"
    }}
}}
"""
        
        return prompt
    
    def _build_decision_prompt(self, analyses: Dict[str, MarketAnalysis], market_data: Dict) -> str:
        """构建交易决策提示"""
        # 整理分析结果
        analysis_summary = {}
        for symbol, analysis in analyses.items():
            analysis_summary[symbol] = {
                'trend': analysis.trend,
                'strength': analysis.strength,
                'sentiment_score': analysis.sentiment_score,
                'technical_indicators': analysis.technical_indicators
            }
        
        # 获取当前性能
        performance_info = {
            'total_trades': self.performance_metrics['total_trades'],
            'win_rate': self.performance_metrics.get('win_rate', 0),
            'total_return': self.performance_metrics['total_return'],
            'sharpe_ratio': self.performance_metrics.get('sharpe_ratio', 0)
        }
        
        prompt = f"""
基于量化分析结果，请做出最优交易决策：

== 量化分析汇总 ==
{json.dumps(analysis_summary, indent=2)}

== 模型历史表现 ==
{json.dumps(performance_info, indent=2)}

== 量化策略参数 ==
- 交易风格: {self.trading_style}
- 分析深度: {self.analysis_depth}
- 风险容忍度: {self.risk_tolerance}

请基于以下量化框架做决策：

1. **信号强度评估**
   - 多因子信号合成
   - 统计显著性检验
   - 信号衰减分析
   - 噪声过滤处理

2. **风险收益优化**
   - 夏普比率最大化
   - 最大回撤控制
   - 波动率目标管理
   - 相关性风险分散

3. **执行成本分析**
   - 市场冲击成本
   - 时间衰减成本
   - 机会成本评估
   - 滑点预期管理

4. **组合优化决策**
   - 权重分配优化
   - 再平衡频率
   - 对冲策略选择
   - 流动性管理

请返回量化交易决策（JSON格式）：
{{
    "action": "buy/sell/hold",
    "symbol": "最优标的",
    "quantity": 最优数量,
    "confidence": 0.0-1.0,
    "expected_return": 预期收益率,
    "expected_volatility": 预期波动率,
    "sharpe_ratio_forecast": 预期夏普比率,
    "max_drawdown_risk": 最大回撤风险,
    "holding_period": 最优持有期,
    "stop_loss": 量化止损位,
    "take_profit": 量化止盈位,
    "position_sizing_method": "kelly/fixed/volatility",
    "risk_budget": 风险预算分配,
    "signal_strength": 信号强度评分,
    "statistical_edge": 统计优势评估,
    "execution_strategy": "market/limit/twap/vwap",
    "reasoning": "量化决策逻辑",
    "alternative_strategies": ["备选策略列表"]
}}

如果没有统计显著的交易机会，请返回：
{{
    "action": "hold",
    "reasoning": "无统计显著信号",
    "signal_analysis": "信号强度分析",
    "market_regime": "当前市场状态",
    "waiting_conditions": ["等待条件列表"]
}}
"""
        
        return prompt
    
    def _parse_analysis_response(self, symbol: str, response_text: str) -> Optional[MarketAnalysis]:
        """解析分析响应"""
        try:
            # 尝试提取JSON部分
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                return self._extract_analysis_from_text(symbol, response_text)
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            # 构建MarketAnalysis对象
            analysis = MarketAnalysis(
                symbol=symbol,
                trend=data.get('trend', 'neutral'),
                strength=float(data.get('strength', data.get('statistical_significance', 0.5))),
                support_level=data.get('support_level'),
                resistance_level=data.get('resistance_level'),
                technical_indicators={
                    'quantitative_score': data.get('quantitative_score', 5.0),
                    'momentum_factor': data.get('momentum_factor', 0.0),
                    'mean_reversion_signal': data.get('mean_reversion_signal', 0.0),
                    'volatility_regime': data.get('volatility_regime', 'medium'),
                    'liquidity_score': data.get('liquidity_score', 5.0),
                    'expected_return': data.get('expected_return', 0.0),
                    'volatility_forecast': data.get('volatility_forecast', 0.2)
                },
                sentiment_score=0.0,  # 从市场数据获取
                news_impact='neutral'
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ 解析DeepSeek分析响应失败: {e}")
            logger.debug(f"响应内容: {response_text[:500]}...")
            return None
    
    def _extract_analysis_from_text(self, symbol: str, text: str) -> Optional[MarketAnalysis]:
        """从文本中提取分析信息"""
        try:
            text_lower = text.lower()
            
            # 量化信号识别
            if any(word in text_lower for word in ['买入信号', '上涨概率', 'bullish', 'positive momentum']):
                trend = 'bullish'
                strength = 0.75
            elif any(word in text_lower for word in ['卖出信号', '下跌概率', 'bearish', 'negative momentum']):
                trend = 'bearish'
                strength = 0.75
            else:
                trend = 'neutral'
                strength = 0.5
            
            return MarketAnalysis(
                symbol=symbol,
                trend=trend,
                strength=strength,
                technical_indicators={'deepseek_analysis': True}
            )
            
        except Exception as e:
            logger.error(f"❌ 从文本提取分析信息失败: {e}")
            return None
    
    def _parse_decision_response(self, response_text: str, market_data: Dict) -> Optional[TradingDecision]:
        """解析交易决策响应"""
        try:
            # 提取JSON部分
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning(f"⚠️ 无法从DeepSeek决策响应中提取JSON")
                return None
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            action = data.get('action', 'hold').lower()
            
            # 如果是hold，记录原因但不返回交易决策
            if action == 'hold':
                reason = data.get('reasoning', '无统计显著信号')
                logger.info(f"🤖 {self.name}: {reason}")
                return None
            
            symbol = data.get('symbol', '')
            if not symbol:
                logger.warning(f"⚠️ DeepSeek交易决策缺少股票代码")
                return None
            
            # 获取当前价格
            current_price = None
            if symbol in market_data:
                current_price = market_data[symbol].get('price')
            
            # 计算交易数量
            quantity = data.get('quantity', 0)
            if quantity == 0 and current_price:
                confidence = float(data.get('confidence', 0.5))
                expected_return = data.get('expected_return', 0.05)
                
                # DeepSeek的量化仓位计算
                risk_multipliers = {
                    'conservative': 0.3,
                    'moderate': 0.5,
                    'aggressive': 0.7
                }
                risk_multiplier = risk_multipliers.get(self.risk_tolerance, 0.5)
                
                # 基于Kelly公式的简化版本
                kelly_fraction = max(0.01, min(0.25, expected_return * confidence * risk_multiplier))
                quantity = int((10000 * kelly_fraction) / current_price)
                quantity = max(1, quantity)
            
            decision = TradingDecision(
                symbol=symbol,
                action=action,
                quantity=max(1, int(quantity)),
                confidence=float(data.get('confidence', 0.5)),
                reason=data.get('reasoning', ''),
                price=current_price,
                stop_loss=data.get('stop_loss'),
                take_profit=data.get('take_profit'),
                risk_level=self.risk_tolerance
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ 解析DeepSeek交易决策失败: {e}")
            logger.debug(f"响应内容: {response_text[:500]}...")
            return None
    
    async def get_quantitative_insights(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取量化洞察"""
        try:
            insights_prompt = f"""
作为{self.name}，请提供当前市场的量化分析洞察：

当前模型表现：
- 总交易: {self.performance_metrics['total_trades']}
- 胜率: {self.performance_metrics.get('win_rate', 0):.1%}
- 总收益: ${self.performance_metrics['total_return']:.2f}
- 夏普比率: {self.performance_metrics.get('sharpe_ratio', 0):.2f}

请从量化角度提供：
1. 市场状态识别（牛市/熊市/震荡）
2. 主要量化因子表现
3. 统计套利机会
4. 风险因子分析
5. 量化策略建议

请用专业的量化分析语言回答。
"""
            
            response_text = await self._call_deepseek_api(insights_prompt)
            
            if response_text:
                return {
                    'model_name': self.name,
                    'timestamp': datetime.now().isoformat(),
                    'quantitative_insights': response_text,
                    'trading_style': self.trading_style,
                    'analysis_depth': self.analysis_depth,
                    'risk_tolerance': self.risk_tolerance,
                    'performance': self.performance_metrics
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ 获取量化洞察失败: {e}")
            return {}
    
    async def cleanup(self):
        """清理资源"""
        await super().cleanup()
        self.api_key = None
        logger.info(f"🧹 {self.name} 已清理完成")
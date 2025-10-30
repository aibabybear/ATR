#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通义千问交易模型实现
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    import requests
except ImportError:
    logger.warning("⚠️ requests库未安装，Qwen模型将无法使用")
    requests = None

from .base_model import BaseAIModel, TradingDecision, MarketAnalysis
from config.settings import Settings


class QwenTrader(BaseAIModel):
    """基于通义千问的交易模型"""
    
    def __init__(self, name: str = "Qwen-Trader", config: Dict[str, Any] = None):
        if config is None:
            config = Settings.AI_MODELS.get('qwen-max', {})
        
        super().__init__(name, config)
        
        self.api_key = None
        self.model_name = config.get('model_name', 'qwen-max')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.1)
        
        # 通义千问特有的交易策略参数
        self.analysis_style = config.get('analysis_style', 'balanced')  # conservative, balanced, aggressive
        self.decision_threshold = config.get('decision_threshold', 0.6)  # 决策置信度阈值
        self.risk_preference = config.get('risk_preference', 'moderate')  # low, moderate, high
        
        # API配置
        self.api_base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        # 系统提示词
        self.system_prompt = self._build_system_prompt()
    
    async def initialize(self) -> bool:
        """初始化通义千问模型"""
        try:
            if requests is None:
                logger.error("❌ requests库未安装")
                return False
            
            # 获取API密钥
            self.api_key = Settings.get_api_key('QWEN_API_KEY')
            if not self.api_key:
                logger.error("❌ 未找到通义千问API密钥")
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
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "Hello, test connection."
                        }
                    ]
                },
                "parameters": {
                    "max_tokens": 10,
                    "temperature": 0.1
                }
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
                if result.get('output'):
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
            
            # 通义千问的策略：平衡分析，关注中长期趋势
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
        # 通义千问的策略：平衡选择，关注稳定性和成长性
        priority_stocks = {
            'conservative': ['AAPL', 'MSFT', 'GOOGL', 'JNJ', 'PG', 'KO'],
            'balanced': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX'],
            'aggressive': ['TSLA', 'NVDA', 'AMD', 'NFLX', 'ZOOM', 'SHOP', 'SQ']
        }
        
        target_stocks = priority_stocks.get(self.analysis_style, priority_stocks['balanced'])
        
        # 只选择有数据的股票
        available_stocks = [s for s in target_stocks if s in market_data]
        
        # 根据分析风格限制数量
        max_stocks = {
            'conservative': 8,
            'balanced': 12,
            'aggressive': 15
        }
        
        limit = max_stocks.get(self.analysis_style, 12)
        return available_stocks[:limit]
    
    async def _analyze_single_stock(self, symbol: str, stock_data: Dict, market_data: Dict) -> Optional[MarketAnalysis]:
        """分析单只股票"""
        try:
            # 构建分析提示
            analysis_prompt = self._build_analysis_prompt(symbol, stock_data, market_data)
            
            # 调用通义千问进行分析
            response_text = await self._call_qwen_api(analysis_prompt)
            
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
            
            # 调用通义千问做出交易决策
            response_text = await self._call_qwen_api(decision_prompt)
            
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
    
    async def _call_qwen_api(self, prompt: str) -> Optional[str]:
        """调用通义千问API"""
        try:
            payload = {
                "model": self.model_name,
                "input": {
                    "messages": [
                        {
                            "role": "system",
                            "content": self.system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                "parameters": {
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": 0.8
                }
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
                output = result.get('output', {})
                text = output.get('text', '')
                return text
            else:
                logger.error(f"❌ 通义千问API请求失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 调用通义千问API失败: {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""
你是{self.name}，一个专业的AI股票交易分析师，基于通义千问大模型。你以平衡分析和稳健投资著称。

你的特征：
- 分析风格: {self.analysis_style}
- 决策阈值: {self.decision_threshold}
- 风险偏好: {self.risk_preference}
- 投资理念: 平衡成长与价值，注重风险控制

分析方法：
1. 综合基本面和技术面分析
2. 重视宏观经济环境影响
3. 关注行业发展趋势
4. 平衡短期机会与长期价值
5. 严格的风险评估和控制

决策原则：
1. 数据驱动的理性决策
2. 适度分散投资
3. 动态风险管理
4. 持续学习和优化
5. 透明的决策逻辑

响应要求：
- 使用结构化的JSON格式
- 提供清晰的分析逻辑
- 包含风险评估
- 给出具体的操作建议

记住：投资需谨慎，每个决策都要有充分的依据。
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
请对股票 {symbol} 进行{self.analysis_style}风格的分析：

== 股票数据 ==
{json.dumps(stock_data, indent=2)}

== 市场情绪 ==
{json.dumps(sentiment, indent=2)}

== 市场指数 ==
{json.dumps(market_indices, indent=2)}

请从以下角度进行分析：

1. **技术面分析**
   - 价格趋势和动量
   - 支撑阻力位分析
   - 技术指标信号

2. **基本面评估**
   - 公司基本情况
   - 行业地位分析
   - 估值水平评估

3. **市场环境**
   - 宏观经济影响
   - 行业发展趋势
   - 市场情绪影响

4. **风险因素**
   - 主要风险点
   - 不确定性因素
   - 风险缓解措施

请以JSON格式返回分析结果：
{{
    "symbol": "{symbol}",
    "trend": "bullish/bearish/neutral",
    "strength": 0.0-1.0,
    "support_level": 支撑价位,
    "resistance_level": 阻力价位,
    "technical_score": 0.0-10.0,
    "fundamental_score": 0.0-10.0,
    "market_sentiment_impact": "positive/negative/neutral",
    "risk_level": "low/medium/high",
    "investment_recommendation": "strong_buy/buy/hold/sell/strong_sell",
    "confidence_level": 0.0-1.0,
    "key_factors": ["关键影响因素列表"],
    "risk_factors": ["主要风险因素列表"],
    "time_horizon": "short/medium/long"
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
            'total_return': self.performance_metrics['total_return']
        }
        
        prompt = f"""
基于市场分析结果，请做出交易决策：

== 股票分析汇总 ==
{json.dumps(analysis_summary, indent=2)}

== 当前模型表现 ==
{json.dumps(performance_info, indent=2)}

== 决策参数 ==
- 分析风格: {self.analysis_style}
- 决策阈值: {self.decision_threshold}
- 风险偏好: {self.risk_preference}

请考虑以下因素：

1. **机会识别**
   - 最佳投资标的筛选
   - 风险收益比评估
   - 时机选择分析

2. **风险控制**
   - 仓位大小控制
   - 止损止盈设置
   - 组合风险管理

3. **市场时机**
   - 当前市场阶段
   - 入场时机判断
   - 持有期规划

请返回交易决策（JSON格式）：
{{
    "action": "buy/sell/hold",
    "symbol": "交易标的",
    "quantity": 建议数量,
    "confidence": 0.0-1.0,
    "reasoning": "详细决策理由",
    "risk_assessment": "风险评估",
    "stop_loss": 止损价格,
    "take_profit": 止盈价格,
    "expected_return": 预期收益率,
    "holding_period": "预期持有期",
    "market_timing": "市场时机分析",
    "alternative_choices": ["备选方案"]
}}

如果没有合适的交易机会，请返回：
{{
    "action": "hold",
    "reasoning": "观望原因",
    "market_outlook": "市场展望",
    "watch_targets": ["关注目标"]
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
                # 如果没有找到JSON，尝试从文本中提取关键信息
                return self._extract_analysis_from_text(symbol, response_text)
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            # 构建MarketAnalysis对象
            analysis = MarketAnalysis(
                symbol=symbol,
                trend=data.get('trend', 'neutral'),
                strength=float(data.get('strength', data.get('confidence_level', 0.5))),
                support_level=data.get('support_level'),
                resistance_level=data.get('resistance_level'),
                technical_indicators={
                    'technical_score': data.get('technical_score', 5.0),
                    'fundamental_score': data.get('fundamental_score', 5.0),
                    'risk_level': data.get('risk_level', 'medium'),
                    'recommendation': data.get('investment_recommendation', 'hold')
                },
                sentiment_score=0.0,  # 从市场数据获取
                news_impact=data.get('market_sentiment_impact', 'neutral')
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ 解析通义千问分析响应失败: {e}")
            logger.debug(f"响应内容: {response_text[:500]}...")
            return None
    
    def _extract_analysis_from_text(self, symbol: str, text: str) -> Optional[MarketAnalysis]:
        """从文本中提取分析信息"""
        try:
            text_lower = text.lower()
            
            # 判断趋势
            if any(word in text_lower for word in ['看涨', '上涨', 'bullish', '买入']):
                trend = 'bullish'
                strength = 0.7
            elif any(word in text_lower for word in ['看跌', '下跌', 'bearish', '卖出']):
                trend = 'bearish'
                strength = 0.7
            else:
                trend = 'neutral'
                strength = 0.5
            
            return MarketAnalysis(
                symbol=symbol,
                trend=trend,
                strength=strength,
                technical_indicators={'text_analysis': True}
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
                logger.warning(f"⚠️ 无法从通义千问决策响应中提取JSON")
                return None
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            action = data.get('action', 'hold').lower()
            
            # 如果是hold，记录原因但不返回交易决策
            if action == 'hold':
                reason = data.get('reasoning', '暂时观望')
                logger.info(f"🤖 {self.name}: {reason}")
                return None
            
            symbol = data.get('symbol', '')
            if not symbol:
                logger.warning(f"⚠️ 通义千问交易决策缺少股票代码")
                return None
            
            # 获取当前价格
            current_price = None
            if symbol in market_data:
                current_price = market_data[symbol].get('price')
            
            # 计算交易数量
            quantity = data.get('quantity', 0)
            if quantity == 0 and current_price:
                confidence = float(data.get('confidence', 0.5))
                
                # 通义千问的仓位计算：平衡风险和收益
                risk_multipliers = {
                    'low': 0.4,
                    'moderate': 0.6,
                    'high': 0.8
                }
                risk_multiplier = risk_multipliers.get(self.risk_preference, 0.6)
                
                quantity = self._calculate_position_size(
                    symbol, confidence, 10000, current_price, self.risk_preference
                ) * risk_multiplier
                quantity = max(1, int(quantity))
            
            decision = TradingDecision(
                symbol=symbol,
                action=action,
                quantity=max(1, int(quantity)),
                confidence=float(data.get('confidence', 0.5)),
                reason=data.get('reasoning', ''),
                price=current_price,
                stop_loss=data.get('stop_loss'),
                take_profit=data.get('take_profit'),
                risk_level=self.risk_preference
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ 解析通义千问交易决策失败: {e}")
            logger.debug(f"响应内容: {response_text[:500]}...")
            return None
    
    async def get_market_insights(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取市场洞察"""
        try:
            insights_prompt = f"""
作为{self.name}，请提供当前市场的洞察和建议：

当前模型表现：
- 总交易: {self.performance_metrics['total_trades']}
- 胜率: {self.performance_metrics.get('win_rate', 0):.1%}
- 总收益: ${self.performance_metrics['total_return']:.2f}

请提供：
1. 当前市场环境分析
2. 主要投资机会和风险
3. 投资策略建议
4. 风险管理要点

请用简洁明了的中文回答。
"""
            
            response_text = await self._call_qwen_api(insights_prompt)
            
            if response_text:
                return {
                    'model_name': self.name,
                    'timestamp': datetime.now().isoformat(),
                    'insights': response_text,
                    'analysis_style': self.analysis_style,
                    'risk_preference': self.risk_preference,
                    'performance': self.performance_metrics
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ 获取市场洞察失败: {e}")
            return {}
    
    async def cleanup(self):
        """清理资源"""
        await super().cleanup()
        self.api_key = None
        logger.info(f"🧹 {self.name} 已清理完成")
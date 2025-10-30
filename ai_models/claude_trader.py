#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude交易模型实现
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    import anthropic
except ImportError:
    logger.warning("⚠️ Anthropic库未安装，Claude模型将无法使用")
    anthropic = None

from .base_model import BaseAIModel, TradingDecision, MarketAnalysis
from config.settings import Settings


class ClaudeTrader(BaseAIModel):
    """基于Claude的交易模型"""
    
    def __init__(self, name: str = "Claude-Trader", config: Dict[str, Any] = None):
        if config is None:
            config = Settings.AI_MODELS.get('claude-3', {})
        
        super().__init__(name, config)
        
        self.client = None
        self.model_name = config.get('model_name', 'claude-3-opus-20240229')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.1)
        
        # Claude特有的交易策略参数
        self.analysis_depth = config.get('analysis_depth', 'comprehensive')  # basic, detailed, comprehensive
        self.risk_management_style = config.get('risk_management_style', 'conservative')  # aggressive, moderate, conservative
        self.market_focus = config.get('market_focus', 'growth')  # value, growth, momentum, dividend
        
        # 系统提示词
        self.system_prompt = self._build_system_prompt()
    
    async def initialize(self) -> bool:
        """初始化Claude模型"""
        try:
            if anthropic is None:
                logger.error("❌ Anthropic库未安装")
                return False
            
            # 获取API密钥
            api_key = Settings.get_api_key('ANTHROPIC_API_KEY')
            if not api_key:
                logger.error("❌ 未找到Anthropic API密钥")
                return False
            
            # 初始化Anthropic客户端
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
            
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
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                temperature=0.1,
                system="You are a helpful assistant.",
                messages=[
                    {"role": "user", "content": "Hello, test connection."}
                ]
            )
            
            if response.content:
                logger.info(f"🔗 {self.name} API连接测试成功")
            else:
                raise Exception("API响应为空")
                
        except Exception as e:
            raise Exception(f"API连接测试失败: {e}")
    
    async def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, MarketAnalysis]:
        """分析市场数据"""
        try:
            analyses = {}
            
            # Claude擅长深度分析，选择重点股票进行详细分析
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
        # Claude的策略：专注于高质量股票的深度分析
        priority_stocks = {
            'growth': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META'],
            'value': ['BRK.B', 'JPM', 'JNJ', 'PG', 'KO', 'WMT'],
            'momentum': ['TSLA', 'NVDA', 'AMD', 'NFLX', 'ZOOM'],
            'dividend': ['MSFT', 'AAPL', 'JNJ', 'PG', 'KO']
        }
        
        focus_stocks = priority_stocks.get(self.market_focus, priority_stocks['growth'])
        
        # 只选择有数据的股票
        available_stocks = [s for s in focus_stocks if s in market_data]
        
        # 根据分析深度限制数量
        max_stocks = {
            'basic': 15,
            'detailed': 10,
            'comprehensive': 6
        }
        
        limit = max_stocks.get(self.analysis_depth, 10)
        return available_stocks[:limit]
    
    async def _analyze_single_stock(self, symbol: str, stock_data: Dict, market_data: Dict) -> Optional[MarketAnalysis]:
        """分析单只股票"""
        try:
            # 构建深度分析提示
            analysis_prompt = self._build_comprehensive_analysis_prompt(symbol, stock_data, market_data)
            
            # 调用Claude进行分析
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": analysis_prompt}
                ]
            )
            
            if not response.content:
                return None
            
            # 解析Claude响应
            analysis_text = response.content[0].text if response.content else ""
            analysis = self._parse_analysis_response(symbol, analysis_text)
            
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
            
            # 调用Claude做出交易决策
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": decision_prompt}
                ]
            )
            
            if not response.content:
                return None
            
            # 解析交易决策
            decision_text = response.content[0].text if response.content else ""
            decision = self._parse_decision_response(decision_text, market_data)
            
            if decision:
                logger.info(
                    f"🤖 {self.name} 交易决策: {decision.action} {decision.symbol} "
                    f"x{decision.quantity} (置信度: {decision.confidence:.2f})"
                )
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ {self.name} 交易决策失败: {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""
你是{self.name}，一个专业的AI股票交易分析师。你以深度分析和谨慎的风险管理著称。

你的特征：
- 分析深度: {self.analysis_depth}
- 风险管理风格: {self.risk_management_style}
- 市场关注点: {self.market_focus}
- 交易哲学: 基于深度研究的长期价值投资

分析方法：
1. 进行全面的基本面分析
2. 结合技术分析验证时机
3. 深度评估风险因素
4. 考虑宏观经济环境
5. 重视公司治理和可持续性

决策原则：
1. 安全边际优先
2. 长期价值导向
3. 严格的风险控制
4. 基于证据的决策
5. 持续学习和调整

响应要求：
- 提供详细的分析逻辑
- 使用结构化的JSON格式
- 包含风险评估和缓解措施
- 给出明确的行动建议

记住：投资有风险，每个决策都要经过深思熟虑。
"""
    
    def _build_comprehensive_analysis_prompt(self, symbol: str, stock_data: Dict, market_data: Dict) -> str:
        """构建综合分析提示"""
        # 获取相关市场数据
        sentiment = market_data.get('sentiment', {})
        market_indices = {
            'QQQ': market_data.get('QQQ', {}),
            'SPY': market_data.get('SPY', {}),
            'VIX': market_data.get('VIX', {})
        }
        
        prompt = f"""
请对股票 {symbol} 进行{self.analysis_depth}分析，重点关注{self.market_focus}特征：

== 股票基础数据 ==
{json.dumps(stock_data, indent=2)}

== 市场情绪数据 ==
{json.dumps(sentiment, indent=2)}

== 大盘指数表现 ==
{json.dumps(market_indices, indent=2)}

请从以下维度进行分析：

1. **基本面分析**
   - 公司财务健康状况
   - 行业地位和竞争优势
   - 增长前景和盈利能力

2. **技术面分析**
   - 价格趋势和支撑阻力
   - 技术指标信号
   - 交易量分析

3. **风险评估**
   - 系统性风险
   - 个股特有风险
   - 流动性风险

4. **宏观环境**
   - 经济周期影响
   - 政策环境
   - 行业趋势

请以JSON格式返回分析结果：
{{
    "symbol": "{symbol}",
    "overall_rating": "strong_buy/buy/hold/sell/strong_sell",
    "confidence_level": 0.0-1.0,
    "fundamental_score": 0.0-10.0,
    "technical_score": 0.0-10.0,
    "risk_score": 0.0-10.0,
    "trend": "bullish/bearish/neutral",
    "strength": 0.0-1.0,
    "support_level": 支撑价位,
    "resistance_level": 阻力价位,
    "target_price": 目标价格,
    "stop_loss_level": 止损价位,
    "investment_thesis": "详细投资逻辑",
    "key_risks": ["主要风险因素列表"],
    "catalysts": ["潜在催化剂列表"],
    "time_horizon": "short/medium/long",
    "position_sizing_recommendation": "small/medium/large"
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
                'technical_indicators': analysis.technical_indicators,
                'support_level': analysis.support_level,
                'resistance_level': analysis.resistance_level
            }
        
        # 获取当前投资组合信息
        portfolio_info = {
            'total_trades': self.performance_metrics['total_trades'],
            'win_rate': self.performance_metrics.get('win_rate', 0),
            'total_return': self.performance_metrics['total_return']
        }
        
        prompt = f"""
基于深度市场分析，请做出最优的交易决策：

== 股票分析汇总 ==
{json.dumps(analysis_summary, indent=2)}

== 当前投资组合表现 ==
{json.dumps(portfolio_info, indent=2)}

== 交易策略参数 ==
- 风险管理风格: {self.risk_management_style}
- 市场关注点: {self.market_focus}
- 分析深度: {self.analysis_depth}

请考虑以下因素做出决策：

1. **机会评估**
   - 最佳投资机会识别
   - 风险调整后收益预期
   - 时机选择的重要性

2. **风险管理**
   - 仓位规模控制
   - 止损策略设置
   - 分散化考虑

3. **市场环境**
   - 当前市场阶段
   - 波动率水平
   - 流动性状况

请返回交易决策（JSON格式）：
{{
    "decision_type": "buy/sell/hold/rebalance",
    "primary_symbol": "主要交易标的",
    "action": "buy/sell/hold",
    "quantity": 建议交易数量,
    "confidence": 0.0-1.0,
    "conviction_level": "low/medium/high",
    "reasoning": "详细决策理由",
    "risk_assessment": "风险评估",
    "stop_loss": 止损价格,
    "take_profit": 止盈价格,
    "expected_holding_period": "预期持有期",
    "alternative_options": ["备选方案"],
    "market_conditions_dependency": "市场条件依赖性分析"
}}

如果当前没有明确的交易机会，请返回：
{{
    "decision_type": "hold",
    "reasoning": "等待更好机会的详细原因",
    "watch_list": ["关注股票列表"],
    "trigger_conditions": ["入场触发条件"]
}}
"""
        
        return prompt
    
    def _parse_analysis_response(self, symbol: str, response_text: str) -> Optional[MarketAnalysis]:
        """解析分析响应"""
        try:
            # Claude的响应通常更结构化，尝试提取JSON
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
                    'overall_rating': data.get('overall_rating', 'hold'),
                    'fundamental_score': data.get('fundamental_score', 5.0),
                    'technical_score': data.get('technical_score', 5.0),
                    'risk_score': data.get('risk_score', 5.0)
                },
                sentiment_score=0.0,  # 从其他数据源获取
                news_impact='neutral'
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ 解析Claude分析响应失败: {e}")
            logger.debug(f"响应内容: {response_text[:500]}...")
            return None
    
    def _extract_analysis_from_text(self, symbol: str, text: str) -> Optional[MarketAnalysis]:
        """从文本中提取分析信息"""
        try:
            # 简化的文本解析逻辑
            text_lower = text.lower()
            
            # 判断趋势
            if 'bullish' in text_lower or 'buy' in text_lower:
                trend = 'bullish'
                strength = 0.7
            elif 'bearish' in text_lower or 'sell' in text_lower:
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
                logger.warning(f"⚠️ 无法从Claude决策响应中提取JSON")
                return None
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            decision_type = data.get('decision_type', 'hold')
            action = data.get('action', decision_type)
            
            # 如果是hold，记录原因但不返回交易决策
            if action.lower() == 'hold':
                reason = data.get('reasoning', '暂时观望')
                logger.info(f"🤖 {self.name}: {reason}")
                return None
            
            symbol = data.get('primary_symbol', data.get('symbol', ''))
            if not symbol:
                logger.warning(f"⚠️ Claude交易决策缺少股票代码")
                return None
            
            # 获取当前价格
            current_price = None
            if symbol in market_data:
                current_price = market_data[symbol].get('price')
            
            # 计算交易数量
            quantity = data.get('quantity', 0)
            if quantity == 0 and current_price:
                confidence = float(data.get('confidence', 0.5))
                conviction = data.get('conviction_level', 'medium')
                
                # Claude的仓位计算更保守
                risk_multipliers = {
                    'low': 0.3,
                    'medium': 0.5,
                    'high': 0.8
                }
                risk_multiplier = risk_multipliers.get(conviction, 0.5)
                
                quantity = self._calculate_position_size(
                    symbol, confidence, 10000, current_price, conviction
                ) * risk_multiplier
                quantity = max(1, int(quantity))
            
            decision = TradingDecision(
                symbol=symbol,
                action=action.lower(),
                quantity=max(1, int(quantity)),
                confidence=float(data.get('confidence', 0.5)),
                reason=data.get('reasoning', ''),
                price=current_price,
                stop_loss=data.get('stop_loss'),
                take_profit=data.get('take_profit'),
                risk_level=data.get('conviction_level', 'medium')
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ 解析Claude交易决策失败: {e}")
            logger.debug(f"响应内容: {response_text[:500]}...")
            return None
    
    async def get_market_outlook(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取市场展望"""
        try:
            outlook_prompt = f"""
作为{self.name}，请提供当前市场的深度分析和展望：

当前模型表现：
- 总交易: {self.performance_metrics['total_trades']}
- 胜率: {self.performance_metrics.get('win_rate', 0):.1%}
- 总收益: ${self.performance_metrics['total_return']:.2f}

请提供：
1. 宏观经济环境分析
2. 主要市场趋势识别
3. 行业轮动机会
4. 风险因素评估
5. 投资策略建议

请提供深度分析和前瞻性见解。
"""
            
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=1500,
                temperature=0.2,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": outlook_prompt}
                ]
            )
            
            if response.content:
                outlook_text = response.content[0].text if response.content else ""
                return {
                    'model_name': self.name,
                    'timestamp': datetime.now().isoformat(),
                    'market_outlook': outlook_text,
                    'analysis_depth': self.analysis_depth,
                    'focus_area': self.market_focus,
                    'performance': self.performance_metrics
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ 获取市场展望失败: {e}")
            return {}
    
    async def cleanup(self):
        """清理资源"""
        await super().cleanup()
        self.client = None
        logger.info(f"🧹 {self.name} 已清理完成")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT交易模型实现
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    import openai
except ImportError:
    logger.warning("⚠️ OpenAI库未安装，GPT模型将无法使用")
    openai = None

from .base_model import BaseAIModel, TradingDecision, MarketAnalysis
from config.settings import Settings


class GPTTrader(BaseAIModel):
    """基于GPT的交易模型"""
    
    def __init__(self, name: str = "GPT-Trader", config: Dict[str, Any] = None):
        if config is None:
            config = Settings.AI_MODELS.get('gpt-4', {})
        
        super().__init__(name, config)
        
        self.client = None
        self.model_name = config.get('model_name', 'gpt-4-turbo-preview')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.1)
        
        # 交易策略参数
        self.risk_tolerance = config.get('risk_tolerance', 'medium')
        self.trading_style = config.get('trading_style', 'swing')  # day, swing, position
        self.max_positions = config.get('max_positions', 5)
        
        # 系统提示词
        self.system_prompt = self._build_system_prompt()
    
    async def initialize(self) -> bool:
        """初始化GPT模型"""
        try:
            if openai is None:
                logger.error("❌ OpenAI库未安装")
                return False
            
            # 获取API密钥
            api_key = Settings.get_api_key('OPENAI_API_KEY')
            if not api_key:
                logger.error("❌ 未找到OpenAI API密钥")
                return False
            
            # 初始化OpenAI客户端
            self.client = openai.AsyncOpenAI(api_key=api_key)
            
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
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, test connection."}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            if response.choices:
                logger.info(f"🔗 {self.name} API连接测试成功")
            else:
                raise Exception("API响应为空")
                
        except Exception as e:
            raise Exception(f"API连接测试失败: {e}")
    
    async def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, MarketAnalysis]:
        """分析市场数据"""
        try:
            analyses = {}
            
            # 选择要分析的股票（限制数量以控制API成本）
            symbols_to_analyze = list(market_data.keys())[:10]  # 最多分析10只股票
            
            for symbol in symbols_to_analyze:
                if symbol in ['sentiment', 'QQQ', 'SPY', 'VIX']:  # 跳过非股票数据
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
    
    async def _analyze_single_stock(self, symbol: str, stock_data: Dict, market_data: Dict) -> Optional[MarketAnalysis]:
        """分析单只股票"""
        try:
            # 构建分析提示
            analysis_prompt = self._build_analysis_prompt(symbol, stock_data, market_data)
            
            # 调用GPT进行分析
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if not response.choices:
                return None
            
            # 解析GPT响应
            analysis_text = response.choices[0].message.content
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
            
            # 首先进行市场分析
            market_analyses = await self.analyze_market(market_data)
            
            if not market_analyses:
                logger.warning(f"⚠️ {self.name}: 没有可用的市场分析")
                return None
            
            # 构建交易决策提示
            decision_prompt = self._build_decision_prompt(market_analyses, market_data)
            
            # 调用GPT做出交易决策
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": decision_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if not response.choices:
                return None
            
            # 解析交易决策
            decision_text = response.choices[0].message.content
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
你是一个专业的AI股票交易员，名为{self.name}。你的任务是分析市场数据并做出明智的交易决策。

你的特征：
- 风险承受能力: {self.risk_tolerance}
- 交易风格: {self.trading_style}
- 最大持仓数: {self.max_positions}

分析原则：
1. 基于技术分析和基本面分析做出决策
2. 考虑市场情绪和新闻影响
3. 严格控制风险，设置止损点
4. 保持客观，避免情绪化交易
5. 提供清晰的交易理由

响应格式要求：
- 使用JSON格式返回结构化数据
- 包含明确的买卖信号和置信度
- 提供详细的分析理由
- 设置合理的止损和止盈点

记住：你正在管理真实资金，每个决策都要谨慎考虑。
"""
    
    def _build_analysis_prompt(self, symbol: str, stock_data: Dict, market_data: Dict) -> str:
        """构建分析提示"""
        # 获取市场情绪数据
        sentiment = market_data.get('sentiment', {})
        
        # 获取大盘指数数据
        market_indices = {
            'QQQ': market_data.get('QQQ', {}),
            'SPY': market_data.get('SPY', {}),
            'VIX': market_data.get('VIX', {})
        }
        
        prompt = f"""
请分析股票 {symbol} 的当前市场状况：

股票数据：
{json.dumps(stock_data, indent=2)}

市场情绪：
{json.dumps(sentiment, indent=2)}

大盘指数：
{json.dumps(market_indices, indent=2)}

请提供以下分析（JSON格式）：
{{
    "symbol": "{symbol}",
    "trend": "bullish/bearish/neutral",
    "strength": 0.0-1.0,
    "support_level": 价格支撑位,
    "resistance_level": 价格阻力位,
    "technical_indicators": {{
        "rsi": RSI值,
        "macd_signal": "buy/sell/neutral",
        "moving_average_signal": "buy/sell/neutral"
    }},
    "sentiment_score": -1.0到1.0,
    "news_impact": "positive/negative/neutral",
    "analysis_summary": "详细分析总结"
}}
"""
        
        return prompt
    
    def _build_decision_prompt(self, analyses: Dict[str, MarketAnalysis], market_data: Dict) -> str:
        """构建交易决策提示"""
        # 将分析结果转换为可读格式
        analysis_summary = {}
        for symbol, analysis in analyses.items():
            analysis_summary[symbol] = {
                'trend': analysis.trend,
                'strength': analysis.strength,
                'sentiment_score': analysis.sentiment_score,
                'technical_indicators': analysis.technical_indicators
            }
        
        prompt = f"""
基于以下市场分析，请做出交易决策：

股票分析结果：
{json.dumps(analysis_summary, indent=2)}

当前投资组合状态：
- 风险承受能力: {self.risk_tolerance}
- 最大持仓数: {self.max_positions}
- 交易风格: {self.trading_style}

请选择最佳的交易机会并返回决策（JSON格式）：
{{
    "action": "buy/sell/hold",
    "symbol": "股票代码",
    "quantity": 交易数量,
    "confidence": 0.0-1.0,
    "reason": "详细交易理由",
    "risk_level": "low/medium/high",
    "stop_loss": 止损价格,
    "take_profit": 止盈价格,
    "holding_period": "预期持有时间"
}}

如果没有好的交易机会，请返回：
{{
    "action": "hold",
    "reason": "等待更好机会的原因"
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
                logger.warning(f"⚠️ 无法从响应中提取JSON: {response_text[:100]}...")
                return None
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            analysis = MarketAnalysis(
                symbol=symbol,
                trend=data.get('trend', 'neutral'),
                strength=float(data.get('strength', 0.5)),
                support_level=data.get('support_level'),
                resistance_level=data.get('resistance_level'),
                technical_indicators=data.get('technical_indicators', {}),
                sentiment_score=float(data.get('sentiment_score', 0.0)),
                news_impact=data.get('news_impact', 'neutral')
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ 解析分析响应失败: {e}")
            logger.debug(f"响应内容: {response_text}")
            return None
    
    def _parse_decision_response(self, response_text: str, market_data: Dict) -> Optional[TradingDecision]:
        """解析交易决策响应"""
        try:
            # 尝试提取JSON部分
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning(f"⚠️ 无法从决策响应中提取JSON: {response_text[:100]}...")
                return None
            
            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            
            action = data.get('action', 'hold').lower()
            
            # 如果是hold，不返回交易决策
            if action == 'hold':
                logger.info(f"🤖 {self.name}: {data.get('reason', '暂时观望')}")
                return None
            
            symbol = data.get('symbol', '')
            if not symbol:
                logger.warning(f"⚠️ 交易决策缺少股票代码")
                return None
            
            # 获取当前价格
            current_price = None
            if symbol in market_data:
                current_price = market_data[symbol].get('price')
            
            # 计算交易数量（如果没有指定）
            quantity = data.get('quantity', 0)
            if quantity == 0 and current_price:
                # 基于置信度和风险等级计算数量
                confidence = float(data.get('confidence', 0.5))
                risk_level = data.get('risk_level', 'medium')
                quantity = self._calculate_position_size(
                    symbol, confidence, 10000, current_price, risk_level
                )
            
            decision = TradingDecision(
                symbol=symbol,
                action=action,
                quantity=max(1, int(quantity)),
                confidence=float(data.get('confidence', 0.5)),
                reason=data.get('reason', ''),
                price=current_price,
                stop_loss=data.get('stop_loss'),
                take_profit=data.get('take_profit'),
                risk_level=data.get('risk_level', 'medium')
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ 解析交易决策失败: {e}")
            logger.debug(f"响应内容: {response_text}")
            return None
    
    async def get_model_insights(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取模型洞察"""
        try:
            insights_prompt = f"""
作为{self.name}，请提供当前市场的整体洞察和展望：

当前性能指标：
- 总交易次数: {self.performance_metrics['total_trades']}
- 胜率: {self.performance_metrics.get('win_rate', 0):.1%}
- 总收益: ${self.performance_metrics['total_return']:.2f}

请提供：
1. 当前市场环境评估
2. 主要关注的投资机会
3. 风险提示
4. 下一步策略调整

请用简洁明了的语言回答。
"""
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": insights_prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            if response.choices:
                insights_text = response.choices[0].message.content
                return {
                    'model_name': self.name,
                    'timestamp': datetime.now().isoformat(),
                    'insights': insights_text,
                    'performance': self.performance_metrics
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ 获取模型洞察失败: {e}")
            return {}
    
    async def cleanup(self):
        """清理资源"""
        await super().cleanup()
        self.client = None
        logger.info(f"🧹 {self.name} 已清理完成")
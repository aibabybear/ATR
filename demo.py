#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Trading Robot 演示脚本
展示系统的基本功能和架构
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))


def print_banner():
    """打印演示横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                 AI Trading Robot 演示                       ║
    ║                 功能展示和架构演示                            ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def demo_market_data():
    """演示市场数据获取"""
    print("\n📊 演示市场数据获取...")
    
    try:
        from data.market_data import MarketDataProvider
        
        # 初始化市场数据提供者
        market_data = MarketDataProvider()
        await market_data.initialize()
        
        # 获取几只股票的数据
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        print(f"  获取 {', '.join(symbols)} 的实时数据:")
        
        for symbol in symbols:
            data = await market_data.get_real_time_data(symbol)
            if data:
                print(f"    {symbol}: ${data['price']:.2f} ({data['change_percent']:+.2f}%) [{data['source']}]")
            else:
                print(f"    {symbol}: 数据获取失败")
        
        # 获取市场情绪
        sentiment = await market_data.get_market_sentiment()
        print(f"  市场情绪综合评分: {sentiment['composite_score']:.2f}")
        
        await market_data.shutdown()
        print("  ✅ 市场数据演示完成")
        
    except Exception as e:
        print(f"  ❌ 市场数据演示失败: {e}")


async def demo_database():
    """演示数据库操作"""
    print("\n🗄️ 演示数据库操作...")
    
    try:
        from utils.database import DatabaseManager
        
        # 初始化数据库
        db = DatabaseManager()
        await db.initialize()
        
        # 保存一个示例AI模型
        model_id = await db.save_ai_model(
            name="Demo-GPT-Trader",
            model_type="gpt-4",
            config={"temperature": 0.1, "max_tokens": 2000}
        )
        print(f"  保存AI模型，ID: {model_id}")
        
        # 保存一个示例交易记录
        trade_data = {
            'model_name': 'Demo-GPT-Trader',
            'symbol': 'AAPL',
            'action': 'buy',
            'quantity': 10,
            'price': 150.00,
            'commission': 1.00,
            'reason': '技术分析显示上涨趋势',
            'confidence': 0.8
        }
        
        trade_id = await db.save_trade(trade_data)
        print(f"  保存交易记录，ID: {trade_id}")
        
        # 获取数据库统计
        stats = await db.get_database_stats()
        print(f"  数据库统计: {stats.get('trades_count', 0)} 笔交易, {stats.get('ai_models_count', 0)} 个模型")
        
        await db.close()
        print("  ✅ 数据库演示完成")
        
    except Exception as e:
        print(f"  ❌ 数据库演示失败: {e}")


async def demo_ai_models():
    """演示AI模型功能"""
    print("\n🤖 演示AI模型功能...")
    
    try:
        from ai_models.base_model import BaseAIModel, TradingDecision, MarketAnalysis
        
        # 创建一个简单的演示模型
        class DemoTrader(BaseAIModel):
            async def initialize(self):
                self.is_active = True
                return True
            
            async def analyze_market(self, market_data):
                analyses = {}
                for symbol in ['AAPL', 'MSFT']:
                    if symbol in market_data:
                        analyses[symbol] = MarketAnalysis(
                            symbol=symbol,
                            trend='bullish',
                            strength=0.7,
                            sentiment_score=0.2
                        )
                return analyses
            
            async def make_trading_decision(self, market_data):
                if 'AAPL' in market_data:
                    return TradingDecision(
                        symbol='AAPL',
                        action='buy',
                        quantity=5,
                        confidence=0.75,
                        reason='演示交易决策'
                    )
                return None
        
        # 创建演示模型实例
        demo_model = DemoTrader("Demo-Trader", {})
        await demo_model.initialize()
        
        print(f"  创建演示模型: {demo_model.name}")
        
        # 模拟市场数据
        mock_market_data = {
            'AAPL': {'price': 150.0, 'change_percent': 1.5},
            'MSFT': {'price': 300.0, 'change_percent': -0.5}
        }
        
        # 进行市场分析
        analyses = await demo_model.analyze_market(mock_market_data)
        print(f"  市场分析结果: 分析了 {len(analyses)} 只股票")
        
        # 做出交易决策
        decision = await demo_model.make_trading_decision(mock_market_data)
        if decision:
            print(f"  交易决策: {decision.action.upper()} {decision.symbol} x{decision.quantity} (置信度: {decision.confidence:.2f})")
        
        print("  ✅ AI模型演示完成")
        
    except Exception as e:
        print(f"  ❌ AI模型演示失败: {e}")


async def demo_risk_management():
    """演示风险管理"""
    print("\n🛡️ 演示风险管理...")
    
    try:
        from core.risk_manager import RiskManager
        from core.trading_engine import TradingDecision
        
        # 创建风险管理器
        risk_manager = RiskManager()
        await risk_manager.initialize()
        
        print("  风险管理器初始化完成")
        
        # 创建一个模拟的交易决策
        decision = TradingDecision(
            symbol='AAPL',
            action='buy',
            quantity=100,  # 较大的数量来触发风险检查
            confidence=0.8,
            reason='演示风险检查'
        )
        
        # 创建模拟投资组合
        class MockPortfolio:
            def __init__(self):
                self.cash_balance = 5000  # 较少的现金来触发风险检查
                self.initial_capital = 10000
        
        mock_portfolio = MockPortfolio()
        
        # 进行风险检查
        risk_result = await risk_manager.check_trade_risk(decision, mock_portfolio)
        
        print(f"  风险检查结果: {'通过' if risk_result.approved else '拒绝'}")
        print(f"  调整后数量: {risk_result.adjusted_quantity}")
        if risk_result.warnings:
            print(f"  风险警告: {', '.join(risk_result.warnings)}")
        
        print("  ✅ 风险管理演示完成")
        
    except Exception as e:
        print(f"  ❌ 风险管理演示失败: {e}")


async def demo_portfolio():
    """演示投资组合管理"""
    print("\n💼 演示投资组合管理...")
    
    try:
        from core.portfolio import Portfolio
        
        # 创建投资组合
        portfolio = Portfolio()
        await portfolio.initialize(10000)  # $10,000 初始资金
        
        print(f"  初始化投资组合: ${portfolio.initial_capital:,.2f}")
        
        # 模拟一些交易
        trades = [
            ('AAPL', 'buy', 10, 150.0),
            ('MSFT', 'buy', 5, 300.0),
            ('GOOGL', 'buy', 2, 2500.0)
        ]
        
        for symbol, action, quantity, price in trades:
            await portfolio.update_position(symbol, action, quantity, price, 'Demo-Model')
            print(f"  执行交易: {action.upper()} {symbol} x{quantity} @ ${price:.2f}")
        
        # 获取投资组合状态
        status = await portfolio.get_status()
        print(f"  投资组合总值: ${status['total_value']:,.2f}")
        print(f"  现金余额: ${status['cash_balance']:,.2f}")
        print(f"  持仓价值: ${status['positions_value']:,.2f}")
        print(f"  总收益率: {status['total_return_percent']:.2f}%")
        
        # 获取持仓信息
        positions = await portfolio.get_positions()
        print(f"  当前持仓: {len(positions)} 只股票")
        
        print("  ✅ 投资组合演示完成")
        
    except Exception as e:
        print(f"  ❌ 投资组合演示失败: {e}")


async def demo_logging():
    """演示日志系统"""
    print("\n📝 演示日志系统...")
    
    try:
        from utils.logger import get_trading_logger, get_performance_logger, get_audit_logger
        
        # 交易日志
        trading_logger = get_trading_logger('Demo-Model')
        trading_logger.trade_executed('AAPL', 'buy', 10, 150.0, 'demo-001', '演示交易')
        trading_logger.decision_made('MSFT', 'sell', 0.8, '技术分析信号')
        
        # 性能日志
        performance_logger = get_performance_logger('Demo-Model')
        performance_logger.daily_summary('2024-01-01', 0.05, 0.02, 5, 0.6)
        
        # 审计日志
        audit_logger = get_audit_logger()
        audit_logger.system_start('1.0.0', {'mode': 'demo'})
        
        print("  ✅ 日志记录完成，请查看 logs/ 目录")
        
    except Exception as e:
        print(f"  ❌ 日志演示失败: {e}")


def demo_configuration():
    """演示配置系统"""
    print("\n⚙️ 演示配置系统...")
    
    try:
        from config.settings import Settings
        
        settings = Settings()
        
        print(f"  初始资金: ${settings.INITIAL_CAPITAL:,.2f}")
        print(f"  交易间隔: {settings.TRADING_INTERVAL} 秒")
        print(f"  最大仓位: {settings.MAX_POSITION_SIZE:.1%}")
        print(f"  支持股票数量: {len(settings.SUPPORTED_SYMBOLS)}")
        
        enabled_models = settings.get_enabled_models()
        print(f"  启用的AI模型: {', '.join(enabled_models) if enabled_models else '无 (需要配置API密钥)'}")
        
        print("  ✅ 配置系统演示完成")
        
    except Exception as e:
        print(f"  ❌ 配置演示失败: {e}")


async def main():
    """主演示函数"""
    print_banner()
    
    print(f"🕐 演示开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行各个演示
    demo_configuration()
    await demo_market_data()
    await demo_database()
    await demo_ai_models()
    await demo_risk_management()
    await demo_portfolio()
    await demo_logging()
    
    print("\n🎉 演示完成！")
    print("\n📋 接下来您可以:")
    print("  1. 运行 python3 start.py 启动完整系统")
    print("  2. 配置 config/api_keys.py 添加真实的API密钥")
    print("  3. 访问 http://localhost:5000 查看Web界面")
    print("  4. 查看 logs/ 目录中的日志文件")
    
    print("\n⚠️ 重要提醒: 这只是演示，实际使用前请充分了解风险！")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示运行出错: {e}")
        import traceback
        traceback.print_exc()
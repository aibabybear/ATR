#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Trading Robot 系统测试脚本
快速验证系统各组件是否正常工作
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    
    test_modules = [
        ('config.settings', 'Settings'),
        ('core.trading_engine', 'TradingEngine'),
        ('core.portfolio', 'Portfolio'),
        ('core.risk_manager', 'RiskManager'),
        ('core.order_manager', 'OrderManager'),
        ('ai_models.base_model', 'BaseAIModel'),
        ('ai_models.model_manager', 'ModelManager'),
        ('data.market_data', 'MarketDataProvider'),
        ('utils.database', 'DatabaseManager'),
        ('utils.logger', 'get_logger'),
        ('web.app', 'create_app')
    ]
    
    success_count = 0
    
    for module_name, class_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
            success_count += 1
        except ImportError as e:
            print(f"  ❌ {module_name}.{class_name} - 导入失败: {e}")
        except AttributeError as e:
            print(f"  ❌ {module_name}.{class_name} - 属性错误: {e}")
        except Exception as e:
            print(f"  ❌ {module_name}.{class_name} - 其他错误: {e}")
    
    print(f"\n导入测试结果: {success_count}/{len(test_modules)} 成功")
    return success_count == len(test_modules)


def test_dependencies():
    """测试外部依赖"""
    print("\n📦 测试外部依赖...")
    
    dependencies = [
        'flask',
        'pandas',
        'numpy',
        'loguru',
        'aiohttp',
        'asyncio',
        'sqlite3',
        'json',
        'datetime'
    ]
    
    success_count = 0
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
            success_count += 1
        except ImportError:
            print(f"  ❌ {dep} - 未安装")
    
    # 测试可选依赖
    optional_deps = [
        ('yfinance', 'Yahoo Finance数据'),
        ('openai', 'OpenAI API'),
        ('anthropic', 'Anthropic API')
    ]
    
    print("\n  可选依赖:")
    for dep, desc in optional_deps:
        try:
            __import__(dep)
            print(f"    ✅ {dep} ({desc})")
        except ImportError:
            print(f"    ⚠️ {dep} ({desc}) - 未安装，某些功能可能不可用")
    
    print(f"\n依赖测试结果: {success_count}/{len(dependencies)} 核心依赖可用")
    return success_count >= len(dependencies) - 2  # 允许2个依赖缺失


async def test_database():
    """测试数据库功能"""
    print("\n🗄️ 测试数据库功能...")
    
    try:
        from utils.database import DatabaseManager
        
        # 创建测试数据库
        db = DatabaseManager()
        await db.initialize()
        
        # 测试基本操作
        model_id = await db.save_ai_model(
            name="Test-Model",
            model_type="test",
            config={"test": True}
        )
        
        if model_id:
            print("  ✅ 数据库写入测试通过")
        
        # 测试读取
        model = await db.get_ai_model("Test-Model")
        if model and model['name'] == "Test-Model":
            print("  ✅ 数据库读取测试通过")
        
        # 测试统计
        stats = await db.get_database_stats()
        if isinstance(stats, dict):
            print("  ✅ 数据库统计测试通过")
        
        await db.close()
        print("  ✅ 数据库功能测试完成")
        return True
        
    except Exception as e:
        print(f"  ❌ 数据库测试失败: {e}")
        return False


async def test_market_data():
    """测试市场数据功能"""
    print("\n📊 测试市场数据功能...")
    
    try:
        from data.market_data import MarketDataProvider
        
        provider = MarketDataProvider()
        await provider.initialize()
        
        # 测试获取数据
        data = await provider.get_real_time_data('AAPL')
        if data and 'price' in data:
            print(f"  ✅ 获取AAPL数据: ${data['price']:.2f} ({data.get('source', 'unknown')})")
        
        # 测试市场情绪
        sentiment = await provider.get_market_sentiment()
        if sentiment and 'composite_score' in sentiment:
            print(f"  ✅ 市场情绪分析: {sentiment['composite_score']:.2f}")
        
        await provider.shutdown()
        print("  ✅ 市场数据功能测试完成")
        return True
        
    except Exception as e:
        print(f"  ❌ 市场数据测试失败: {e}")
        return False


async def test_trading_engine():
    """测试交易引擎"""
    print("\n⚙️ 测试交易引擎...")
    
    try:
        from core.trading_engine import TradingEngine
        
        engine = TradingEngine()
        await engine.initialize()
        
        # 测试市场状态检查
        market_open = engine.is_market_open()
        print(f"  ✅ 市场状态检查: {'开盘' if market_open else '休市'}")
        
        # 测试获取市场数据
        market_data = await engine.get_market_data()
        if market_data:
            print(f"  ✅ 获取市场数据: {len(market_data)} 个数据源")
        
        await engine.shutdown()
        print("  ✅ 交易引擎测试完成")
        return True
        
    except Exception as e:
        print(f"  ❌ 交易引擎测试失败: {e}")
        return False


async def test_portfolio():
    """测试投资组合"""
    print("\n💼 测试投资组合功能...")
    
    try:
        from core.portfolio import Portfolio
        
        portfolio = Portfolio()
        await portfolio.initialize(10000)
        
        # 测试基本状态
        status = await portfolio.get_status()
        if status['total_value'] == 10000:
            print("  ✅ 投资组合初始化正确")
        
        # 测试模拟交易
        await portfolio.update_position('AAPL', 'buy', 10, 150.0, 'Test-Model')
        
        new_status = await portfolio.get_status()
        if new_status['total_value'] != 10000:  # 应该有变化
            print("  ✅ 投资组合更新功能正常")
        
        print("  ✅ 投资组合功能测试完成")
        return True
        
    except Exception as e:
        print(f"  ❌ 投资组合测试失败: {e}")
        return False


def test_configuration():
    """测试配置系统"""
    print("\n⚙️ 测试配置系统...")
    
    try:
        from config.settings import Settings
        
        settings = Settings()
        
        # 测试基本配置
        if hasattr(settings, 'INITIAL_CAPITAL') and settings.INITIAL_CAPITAL > 0:
            print(f"  ✅ 初始资金配置: ${settings.INITIAL_CAPITAL:,.2f}")
        
        if hasattr(settings, 'SUPPORTED_SYMBOLS') and len(settings.SUPPORTED_SYMBOLS) > 0:
            print(f"  ✅ 支持股票配置: {len(settings.SUPPORTED_SYMBOLS)} 只")
        
        # 测试API密钥检查
        enabled_models = settings.get_enabled_models()
        print(f"  ✅ 启用的AI模型: {len(enabled_models)} 个")
        
        print("  ✅ 配置系统测试完成")
        return True
        
    except Exception as e:
        print(f"  ❌ 配置系统测试失败: {e}")
        return False


def test_web_app():
    """测试Web应用"""
    print("\n🌐 测试Web应用...")
    
    try:
        from web.app import create_app
        
        # 创建模拟系统
        class MockSystem:
            def __init__(self):
                self.running = False
                self.trading_engine = MockTradingEngine()
                self.model_manager = MockModelManager()
        
        class MockTradingEngine:
            def is_market_open(self):
                return True
        
        class MockModelManager:
            def get_active_models(self):
                return []
            def get_model_rankings(self):
                return []
            def get_performance_summary(self):
                return {}
        
        mock_system = MockSystem()
        app = create_app(mock_system)
        
        if app:
            print("  ✅ Web应用创建成功")
            
            # 测试路由
            with app.test_client() as client:
                response = client.get('/')
                if response.status_code == 200:
                    print("  ✅ 主页路由正常")
                
                response = client.get('/api/status')
                if response.status_code == 200:
                    print("  ✅ API路由正常")
        
        print("  ✅ Web应用测试完成")
        return True
        
    except Exception as e:
        print(f"  ❌ Web应用测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🧪 AI Trading Robot 系统测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("模块导入", test_imports()))
    test_results.append(("外部依赖", test_dependencies()))
    test_results.append(("配置系统", test_configuration()))
    test_results.append(("数据库功能", await test_database()))
    test_results.append(("市场数据", await test_market_data()))
    test_results.append(("交易引擎", await test_trading_engine()))
    test_results.append(("投资组合", await test_portfolio()))
    test_results.append(("Web应用", test_web_app()))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("📋 测试结果汇总:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统可以正常运行。")
        print("\n📋 下一步:")
        print("  1. 配置API密钥: config/api_keys.py")
        print("  2. 运行演示: python3 demo.py")
        print("  3. 启动系统: python3 start.py")
    elif passed >= total * 0.8:
        print("\n⚠️ 大部分测试通过，系统基本可用。")
        print("请检查失败的测试项目。")
    else:
        print("\n❌ 多项测试失败，请检查系统配置和依赖。")
        print("建议运行: pip install -r requirements.txt")
    
    return passed >= total * 0.8


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
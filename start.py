#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Trading Robot 启动脚本
快速启动和配置向导
"""

import os
import sys
import asyncio
from pathlib import Path
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))


def print_banner():
    """打印启动横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    AI Trading Robot (ATR)                   ║
    ║                   多AI模型自动交易系统                        ║
    ║                                                              ║
    ║  🤖 支持GPT、Claude等多种AI模型                              ║
    ║  📈 自动市场分析和交易决策                                    ║
    ║  🛡️ 智能风险管理                                            ║
    ║  📊 实时性能监控                                             ║
    ║  🌐 Web界面管理                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_dependencies():
    """检查依赖项"""
    print("🔍 检查系统依赖...")
    
    required_packages = [
        'flask', 'flask-socketio', 'pandas', 'numpy', 'loguru',
        'aiohttp', 'asyncio', 'yfinance', 'openai', 'anthropic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package} (缺失)")
    
    if missing_packages:
        print(f"\n⚠️ 发现缺失的依赖包: {', '.join(missing_packages)}")
        print("请运行以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ 所有依赖项检查通过")
    return True


def setup_api_keys():
    """设置API密钥"""
    print("\n🔑 API密钥配置")
    
    api_keys_file = Path("config/api_keys.py")
    example_file = Path("config/api_keys.example.py")
    
    if api_keys_file.exists():
        print("  ✅ API密钥文件已存在")
        return True
    
    if not example_file.exists():
        print("  ❌ 找不到API密钥模板文件")
        return False
    
    print("  📝 创建API密钥配置文件...")
    
    # 复制示例文件
    with open(example_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 交互式配置
    print("\n请输入您的API密钥 (直接回车跳过):")
    
    # OpenAI API Key
    openai_key = input("OpenAI API Key: ").strip()
    if openai_key:
        content = content.replace('your_openai_api_key_here', openai_key)
    
    # Anthropic API Key
    anthropic_key = input("Anthropic API Key: ").strip()
    if anthropic_key:
        content = content.replace('your_anthropic_api_key_here', anthropic_key)
    
    # Alpha Vantage API Key
    alpha_vantage_key = input("Alpha Vantage API Key: ").strip()
    if alpha_vantage_key:
        content = content.replace('your_alpha_vantage_api_key_here', alpha_vantage_key)
    
    # 保存配置文件
    with open(api_keys_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✅ API密钥配置文件已创建: {api_keys_file}")
    print("  💡 您可以稍后编辑此文件来添加或修改API密钥")
    
    return True


def create_directories():
    """创建必要的目录"""
    print("\n📁 创建项目目录...")
    
    directories = [
        'logs',
        'data',
        'backups',
        'web/static/css',
        'web/static/js',
        'web/static/images'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")
    
    print("✅ 目录创建完成")


def show_startup_options():
    """显示启动选项"""
    print("\n🚀 启动选项:")
    print("  1. 启动完整系统 (推荐)")
    print("  2. 仅启动Web界面")
    print("  3. 运行系统测试")
    print("  4. 查看配置信息")
    print("  5. 退出")
    
    while True:
        try:
            choice = input("\n请选择 (1-5): ").strip()
            
            if choice == '1':
                return 'full'
            elif choice == '2':
                return 'web_only'
            elif choice == '3':
                return 'test'
            elif choice == '4':
                return 'config'
            elif choice == '5':
                return 'exit'
            else:
                print("❌ 无效选择，请输入1-5")
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            return 'exit'


def show_config_info():
    """显示配置信息"""
    print("\n📋 系统配置信息:")
    
    try:
        from config.settings import Settings
        settings = Settings()
        
        print(f"  🌐 Web服务器: http://{settings.WEB_HOST}:{settings.WEB_PORT}")
        print(f"  💰 初始资金: ${settings.INITIAL_CAPITAL:,.2f}")
        print(f"  ⏱️ 交易间隔: {settings.TRADING_INTERVAL}秒")
        print(f"  📊 最大仓位: {settings.MAX_POSITION_SIZE:.1%}")
        print(f"  🛡️ 止损比例: {settings.STOP_LOSS_PERCENTAGE:.1%}")
        
        enabled_models = settings.get_enabled_models()
        print(f"  🤖 启用的AI模型: {', '.join(enabled_models) if enabled_models else '无'}")
        
        print(f"  📈 支持的股票数量: {len(settings.SUPPORTED_SYMBOLS)}")
        print(f"  🗄️ 数据库: {settings.DATABASE_URL}")
        
    except Exception as e:
        print(f"  ❌ 读取配置失败: {e}")


async def run_system_test():
    """运行系统测试"""
    print("\n🧪 运行系统测试...")
    
    try:
        # 测试数据库连接
        print("  📊 测试数据库连接...")
        from utils.database import DatabaseManager
        db = DatabaseManager()
        await db.initialize()
        stats = await db.get_database_stats()
        await db.close()
        print("    ✅ 数据库连接正常")
        
        # 测试市场数据
        print("  📈 测试市场数据获取...")
        from data.market_data import MarketDataProvider
        market_data = MarketDataProvider()
        await market_data.initialize()
        test_data = await market_data.get_real_time_data('AAPL')
        await market_data.shutdown()
        
        if test_data:
            print(f"    ✅ 市场数据获取正常 (AAPL: ${test_data.get('price', 'N/A')})")
        else:
            print("    ⚠️ 市场数据获取异常，将使用模拟数据")
        
        # 测试AI模型
        print("  🤖 测试AI模型...")
        from config.settings import Settings
        enabled_models = Settings.get_enabled_models()
        
        if enabled_models:
            print(f"    ✅ 发现 {len(enabled_models)} 个可用的AI模型")
            for model in enabled_models:
                print(f"      - {model}")
        else:
            print("    ⚠️ 没有可用的AI模型，请检查API密钥配置")
        
        print("\n✅ 系统测试完成")
        
    except Exception as e:
        print(f"\n❌ 系统测试失败: {e}")
        logger.exception("系统测试异常")


async def start_full_system():
    """启动完整系统"""
    print("\n🚀 启动AI Trading Robot完整系统...")
    
    try:
        # 导入并启动主系统
        from main import main
        await main()
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，系统正在关闭...")
    except Exception as e:
        print(f"\n❌ 系统启动失败: {e}")
        logger.exception("系统启动异常")


def start_web_only():
    """仅启动Web界面"""
    print("\n🌐 启动Web界面...")
    
    try:
        from web.app import create_app
        
        # 创建模拟系统用于Web界面
        class MockATRSystem:
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
                return {
                    'total_models': 0,
                    'active_models': 0,
                    'total_trades': 0,
                    'average_return': 0.0
                }
        
        mock_system = MockATRSystem()
        app = create_app(mock_system)
        
        print("\n🌐 Web界面已启动: http://localhost:5000")
        print("💡 这是演示模式，没有实际的交易功能")
        print("按 Ctrl+C 停止服务器")
        
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\n👋 Web服务器已停止")
    except Exception as e:
        print(f"\n❌ Web界面启动失败: {e}")
        logger.exception("Web界面启动异常")


async def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 请先安装缺失的依赖包")
        return
    
    # 创建目录
    create_directories()
    
    # 设置API密钥
    if not setup_api_keys():
        print("\n❌ API密钥配置失败")
        return
    
    # 导入API密钥配置
    try:
        import config.api_keys
        print("✅ API密钥配置已加载")
    except ImportError:
        print("⚠️ API密钥配置文件未找到，某些功能可能不可用")
    
    # 显示启动选项
    while True:
        choice = show_startup_options()
        
        if choice == 'full':
            await start_full_system()
            break
        elif choice == 'web_only':
            start_web_only()
            break
        elif choice == 'test':
            await run_system_test()
            input("\n按回车键继续...")
        elif choice == 'config':
            show_config_info()
            input("\n按回车键继续...")
        elif choice == 'exit':
            print("\n👋 再见！")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        sys.exit(1)
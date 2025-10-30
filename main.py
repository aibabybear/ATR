#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Trading Robot (ATR) - 主程序入口
多AI模型自动交易系统
"""

import asyncio
import threading
import time
from datetime import datetime
from loguru import logger

from core.trading_engine import TradingEngine
from ai_models.model_manager import ModelManager
from web.app import create_app
from config.settings import Settings
from utils.database import DatabaseManager


class ATRSystem:
    """AI交易机器人系统主类"""
    
    def __init__(self):
        self.settings = Settings()
        self.db_manager = DatabaseManager()
        self.trading_engine = TradingEngine()
        self.model_manager = ModelManager()
        self.web_app = None
        self.running = False
        
        # 配置日志
        logger.add(
            "logs/atr_{time}.log",
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
    
    async def initialize(self):
        """初始化系统"""
        logger.info("🚀 初始化AI交易系统...")
        
        # 初始化数据库
        await self.db_manager.initialize()
        logger.info("✅ 数据库初始化完成")
        
        # 初始化交易引擎
        await self.trading_engine.initialize()
        logger.info("✅ 交易引擎初始化完成")
        
        # 初始化AI模型管理器
        await self.model_manager.initialize()
        logger.info("✅ AI模型管理器初始化完成")
        
        # 创建Web应用
        self.web_app = create_app(self)
        logger.info("✅ Web应用创建完成")
        
        logger.info("🎉 系统初始化完成！")
    
    async def start_trading(self):
        """启动交易循环"""
        logger.info("📈 启动交易循环...")
        self.running = True
        
        while self.running:
            try:
                # 检查市场开放状态
                if self.trading_engine.is_market_open():
                    # 获取所有活跃的AI模型
                    active_models = self.model_manager.get_active_models()
                    
                    # 并行执行所有模型的交易决策
                    tasks = []
                    for model in active_models:
                        task = asyncio.create_task(
                            self.execute_model_trading(model)
                        )
                        tasks.append(task)
                    
                    # 等待所有模型完成交易决策
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    logger.info(f"📊 完成 {len(active_models)} 个模型的交易循环")
                else:
                    logger.info("🌙 市场关闭，等待下次开盘...")
                
                # 等待下一个交易周期
                await asyncio.sleep(self.settings.TRADING_INTERVAL)
                
            except Exception as e:
                logger.error(f"❌ 交易循环出错: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟
    
    async def execute_model_trading(self, model):
        """执行单个模型的交易逻辑"""
        try:
            # 获取市场数据
            market_data = await self.trading_engine.get_market_data()
            
            # AI模型分析和决策
            decision = await model.make_trading_decision(market_data)
            
            # 执行交易决策
            if decision:
                result = await self.trading_engine.execute_trade(
                    model.name, decision
                )
                logger.info(
                    f"🤖 {model.name} 执行交易: {decision['action']} "
                    f"{decision['symbol']} x{decision['quantity']}"
                )
        
        except Exception as e:
            logger.error(f"❌ 模型 {model.name} 交易出错: {e}")
    
    def start_web_server(self):
        """启动Web服务器"""
        logger.info("🌐 启动Web服务器...")
        self.web_app.run(
            host=self.settings.WEB_HOST,
            port=self.settings.WEB_PORT,
            debug=False,  # 在子线程中禁用调试模式
            use_reloader=False,  # 禁用重载器
            threaded=True
        )
    
    async def shutdown(self):
        """关闭系统"""
        logger.info("🛑 正在关闭系统...")
        self.running = False
        
        # 关闭各个组件
        await self.trading_engine.shutdown()
        await self.model_manager.shutdown()
        await self.db_manager.close()
        
        logger.info("✅ 系统已安全关闭")


async def main():
    """主函数"""
    system = ATRSystem()
    
    try:
        # 初始化系统
        await system.initialize()
        
        # 在单独线程中启动Web服务器
        web_thread = threading.Thread(
            target=system.start_web_server,
            daemon=True
        )
        web_thread.start()
        
        logger.info("🌐 Web界面: http://localhost:5000")
        
        # 启动交易循环
        await system.start_trading()
        
    except KeyboardInterrupt:
        logger.info("👋 收到退出信号")
    except Exception as e:
        logger.error(f"❌ 系统运行出错: {e}")
    finally:
        await system.shutdown()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║        AI Trading Robot (ATR)        ║
    ║      多AI模型自动交易系统              ║
    ╚══════════════════════════════════════╝
    """)
    
    # 运行主程序
    asyncio.run(main())
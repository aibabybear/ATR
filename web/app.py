#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web应用 - Flask后端
"""

import asyncio
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from loguru import logger
import json
from typing import Dict, Any


def create_app(atr_system):
    """创建Flask应用"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'atr-trading-system-2024'
    
    # 初始化SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # 存储ATR系统引用
    app.atr_system = atr_system
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard():
        """仪表板页面"""
        return render_template('dashboard.html')
    
    @app.route('/models')
    def models():
        """模型管理页面"""
        return render_template('models.html')
    
    @app.route('/trades')
    def trades():
        """交易记录页面"""
        return render_template('trades.html')
    
    @app.route('/api/status')
    def api_status():
        """系统状态API"""
        try:
            status = {
                'system_running': app.atr_system.running,
                'market_open': app.atr_system.trading_engine.is_market_open(),
                'active_models': len(app.atr_system.model_manager.get_active_models()),
                'timestamp': datetime.now().isoformat()
            }
            return jsonify(status)
        except Exception as e:
            logger.error(f"❌ 获取系统状态失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/models')
    def api_models():
        """模型信息API"""
        try:
            models_info = []
            
            for model in app.atr_system.model_manager.get_active_models():
                model_info = {
                    'name': model.name,
                    'is_active': model.is_active,
                    'performance': model.get_performance_metrics(),
                    'trade_count': len(model.get_trade_history())
                }
                models_info.append(model_info)
            
            return jsonify(models_info)
        except Exception as e:
            logger.error(f"❌ 获取模型信息失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/rankings')
    def api_rankings():
        """模型排名API"""
        try:
            rankings = app.atr_system.model_manager.get_model_rankings()
            return jsonify(rankings)
        except Exception as e:
            logger.error(f"❌ 获取模型排名失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/portfolio/<model_name>')
    def api_portfolio(model_name):
        """投资组合API"""
        try:
            # 这里需要异步调用，简化处理
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            portfolio_status = loop.run_until_complete(
                app.atr_system.trading_engine.get_portfolio_status(model_name)
            )
            
            loop.close()
            
            return jsonify(portfolio_status)
        except Exception as e:
            logger.error(f"❌ 获取投资组合失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/trades')
    def api_trades():
        """交易记录API"""
        try:
            limit = request.args.get('limit', 50, type=int)
            model_name = request.args.get('model', '')
            
            # 异步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            trades = loop.run_until_complete(
                app.atr_system.trading_engine.portfolio.get_trade_history(
                    model_name, limit
                )
            )
            
            loop.close()
            
            return jsonify(trades)
        except Exception as e:
            logger.error(f"❌ 获取交易记录失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/market-data')
    def api_market_data():
        """市场数据API"""
        try:
            symbols = request.args.get('symbols', 'AAPL,MSFT,GOOGL').split(',')
            
            # 异步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            market_data = {}
            for symbol in symbols[:10]:  # 限制数量
                data = loop.run_until_complete(
                    app.atr_system.trading_engine.market_data.get_real_time_data(symbol.strip())
                )
                if data:
                    market_data[symbol.strip()] = data
            
            loop.close()
            
            return jsonify(market_data)
        except Exception as e:
            logger.error(f"❌ 获取市场数据失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/performance')
    def api_performance():
        """性能分析API"""
        try:
            performance_summary = app.atr_system.model_manager.get_performance_summary()
            return jsonify(performance_summary)
        except Exception as e:
            logger.error(f"❌ 获取性能分析失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/insights')
    def api_insights():
        """AI洞察API"""
        try:
            # 异步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            market_data = loop.run_until_complete(
                app.atr_system.trading_engine.get_market_data()
            )
            
            insights = loop.run_until_complete(
                app.atr_system.model_manager.get_model_insights(market_data)
            )
            
            loop.close()
            
            return jsonify(insights)
        except Exception as e:
            logger.error(f"❌ 获取AI洞察失败: {e}")
            return jsonify({'error': str(e)}), 500
    
    # WebSocket事件处理
    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        logger.info("🔌 客户端已连接")
        emit('status', {'message': '连接成功', 'timestamp': datetime.now().isoformat()})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开连接"""
        logger.info("🔌 客户端已断开连接")
    
    @socketio.on('request_update')
    def handle_request_update():
        """请求数据更新"""
        try:
            # 发送实时数据
            emit('data_update', {
                'timestamp': datetime.now().isoformat(),
                'models': len(app.atr_system.model_manager.get_active_models()),
                'market_open': app.atr_system.trading_engine.is_market_open()
            })
        except Exception as e:
            logger.error(f"❌ 处理更新请求失败: {e}")
            emit('error', {'message': str(e)})
    
    # 定期广播数据更新
    def broadcast_updates():
        """广播数据更新"""
        try:
            if not app.atr_system.running:
                return
            
            # 获取最新数据
            update_data = {
                'timestamp': datetime.now().isoformat(),
                'system_status': {
                    'running': app.atr_system.running,
                    'market_open': app.atr_system.trading_engine.is_market_open(),
                    'active_models': len(app.atr_system.model_manager.get_active_models())
                },
                'rankings': app.atr_system.model_manager.get_model_rankings()[:5]  # 前5名
            }
            
            socketio.emit('live_update', update_data)
            
        except Exception as e:
            logger.error(f"❌ 广播更新失败: {e}")
    
    # 启动定期更新任务
    def start_background_tasks():
        """启动后台任务"""
        def update_loop():
            while True:
                socketio.sleep(30)  # 每30秒更新一次
                broadcast_updates()
        
        socketio.start_background_task(update_loop)
    
    # 启动后台任务
    start_background_tasks()
    
    return app


# 如果直接运行此文件
if __name__ == '__main__':
    # 创建一个简单的测试应用
    class MockATRSystem:
        def __init__(self):
            self.running = True
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
    
    mock_system = MockATRSystem()
    app = create_app(mock_system)
    
    print("""
    ╔══════════════════════════════════════╗
    ║           ATR Web Interface          ║
    ║        http://localhost:5000         ║
    ╚══════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
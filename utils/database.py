#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作模块
"""

import asyncio
import sqlite3
import aiosqlite
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from loguru import logger
import json

from config.settings import Settings


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.settings = Settings()
        self.db_path = self._get_db_path()
        self.connection = None
        self.is_initialized = False
    
    def _get_db_path(self) -> str:
        """获取数据库路径"""
        db_url = self.settings.DATABASE_URL
        
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            # 确保数据库目录存在
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            return db_path
        else:
            # 其他数据库类型的处理
            raise NotImplementedError("目前只支持SQLite数据库")
    
    async def initialize(self):
        """初始化数据库"""
        try:
            logger.info(f"🗄️ 初始化数据库: {self.db_path}")
            
            # 创建数据库连接
            self.connection = await aiosqlite.connect(self.db_path)
            
            # 启用外键约束
            await self.connection.execute("PRAGMA foreign_keys = ON")
            
            # 创建表结构
            await self._create_tables()
            
            # 创建索引
            await self._create_indexes()
            
            self.is_initialized = True
            logger.info("✅ 数据库初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
    
    async def _create_tables(self):
        """创建数据库表"""
        # AI模型表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS ai_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                model_type TEXT NOT NULL,
                config TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 交易记录表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                commission REAL DEFAULT 0.0,
                pnl REAL DEFAULT 0.0,
                order_id TEXT,
                reason TEXT,
                confidence REAL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES ai_models (id)
            )
        """)
        
        # 持仓表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                avg_cost REAL NOT NULL,
                current_price REAL DEFAULT 0.0,
                market_value REAL DEFAULT 0.0,
                unrealized_pnl REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES ai_models (id),
                UNIQUE(model_id, symbol)
            )
        """)
        
        # 投资组合快照表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                total_value REAL NOT NULL,
                cash_balance REAL NOT NULL,
                positions_value REAL NOT NULL,
                total_return REAL DEFAULT 0.0,
                daily_return REAL DEFAULT 0.0,
                snapshot_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES ai_models (id)
            )
        """)
        
        # 性能指标表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES ai_models (id)
            )
        """)
        
        # 市场数据表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER,
                change_percent REAL,
                market_cap REAL,
                data_source TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 系统日志表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_level TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                function TEXT,
                line_number INTEGER,
                extra_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 风险事件表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                event_type TEXT NOT NULL,
                symbol TEXT,
                risk_score REAL,
                description TEXT,
                action_taken TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES ai_models (id)
            )
        """)
        
        await self.connection.commit()
        logger.info("📋 数据库表创建完成")
    
    async def _create_indexes(self):
        """创建数据库索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_trades_model_id ON trades(model_id)",
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at)",
            "CREATE INDEX IF NOT EXISTS idx_positions_model_id ON positions(model_id)",
            "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_model_id ON portfolio_snapshots(model_id)",
            "CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_date ON portfolio_snapshots(snapshot_date)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_model_id ON performance_metrics(model_id)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_date ON performance_metrics(metric_date)",
            "CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(log_level)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_risk_events_model_id ON risk_events(model_id)",
            "CREATE INDEX IF NOT EXISTS idx_risk_events_created_at ON risk_events(created_at)"
        ]
        
        for index_sql in indexes:
            await self.connection.execute(index_sql)
        
        await self.connection.commit()
        logger.info("📊 数据库索引创建完成")
    
    # AI模型相关操作
    async def save_ai_model(self, name: str, model_type: str, config: Dict[str, Any]) -> int:
        """保存AI模型"""
        try:
            config_json = json.dumps(config)
            
            cursor = await self.connection.execute(
                "INSERT OR REPLACE INTO ai_models (name, model_type, config, updated_at) VALUES (?, ?, ?, ?)",
                (name, model_type, config_json, datetime.now())
            )
            
            await self.connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"❌ 保存AI模型失败: {e}")
            raise
    
    async def get_ai_model(self, name: str) -> Optional[Dict[str, Any]]:
        """获取AI模型"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM ai_models WHERE name = ?",
                (name,)
            )
            
            row = await cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'model_type': row[2],
                    'config': json.loads(row[3]) if row[3] else {},
                    'is_active': bool(row[4]),
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取AI模型失败: {e}")
            return None
    
    async def get_all_ai_models(self) -> List[Dict[str, Any]]:
        """获取所有AI模型"""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM ai_models ORDER BY created_at DESC"
            )
            
            rows = await cursor.fetchall()
            models = []
            
            for row in rows:
                models.append({
                    'id': row[0],
                    'name': row[1],
                    'model_type': row[2],
                    'config': json.loads(row[3]) if row[3] else {},
                    'is_active': bool(row[4]),
                    'created_at': row[5],
                    'updated_at': row[6]
                })
            
            return models
            
        except Exception as e:
            logger.error(f"❌ 获取所有AI模型失败: {e}")
            return []
    
    # 交易记录相关操作
    async def save_trade(self, trade_data: Dict[str, Any]) -> int:
        """保存交易记录"""
        try:
            # 获取模型ID
            model_id = await self._get_model_id(trade_data.get('model_name', ''))
            
            cursor = await self.connection.execute(
                """
                INSERT INTO trades 
                (model_id, symbol, action, quantity, price, commission, pnl, order_id, reason, confidence, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_id,
                    trade_data.get('symbol'),
                    trade_data.get('action'),
                    trade_data.get('quantity'),
                    trade_data.get('price'),
                    trade_data.get('commission', 0.0),
                    trade_data.get('pnl', 0.0),
                    trade_data.get('order_id'),
                    trade_data.get('reason'),
                    trade_data.get('confidence'),
                    trade_data.get('executed_at', datetime.now())
                )
            )
            
            await self.connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"❌ 保存交易记录失败: {e}")
            raise
    
    async def get_trades(self, model_name: str = None, symbol: str = None, 
                        limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取交易记录"""
        try:
            query = """
                SELECT t.*, m.name as model_name 
                FROM trades t 
                LEFT JOIN ai_models m ON t.model_id = m.id 
                WHERE 1=1
            """
            params = []
            
            if model_name:
                query += " AND m.name = ?"
                params.append(model_name)
            
            if symbol:
                query += " AND t.symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY t.executed_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = await self.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            trades = []
            for row in rows:
                trades.append({
                    'id': row[0],
                    'model_id': row[1],
                    'symbol': row[2],
                    'action': row[3],
                    'quantity': row[4],
                    'price': row[5],
                    'commission': row[6],
                    'pnl': row[7],
                    'order_id': row[8],
                    'reason': row[9],
                    'confidence': row[10],
                    'executed_at': row[11],
                    'model_name': row[12]
                })
            
            return trades
            
        except Exception as e:
            logger.error(f"❌ 获取交易记录失败: {e}")
            return []
    
    # 持仓相关操作
    async def update_position(self, model_name: str, symbol: str, quantity: int, 
                            avg_cost: float, current_price: float = 0.0) -> bool:
        """更新持仓"""
        try:
            model_id = await self._get_model_id(model_name)
            
            market_value = quantity * current_price if current_price > 0 else quantity * avg_cost
            unrealized_pnl = (current_price - avg_cost) * quantity if current_price > 0 else 0.0
            
            await self.connection.execute(
                """
                INSERT OR REPLACE INTO positions 
                (model_id, symbol, quantity, avg_cost, current_price, market_value, unrealized_pnl, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (model_id, symbol, quantity, avg_cost, current_price, market_value, unrealized_pnl, datetime.now())
            )
            
            await self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新持仓失败: {e}")
            return False
    
    async def get_positions(self, model_name: str = None) -> List[Dict[str, Any]]:
        """获取持仓"""
        try:
            query = """
                SELECT p.*, m.name as model_name 
                FROM positions p 
                LEFT JOIN ai_models m ON p.model_id = m.id 
                WHERE p.quantity > 0
            """
            params = []
            
            if model_name:
                query += " AND m.name = ?"
                params.append(model_name)
            
            query += " ORDER BY p.market_value DESC"
            
            cursor = await self.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            positions = []
            for row in rows:
                positions.append({
                    'id': row[0],
                    'model_id': row[1],
                    'symbol': row[2],
                    'quantity': row[3],
                    'avg_cost': row[4],
                    'current_price': row[5],
                    'market_value': row[6],
                    'unrealized_pnl': row[7],
                    'last_updated': row[8],
                    'model_name': row[9]
                })
            
            return positions
            
        except Exception as e:
            logger.error(f"❌ 获取持仓失败: {e}")
            return []
    
    # 投资组合快照相关操作
    async def save_portfolio_snapshot(self, model_name: str, total_value: float, 
                                    cash_balance: float, positions_value: float,
                                    total_return: float = 0.0, daily_return: float = 0.0) -> bool:
        """保存投资组合快照"""
        try:
            model_id = await self._get_model_id(model_name)
            today = datetime.now().date()
            
            await self.connection.execute(
                """
                INSERT OR REPLACE INTO portfolio_snapshots 
                (model_id, total_value, cash_balance, positions_value, total_return, daily_return, snapshot_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (model_id, total_value, cash_balance, positions_value, total_return, daily_return, today)
            )
            
            await self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存投资组合快照失败: {e}")
            return False
    
    async def get_portfolio_history(self, model_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取投资组合历史"""
        try:
            model_id = await self._get_model_id(model_name)
            
            cursor = await self.connection.execute(
                """
                SELECT * FROM portfolio_snapshots 
                WHERE model_id = ? 
                ORDER BY snapshot_date DESC 
                LIMIT ?
                """,
                (model_id, days)
            )
            
            rows = await cursor.fetchall()
            history = []
            
            for row in rows:
                history.append({
                    'id': row[0],
                    'model_id': row[1],
                    'total_value': row[2],
                    'cash_balance': row[3],
                    'positions_value': row[4],
                    'total_return': row[5],
                    'daily_return': row[6],
                    'snapshot_date': row[7],
                    'created_at': row[8]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"❌ 获取投资组合历史失败: {e}")
            return []
    
    # 性能指标相关操作
    async def save_performance_metric(self, model_name: str, metric_name: str, 
                                    metric_value: float, metric_date: str = None) -> bool:
        """保存性能指标"""
        try:
            model_id = await self._get_model_id(model_name)
            
            if metric_date is None:
                metric_date = datetime.now().date()
            
            await self.connection.execute(
                """
                INSERT OR REPLACE INTO performance_metrics 
                (model_id, metric_name, metric_value, metric_date)
                VALUES (?, ?, ?, ?)
                """,
                (model_id, metric_name, metric_value, metric_date)
            )
            
            await self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存性能指标失败: {e}")
            return False
    
    async def get_performance_metrics(self, model_name: str = None, 
                                    metric_name: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """获取性能指标"""
        try:
            query = """
                SELECT pm.*, m.name as model_name 
                FROM performance_metrics pm 
                LEFT JOIN ai_models m ON pm.model_id = m.id 
                WHERE pm.metric_date >= date('now', '-{} days')
            """.format(days)
            
            params = []
            
            if model_name:
                query += " AND m.name = ?"
                params.append(model_name)
            
            if metric_name:
                query += " AND pm.metric_name = ?"
                params.append(metric_name)
            
            query += " ORDER BY pm.metric_date DESC, pm.created_at DESC"
            
            cursor = await self.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            metrics = []
            for row in rows:
                metrics.append({
                    'id': row[0],
                    'model_id': row[1],
                    'metric_name': row[2],
                    'metric_value': row[3],
                    'metric_date': row[4],
                    'created_at': row[5],
                    'model_name': row[6]
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ 获取性能指标失败: {e}")
            return []
    
    # 市场数据相关操作
    async def save_market_data(self, symbol: str, price: float, volume: int = None,
                             change_percent: float = None, market_cap: float = None,
                             data_source: str = None) -> bool:
        """保存市场数据"""
        try:
            await self.connection.execute(
                """
                INSERT INTO market_data 
                (symbol, price, volume, change_percent, market_cap, data_source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (symbol, price, volume, change_percent, market_cap, data_source)
            )
            
            await self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存市场数据失败: {e}")
            return False
    
    # 工具方法
    async def _get_model_id(self, model_name: str) -> Optional[int]:
        """获取模型ID"""
        if not model_name:
            return None
        
        cursor = await self.connection.execute(
            "SELECT id FROM ai_models WHERE name = ?",
            (model_name,)
        )
        
        row = await cursor.fetchone()
        if row:
            return row[0]
        else:
            # 如果模型不存在，创建一个新的
            return await self.save_ai_model(model_name, 'unknown', {})
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行自定义查询"""
        try:
            cursor = await self.connection.execute(query, params or ())
            rows = await cursor.fetchall()
            
            # 获取列名
            columns = [description[0] for description in cursor.description]
            
            # 转换为字典列表
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 执行查询失败: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            stats = {}
            
            # 获取各表的记录数
            tables = ['ai_models', 'trades', 'positions', 'portfolio_snapshots', 
                     'performance_metrics', 'market_data', 'system_logs', 'risk_events']
            
            for table in tables:
                cursor = await self.connection.execute(f"SELECT COUNT(*) FROM {table}")
                count = await cursor.fetchone()
                stats[f"{table}_count"] = count[0] if count else 0
            
            # 获取数据库大小
            cursor = await self.connection.execute("PRAGMA page_count")
            page_count = await cursor.fetchone()
            
            cursor = await self.connection.execute("PRAGMA page_size")
            page_size = await cursor.fetchone()
            
            if page_count and page_size:
                stats['database_size_bytes'] = page_count[0] * page_size[0]
                stats['database_size_mb'] = stats['database_size_bytes'] / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取数据库统计信息失败: {e}")
            return {}
    
    async def cleanup_old_data(self, days: int = 90):
        """清理旧数据"""
        try:
            # 清理旧的市场数据
            await self.connection.execute(
                "DELETE FROM market_data WHERE timestamp < date('now', '-{} days')".format(days)
            )
            
            # 清理旧的系统日志
            await self.connection.execute(
                "DELETE FROM system_logs WHERE created_at < date('now', '-{} days')".format(days)
            )
            
            await self.connection.commit()
            logger.info(f"🧹 清理了 {days} 天前的旧数据")
            
        except Exception as e:
            logger.error(f"❌ 清理旧数据失败: {e}")
    
    async def backup_database(self, backup_path: str = None) -> bool:
        """备份数据库"""
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backup_atr_{timestamp}.db"
            
            # 创建备份目录
            Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 执行备份
            backup_conn = await aiosqlite.connect(backup_path)
            await self.connection.backup(backup_conn)
            await backup_conn.close()
            
            logger.info(f"💾 数据库备份完成: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库备份失败: {e}")
            return False
    
    async def close(self):
        """关闭数据库连接"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.is_initialized = False
            logger.info("🗄️ 数据库连接已关闭")
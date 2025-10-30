#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统配置
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger
from config.settings import Settings


class LoggerConfig:
    """日志配置类"""
    
    def __init__(self):
        self.settings = Settings()
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 移除默认处理器
        logger.remove()
        
        # 配置日志
        self._setup_console_logger()
        self._setup_file_logger()
        self._setup_error_logger()
        self._setup_trading_logger()
        self._setup_performance_logger()
    
    def _setup_console_logger(self):
        """配置控制台日志"""
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
            level=self.settings.LOG_LEVEL,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
    
    def _setup_file_logger(self):
        """配置文件日志"""
        logger.add(
            self.log_dir / "atr_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="INFO",
            rotation="1 day",
            retention="30 days",
            compression="zip",
            encoding="utf-8"
        )
    
    def _setup_error_logger(self):
        """配置错误日志"""
        logger.add(
            self.log_dir / "error_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
            level="ERROR",
            rotation="1 day",
            retention="90 days",
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=True
        )
    
    def _setup_trading_logger(self):
        """配置交易日志"""
        logger.add(
            self.log_dir / "trading_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            level="INFO",
            rotation="1 day",
            retention="365 days",
            compression="zip",
            encoding="utf-8",
            filter=lambda record: "TRADING" in record["extra"]
        )
    
    def _setup_performance_logger(self):
        """配置性能日志"""
        logger.add(
            self.log_dir / "performance_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            level="INFO",
            rotation="1 day",
            retention="180 days",
            compression="zip",
            encoding="utf-8",
            filter=lambda record: "PERFORMANCE" in record["extra"]
        )
    
    @staticmethod
    def get_logger(name: str = None):
        """获取日志器"""
        if name:
            return logger.bind(name=name)
        return logger


class TradingLogger:
    """交易专用日志器"""
    
    def __init__(self, model_name: str = ""):
        self.model_name = model_name
        self.logger = logger.bind(TRADING=True, model=model_name)
    
    def trade_executed(self, symbol: str, action: str, quantity: int, price: float, 
                      order_id: str = "", reason: str = ""):
        """记录交易执行"""
        self.logger.info(
            f"TRADE_EXECUTED | {self.model_name} | {action.upper()} {symbol} x{quantity} @ ${price:.2f} | "
            f"OrderID: {order_id} | Reason: {reason}"
        )
    
    def trade_failed(self, symbol: str, action: str, quantity: int, reason: str):
        """记录交易失败"""
        self.logger.error(
            f"TRADE_FAILED | {self.model_name} | {action.upper()} {symbol} x{quantity} | "
            f"Reason: {reason}"
        )
    
    def decision_made(self, symbol: str, action: str, confidence: float, reason: str):
        """记录交易决策"""
        self.logger.info(
            f"DECISION_MADE | {self.model_name} | {action.upper()} {symbol} | "
            f"Confidence: {confidence:.2f} | Reason: {reason}"
        )
    
    def risk_check(self, symbol: str, action: str, risk_score: float, approved: bool, reason: str = ""):
        """记录风险检查"""
        status = "APPROVED" if approved else "REJECTED"
        self.logger.info(
            f"RISK_CHECK | {self.model_name} | {action.upper()} {symbol} | "
            f"Risk: {risk_score:.2f} | Status: {status} | Reason: {reason}"
        )
    
    def portfolio_update(self, total_value: float, cash_balance: float, positions_count: int):
        """记录投资组合更新"""
        self.logger.info(
            f"PORTFOLIO_UPDATE | {self.model_name} | Total: ${total_value:.2f} | "
            f"Cash: ${cash_balance:.2f} | Positions: {positions_count}"
        )


class PerformanceLogger:
    """性能专用日志器"""
    
    def __init__(self, model_name: str = ""):
        self.model_name = model_name
        self.logger = logger.bind(PERFORMANCE=True, model=model_name)
    
    def daily_summary(self, date: str, total_return: float, daily_return: float, 
                     trades_count: int, win_rate: float):
        """记录日度总结"""
        self.logger.info(
            f"DAILY_SUMMARY | {self.model_name} | Date: {date} | "
            f"Total Return: {total_return:.4f} | Daily Return: {daily_return:.4f} | "
            f"Trades: {trades_count} | Win Rate: {win_rate:.2%}"
        )
    
    def model_ranking(self, rankings: list):
        """记录模型排名"""
        ranking_str = " | ".join([
            f"{i+1}. {r['model_name']}: {r['total_return']:.4f}" 
            for i, r in enumerate(rankings[:5])
        ])
        self.logger.info(f"MODEL_RANKING | {ranking_str}")
    
    def system_metrics(self, cpu_usage: float, memory_usage: float, 
                      active_models: int, total_trades: int):
        """记录系统指标"""
        self.logger.info(
            f"SYSTEM_METRICS | CPU: {cpu_usage:.1f}% | Memory: {memory_usage:.1f}% | "
            f"Active Models: {active_models} | Total Trades: {total_trades}"
        )
    
    def api_call(self, model_name: str, api_type: str, duration: float, 
                tokens_used: int = 0, cost: float = 0.0):
        """记录API调用"""
        self.logger.info(
            f"API_CALL | {model_name} | Type: {api_type} | Duration: {duration:.3f}s | "
            f"Tokens: {tokens_used} | Cost: ${cost:.4f}"
        )


class AuditLogger:
    """审计日志器"""
    
    def __init__(self):
        self.logger = logger.bind(AUDIT=True)
        
        # 单独的审计日志文件
        logger.add(
            Path("logs") / "audit_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | AUDIT | {message}",
            level="INFO",
            rotation="1 day",
            retention="2 years",
            compression="zip",
            encoding="utf-8",
            filter=lambda record: "AUDIT" in record["extra"]
        )
    
    def system_start(self, version: str, config: dict):
        """记录系统启动"""
        self.logger.info(
            f"SYSTEM_START | Version: {version} | Config: {config}"
        )
    
    def system_stop(self, reason: str = "normal"):
        """记录系统停止"""
        self.logger.info(f"SYSTEM_STOP | Reason: {reason}")
    
    def model_added(self, model_name: str, config: dict):
        """记录模型添加"""
        self.logger.info(
            f"MODEL_ADDED | Name: {model_name} | Config: {config}"
        )
    
    def model_removed(self, model_name: str, reason: str = ""):
        """记录模型移除"""
        self.logger.info(
            f"MODEL_REMOVED | Name: {model_name} | Reason: {reason}"
        )
    
    def config_changed(self, section: str, old_value: any, new_value: any):
        """记录配置变更"""
        self.logger.info(
            f"CONFIG_CHANGED | Section: {section} | Old: {old_value} | New: {new_value}"
        )
    
    def security_event(self, event_type: str, details: str, severity: str = "INFO"):
        """记录安全事件"""
        self.logger.info(
            f"SECURITY_EVENT | Type: {event_type} | Severity: {severity} | Details: {details}"
        )


class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
    
    def get_trading_summary(self, date: str = None) -> dict:
        """获取交易总结"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        trading_log_file = self.log_dir / f"trading_{date}.log"
        
        if not trading_log_file.exists():
            return {"error": "日志文件不存在"}
        
        summary = {
            "total_trades": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "models": {},
            "symbols": {},
            "actions": {"buy": 0, "sell": 0}
        }
        
        try:
            with open(trading_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if "TRADE_EXECUTED" in line:
                        summary["total_trades"] += 1
                        summary["successful_trades"] += 1
                        
                        # 解析交易信息
                        parts = line.split(" | ")
                        if len(parts) >= 4:
                            model = parts[1].strip()
                            action_symbol = parts[2].strip()
                            
                            # 统计模型
                            if model not in summary["models"]:
                                summary["models"][model] = 0
                            summary["models"][model] += 1
                            
                            # 统计动作
                            if "BUY" in action_symbol:
                                summary["actions"]["buy"] += 1
                            elif "SELL" in action_symbol:
                                summary["actions"]["sell"] += 1
                    
                    elif "TRADE_FAILED" in line:
                        summary["failed_trades"] += 1
            
            # 计算成功率
            total = summary["successful_trades"] + summary["failed_trades"]
            summary["success_rate"] = summary["successful_trades"] / total if total > 0 else 0
            
            return summary
            
        except Exception as e:
            return {"error": f"分析日志失败: {str(e)}"}
    
    def get_performance_metrics(self, date: str = None) -> dict:
        """获取性能指标"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        performance_log_file = self.log_dir / f"performance_{date}.log"
        
        if not performance_log_file.exists():
            return {"error": "性能日志文件不存在"}
        
        metrics = {
            "api_calls": 0,
            "total_api_duration": 0.0,
            "total_api_cost": 0.0,
            "models_performance": {},
            "system_metrics": []
        }
        
        try:
            with open(performance_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if "API_CALL" in line:
                        metrics["api_calls"] += 1
                        
                        # 解析API调用信息
                        if "Duration:" in line:
                            duration_part = line.split("Duration: ")[1].split("s")[0]
                            try:
                                duration = float(duration_part)
                                metrics["total_api_duration"] += duration
                            except ValueError:
                                pass
                        
                        if "Cost: $" in line:
                            cost_part = line.split("Cost: $")[1].split(" ")[0]
                            try:
                                cost = float(cost_part)
                                metrics["total_api_cost"] += cost
                            except ValueError:
                                pass
                    
                    elif "DAILY_SUMMARY" in line:
                        # 解析每日总结
                        parts = line.split(" | ")
                        if len(parts) >= 3:
                            model = parts[1].strip()
                            if model not in metrics["models_performance"]:
                                metrics["models_performance"][model] = {}
                            
                            # 提取性能数据
                            for part in parts[2:]:
                                if "Total Return:" in part:
                                    try:
                                        return_val = float(part.split("Total Return: ")[1])
                                        metrics["models_performance"][model]["total_return"] = return_val
                                    except (ValueError, IndexError):
                                        pass
            
            # 计算平均值
            if metrics["api_calls"] > 0:
                metrics["avg_api_duration"] = metrics["total_api_duration"] / metrics["api_calls"]
                metrics["avg_api_cost"] = metrics["total_api_cost"] / metrics["api_calls"]
            
            return metrics
            
        except Exception as e:
            return {"error": f"分析性能日志失败: {str(e)}"}
    
    def get_error_summary(self, date: str = None) -> dict:
        """获取错误总结"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        error_log_file = self.log_dir / f"error_{date}.log"
        
        if not error_log_file.exists():
            return {"error": "错误日志文件不存在"}
        
        summary = {
            "total_errors": 0,
            "error_types": {},
            "error_sources": {},
            "recent_errors": []
        }
        
        try:
            with open(error_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                for line in lines:
                    if "ERROR" in line:
                        summary["total_errors"] += 1
                        
                        # 添加到最近错误（最多保留10条）
                        if len(summary["recent_errors"]) < 10:
                            summary["recent_errors"].append(line.strip())
                        
                        # 分析错误类型和来源
                        parts = line.split(" | ")
                        if len(parts) >= 3:
                            source = parts[2].split(":")[0] if ":" in parts[2] else "unknown"
                            
                            if source not in summary["error_sources"]:
                                summary["error_sources"][source] = 0
                            summary["error_sources"][source] += 1
            
            return summary
            
        except Exception as e:
            return {"error": f"分析错误日志失败: {str(e)}"}


# 初始化日志配置
logger_config = LoggerConfig()

# 导出常用的日志器
def get_logger(name: str = None):
    """获取通用日志器"""
    return LoggerConfig.get_logger(name)

def get_trading_logger(model_name: str = ""):
    """获取交易日志器"""
    return TradingLogger(model_name)

def get_performance_logger(model_name: str = ""):
    """获取性能日志器"""
    return PerformanceLogger(model_name)

def get_audit_logger():
    """获取审计日志器"""
    return AuditLogger()

def get_log_analyzer():
    """获取日志分析器"""
    return LogAnalyzer()
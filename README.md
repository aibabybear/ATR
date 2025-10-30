# AI Trading Robot (ATR)

基于AI的自动交易系统，支持多模型竞争和策略优化。

## 🎯 核心功能

### 1. 多AI模型竞争
- 支持多个AI模型同时交易（GPT-4、Claude-3等）
- 实时性能对比和排名
- 独立决策，无人工干预
- 自动选择最优策略

### 2. 自主交易能力
- 市场数据分析和情感分析
- 自动买卖决策执行
- 智能风险管理和仓位控制
- 技术指标分析

### 3. 实时监控
- 交易记录追踪和分析
- 收益分析和性能指标
- Web界面实时展示
- 系统日志和审计

### 4. 数据集成
- 实时市场数据（Yahoo Finance、Alpha Vantage）
- 新闻情感分析
- 技术指标计算
- 历史数据回测

## 🏗️ 技术架构

```
ATR/
├── main.py                 # 主程序入口
├── start.py                # 启动脚本
├── install.sh              # 安装脚本
├── requirements.txt        # Python依赖
├── core/                   # 核心交易引擎
│   ├── trading_engine.py   # 交易引擎
│   ├── portfolio.py        # 投资组合管理
│   ├── risk_manager.py     # 风险管理
│   └── order_manager.py    # 订单管理
├── ai_models/              # AI模型集成
│   ├── base_model.py       # 基础模型接口
│   ├── gpt_trader.py       # GPT交易模型
│   ├── claude_trader.py    # Claude交易模型
│   └── model_manager.py    # 模型管理器
├── data/                   # 数据处理
│   ├── market_data.py      # 市场数据获取
│   ├── news_analyzer.py    # 新闻分析
│   └── indicators.py       # 技术指标
├── web/                    # Web界面
│   ├── app.py             # Flask应用
│   ├── templates/         # HTML模板
│   │   ├── base.html      # 基础模板
│   │   ├── index.html     # 主页
│   │   └── dashboard.html # 仪表板
│   └── static/            # 静态资源
├── config/                 # 配置文件
│   ├── settings.py        # 系统配置
│   └── api_keys.py        # API密钥
├── utils/                  # 工具函数
│   ├── logger.py          # 日志系统
│   └── database.py        # 数据库操作
└── logs/                   # 日志文件
```

## 🚀 快速开始

### 方法一：使用安装脚本（推荐）

```bash
# 1. 克隆或下载项目
cd ATR

# 2. 运行安装脚本
./install.sh

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 启动系统
python3 start.py
```

### 方法二：手动安装

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置API密钥
cp config/api_keys.example.py config/api_keys.py
# 编辑 config/api_keys.py 添加你的API密钥

# 4. 启动系统
python3 start.py
```

### 方法三：直接运行主程序

```bash
# 确保已安装依赖和配置API密钥
python3 main.py
```

## 🔑 API密钥配置

系统需要以下API密钥才能正常工作：

### 必需的API密钥
- **OpenAI API Key**: 用于GPT模型
- **Anthropic API Key**: 用于Claude模型

### 可选的API密钥
- **Alpha Vantage API Key**: 用于获取金融数据
- **News API Key**: 用于新闻情感分析

### 配置方法

1. 复制配置模板：
```bash
cp config/api_keys.example.py config/api_keys.py
```

2. 编辑 `config/api_keys.py` 文件，添加你的API密钥：
```python
import os

# OpenAI API配置
os.environ['OPENAI_API_KEY'] = 'your_openai_api_key_here'

# Anthropic Claude API配置
os.environ['ANTHROPIC_API_KEY'] = 'your_anthropic_api_key_here'

# Alpha Vantage API配置 (可选)
os.environ['ALPHA_VANTAGE_API_KEY'] = 'your_alpha_vantage_api_key_here'
```

## 📊 支持的交易市场

- **美股**: NASDAQ 100 主要股票
- **指数**: QQQ, SPY, VIX
- **扩展性**: 可轻松添加其他市场

### 默认支持的股票
```python
SUPPORTED_SYMBOLS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
    'ADBE', 'CRM', 'ORCL', 'INTC', 'AMD', 'QCOM', 'AVGO', 'TXN',
    'COST', 'SBUX', 'PYPL', 'ZOOM', 'DOCU', 'SHOP', 'SQ', 'ROKU'
]
```

## 🤖 支持的AI模型

### GPT-4 Trader
- **特点**: 快速决策，适合短线交易
- **策略**: 基于技术分析和市场情绪
- **风险偏好**: 中等

### Claude-3 Trader
- **特点**: 深度分析，注重基本面
- **策略**: 价值投资导向
- **风险偏好**: 保守

### 扩展性
- 支持自定义AI模型
- 插件化架构
- 标准化接口

## 🛡️ 风险管理

### 内置风险控制
- **仓位限制**: 单一股票最大10%仓位
- **止损机制**: 自动5%止损
- **日损失限制**: 最大日损失5%
- **相关性检查**: 避免过度集中

### 风险指标监控
- 投资组合VaR
- 最大回撤
- 夏普比率
- 波动率分析

## 📈 性能监控

### 实时指标
- 总收益率
- 胜率统计
- 交易次数
- 资金使用率

### 历史分析
- 收益曲线
- 回撤分析
- 模型对比
- 风险调整收益

## 🌐 Web界面

访问 `http://localhost:5000` 查看：

- **主页**: 系统概览和快速操作
- **仪表板**: 详细的性能分析和图表
- **AI模型**: 模型管理和配置
- **交易记录**: 完整的交易历史

### 主要功能
- 实时数据更新
- 交互式图表
- 模型性能对比
- 交易记录查询
- 系统日志监控

## ⚙️ 系统配置

主要配置文件：`config/settings.py`

### 交易配置
```python
TRADING_INTERVAL = 300          # 交易间隔(秒)
INITIAL_CAPITAL = 10000         # 初始资金
MAX_POSITION_SIZE = 0.1         # 最大仓位比例
STOP_LOSS_PERCENTAGE = 0.05     # 止损比例
```

### 风险管理配置
```python
RISK_MANAGEMENT = {
    'max_daily_loss': 0.05,         # 5% 最大日损失
    'max_portfolio_risk': 0.02,     # 2% 最大组合风险
    'correlation_threshold': 0.7     # 相关性阈值
}
```

## 📝 日志系统

### 日志类型
- **系统日志**: `logs/atr_YYYY-MM-DD.log`
- **交易日志**: `logs/trading_YYYY-MM-DD.log`
- **性能日志**: `logs/performance_YYYY-MM-DD.log`
- **错误日志**: `logs/error_YYYY-MM-DD.log`

### 日志分析
```python
from utils.logger import get_log_analyzer

analyzer = get_log_analyzer()
summary = analyzer.get_trading_summary('2024-01-01')
print(summary)
```

## 🗄️ 数据存储

### SQLite数据库
- **ai_models**: AI模型配置
- **trades**: 交易记录
- **positions**: 持仓信息
- **portfolio_snapshots**: 投资组合快照
- **performance_metrics**: 性能指标
- **market_data**: 市场数据

### 数据备份
```python
from utils.database import DatabaseManager

db = DatabaseManager()
await db.backup_database('backup_20240101.db')
```

## 🔧 开发和扩展

### 添加新的AI模型

1. 继承 `BaseAIModel` 类：
```python
from ai_models.base_model import BaseAIModel

class MyTrader(BaseAIModel):
    async def analyze_market(self, market_data):
        # 实现市场分析逻辑
        pass
    
    async def make_trading_decision(self, market_data):
        # 实现交易决策逻辑
        pass
```

2. 在 `model_manager.py` 中注册：
```python
self.model_classes = {
    'my-model': MyTrader,
    # ... 其他模型
}
```

### 添加新的数据源

1. 在 `data/market_data.py` 中添加新的数据获取方法
2. 更新 `MarketDataProvider` 类
3. 配置数据源参数

### 自定义风险策略

1. 修改 `core/risk_manager.py`
2. 实现自定义风险检查逻辑
3. 更新风险配置参数

## 🧪 测试

### 运行系统测试
```bash
python3 start.py
# 选择选项 3: 运行系统测试
```

### 单元测试
```bash
pytest tests/
```

### 模拟交易测试
```bash
python3 -c "from core.trading_engine import TradingEngine; print('测试通过')"
```

## 📚 依赖项

### 核心依赖
- **Flask**: Web框架
- **pandas**: 数据处理
- **numpy**: 数值计算
- **loguru**: 日志系统
- **aiohttp**: 异步HTTP客户端
- **yfinance**: Yahoo Finance数据
- **openai**: OpenAI API
- **anthropic**: Anthropic API

### 可选依赖
- **TA-Lib**: 技术指标计算
- **plotly**: 图表绘制
- **redis**: 缓存系统

## ⚠️ 重要提醒

### 风险声明
1. **投资有风险**: 本系统仅供学习和研究使用
2. **模拟交易**: 建议先在模拟环境中测试
3. **资金安全**: 请勿投入超过承受能力的资金
4. **监管合规**: 请遵守当地金融监管法规

### 使用建议
1. **充分测试**: 在实盘前进行充分的回测和模拟
2. **风险控制**: 设置合理的止损和仓位限制
3. **持续监控**: 定期检查系统运行状态
4. **策略调整**: 根据市场变化调整交易策略

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

### 贡献指南
1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如果您遇到问题或需要帮助：

1. 查看 [FAQ](docs/FAQ.md)
2. 提交 [Issue](https://github.com/aibabybear/ATR/issues)
3. 查看系统日志文件
4. 运行系统诊断测试

---

**免责声明**: 本软件仅供教育和研究目的使用。使用本软件进行实际交易的任何损失，开发者概不负责。投资有风险，入市需谨慎。
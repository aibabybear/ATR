#!/bin/bash

# AI Trading Robot (ATR) 安装脚本
# 适用于 macOS 和 Linux 系统

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 打印横幅
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    AI Trading Robot (ATR)                   ║"
    echo "║                      自动安装脚本                            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查操作系统
check_os() {
    print_info "检查操作系统..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_success "检测到 macOS 系统"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_success "检测到 Linux 系统"
    else
        print_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
}

# 检查 Python 版本
check_python() {
    print_info "检查 Python 版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -ge 8 ]]; then
            print_success "Python 版本: $PYTHON_VERSION (符合要求)"
            PYTHON_CMD="python3"
        else
            print_error "需要 Python 3.8 或更高版本，当前版本: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "未找到 Python 3，请先安装 Python 3.8+"
        exit 1
    fi
}

# 检查 pip
check_pip() {
    print_info "检查 pip..."
    
    if command -v pip3 &> /dev/null; then
        print_success "pip3 已安装"
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        print_success "pip 已安装"
        PIP_CMD="pip"
    else
        print_error "未找到 pip，请先安装 pip"
        exit 1
    fi
}

# 创建虚拟环境
create_venv() {
    print_info "创建 Python 虚拟环境..."
    
    if [[ -d "venv" ]]; then
        print_warning "虚拟环境已存在，跳过创建"
    else
        $PYTHON_CMD -m venv venv
        print_success "虚拟环境创建完成"
    fi
    
    # 激活虚拟环境
    print_info "激活虚拟环境..."
    source venv/bin/activate
    print_success "虚拟环境已激活"
}

# 升级 pip
upgrade_pip() {
    print_info "升级 pip..."
    pip install --upgrade pip
    print_success "pip 升级完成"
}

# 安装 Python 依赖
install_dependencies() {
    print_info "安装 Python 依赖包..."
    
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        print_success "依赖包安装完成"
    else
        print_warning "requirements.txt 文件不存在，手动安装核心依赖..."
        
        # 核心依赖列表
        CORE_DEPS=(
            "flask==2.3.3"
            "flask-socketio==5.3.6"
            "pandas==2.1.1"
            "numpy==1.24.3"
            "loguru==0.7.2"
            "aiohttp==3.8.6"
            "yfinance==0.2.22"
            "openai==1.3.5"
            "anthropic==0.7.7"
            "aiosqlite"
            "python-dotenv==1.0.0"
        )
        
        for dep in "${CORE_DEPS[@]}"; do
            print_info "安装 $dep..."
            pip install "$dep"
        done
        
        print_success "核心依赖安装完成"
    fi
}

# 安装可选依赖
install_optional_dependencies() {
    print_info "安装可选依赖 (TA-Lib)..."
    
    if [[ "$OS" == "macos" ]]; then
        # macOS 上安装 TA-Lib
        if command -v brew &> /dev/null; then
            print_info "使用 Homebrew 安装 TA-Lib..."
            brew install ta-lib || print_warning "TA-Lib 安装失败，跳过"
            pip install TA-Lib || print_warning "TA-Lib Python 包安装失败，跳过"
        else
            print_warning "未找到 Homebrew，跳过 TA-Lib 安装"
        fi
    elif [[ "$OS" == "linux" ]]; then
        # Linux 上安装 TA-Lib
        print_warning "Linux 系统需要手动安装 TA-Lib，请参考文档"
    fi
}

# 创建配置文件
setup_config() {
    print_info "设置配置文件..."
    
    # 创建必要的目录
    mkdir -p logs data backups web/static/{css,js,images}
    print_success "目录创建完成"
    
    # 复制 API 密钥配置模板
    if [[ -f "config/api_keys.example.py" && ! -f "config/api_keys.py" ]]; then
        cp config/api_keys.example.py config/api_keys.py
        print_success "API 密钥配置文件已创建"
        print_warning "请编辑 config/api_keys.py 文件，添加您的 API 密钥"
    fi
}

# 运行测试
run_tests() {
    print_info "运行基础测试..."
    
    # 测试 Python 导入
    $PYTHON_CMD -c "import flask, pandas, numpy, loguru; print('核心模块导入成功')" || {
        print_error "核心模块导入失败"
        exit 1
    }
    
    print_success "基础测试通过"
}

# 显示安装完成信息
show_completion_info() {
    echo
    print_success "🎉 AI Trading Robot 安装完成！"
    echo
    echo -e "${BLUE}📋 下一步操作:${NC}"
    echo "1. 编辑配置文件: config/api_keys.py"
    echo "2. 添加您的 API 密钥 (OpenAI, Anthropic, Alpha Vantage 等)"
    echo "3. 运行启动脚本: python3 start.py"
    echo
    echo -e "${BLUE}🚀 快速启动:${NC}"
    echo "   source venv/bin/activate  # 激活虚拟环境"
    echo "   python3 start.py         # 启动系统"
    echo
    echo -e "${BLUE}🌐 Web 界面:${NC}"
    echo "   http://localhost:5000"
    echo
    echo -e "${BLUE}📚 文档和帮助:${NC}"
    echo "   README.md - 详细使用说明"
    echo "   config/settings.py - 系统配置"
    echo
    print_warning "⚠️  重要提醒: 这是一个交易系统，请在充分了解风险后使用！"
}

# 主安装流程
main() {
    print_banner
    
    # 检查系统环境
    check_os
    check_python
    check_pip
    
    # 创建和激活虚拟环境
    create_venv
    
    # 升级 pip
    upgrade_pip
    
    # 安装依赖
    install_dependencies
    install_optional_dependencies
    
    # 设置配置
    setup_config
    
    # 运行测试
    run_tests
    
    # 显示完成信息
    show_completion_info
}

# 错误处理
trap 'print_error "安装过程中发生错误，请检查上面的错误信息"' ERR

# 运行主函数
main "$@"
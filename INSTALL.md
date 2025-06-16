# 安装指南

## 快速开始

### 1. 最小安装（仅核心功能）
```bash
pip install -r requirements-core.txt
```
这将安装运行系统所需的最小依赖集。

### 2. 使用 setup.py 安装（推荐）

#### 基础安装
```bash
pip install -e .
```

#### 安装特定功能
```bash
# LLM 提供商
pip install -e ".[anthropic]"      # Anthropic Claude
pip install -e ".[openai]"         # OpenAI / Azure OpenAI  
pip install -e ".[gemini]"         # Google Gemini

# 通知渠道
pip install -e ".[telegram]"       # Telegram 机器人
pip install -e ".[email_advanced]" # 高级邮件功能

# 多个功能
pip install -e ".[anthropic,telegram]"
```

#### 完整安装
```bash
pip install -e ".[all]"            # 所有功能
pip install -e ".[all,dev]"        # 所有功能 + 开发工具
```

## 功能对应关系

| 功能 | 所需依赖 | 安装命令 |
|------|---------|----------|
| Anthropic Claude | anthropic | `pip install -e ".[anthropic]"` |
| OpenAI/Azure | openai | `pip install -e ".[openai]"` |
| Google Gemini | google-generativeai | `pip install -e ".[gemini]"` |
| Telegram 通知 | python-telegram-bot | `pip install -e ".[telegram]"` |
| 高级邮件 | emails | `pip install -e ".[email_advanced]"` |
| NewsAPI SDK | newsapi-python | `pip install -e ".[news_advanced]"` |

## 检查已安装的依赖

```python
# 检查某个插件的依赖是否已安装
from core.dependency_checker import DependencyChecker

# 检查 openai 插件的依赖
DependencyChecker.check_and_suggest('openai_sender')
```

## Docker 部署

如果希望避免本地依赖管理，可以使用 Docker：

```dockerfile
# Dockerfile.minimal - 最小镜像
FROM python:3.9-slim
COPY requirements-core.txt .
RUN pip install -r requirements-core.txt
COPY . /app
WORKDIR /app
CMD ["python", "main.py"]

# Dockerfile.full - 完整功能镜像  
FROM python:3.9-slim
COPY setup.py README.md ./
COPY . /app
WORKDIR /app
RUN pip install -e ".[all]"
CMD ["python", "main.py"]
```

## 故障排除

1. **插件报错提示缺少依赖**
   - 查看错误信息中的安装命令
   - 使用对应的 pip install 命令安装

2. **不确定需要哪些依赖**
   - 先最小安装，根据使用的功能按需添加
   - 查看 setup.py 中的 extras_require 了解所有可选依赖

3. **版本冲突**
   - 使用虚拟环境隔离项目依赖
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   ```
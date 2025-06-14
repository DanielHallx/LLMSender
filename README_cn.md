# LLMSender
**Together, we run towards the future**  , LLMSender By Daniel Hall  
一个模块化的Python应用程序，用于定时内容摘要和通知。从各种来源（天气、汇率等）获取数据，使用AI进行摘要，并通过多种渠道发送通知。

[English](README.md) ｜ 简体中文

## 功能特点

- **模块化插件系统**：轻松添加/删除功能
- **多种内容源**：天气、汇率、加密货币价格，用户可以轻松使用Python或外部API定义新内容
- **AI集成**：支持OpenAI、Azure OpenAI和Google Gemini
- **多种通知渠道**：Telegram、Bark (iOS)、邮件
- **灵活调度**：基于Cron和间隔的调度
- **配置驱动**：基于YAML的配置
- **错误处理**：重试逻辑和错误通知

## 下一步计划

- **Web界面构建**：用于更简单配置和监控的Web界面
- **插件市场**：用于共享和发现插件的市场
- **高级调度**：更复杂的调度选项，如任务间的依赖关系
- **构建Docker镜像**：创建Docker镜像以便于部署

## 项目结构

```
LLMSender/
├── core/                      # 核心模块
│   ├── interfaces.py         # 插件接口
│   ├── plugin_loader.py      # 动态插件加载
│   └── utils.py             # 工具函数
├── send_to_ai_content/       # 内容提供者插件
│   ├── weather.py           # 天气数据获取器
│   └── exchange_rate.py     # 汇率获取器
├── llm_message_sender/       # AI提供者插件
│   ├── openai_sender.py     # OpenAI/Azure OpenAI
│   └── gemini_sender.py     # Google Gemini
├── message_notice/           # 通知插件
│   ├── telegram.py          # Telegram通知
│   ├── bark.py             # Bark iOS通知
│   └── email.py            # 邮件通知
├── config/                   # 配置文件
│   └── config.yaml.example  # 示例配置
├── main.py                  # 主应用程序
└── requirements.txt         # Python依赖
```

## 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone <repository-url>
cd LLMSender

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows系统: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制示例配置
cp config/config.yaml.example config/config.yaml

# 编辑config/config.yaml设置您的配置
```

### 3. 设置环境变量

```bash
# 必需的API密钥
export OPENAI_API_KEY="your-openai-api-key"
export OPENWEATHER_API_KEY="your-weather-api-key"
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
export TELEGRAM_CHAT_ID="your-telegram-chat-id"
export BARK_DEVICE_KEY="your-bark-device-key"

# 可选：邮件通知
export EMAIL_USERNAME="your-email@example.com"
export EMAIL_PASSWORD="your-app-password"
export EMAIL_FROM="your-email@example.com"
export EMAIL_TO_EMAILS="recipient1@example.com,recipient2@example.com"
export SMTP_SERVER="smtp.gmail.com"

# 可选：Google Gemini
export GEMINI_API_KEY="your-gemini-api-key"

# 可选：Azure OpenAI
export AZURE_OPENAI_API_KEY="your-azure-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
```

### 4. 运行应用程序

```bash
# 正常模式（运行计划任务）
python main.py

# 测试模式（运行所有任务一次）
python main.py --test

# 使用自定义配置文件
python main.py -c path/to/config.yaml

# 启用调试日志
python main.py -l DEBUG
```

## 配置指南

### 任务配置

`config.yaml`中的每个任务具有以下结构：

```yaml
tasks:
  - name: "任务名称"
    title: "通知标题"
    
    content:
      plugin: weather  # 插件名称（不带.py的文件名）
      # 插件特定配置
      city: "London"
      units: "metric"
    
    llm:
      plugin: openai_sender
      model: "gpt-4o"
      temperature: 0.7
    
    notifiers:
      - plugin: telegram
        parse_mode: "HTML"
      - plugin: bark
        sound: "bell"
    
    schedule:
      type: "cron"  # 或 "interval" 或 "once"
      hour: 7
      minute: 30
```

### 调度类型

1. **Cron调度**：
   ```yaml
   schedule:
     type: "cron"
     hour: 7
     minute: 30
     day_of_week: "mon-fri"  # 可选
   ```

2. **间隔调度**：
   ```yaml
   schedule:
     type: "interval"
     hours: 6  # 每6小时运行一次
     minutes: 30  # 可以组合：每6.5小时
   ```

3. **运行一次**：
   ```yaml
   schedule:
     type: "once"  # 启动时运行
   ```

## 创建自定义插件

### 内容提供者插件

在`send_to_ai_content/`中创建文件：

```python
from core.interfaces import ContentProvider

class MyDataProvider(ContentProvider):
    def get_prompt(self) -> str:
        return "总结这些数据..."
    
    def fetch(self) -> str:
        # 获取并返回数据
        return "数据内容..."

def factory(config):
    return MyDataProvider(config)
```

### LLM插件

在`llm_message_sender/`中创建文件：

```python
from core.interfaces import LLMSender

class MyLLMSender(LLMSender):
    def summarize(self, prompt: str, content: str) -> str:
        # 调用AI API并返回摘要
        return "摘要..."

def factory(config):
    return MyLLMSender(config)
```

### 通知插件

在`message_notice/`中创建文件：

```python
from core.interfaces import Notifier

class MyNotifier(Notifier):
    def send(self, message: str, title: str = None) -> bool:
        # 发送通知
        return True

def factory(config):
    return MyNotifier(config)
```

## API密钥设置

### OpenWeatherMap
1. 在https://openweathermap.org/api注册
2. 从仪表板获取您的API密钥

### OpenAI
1. 在https://platform.openai.com注册
2. 在仪表板中创建API密钥

### Google Gemini
1. 访问https://ai.google.dev/
2. 通过Google AI Studio获取API访问权限
3. 在控制台中创建API密钥

### Telegram Bot
1. 在Telegram上与@BotFather对话
2. 创建新机器人并获取令牌
3. 通过向机器人发送消息并访问以下链接获取您的聊天ID：
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`

### Bark (iOS)
1. 从App Store安装Bark应用
2. 从应用中获取您的设备密钥

### 邮件设置
1. **Gmail**：使用应用专用密码（不是您的常规密码）
   - 启用双因素认证
   - 生成应用密码：账户设置 → 安全 → 两步验证 → 应用密码
2. **Outlook/Hotmail**：使用您的常规凭据或应用密码
3. **通用SMTP**：配置您的SMTP服务器设置

## 故障排除

### 常见问题

1. **模块未找到错误**：确保您在虚拟环境中
2. **API密钥错误**：检查环境变量是否正确设置
3. **调度问题**：验证配置中的时区设置
4. **连接错误**：检查网络和API端点

### 调试模式

使用调试日志运行以查看详细信息：

```bash
python main.py -l DEBUG --log-file debug.log
```

## 安全最佳实践

1. 永远不要将API密钥提交到版本控制
2. 对敏感数据使用环境变量
3. 限制配置文件的文件权限
4. 定期轮换API密钥
5. 尽可能使用HTTPS端点

## 贡献

1. 遵循插件接口定义
2. 添加适当的错误处理
3. 包含日志语句
4. 编写清晰的文档
5. 彻底测试您的插件

## 许可证

本项目采用GNU通用公共许可证v3.0许可。

### GPL v3许可证要点

- ✅ **使用自由**：您可以自由运行该程序。
- ✅ **学习自由**：您可以研究程序的工作原理并修改它。
- ✅ **分发自由**：您可以重新分发副本。
- ✅ **改进自由**：您可以改进程序并发布改进版本。
- ⚠️ **Copyleft要求**：基于此项目的所有衍生作品也必须在GPL v3下许可。
- ⚠️ **源代码披露**：分发时，您必须提供源代码或获取源代码的方式。

### 许可证文本

```
LLMSender - 一个用于定时内容摘要和通知的模块化Python应用程序
版权所有 (C) 2025 Daniel Hall

本程序是自由软件：您可以根据自由软件基金会发布的
GNU通用公共许可证的条款重新分发和/或修改它，
无论是许可证的第3版，还是（根据您的选择）任何后续版本。

分发本程序是希望它有用，但不提供任何保证；
甚至不提供适销性或特定用途适用性的默示保证。
有关更多详细信息，请参阅GNU通用公共许可证。

您应该已经收到了GNU通用公共许可证的副本
以及本程序。如果没有，请参阅<https://www.gnu.org/licenses/>。
```
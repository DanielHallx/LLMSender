# LLMSender
**Together, we run towards the future**  LLMSender By Daniel Hall
A modular Python application for scheduled content summarization and notification. Fetch data from various sources (weather, exchange rates, etc.), summarize it using AI, and send notifications via multiple channels.

English ｜ [简体中文](README_cn.md)
## Features

- **Modular Plugin System**: Easy to add/remove functionality
- **Multiple Content Sources**: Weather, exchange rates, cryptocurrency prices, Users can easily define new content using Python or external APIs.
- **AI Integration**: Support for OpenAI, Azure OpenAI, and Google Gemini
- **Multiple Notification Channels**: Telegram, Bark (iOS), Email
- **Flexible Scheduling**: Cron and interval-based scheduling
- **Configuration-Driven**: YAML-based configuration
- **Error Handling**: Retry logic and error notifications


## What is next?
- **Web UI Build**: A web interface for easier configuration and monitoring.
- **Plugin Marketplace**: A marketplace for sharing and discovering plugins.
- **Advanced Scheduling**: More complex scheduling options like dependencies between tasks.
- **Build docker image**: Create a Docker image for easy deployment.

## Project Structure

```
LLMSender/
├── core/                      # Core modules
│   ├── interfaces.py         # Plugin interfaces
│   ├── plugin_loader.py      # Dynamic plugin loading
│   └── utils.py             # Utilities
├── send_to_ai_content/       # Content provider plugins
│   ├── weather.py           # Weather data fetcher
│   └── exchange_rate.py     # Exchange rate fetcher
├── llm_message_sender/       # AI provider plugins
│   ├── openai_sender.py     # OpenAI/Azure OpenAI
│   └── gemini_sender.py     # Google Gemini
├── message_notice/           # Notification plugins
│   ├── telegram.py          # Telegram notifications
│   ├── bark.py             # Bark iOS notifications
│   └── email.py            # Email notifications
├── config/                   # Configuration files
│   └── config.yaml.example  # Example configuration
├── main.py                  # Main application
└── requirements.txt         # Python dependencies
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd LLMSender

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy example configuration
cp config/config.yaml.example config/config.yaml

# Edit config/config.yaml with your settings
```

### 3. Set Environment Variables

```bash
# Required API keys
export OPENAI_API_KEY="your-openai-api-key"
export OPENWEATHER_API_KEY="your-weather-api-key"
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
export TELEGRAM_CHAT_ID="your-telegram-chat-id"
export BARK_DEVICE_KEY="your-bark-device-key"

# Optional: Email notifications
export EMAIL_USERNAME="your-email@example.com"
export EMAIL_PASSWORD="your-app-password"
export EMAIL_FROM="your-email@example.com"
export EMAIL_TO_EMAILS="recipient1@example.com,recipient2@example.com"
export SMTP_SERVER="smtp.gmail.com"

# Optional: Google Gemini
export GEMINI_API_KEY="your-gemini-api-key"

# Optional: Azure OpenAI
export AZURE_OPENAI_API_KEY="your-azure-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
```

### 4. Run the Application

```bash
# Normal mode (runs scheduled tasks)
python main.py

# Test mode (runs all tasks once)
python main.py --test

# With custom config file
python main.py -c path/to/config.yaml

# With debug logging
python main.py -l DEBUG
```

## Configuration Guide

### Task Configuration

Each task in `config.yaml` has the following structure:

```yaml
tasks:
  - name: "Task Name"
    title: "Notification Title"
    
    content:
      plugin: weather  # Plugin name (filename without .py)
      # Plugin-specific configuration
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
      type: "cron"  # or "interval" or "once"
      hour: 7
      minute: 30
```

### Schedule Types

1. **Cron Schedule**:
   ```yaml
   schedule:
     type: "cron"
     hour: 7
     minute: 30
     day_of_week: "mon-fri"  # Optional
   ```

2. **Interval Schedule**:
   ```yaml
   schedule:
     type: "interval"
     hours: 6  # Run every 6 hours
     minutes: 30  # Can combine: every 6.5 hours
   ```

3. **Run Once**:
   ```yaml
   schedule:
     type: "once"  # Runs at startup
   ```

## Creating Custom Plugins

### Content Provider Plugin

Create a file in `send_to_ai_content/`:

```python
from core.interfaces import ContentProvider

class MyDataProvider(ContentProvider):
    def get_prompt(self) -> str:
        return "Summarize this data..."
    
    def fetch(self) -> str:
        # Fetch and return data
        return "Data content..."

def factory(config):
    return MyDataProvider(config)
```

### LLM Plugin

Create a file in `llm_message_sender/`:

```python
from core.interfaces import LLMSender

class MyLLMSender(LLMSender):
    def summarize(self, prompt: str, content: str) -> str:
        # Call AI API and return summary
        return "Summary..."

def factory(config):
    return MyLLMSender(config)
```

### Notifier Plugin

Create a file in `message_notice/`:

```python
from core.interfaces import Notifier

class MyNotifier(Notifier):
    def send(self, message: str, title: str = None) -> bool:
        # Send notification
        return True

def factory(config):
    return MyNotifier(config)
```

## API Keys Setup

### OpenWeatherMap
1. Sign up at https://openweathermap.org/api
2. Get your API key from the dashboard

### OpenAI
1. Sign up at https://platform.openai.com
2. Create an API key in the dashboard

### Google Gemini
1. Visit https://ai.google.dev/
2. Get API access through Google AI Studio
3. Create an API key in the console

### Telegram Bot
1. Talk to @BotFather on Telegram
2. Create a new bot and get the token
3. Get your chat ID by messaging the bot and visiting:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`

### Bark (iOS)
1. Install Bark app from App Store
2. Get your device key from the app

### Email Setup
1. **Gmail**: Use App Passwords (not your regular password)
   - Enable 2-factor authentication
   - Generate App Password: Account Settings → Security → 2-Step Verification → App passwords
2. **Outlook/Hotmail**: Use your regular credentials or App Password
3. **Generic SMTP**: Configure your SMTP server settings

## Troubleshooting

### Common Issues

1. **Module not found errors**: Ensure you're in the virtual environment
2. **API key errors**: Check environment variables are set correctly
3. **Scheduling issues**: Verify timezone settings in config
4. **Connection errors**: Check network and API endpoints

### Debug Mode

Run with debug logging to see detailed information:

```bash
python main.py -l DEBUG --log-file debug.log
```

## Security Best Practices

1. Never commit API keys to version control
2. Use environment variables for sensitive data
3. Restrict file permissions on config files
4. Regularly rotate API keys
5. Use HTTPS endpoints when available

## Contributing

1. Follow the plugin interface definitions
2. Add appropriate error handling
3. Include logging statements
4. Write clear documentation
5. Test your plugins thoroughly

## License

This project is licensed under the GNU General Public License v3.0.

### Key Points of GPL v3 License

- ✅ **Freedom to Use**: You can freely run the program.
- ✅ **Freedom to Study**: You can study how the program works and modify it.
- ✅ **Freedom to Distribute**: You can redistribute copies.
- ✅ **Freedom to Improve**: You can improve the program and release improved versions.
- ⚠️ **Copyleft Requirement**: All derivative works based on this project must also be licensed under the GPL v3.
- ⚠️ **Source Code Disclosure**: When distributing, you must provide the source code or a way to obtain it.

### License Text

```
LLMSender - A modular Python application for scheduled content summarization and notification
Copyright (C) 2025 Daniel Hall

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
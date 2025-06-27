# LLMSender Pack Architecture

## Overview

LLMSender has been completely redesigned with a new Pack-based architecture that introduces an Action mechanism between LLM processing and notification. This new system provides unprecedented modularity, extensibility, and customization capabilities.

## New Architecture Flow

**Previous Flow**: Trigger → Content → LLM → Notifier  
**New Flow**: Trigger → Content → LLM → **Action** → Notifier

## Key Components

### 1. Packs

Packs are self-contained modules that bundle related functionality. Each pack can contain:

- **Triggers**: Event-driven activators (time-based, API webhooks, content monitoring)
- **Content Providers**: Data fetchers from various sources
- **Actions**: Post-LLM processors that can transform, filter, or enhance content
- **Notifiers**: Output channels for sending processed content

#### Pack Structure
```
PackName/
├── LLMSender_Pack.json          # Pack metadata and configuration
├── llmsender_pack_trigger/      # Trigger components
│   ├── main.py
│   └── __init__.py
├── llmsender_pack_content/      # Content provider components
│   ├── main.py
│   └── __init__.py
├── llmsender_pack_action/       # Action components
│   ├── main.py
│   └── __init__.py
└── llmsender_pack_notice/       # Notifier components
    ├── main.py
    └── __init__.py
```

### 2. Actions - The New Layer

Actions are the most significant addition to the architecture. They process LLM output before notification and can:

- **Filter content** based on sentiment, keywords, length, etc.
- **Transform output** (translate, format, summarize further)
- **Enhance content** (add search results, metadata, links)
- **Control flow** (decide whether to proceed with notification)
- **Function as LLM tools** (available to LLM during generation)

#### Action Interface
```python
class Action(ABC):
    def process(self, llm_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process LLM output and return enhanced result"""
        
    def get_tool_spec(self) -> Optional[Dict[str, Any]]:
        """Get OpenAI-compatible function specification for LLM tools"""
        
    def should_notify(self) -> bool:
        """Whether this action's result should trigger notifications"""
```

### 3. Enhanced Triggers

The new trigger system supports:

- **Time-based triggers** (cron, interval, once)
- **Custom pack triggers** (Twitter monitoring, webhook endpoints)
- **Event-driven activation** with rich context data

### 4. Backward Compatibility

The system maintains full backward compatibility with existing configurations while enabling new pack-based functionality.

## Pack Examples

### Twitter Pack

Complete Twitter integration with:

**Triggers:**
- `twitter.new_tweet` - Monitor for new tweets from specific users
- `twitter.user_mention` - Detect mentions

**Content:**
- `twitter.fetch_tweets` - Get user timeline
- `twitter.fetch_timeline` - Get home timeline

**Actions:**
- `twitter.filter_tweets` - Filter by engagement, keywords
- `twitter.analyze_sentiment` - Sentiment analysis and notification control
- `twitter.translate_tweet` - Language translation

**Notifiers:**
- `twitter.post_tweet` - Post new tweets
- `twitter.send_dm` - Send direct messages
- `twitter.post_thread` - Create Twitter threads

### Core Actions Pack

Essential processing actions:

- `core.filter` - Content filtering by length, keywords
- `core.format` - Output formatting (Markdown, HTML, JSON)
- `core.web_search` - Web search enhancement (LLM tool)

## Configuration Examples

### Pack-Based Task
```yaml
- name: "AI News Monitor"
  pack: "twitter"
  
  trigger:
    type: "twitter.new_tweet"
    username: "OpenAI"
    check_interval: 300
  
  content:
    type: "fetch_tweets"
    count: 5
  
  llm:
    plugin: "openai_sender"
    model: "gpt-4"
  
  actions:
    - type: "twitter.filter_tweets"
      min_likes: 50
      keywords: ["AI", "GPT"]
    
    - type: "twitter.analyze_sentiment"
      notify_on_negative: false
  
  notifiers:
    - plugin: "telegram"
```

### Mixed Legacy/Pack Task
```yaml
- name: "Enhanced Weather"
  
  content:
    plugin: "weather"  # Legacy plugin
    city: "London"
  
  llm:
    plugin: "openai_sender"
  
  actions:
    - type: "core.filter"
      min_length: 50
    
    - type: "core.format"
      format: "markdown"
  
  notifiers:
    - plugin: "email"  # Legacy notifier
```

## LLM Tool Integration

Actions can be exposed as tools that the LLM can call during generation:

```yaml
llm:
  plugin: "openai_sender"
  model: "gpt-4"
  tools: true  # Enable tool access

actions:
  - type: "core.web_search"  # Available as LLM tool
  - type: "twitter.filter_tweets"  # Available as LLM tool
```

## Development Guide

### Creating a New Pack

1. **Create pack directory structure**
2. **Define metadata in `LLMSender_Pack.json`**
3. **Implement components using the respective interfaces**
4. **Add factory functions for component loading**
5. **Test with example configurations**

### Creating Actions

Actions are the most powerful new feature. They can:

- Process and modify LLM output
- Control notification flow
- Serve as LLM tools for enhanced generation
- Chain together for complex processing pipelines

## Migration Path

1. **Existing configurations continue to work unchanged**
2. **Gradually adopt pack-based components**
3. **Add actions for enhanced processing**
4. **Leverage custom triggers for advanced automation**

## Benefits

1. **Modularity**: Each pack is self-contained and reusable
2. **Extensibility**: Easy to add new functionality without core changes
3. **Flexibility**: Mix and match components from different packs
4. **Power**: Action layer enables sophisticated content processing
5. **LLM Integration**: Actions can enhance LLM capabilities through tool use
6. **Backward Compatibility**: Seamless migration from existing setups

## Technical Implementation

- **PackLoader**: Dynamic pack discovery and component loading
- **ActionPipeline**: Manages action chains and LLM tool integration
- **TriggerManager**: Handles both legacy and pack-based triggers
- **Enhanced Main**: Supports both execution flows with automatic detection

This architecture transforms LLMSender from a simple pipeline into a powerful, extensible platform for AI-powered content processing and automation.
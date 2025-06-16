from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="llmsender",
    version="0.1.0",
    description="A modular system for AI-powered content summarization and notification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    
    # 核心依赖 - 必需的最小依赖集
    install_requires=[
        "requests>=2.31.0",
        "PyYAML>=6.0.1", 
        "APScheduler>=3.10.4",
        "python-dotenv>=1.0.0",
    ],
    
    # 可选依赖 - 按功能分组
    extras_require={
        # LLM 提供商
        'anthropic': ['anthropic>=0.54.0'],
        'openai': ['openai>=1.0.0'],
        'gemini': ['google-generativeai>=0.3.0'],
        
        # 通知渠道
        'telegram': ['python-telegram-bot>=20.0'],
        'email_advanced': ['emails>=0.6.0'],  # 高级邮件功能
        
        # 内容源
        'news_advanced': ['newsapi-python>=0.2.7'],  # NewsAPI 官方 SDK
        
        # 开发工具
        'dev': [
            'pytest>=7.4.3',
            'black>=23.11.0',
            'flake8>=6.1.0',
            'mypy>=1.7.0',
        ],
        
        # 完整安装
        'all': [
            'anthropic>=0.54.0',
            'openai>=1.0.0',
            'google-generativeai>=0.3.0',
            'python-telegram-bot>=20.0',
            'emails>=0.6.0',
            'newsapi-python>=0.2.7',
        ],
    },
    
    entry_points={
        'console_scripts': [
            'llmsender=main:main',
        ],
    },
)
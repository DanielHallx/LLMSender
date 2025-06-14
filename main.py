#!/usr/bin/env python3
import argparse
import logging
import signal
import sys
from typing import Dict, Any, List
import yaml
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from core.plugin_loader import PluginLoader
from core.utils import setup_logging, TaskTimer, get_env_var

logger = logging.getLogger(__name__)


class LLMSenderApp:
    """LLMSender 的主应用程序类。"""

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self._load_config()
        self.scheduler = BlockingScheduler(timezone=self.config.get('timezone', 'Asia/Shanghai'))
        self.running = True
        
        # 设置信号处理程序以实现正常关闭
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self) -> Dict[str, Any]:
        """从 YAML 文件加载配置。"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 替换环境变量占位符
            config = self._replace_env_vars(config)
            
            logger.info(f"Successfully loaded config from {self.config_file}")
            logger.info(f"LLMSender is running | Together, we run towards the future ----- LLMSender By Daniel Hall")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def _replace_env_vars(self, obj: Any) -> Any:
        """递归替换配置中的环境变量占位符。"""
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            env_var = obj[2:-1]
            return get_env_var(env_var, required=True)
        else:
            return obj
    
    def _signal_handler(self, signum, frame):
        """正常处理关闭信号。"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.scheduler.shutdown(wait=False)
        sys.exit(0)
    
    def execute_task(self, task_config: Dict[str, Any]):
        """Execute a single task based on configuration."""
        task_name = task_config.get('name', 'Unnamed Task')

        with TaskTimer(task_name):
            try:
                # Load content provider plugin
                content_config = task_config.get('content', {}).copy()
                content_plugin_name = content_config.pop('plugin', None)
                
                if not content_plugin_name:
                    raise ValueError("Content plugin not specified")

                content_provider = PluginLoader.load_plugin(
                    'content', content_plugin_name, content_config
                )
                
                # Fetch content
                logger.info(f"Using {content_plugin_name} to fetch content")
                content = content_provider.fetch()
                prompt = content_provider.get_prompt()
                
                # Load LLM plugin
                llm_config = task_config.get('llm', {}).copy()
                llm_plugin_name = llm_config.pop('plugin', None)
                
                # Debug: Log the config being passed to LLM plugin
                logger.debug(f"Passing config to {llm_plugin_name}: {list(llm_config.keys())}")
                
                if not llm_plugin_name:
                    raise ValueError("LLM plugin not specified")

                llm_sender = PluginLoader.load_plugin(
                    'llm', llm_plugin_name, llm_config
                )
                
                # Generate summary
                logger.info(f"Using {llm_plugin_name} to generate summary")
                summary = llm_sender.summarize(prompt, content)
                
                # Send notifications
                notifiers = task_config.get('notifiers', [])
                title = task_config.get('title', task_name)
                
                for notifier_config in notifiers:
                    # Make a copy to avoid modifying the original config
                    notifier_config_copy = notifier_config.copy()
                    notifier_plugin_name = notifier_config_copy.pop('plugin', None)
                    
                    if not notifier_plugin_name:
                        logger.warning("Notifier plugin not specified, skipping")
                        continue
                    
                    try:
                        notifier = PluginLoader.load_plugin(
                            'notifier', notifier_plugin_name, notifier_config_copy
                        )
                        
                        logger.info(f"Sending notification via {notifier_plugin_name}")
                        success = notifier.send(summary, title)
                        
                        if success:
                            logger.info(f"Notification sent successfully via {notifier_plugin_name}")
                        else:
                            logger.error(f"Failed to send notification via {notifier_plugin_name}")

                    except Exception as e:
                        logger.error(f"Notifier {notifier_plugin_name} error: {e}")

                logger.info(f"Task '{task_name}' completed successfully")

            except Exception as e:
                logger.error(f"Task '{task_name}' failed: {e}")

                # Send error notification if configured
                error_notifiers = task_config.get('error_notifiers', [])
                for notifier_config in error_notifiers:
                    try:
                        # Make a copy to avoid modifying the original config
                        notifier_config_copy = notifier_config.copy()
                        notifier_plugin_name = notifier_config_copy.pop('plugin', None)
                        if notifier_plugin_name:
                            notifier = PluginLoader.load_plugin(
                                'notifier', notifier_plugin_name, notifier_config_copy
                            )
                            notifier.send(
                                f"Task failed: {str(e)}",
                                f"Error: {task_name}"
                            )
                    except Exception as notify_error:
                        logger.error(f"Failed to send error notification: {notify_error}")

    def schedule_tasks(self):
        """根据配置计划所有任务。"""
        tasks = self.config.get('tasks', [])
        
        for task in tasks:
            schedule = task.get('schedule', {})
            if schedule.get('type') == 'cron':
                # 基于 Cron 的计划
                trigger = CronTrigger(
                    hour=schedule.get('hour'),
                    minute=schedule.get('minute', 0),
                    day_of_week=schedule.get('day_of_week'),
                    day=schedule.get('day'),
                    month=schedule.get('month'),
                    timezone=self.config.get('timezone', 'Asia/Shanghai')
                )
                self.scheduler.add_job(
                    func=self.execute_task,
                    trigger=trigger,
                    args=[task],
                    id=task.get('name', f'task_{id(task)}'),
                    name=task.get('name', 'Unnamed Task')
                )
                logger.info(f"Scheduled cron task '{task.get('name')}'")

            elif schedule.get('type') == 'interval':
                # 基于间隔的计划
                self.scheduler.add_job(
                    func=self.execute_task,
                    trigger='interval',
                    seconds=schedule.get('seconds', 0),
                    minutes=schedule.get('minutes', 0),
                    hours=schedule.get('hours', 0),
                    args=[task],
                    id=task.get('name', f'task_{id(task)}'),
                    name=task.get('name', 'Unnamed Task')
                )
                logger.info(f"Scheduled interval task '{task.get('name')}'")

            elif schedule.get('type') == 'once':
                # 启动时运行一次
                self.scheduler.add_job(
                    func=self.execute_task,
                    args=[task],
                    id=task.get('name', f'task_{id(task)}'),
                    name=task.get('name', 'Unnamed Task')
                )
                logger.info(f"Scheduled one-time task '{task.get('name')}'")

    def run(self):
        """启动应用程序。"""
        logger.info("Starting LLMSender application")

        # 发现可用的插件
        for plugin_type in ['content', 'llm', 'notifier']:
            plugins = PluginLoader.discover_plugins(plugin_type)
            logger.info(f"Available {plugin_type} plugins: {list(plugins.keys())}")

        # 计划任务
        self.schedule_tasks()
        
        # 启动调度程序
        try:
            logger.info("Starting scheduler...")
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise


def main():
    """主入口点。"""
    parser = argparse.ArgumentParser(description='LLMSender - 模块化内容摘要和通知系统')
    parser.add_argument(
        '-c', '--config',
        default='config/config.yaml',
        help='配置文件路径（默认值：config/config.yaml）'
    )
    parser.add_argument(
        '-l', '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志记录级别（默认值：INFO）'
    )
    parser.add_argument(
        '--log-file',
        help='日志文件路径（可选）'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='运行所有任务一次并退出'
    )
    
    args = parser.parse_args()
    
    # 设置日志记录
    setup_logging(args.log_level, args.log_file)
    
    try:
        app = LLMSenderApp(args.config)
        
        if args.test:
            # 测试模式：运行所有任务一次
            logger.info("正在以测试模式运行 - 执行所有任务一次")
            for task in app.config.get('tasks', []):
                app.execute_task(task)
            logger.info("测试模式完成")
        else:
            # 正常模式：启动调度程序
            app.run()
            
    except Exception as e:
        logger.error(f"应用程序失败：{e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
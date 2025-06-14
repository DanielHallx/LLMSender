import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from core.interfaces import Notifier
from core.utils import retry_with_backoff, get_env_var

logger = logging.getLogger(__name__)


class EmailNotifier(Notifier):
    """Send notifications via email using SMTP."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # SMTP server configuration
        self.smtp_server = config.get('smtp_server') or get_env_var('SMTP_SERVER')
        self.smtp_port = config.get('smtp_port', 587)
        self.use_tls = config.get('use_tls', True)
        self.use_ssl = config.get('use_ssl', False)
        
        # Authentication
        self.username = config.get('username') or get_env_var('EMAIL_USERNAME')
        self.password = config.get('password') or get_env_var('EMAIL_PASSWORD')
        
        # Email addresses
        self.from_email = config.get('from_email') or get_env_var('EMAIL_FROM') or self.username
        self.to_emails = config.get('to_emails', [])
        
        # If to_emails is a string, convert to list
        if isinstance(self.to_emails, str):
            self.to_emails = [email.strip() for email in self.to_emails.split(',')]
        
        # Add environment variable for recipients
        env_to_emails = get_env_var('EMAIL_TO_EMAILS')
        if env_to_emails:
            env_emails = [email.strip() for email in env_to_emails.split(',')]
            self.to_emails.extend(env_emails)
        
        # Email formatting
        self.html_format = config.get('html_format', True)
        self.signature = config.get('signature', '')
        
        # Validation
        if not all([self.smtp_server, self.username, self.password, self.from_email]):
            raise ValueError("SMTP server, username, password, and from_email are required")
        
        if not self.to_emails:
            raise ValueError("At least one recipient email address is required")
    
    @retry_with_backoff(max_retries=3, exceptions=(smtplib.SMTPException, ConnectionError))
    def send(self, message: str, title: Optional[str] = None) -> bool:
        """Send email notification."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = title or 'LLMSender Notification'
            
            # Prepare message content
            if self.signature:
                message_with_signature = f"{message}\n\n{self.signature}"
            else:
                message_with_signature = message
            
            # Create text and HTML parts
            text_content = message_with_signature
            
            if self.html_format:
                # Convert text to basic HTML
                html_content = self._text_to_html(message_with_signature)
                
                # Attach both text and HTML parts
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                html_part = MIMEText(html_content, 'html', 'utf-8')
                
                msg.attach(text_part)
                msg.attach(html_part)
            else:
                # Text only
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Send email
            if self.use_ssl:
                # Use SSL connection
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                # Use regular connection with optional TLS
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.use_tls:
                    server.starttls()
            
            # Authenticate and send
            server.login(self.username, self.password)
            
            # Send to all recipients
            server.send_message(msg, to_addrs=self.to_emails)
            server.quit()
            
            logger.info(f"Successfully sent email notification to {len(self.to_emails)} recipients")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _text_to_html(self, text: str) -> str:
        """Convert plain text to basic HTML format."""
        # Escape HTML characters
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Convert line breaks to <br>
        lines = text.split('\n')
        html_lines = []
        
        for line in lines:
            if line.strip() == '':
                html_lines.append('<br>')
            elif line.startswith('#'):
                # Convert headers
                level = len(line) - len(line.lstrip('#'))
                header_text = line.lstrip('# ').strip()
                html_lines.append(f'<h{min(level, 6)}>{header_text}</h{min(level, 6)}>')
            elif line.startswith('- ') or line.startswith('* '):
                # Convert bullet points
                bullet_text = line[2:].strip()
                html_lines.append(f'<li>{bullet_text}</li>')
            else:
                html_lines.append(f'<p>{line}</p>')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                p {{ margin: 10px 0; }}
                li {{ margin: 5px 0; }}
                .signature {{ margin-top: 20px; font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            {''.join(html_lines)}
        </body>
        </html>
        """
        
        return html_content


class GmailNotifier(EmailNotifier):
    """Gmail-specific email notifier with app password support."""
    
    def __init__(self, config: Dict[str, Any]):
        # Set Gmail defaults
        gmail_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'use_tls': True,
            'use_ssl': False,
            **config
        }
        super().__init__(gmail_config)


class OutlookNotifier(EmailNotifier):
    """Outlook/Hotmail-specific email notifier."""
    
    def __init__(self, config: Dict[str, Any]):
        # Set Outlook defaults
        outlook_config = {
            'smtp_server': 'smtp-mail.outlook.com',
            'smtp_port': 587,
            'use_tls': True,
            'use_ssl': False,
            **config
        }
        super().__init__(outlook_config)


def factory(config: Dict[str, Any]) -> Notifier:
    """Factory function to create appropriate email notifier."""
    provider = config.get('provider', 'generic').lower()
    
    if provider == 'gmail':
        return GmailNotifier(config)
    elif provider in ['outlook', 'hotmail']:
        return OutlookNotifier(config)
    else:
        return EmailNotifier(config)
import os
import logging
from typing import Optional
from pathlib import Path

# Configure logging for config module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecureConfig:
    """Secure configuration manager with validation and security checks."""
    
    def __init__(self):
        self._validate_environment()
        self._load_config()
    
    def _validate_environment(self):
        """Validate that all required environment variables are set."""
        required_vars = [
            'BOT_TOKEN',
            'ADMIN_CHAT_ID',
            'ADMIN_EMAIL',
            'ADMIN_EMAIL_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = f"❌ CRITICAL: Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise EnvironmentError(error_msg)
        
        # Validate bot token format
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token or ':' not in bot_token:
            raise EnvironmentError("❌ CRITICAL: Invalid BOT_TOKEN format. Expected: <bot_id>:<token>")
        
        # Validate admin chat ID is numeric
        try:
            admin_id = int(os.environ.get('ADMIN_CHAT_ID'))
            if admin_id <= 0:
                raise ValueError("Admin chat ID must be positive")
        except (ValueError, TypeError):
            raise EnvironmentError("❌ CRITICAL: ADMIN_CHAT_ID must be a valid positive integer")
        
        logger.info("✅ Environment validation passed")
    
    def _load_config(self):
        """Load and validate configuration values."""
        # Bot configuration
        self.BOT_TOKEN = os.environ['BOT_TOKEN']
        self.BOT_ID = self.BOT_TOKEN.split(':')[0]
        
        # Web app configuration
        self.BASE_WEBAPP_URL = os.environ.get(
            'BASE_WEBAPP_URL', 
            'https://miniapp.drazhin.by/bot-app/'
        )
        
        # Admin configuration
        self.ADMIN_CHAT_ID = int(os.environ['ADMIN_CHAT_ID'])
        self.ADMIN_EMAIL = os.environ['ADMIN_EMAIL']
        self.ADMIN_EMAIL_PASSWORD = os.environ['ADMIN_EMAIL_PASSWORD']
        
        # SMTP configuration
        self.SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
        self.SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
        
        # Security configuration
        self.ENABLE_RATE_LIMITING = os.environ.get('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
        self.RATE_LIMIT_MAX_REQUESTS = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', '100'))
        self.RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', '3600'))  # 1 hour
        
        # Webhook security
        self.ALLOW_WEBHOOKS = os.environ.get('ALLOW_WEBHOOKS', 'false').lower() == 'true'
        self.TRUSTED_DOMAINS = os.environ.get('TRUSTED_DOMAINS', '').split(',')
        self.WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
        
        # Logging configuration
        self.LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
        self.LOG_SECURITY_EVENTS = os.environ.get('LOG_SECURITY_EVENTS', 'true').lower() == 'true'
        
        # Feature flags
        self.ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'true').lower() == 'true'
        self.ENABLE_SECURITY_MONITORING = os.environ.get('ENABLE_SECURITY_MONITORING', 'true').lower() == 'true'
        
        logger.info("✅ Configuration loaded successfully")
    
    def get_webhook_security_config(self) -> dict:
        """Get webhook security configuration."""
        return {
            'allow_webhooks': self.ALLOW_WEBHOOKS,
            'trusted_domains': self.TRUSTED_DOMAINS,
            'webhook_secret': self.WEBHOOK_SECRET,
            'bot_id': self.BOT_ID
        }
    
    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration."""
        return {
            'enabled': self.ENABLE_RATE_LIMITING,
            'max_requests': self.RATE_LIMIT_MAX_REQUESTS,
            'window': self.RATE_LIMIT_WINDOW
        }
    
    def validate_webhook_url(self, url: str) -> bool:
        """Validate if a webhook URL is allowed."""
        if not self.ALLOW_WEBHOOKS:
            return False
        
        if not url.startswith('https://'):
            return False
        
        # Extract domain from URL
        try:
            domain = url.split('://')[1].split('/')[0]
            return domain in self.TRUSTED_DOMAINS
        except (IndexError, AttributeError):
            return False

# Create global config instance
try:
    config = SecureConfig()
    
    # Export all config values for backward compatibility
    BOT_TOKEN = config.BOT_TOKEN
    BOT_ID = config.BOT_ID
    BASE_WEBAPP_URL = config.BASE_WEBAPP_URL
    ADMIN_CHAT_ID = config.ADMIN_CHAT_ID
    ADMIN_EMAIL = config.ADMIN_EMAIL
    ADMIN_EMAIL_PASSWORD = config.ADMIN_EMAIL_PASSWORD
    SMTP_SERVER = config.SMTP_SERVER
    SMTP_PORT = config.SMTP_PORT
    SMTP_USE_TLS = config.SMTP_USE_TLS
    ENABLE_EMAIL_NOTIFICATIONS = config.ENABLE_EMAIL_NOTIFICATIONS
    
    logger.info("✅ Configuration module initialized successfully")
    
except Exception as e:
    logger.error(f"❌ Failed to initialize configuration: {e}")
    raise
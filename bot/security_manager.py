import asyncio
import hashlib
import hmac
import json
import logging
import time
import base64
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
import socket

from bot.config import config

logger = logging.getLogger(__name__)

class SecurityManager:
    """Comprehensive security manager for the bot."""
    
    def __init__(self):
        self.rate_limit_store = defaultdict(list)
        self.suspicious_activities = []
        self.security_events = []
        self.last_cleanup = time.time()
        self.cleanup_interval = 3600  # 1 hour
        
        # HMAC configuration
        self.hmac_secret = os.environ.get('HMAC_SECRET', 'default-secret-key-change-in-production')
        self.hmac_algorithm = 'sha256'
        
    async def validate_webhook_request(self, request_data: dict, signature: str = None) -> bool:
        """Validate incoming webhook request."""
        if not config.ALLOW_WEBHOOKS:
            logger.warning("🚫 Webhook request rejected: webhooks not allowed")
            return False
        
        # Validate signature if webhook secret is configured
        if config.WEBHOOK_SECRET and signature:
            if not self._verify_webhook_signature(request_data, signature):
                logger.warning("🚫 Webhook request rejected: invalid signature")
                self._log_security_event("webhook_invalid_signature", request_data)
                return False
        
        # Validate request structure
        if not self._validate_webhook_structure(request_data):
            logger.warning("🚫 Webhook request rejected: invalid structure")
            self._log_security_event("webhook_invalid_structure", request_data)
            return False
        
        logger.info("✅ Webhook request validated successfully")
        return True
    
    def _verify_webhook_signature(self, data: dict, signature: str) -> bool:
        """Verify webhook signature using HMAC."""
        try:
            # Create expected signature
            message = json.dumps(data, separators=(',', ':'))
            expected_signature = hmac.new(
                config.WEBHOOK_SECRET.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def _validate_webhook_structure(self, data: dict) -> bool:
        """Validate webhook data structure."""
        required_fields = ['update_id']
        return all(field in data for field in required_fields)
    
    async def check_rate_limit(self, user_id: int, action: str = "general") -> bool:
        """Check if user has exceeded rate limits."""
        if not config.ENABLE_RATE_LIMITING:
            return True
        
        current_time = time.time()
        key = f"{user_id}:{action}"
        
        # Clean old entries
        self.rate_limit_store[key] = [
            timestamp for timestamp in self.rate_limit_store[key]
            if current_time - timestamp < config.RATE_LIMIT_WINDOW
        ]
        
        # Check if limit exceeded
        if len(self.rate_limit_store[key]) >= config.RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"🚫 Rate limit exceeded for user {user_id}, action: {action}")
            self._log_security_event("rate_limit_exceeded", {
                "user_id": user_id,
                "action": action,
                "current_count": len(self.rate_limit_store[key])
            })
            return False
        
        # Add current request
        self.rate_limit_store[key].append(current_time)
        return True
    
    def validate_input_data(self, data: dict, expected_structure: dict) -> Tuple[bool, List[str]]:
        """Validate input data structure and content."""
        errors = []
        
        # Check required fields
        for field, field_type in expected_structure.items():
            if field not in data:
                errors.append(f"Missing required field: {field}")
                continue
            
            value = data[field]
            
            # Type validation
            if field_type == "str" and not isinstance(value, str):
                errors.append(f"Field {field} must be string, got {type(value).__name__}")
            elif field_type == "int" and not isinstance(value, int):
                errors.append(f"Field {field} must be integer, got {type(value).__name__}")
            elif field_type == "float" and not isinstance(value, (int, float)):
                errors.append(f"Field {field} must be number, got {type(value).__name__}")
            elif field_type == "list" and not isinstance(value, list):
                errors.append(f"Field {field} must be list, got {type(value).__name__}")
            elif field_type == "dict" and not isinstance(value, dict):
                errors.append(f"Field {field} must be dict, got {type(value).__name__}")
        
        # Content validation
        if "phone" in data and isinstance(data["phone"], str):
            if not self._validate_phone_number(data["phone"]):
                errors.append("Invalid phone number format")
        
        if "email" in data and isinstance(data["email"], str):
            if not self._validate_email(data["email"]):
                errors.append("Invalid email format")
        
        return len(errors) == 0, errors
    
    def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format."""
        import re
        # Basic phone validation - adjust regex as needed
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(phone_pattern, phone.replace(' ', '').replace('-', '')))
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    async def monitor_webhook_security(self) -> Dict:
        """Monitor webhook security status."""
        try:
            connector = aiohttp.TCPConnector(family=socket.AF_INET)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Get current webhook info
                webhook_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getWebhookInfo"
                async with session.get(webhook_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        webhook_info = data.get("result", {})
                        
                        # Analyze webhook security
                        security_status = self._analyze_webhook_security(webhook_info)
                        
                        # Log security event
                        self._log_security_event("webhook_security_check", security_status)
                        
                        return security_status
                    else:
                        logger.error(f"Failed to get webhook info: {response.status}")
                        return {"error": "Failed to get webhook info"}
                        
        except Exception as e:
            logger.error(f"Error monitoring webhook security: {e}")
            return {"error": str(e)}
    
    def _analyze_webhook_security(self, webhook_info: dict) -> Dict:
        """Analyze webhook security status."""
        url = webhook_info.get("url", "")
        
        if not url:
            return {
                "secure": True,
                "status": "No webhook set",
                "recommendation": "Safe - using long polling"
            }
        
        # Check if webhook URL is trusted
        if not config.validate_webhook_url(url):
            return {
                "secure": False,
                "status": "Untrusted webhook domain",
                "url": url,
                "recommendation": "Delete webhook immediately and regenerate bot token"
            }
        
        # Check for suspicious patterns
        suspicious_patterns = [
            "botelegram.work.gd",
            "casino",
            "spam",
            "malicious",
            "suspicious"
        ]
        
        for pattern in suspicious_patterns:
            if pattern.lower() in url.lower():
                return {
                    "secure": False,
                    "status": "Suspicious webhook detected",
                    "url": url,
                    "pattern": pattern,
                    "recommendation": "Delete webhook immediately and regenerate bot token"
                }
        
        return {
            "secure": True,
            "status": "Webhook appears safe",
            "url": url,
            "recommendation": "Monitor regularly"
        }
    
    async def delete_webhook(self) -> Dict:
        """Delete current webhook."""
        try:
            connector = aiohttp.TCPConnector(family=socket.AF_INET)
            async with aiohttp.ClientSession(connector=connector) as session:
                delete_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/deleteWebhook"
                async with session.post(delete_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            logger.info("✅ Webhook deleted successfully")
                            self._log_security_event("webhook_deleted", {"status": "success"})
                            return {"success": True, "message": "Webhook deleted successfully"}
                        else:
                            logger.error(f"Failed to delete webhook: {data}")
                            return {"success": False, "error": data.get("description", "Unknown error")}
                    else:
                        logger.error(f"Failed to delete webhook: {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}
                        
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def _log_security_event(self, event_type: str, details: dict):
        """Log security event."""
        if not config.LOG_SECURITY_EVENTS:
            return
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        self.security_events.append(event)
        logger.warning(f"🚨 SECURITY EVENT: {event_type} - {details}")
        
        # Keep only last 1000 events
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
    
    async def cleanup_old_data(self):
        """Clean up old rate limit and security data."""
        current_time = time.time()
        
        # Clean rate limit store
        for key in list(self.rate_limit_store.keys()):
            self.rate_limit_store[key] = [
                timestamp for timestamp in self.rate_limit_store[key]
                if current_time - timestamp < config.RATE_LIMIT_WINDOW
            ]
            
            # Remove empty entries
            if not self.rate_limit_store[key]:
                del self.rate_limit_store[key]
        
        # Clean old security events (keep last 24 hours)
        cutoff_time = current_time - 86400
        self.security_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event["timestamp"]).timestamp() > cutoff_time
        ]
        
        self.last_cleanup = current_time
        logger.debug("🧹 Security data cleanup completed")
    
    def get_security_report(self) -> Dict:
        """Get current security status report."""
        return {
            "rate_limiting": {
                "enabled": config.ENABLE_RATE_LIMITING,
                "active_limits": len(self.rate_limit_store),
                "total_requests": sum(len(requests) for requests in self.rate_limit_store.values())
            },
            "webhook_security": {
                "allowed": config.ALLOW_WEBHOOKS,
                "trusted_domains": config.TRUSTED_DOMAINS
            },
            "hmac_security": {
                "enabled": True,
                "algorithm": self.hmac_algorithm,
                "secret_configured": bool(self.hmac_secret and self.hmac_secret != 'default-secret-key-change-in-production')
            },
            "security_events": {
                "total": len(self.security_events),
                "recent": len([e for e in self.security_events 
                              if datetime.fromisoformat(e["timestamp"]) > datetime.now() - timedelta(hours=1)])
            },
            "last_cleanup": datetime.fromtimestamp(self.last_cleanup).isoformat()
        }
    
    def generate_hmac_signature(self, data: str, secret: str = None) -> str:
        """Generate HMAC signature for data."""
        if secret is None:
            secret = self.hmac_secret
        
        signature = hmac.new(
            secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_hmac_signature(self, data: str, signature: str, secret: str = None) -> bool:
        """Verify HMAC signature."""
        if secret is None:
            secret = self.hmac_secret
        
        expected_signature = self.generate_hmac_signature(data, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    def generate_auth_token(self) -> dict:
        """Generate authentication token for client."""
        timestamp = int(time.time())
        token_data = f"auth:{timestamp}"
        signature = self.generate_hmac_signature(token_data)
        
        return {
            "token": signature,
            "timestamp": timestamp,
            "expires_in": 3600  # 1 hour
        }
    
    def validate_timestamp(self, timestamp: int, tolerance: int = 300) -> bool:
        """Validate timestamp to prevent replay attacks."""
        current_time = int(time.time())
        return abs(current_time - timestamp) <= tolerance

# Global security manager instance
security_manager = SecurityManager()

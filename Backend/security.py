"""
Security Module
Provides security enhancements including input sanitization, rate limiting, and authentication helpers.
"""

import re
import hashlib
import secrets
import logging
from functools import wraps
from flask import request, jsonify, current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import bleach
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security-related operations."""

    def __init__(self):
        self.limiter = None

    def init_limiter(self, app):
        """Initialize rate limiter."""
        self.limiter = Limiter(
            app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"]
        )

    def sanitize_input(self, text, allow_html=False):
        """
        Sanitize user input to prevent XSS attacks.

        Args:
            text (str): Input text to sanitize
            allow_html (bool): Whether to allow basic HTML tags

        Returns:
            str: Sanitized text
        """
        if not text:
            return text

        if allow_html:
            # Allow basic formatting tags
            allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
            allowed_attributes = {}
            return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes)
        else:
            # Strip all HTML
            return bleach.clean(text, tags=[], attributes={})

    def validate_email(self, email):
        """
        Validate email format.

        Args:
            email (str): Email to validate

        Returns:
            bool: True if valid
        """
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None

    def validate_password_strength(self, password):
        """
        Validate password strength.

        Args:
            password (str): Password to validate

        Returns:
            dict: Validation result with score and feedback
        """
        score = 0
        feedback = []

        if len(password) >= 8:
            score += 1
        else:
            feedback.append("Password must be at least 8 characters long")

        if re.search(r'[A-Z]', password):
            score += 1
        else:
            feedback.append("Password must contain at least one uppercase letter")

        if re.search(r'[a-z]', password):
            score += 1
        else:
            feedback.append("Password must contain at least one lowercase letter")

        if re.search(r'\d', password):
            score += 1
        else:
            feedback.append("Password must contain at least one number")

        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        else:
            feedback.append("Password must contain at least one special character")

        return {
            'is_strong': score >= 4,
            'score': score,
            'feedback': feedback
        }

    def hash_password(self, password):
        """
        Hash a password using werkzeug.

        Args:
            password (str): Plain password

        Returns:
            str: Hashed password
        """
        return generate_password_hash(password, method='pbkdf2:sha256')

    def verify_password(self, hashed_password, password):
        """
        Verify a password against its hash.

        Args:
            hashed_password (str): Hashed password
            password (str): Plain password

        Returns:
            bool: True if matches
        """
        return check_password_hash(hashed_password, password)

    def generate_secure_token(self, length=32):
        """
        Generate a secure random token.

        Args:
            length (int): Token length in bytes

        Returns:
            str: Hex token
        """
        return secrets.token_hex(length)

    def generate_api_key(self):
        """
        Generate a unique API key.

        Returns:
            str: API key
        """
        return secrets.token_urlsafe(32)

    def hash_api_key(self, api_key):
        """
        Hash an API key for storage.

        Args:
            api_key (str): Plain API key

        Returns:
            str: Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    def validate_filename(self, filename):
        """
        Validate and sanitize filename.

        Args:
            filename (str): Filename to validate

        Returns:
            str: Sanitized filename or None if invalid
        """
        if not filename:
            return None

        # Remove path separators and dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)

        # Limit length
        if len(sanitized) > 255:
            return None

        # Check for dangerous extensions
        dangerous_exts = ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs']
        if any(sanitized.lower().endswith(ext) for ext in dangerous_exts):
            return None

        return sanitized

    def rate_limit(self, limit_string):
        """
        Decorator for rate limiting endpoints.

        Args:
            limit_string (str): Rate limit string (e.g., "5 per minute")

        Returns:
            decorator: Rate limiting decorator
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if self.limiter:
                    return self.limiter.limit(limit_string)(f)(*args, **kwargs)
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    def require_auth(self, f):
        """
        Decorator to require authentication for endpoints.

        Args:
            f: Function to decorate

        Returns:
            decorated function
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid authorization header'}), 401

            token = auth_header.split(' ')[1]
            # Verify token (implement JWT verification here)
            user_id = self.verify_token(token)
            if not user_id:
                return jsonify({'error': 'Invalid or expired token'}), 401

            g.user_id = user_id
            return f(*args, **kwargs)
        return decorated_function

    def verify_token(self, token):
        """
        Verify JWT token (placeholder - implement actual JWT verification).

        Args:
            token (str): JWT token

        Returns:
            int: User ID if valid, None otherwise
        """
        # Placeholder implementation - replace with actual JWT verification
        try:
            # Decode and verify JWT
            # For now, return a mock user ID
            return 1  # Mock user ID
        except:
            return None

    def log_security_event(self, event_type, user_id=None, details=None):
        """
        Log security-related events.

        Args:
            event_type (str): Type of security event
            user_id (int): User ID if applicable
            details (dict): Additional event details
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'details': details or {}
        }

        logger.warning(f"Security Event: {log_data}")

    def check_suspicious_activity(self, user_id, action):
        """
        Check for suspicious user activity.

        Args:
            user_id (int): User ID
            action (str): Action being performed

        Returns:
            bool: True if suspicious activity detected
        """
        # Implement suspicious activity detection logic
        # This could include checking for rapid login attempts, unusual file uploads, etc.
        return False  # Placeholder

    def encrypt_sensitive_data(self, data):
        """
        Encrypt sensitive data (placeholder - implement actual encryption).

        Args:
            data (str): Data to encrypt

        Returns:
            str: Encrypted data
        """
        # Placeholder - implement proper encryption
        return data  # Return as-is for now

    def decrypt_sensitive_data(self, encrypted_data):
        """
        Decrypt sensitive data (placeholder - implement actual decryption).

        Args:
            encrypted_data (str): Data to decrypt

        Returns:
            str: Decrypted data
        """
        # Placeholder - implement proper decryption
        return encrypted_data  # Return as-is for now

# Global security manager instance
security_manager = SecurityManager()

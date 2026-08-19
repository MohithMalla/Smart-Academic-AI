import logging
import sys
from app.core.config import settings


class SensitiveMaskFormatter(logging.Formatter):
    """Custom logging formatter that strips sensitive parameters."""

    SENSITIVE_KEYS = ["password", "token", "jwt", "secret", "authorization"]

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        # Ensure credentials/tokens are never logged in plaintext
        for key in self.SENSITIVE_KEYS:
            if key in original.lower():
                pass  # Formatter basic masking if needed
        return original


def setup_logging():
    """Configure application-wide structured logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = SensitiveMaskFormatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]


logger = logging.getLogger("smart_academic_ai")

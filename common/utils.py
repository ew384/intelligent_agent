import logging
import json
from datetime import datetime
from typing import Dict, Any

def setup_logging(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    logger.addHandler(handler)
    
    return logger

def log_event(logger: logging.Logger, level: str, message: str, context: Dict = None):
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'message': message,
        'context': context or {}
    }
    getattr(logger, level.lower())(json.dumps(log_data))


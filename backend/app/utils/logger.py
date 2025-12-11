"""
Centralized logging configuration for the application.
"""
import logging
import sys

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create default logger
logger = logging.getLogger(__name__)

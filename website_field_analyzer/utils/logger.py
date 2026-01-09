"""
Structured logging for the analyzer.
Provides step-by-step tracking of the 14-step pipeline.
"""

import logging
import sys
from typing import Optional


class AnalyzerLogger:
    """Custom logger for the analyzer with step tracking."""
    
    def __init__(self, name: str = "FieldAnalyzer", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self.current_step: Optional[int] = None
    
    def step(self, step_number: int, message: str):
        """Log a step in the 14-step pipeline."""
        self.current_step = step_number
        self.logger.info(f"[STEP {step_number:02d}] {message}")
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def success(self, message: str):
        """Log success message."""
        self.logger.info(f"[OK] {message}")
    
    def metric(self, name: str, value: any):
        """Log a metric."""
        self.logger.info(f"[METRIC] {name}: {value}")


# Global logger instance
logger = AnalyzerLogger()

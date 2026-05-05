# python imports
from typing import Optional
import logging
import json
import time


class AIBuilderEvalLogger:
    """AI Asset Builder logger for evaluator processing"""

    def __init__(self, name: Optional[str] = None, log_level: str = "INFO"):
        # Setup logger
        self.logger = logging.getLogger(f'asset_builder_evaluator.{name}')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.propagate = False

        self.logger.addHandler(console_handler)
        
        # Metrics
        self.sessions = {}

    def info(self, message: str, **kwargs):
        if kwargs:
            message += f" | {json.dumps(kwargs, default=str)}"
        self.logger.info(message)
    
    def error(self, message: str, **kwargs):
        if kwargs:
            message += f" | {json.dumps(kwargs, default=str)}"
        self.logger.error(message)
    
    def warning(self, message: str, **kwargs):
        if kwargs:
            message += f" | {json.dumps(kwargs, default=str)}"
        self.logger.warning(message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        if kwargs:
            message += f" | {json.dumps(kwargs, default=str)}"
        self.logger.debug(message)
    
    def log_connection_start(self, client_id: str):
        """Log when client connects"""
        self.info("Connection started", client_id=client_id)
        self.sessions[client_id] = {
            "start_time": time.time(),
            "messages": 0,
            "tokens": 0,
            "errors": 0
        }
    
    def log_pause_singnal(self, meeting_id: str):
        self.info("Connection paused for MIKI", meeting_id=meeting_id)

    def log_stop_singnal(self, meeting_id: str):
        self.info("Connection terminated for MIKI", meeting_id=meeting_id)
    
    def log_connection_end(self, client_id: str):
        """Log when client disconnects"""
        if client_id in self.sessions:
            session = self.sessions[client_id]
            duration = time.time() - session["start_time"]
            self.info(
                "Connection ended", 
                client_id=client_id,
                duration_seconds=round(duration, 2),
                total_messages=session["messages"],
                total_tokens=session["tokens"],
                total_errors=session["errors"]
            )
            del self.sessions[client_id]
        else:
            self.info("Connection ended", client_id=client_id)
    
    def log_request(self, client_id: str, meeting_id: str, has_tokens: bool, token_count: int = 0):
        if client_id in self.sessions:
            self.sessions[client_id]["messages"] += 1
            self.sessions[client_id]["tokens"] += token_count
        
        self.debug(
            "Request processed", 
            client_id=client_id,
            meeting_id=meeting_id,
            has_tokens=has_tokens,
            token_count=token_count
        )

    def log_transcript_update(self, client_id: str, meeting_id: str, new_sentences_count: int):
        """Log transcript update"""
        self.info(
            "Transcript updated", 
            client_id=client_id,
            meeting_id=meeting_id,
            new_sentences=new_sentences_count
        )

    def log_recovery(self, client_id: str, meeting_id: str, success: bool):
        """Log recovery attempt"""
        self.warning(
            "Recovery mode", 
            client_id=client_id,
            meeting_id=meeting_id,
            success=success
        )
    
    def log_db_sync(self, client_id: str, meeting_id: str):
        """Log database sync"""
        self.info(
            "Database sync initiated", 
            client_id=client_id,
            meeting_id=meeting_id
        )

    def log_error(self, client_id: str, error: Exception, context: str = ""):
        """Log error"""
        if client_id in self.sessions:
            self.sessions[client_id]["errors"] += 1
        
        self.error(
            "Exception occurred", 
            client_id=client_id,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context
        )

    def exception(self, message: str, **kwargs):
        if kwargs:
            message += f" | {json.dumps(kwargs, default=str)}"
        self.logger.exception(message)
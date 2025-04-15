"""
Ping Service Module
This module contains the core functionality for the website ping service.
"""

import time
import threading
import logging
import requests
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

class PingService:
    """
    Service that periodically pings a website to prevent it from going to sleep.
    """
    
    def __init__(self, history_size=100):
        """
        Initialize the ping service.
        
        Args:
            history_size (int): Maximum number of ping records to keep in history
        """
        self.history = deque(maxlen=history_size)
        self.stats = {
            "total_pings": 0,
            "successful_pings": 0,
            "failed_pings": 0
        }
        self.config = {
            "url": "https://www.google.com",
            "interval": 5,  # minutes
            "is_running": False
        }
        self.thread = None
        self.stop_event = threading.Event()
        
    def ping(self, url=None):
        """
        Ping a website and record the result.
        
        Args:
            url (str, optional): URL to ping. If None, use the configured URL.
            
        Returns:
            dict: Ping result information
        """
        if url is None:
            url = self.config["url"]
            
        try:
            # Send ping request
            start_time = time.time()
            response = requests.get(
                url, 
                timeout=10,
                headers={'User-Agent': 'Website Ping Service/1.0'}
            )
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000)  # in milliseconds
            
            # Record ping result
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            success = response.status_code < 400
            
            ping_entry = {
                "timestamp": timestamp,
                "url": url,
                "status_code": response.status_code,
                "success": success,
                "response_time": response_time
            }
            
            self.history.appendleft(ping_entry)
            self.stats["total_pings"] += 1
            if success:
                self.stats["successful_pings"] += 1
                logger.info(f"Ping successful: {url} - Status: {response.status_code} - Time: {response_time}ms")
            else:
                self.stats["failed_pings"] += 1
                logger.warning(f"Ping failed: {url} - Status: {response.status_code}")
                
            return ping_entry
                
        except Exception as e:
            # Handle connection errors
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ping_entry = {
                "timestamp": timestamp,
                "url": url,
                "status_code": 0,
                "success": False,
                "error": str(e),
                "response_time": 0
            }
            self.history.appendleft(ping_entry)
            self.stats["total_pings"] += 1
            self.stats["failed_pings"] += 1
            logger.error(f"Ping error: {url} - Error: {str(e)}")
            
            return ping_entry
            
    def _ping_loop(self):
        """
        Main loop for the ping service.
        """
        logger.info(f"Starting ping service for {self.config['url']} every {self.config['interval']} minutes")
        
        while not self.stop_event.is_set():
            self.ping()
            
            # Wait for the configured interval
            # Convert minutes to seconds and use small intervals to check for stop event
            for _ in range(int(self.config['interval'] * 60)):
                if self.stop_event.is_set():
                    break
                time.sleep(1)
        
        logger.info("Ping service stopped")
        self.config["is_running"] = False
    
    def start(self, url=None, interval=None):
        """
        Start the ping service.
        
        Args:
            url (str, optional): URL to ping. If None, use the current URL.
            interval (float, optional): Interval in minutes. If None, use the current interval.
        """
        if url is not None:
            self.config["url"] = url
            
        if interval is not None:
            self.config["interval"] = max(0.5, float(interval))  # Minimum interval: 30 seconds
            
        if self.thread and self.thread.is_alive():
            logger.info("Ping service already running")
            return
        
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._ping_loop)
        self.thread.daemon = True
        self.thread.start()
        self.config["is_running"] = True
        logger.info(f"Ping service started for {self.config['url']}")
        
    def stop(self):
        """
        Stop the ping service.
        """
        if not self.thread or not self.thread.is_alive():
            logger.info("No ping service running to stop")
            return
        
        self.stop_event.set()
        self.thread.join(timeout=5)
        self.config["is_running"] = False
        logger.info("Ping service stopped")
        
    def get_history(self):
        """
        Get the ping history.
        
        Returns:
            list: List of ping records
        """
        return list(self.history)
        
    def get_stats(self):
        """
        Get ping statistics.
        
        Returns:
            dict: Ping statistics
        """
        return self.stats
        
    def get_status(self):
        """
        Get the current status of the ping service.
        
        Returns:
            dict: Service status information
        """
        return {
            "status": "running" if self.config["is_running"] else "stopped",
            "config": self.config,
            "stats": self.stats
        }

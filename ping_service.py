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
from discord_webhook import DiscordWebhook, DiscordEmbed

logger = logging.getLogger(__name__)

class PingService:
    """
    Service that periodically pings a website to prevent it from going to sleep.
    """
    
    _instance = None  # Class variable to store singleton instance
    
    def __new__(cls, *args, **kwargs):
        """
        Create a new instance or return the existing one (Singleton pattern).
        This ensures that only one instance of PingService exists.
        """
        if cls._instance is None:
            cls._instance = super(PingService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self, history_size=100):
        """
        Initialize the ping service.
        
        Args:
            history_size (int): Maximum number of ping records to keep in history
        """
        # Skip initialization if already initialized (part of Singleton pattern)
        if getattr(self, "_initialized", False):
            return
            
        self.history = deque(maxlen=history_size)
        self.stats = {
            "total_pings": 0,
            "successful_pings": 0,
            "failed_pings": 0,
            "retry_pings": 0
        }
        self.config = {
            "url": "https://www.google.com",
            "interval": 5,  # minutes
            "is_running": False,
            "discord_webhook_url": "",  # Discord webhook URL for notifications
            "retry_on_failure": True,  # Whether to retry failed pings
            "max_retries": 3,  # Maximum number of retry attempts
            "retry_delay": 10,  # Delay between retries in seconds
            "send_discord_on_success": False,  # Send Discord alerts on successful pings
            "send_discord_on_failure": True  # Send Discord alerts on failed pings
        }
        self.thread = None
        self.stop_event = threading.Event()
        self._initialized = True  # Mark as initialized
        
    def send_discord_notification(self, ping_result):
        """
        Send a notification to Discord via webhook.
        
        Args:
            ping_result (dict): The result of the ping operation
        """
        if not self.config["discord_webhook_url"]:
            return
            
        try:
            webhook = DiscordWebhook(url=self.config["discord_webhook_url"])
            
            # Create embed for better formatting
            if ping_result["success"]:
                color = 0x00FF00  # Green
                title = "✅ Website Ping Successful"
            else:
                color = 0xFF0000  # Red
                title = "❌ Website Ping Failed"
                
            embed = DiscordEmbed(
                title=title,
                color=color,
                description=f"URL: {ping_result['url']}",
                timestamp=datetime.utcnow().isoformat()
            )
            
            embed.add_embed_field(name="Status Code", value=str(ping_result.get("status_code", "N/A")))
            embed.add_embed_field(name="Response Time", value=f"{ping_result.get('response_time', 0)}ms")
            
            if not ping_result["success"] and "error" in ping_result:
                embed.add_embed_field(name="Error", value=ping_result["error"])
                
            webhook.add_embed(embed)
            webhook.execute()
            logger.info(f"Discord notification sent for {ping_result['url']}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {str(e)}")
        
    def ping(self, url=None, is_retry=False):
        """
        Ping a website and record the result.
        
        Args:
            url (str, optional): URL to ping. If None, use the configured URL.
            is_retry (bool, optional): Whether this ping is a retry attempt.
            
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
                timeout=10
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
                "response_time": response_time,
                "is_retry": is_retry
            }
            
            if not is_retry:  # Only count in stats if not a retry
                self.history.appendleft(ping_entry)
                self.stats["total_pings"] += 1
                if success:
                    self.stats["successful_pings"] += 1
                    logger.info(f"Ping successful: {url} - Status: {response.status_code} - Time: {response_time}ms")
                    
                    # Send Discord notification for successful pings if enabled
                    if self.config["send_discord_on_success"]:
                        self.send_discord_notification(ping_entry)
                else:
                    self.stats["failed_pings"] += 1
                    logger.warning(f"Ping failed: {url} - Status: {response.status_code}")
                    
                    # Send Discord notification for failed pings if enabled
                    if self.config["send_discord_on_failure"]:
                        self.send_discord_notification(ping_entry)
            else:
                # This is a retry attempt
                self.stats["retry_pings"] += 1
                if success:
                    logger.info(f"Retry successful: {url} - Status: {response.status_code} - Time: {response_time}ms")
                else:
                    logger.warning(f"Retry failed: {url} - Status: {response.status_code}")
                
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
                "response_time": 0,
                "is_retry": is_retry
            }
            
            if not is_retry:  # Only count in stats if not a retry
                self.history.appendleft(ping_entry)
                self.stats["total_pings"] += 1
                self.stats["failed_pings"] += 1
                logger.error(f"Ping error: {url} - Error: {str(e)}")
                
                # Send Discord notification for errors if enabled
                if self.config["send_discord_on_failure"]:
                    self.send_discord_notification(ping_entry)
            else:
                # This is a retry attempt
                self.stats["retry_pings"] += 1
                logger.error(f"Retry error: {url} - Error: {str(e)}")
            
            return ping_entry
            
    def _ping_loop(self):
        """
        Main loop for the ping service.
        """
        logger.info(f"Starting ping service for {self.config['url']} every {self.config['interval']} minutes")
        
        while not self.stop_event.is_set():
            # Perform initial ping
            ping_result = self.ping()
            
            # If ping failed and retry is enabled, attempt retries
            if not ping_result["success"] and self.config["retry_on_failure"]:
                retry_count = 0
                while (not ping_result["success"] and 
                      retry_count < self.config["max_retries"] and 
                      not self.stop_event.is_set()):
                    # Wait for retry delay
                    logger.info(f"Waiting {self.config['retry_delay']} seconds before retry {retry_count + 1}/{self.config['max_retries']}")
                    
                    # Use small intervals to check for stop event
                    for _ in range(int(self.config['retry_delay'])):
                        if self.stop_event.is_set():
                            break
                        time.sleep(1)
                    
                    # Break the retry loop if stop event is set
                    if self.stop_event.is_set():
                        break
                        
                    # Attempt a retry
                    retry_count += 1
                    logger.info(f"Retry attempt {retry_count}/{self.config['max_retries']} for {self.config['url']}")
                    ping_result = self.ping(is_retry=True)
                    
                    # If retry succeeded, add it to history
                    if ping_result["success"]:
                        ping_result["retry_count"] = retry_count
                        self.history.appendleft(ping_result)
                        logger.info(f"Successfully recovered after {retry_count} retries")
                
                # If all retries failed, log the result
                if not ping_result["success"] and retry_count >= self.config["max_retries"]:
                    logger.error(f"All {retry_count} retry attempts failed for {self.config['url']}")
            
            # Wait for the configured interval
            # Convert minutes to seconds and use small intervals to check for stop event
            for _ in range(int(self.config['interval'] * 60)):
                if self.stop_event.is_set():
                    break
                time.sleep(1)
        
        logger.info("Ping service stopped")
        self.config["is_running"] = False
    
    def start(self, url=None, interval=None, **kwargs):
        """
        Start the ping service.
        
        Args:
            url (str, optional): URL to ping. If None, use the current URL.
            interval (float, optional): Interval in minutes. If None, use the current interval.
            **kwargs: Additional configuration options including:
                - discord_webhook_url: URL for Discord webhook notifications
                - retry_on_failure: Whether to retry failed pings
                - max_retries: Maximum number of retry attempts
                - retry_delay: Seconds to wait between retries
                - send_discord_on_success: Send Discord alerts on successful pings
                - send_discord_on_failure: Send Discord alerts on failed pings
        """
        if url is not None:
            self.config["url"] = url
            
        if interval is not None:
            self.config["interval"] = max(0.5, float(interval))  # Minimum interval: 30 seconds
            
        # Update other configuration options if provided
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"Updated configuration: {key}={value}")
            
        if self.thread and self.thread.is_alive():
            logger.info("Ping service already running")
            return
        
        # Log configuration summary
        config_summary = {
            "url": self.config["url"],
            "interval": self.config["interval"],
            "retry_on_failure": self.config["retry_on_failure"],
            "max_retries": self.config["max_retries"],
            "retry_delay": self.config["retry_delay"],
            "discord_webhook_enabled": bool(self.config["discord_webhook_url"])
        }
        logger.info(f"Starting ping service with configuration: {config_summary}")
        
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

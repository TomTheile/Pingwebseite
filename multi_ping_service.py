"""
Multi-Ping Service Module
This module contains the core functionality for the website ping service with multiple target support.
"""
import logging
import threading
import time
import uuid
from collections import deque
from datetime import datetime

import requests
from discord_webhook import DiscordEmbed, DiscordWebhook

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PingTarget:
    """
    A class representing a website target to be pinged.
    Each target has its own configuration, history, and statistics.
    """
    
    def __init__(self, url, interval=5, history_size=100, **kwargs):
        """
        Initialize a ping target.
        
        Args:
            url (str): The URL to ping
            interval (float): Interval between pings in minutes
            history_size (int): Maximum number of ping records to keep in history
            **kwargs: Additional configuration options
        """
        self.id = str(uuid.uuid4())
        self.history = deque(maxlen=history_size)
        self.stats = {
            "total_pings": 0,
            "successful_pings": 0,
            "failed_pings": 0,
            "retry_pings": 0
        }
        
        self.config = {
            "url": url,
            "interval": interval,  # minutes
            "is_running": False,
            "discord_webhook_url": kwargs.get("discord_webhook_url", ""),
            "retry_on_failure": kwargs.get("retry_on_failure", True),
            "max_retries": kwargs.get("max_retries", 3),
            "retry_delay": kwargs.get("retry_delay", 10),
            "send_discord_on_success": kwargs.get("send_discord_on_success", False),
            "send_discord_on_failure": kwargs.get("send_discord_on_failure", True)
        }
        
        self.thread = None
        self.stop_event = threading.Event()
    
    def to_dict(self):
        """Convert target to dictionary representation"""
        return {
            "id": self.id,
            "url": self.config["url"],
            "interval": self.config["interval"],
            "is_running": self.config["is_running"],
            "stats": self.stats,
            "config": self.config
        }
    
    def add_history_entry(self, entry):
        """Add an entry to the history"""
        self.history.appendleft(entry)
    
    def update_stats(self, success, is_retry=False):
        """Update statistics based on ping result"""
        self.stats["total_pings"] += 0 if is_retry else 1
        
        if is_retry:
            self.stats["retry_pings"] += 1
            return
            
        if success:
            self.stats["successful_pings"] += 1
        else:
            self.stats["failed_pings"] += 1

class MultiPingService:
    """
    Service that periodically pings multiple websites to prevent them from going to sleep.
    """
    
    _instance = None  # Class variable to store singleton instance
    
    def __new__(cls, *args, **kwargs):
        """
        Create a new instance or return the existing one (Singleton pattern).
        This ensures that only one instance of MultiPingService exists.
        """
        if cls._instance is None:
            cls._instance = super(MultiPingService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        """Initialize the ping service."""
        # Skip initialization if already initialized (part of Singleton pattern)
        if getattr(self, "_initialized", False):
            return
            
        # Dictionary to store all ping targets, keyed by their ID
        self.targets = {}
        
        # For backward compatibility - add a default target
        default_target = PingTarget(
            url="https://www.google.com",
            interval=5
        )
        self.targets[default_target.id] = default_target
        
        self._initialized = True  # Mark as initialized
        
    def send_discord_notification(self, target, ping_result):
        """
        Send a notification to Discord via webhook.
        
        Args:
            target (PingTarget): The target being pinged
            ping_result (dict): The result of the ping operation
        """
        if not target.config["discord_webhook_url"]:
            return
            
        try:
            webhook = DiscordWebhook(url=target.config["discord_webhook_url"])
            
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
        
    def ping(self, target_id=None, url=None, is_retry=False):
        """
        Ping a website and record the result.
        
        Args:
            target_id (str, optional): ID of the target to ping
            url (str, optional): URL to ping. If None, use the target's configured URL.
            is_retry (bool, optional): Whether this ping is a retry attempt.
            
        Returns:
            dict: Ping result information
        """
        # If no target_id specified but URL is specified, find the first target with that URL
        if target_id is None and url is not None:
            for tid, target in self.targets.items():
                if target.config["url"] == url:
                    target_id = tid
                    break
                    
        # If no target with the URL found, use the first target
        if target_id is None:
            if not self.targets:
                return {"success": False, "error": "No ping targets configured"}
            target_id = next(iter(self.targets))
            
        # Get the target
        target = self.targets.get(target_id)
        if not target:
            return {"success": False, "error": f"Target with ID {target_id} not found"}
            
        # Use the target's URL if none specified
        if url is None:
            url = target.config["url"]
            
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
                "target_id": target_id,
                "status_code": response.status_code,
                "success": success,
                "response_time": response_time,
                "is_retry": is_retry
            }
            
            # Update stats and history
            target.update_stats(success, is_retry)
            
            if not is_retry:
                target.add_history_entry(ping_entry)
                logger.info(f"Ping successful: {url} - Status: {response.status_code} - Time: {response_time}ms")
                
                # Send Discord notification for successful pings if enabled
                if success and target.config["send_discord_on_success"]:
                    self.send_discord_notification(target, ping_entry)
                elif not success and target.config["send_discord_on_failure"]:
                    self.send_discord_notification(target, ping_entry)
            else:
                # This is a retry attempt
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
                "target_id": target_id,
                "status_code": 0,
                "success": False,
                "error": str(e),
                "response_time": 0,
                "is_retry": is_retry
            }
            
            # Update stats and history
            target.update_stats(False, is_retry)
            
            if not is_retry:
                target.add_history_entry(ping_entry)
                logger.error(f"Ping error: {url} - Error: {str(e)}")
                
                # Send Discord notification for errors if enabled
                if target.config["send_discord_on_failure"]:
                    self.send_discord_notification(target, ping_entry)
            else:
                # This is a retry attempt
                logger.error(f"Retry error: {url} - Error: {str(e)}")
            
            return ping_entry
            
    def _ping_loop(self, target_id):
        """
        Main loop for pinging a specific target.
        
        Args:
            target_id (str): ID of the target to ping
        """
        target = self.targets.get(target_id)
        if not target:
            logger.error(f"Target with ID {target_id} not found, cannot start ping loop")
            return
            
        logger.info(f"Starting ping service for {target.config['url']} every {target.config['interval']} minutes")
        
        while not target.stop_event.is_set():
            # Perform initial ping
            ping_result = self.ping(target_id=target_id)
            
            # If ping failed and retry is enabled, attempt retries
            if not ping_result["success"] and target.config["retry_on_failure"]:
                retry_count = 0
                while (not ping_result["success"] and 
                      retry_count < target.config["max_retries"] and 
                      not target.stop_event.is_set()):
                    # Wait for retry delay
                    logger.info(f"Waiting {target.config['retry_delay']} seconds before retry {retry_count + 1}/{target.config['max_retries']}")
                    
                    # Use small intervals to check for stop event
                    for _ in range(int(target.config['retry_delay'])):
                        if target.stop_event.is_set():
                            break
                        time.sleep(1)
                    
                    # Break the retry loop if stop event is set
                    if target.stop_event.is_set():
                        break
                        
                    # Attempt a retry
                    retry_count += 1
                    logger.info(f"Retry attempt {retry_count}/{target.config['max_retries']} for {target.config['url']}")
                    ping_result = self.ping(target_id=target_id, is_retry=True)
                    
                    # If retry succeeded, add it to history
                    if ping_result["success"]:
                        ping_result["retry_count"] = retry_count
                        target.add_history_entry(ping_result)
                        logger.info(f"Successfully recovered after {retry_count} retries")
                
                # If all retries failed, log the result
                if not ping_result["success"] and retry_count >= target.config["max_retries"]:
                    logger.error(f"All {retry_count} retry attempts failed for {target.config['url']}")
            
            # Wait for the configured interval
            # Convert minutes to seconds and use small intervals to check for stop event
            for _ in range(int(target.config['interval'] * 60)):
                if target.stop_event.is_set():
                    break
                time.sleep(1)
        
        logger.info(f"Ping service stopped for {target.config['url']}")
        target.config["is_running"] = False
    
    def add_target(self, url, interval=5, **kwargs):
        """
        Add a new website target to ping.
        
        Args:
            url (str): URL to ping
            interval (float): Interval in minutes
            **kwargs: Additional configuration options
            
        Returns:
            str: ID of the newly created target
        """
        target = PingTarget(url=url, interval=interval, **kwargs)
        self.targets[target.id] = target
        logger.info(f"Added new ping target: {url}")
        return target.id
        
    def remove_target(self, target_id):
        """
        Remove a ping target.
        
        Args:
            target_id (str): ID of the target to remove
            
        Returns:
            bool: True if target was removed, False otherwise
        """
        if target_id not in self.targets:
            return False
            
        # Stop the target if it's running
        target = self.targets[target_id]
        if target.config["is_running"]:
            self.stop_target(target_id)
            
        # Remove the target
        del self.targets[target_id]
        logger.info(f"Removed ping target: {target.config['url']}")
        return True
    
    def start_target(self, target_id, url=None, interval=None, **kwargs):
        """
        Start pinging a specific target.
        
        Args:
            target_id (str): ID of the target to start
            url (str, optional): New URL to use. If None, use the current URL.
            interval (float, optional): New interval to use. If None, use the current interval.
            **kwargs: Additional configuration options
            
        Returns:
            bool: True if target was started, False otherwise
        """
        target = self.targets.get(target_id)
        if not target:
            logger.error(f"Target with ID {target_id} not found")
            return False
            
        # Update configuration if provided
        if url is not None:
            target.config["url"] = url
            
        if interval is not None:
            target.config["interval"] = max(0.5, float(interval))  # Minimum interval: 30 seconds
            
        # Update other configuration options if provided
        for key, value in kwargs.items():
            if key in target.config:
                target.config[key] = value
                logger.info(f"Updated configuration for {target.config['url']}: {key}={value}")
            
        if target.thread and target.thread.is_alive():
            logger.info(f"Ping service already running for {target.config['url']}")
            return True
        
        # Log configuration summary
        config_summary = {
            "url": target.config["url"],
            "interval": target.config["interval"],
            "retry_on_failure": target.config["retry_on_failure"],
            "max_retries": target.config["max_retries"],
            "retry_delay": target.config["retry_delay"],
            "discord_webhook_enabled": bool(target.config["discord_webhook_url"])
        }
        logger.info(f"Starting ping service for {target.config['url']} with configuration: {config_summary}")
        
        target.stop_event.clear()
        target.thread = threading.Thread(target=self._ping_loop, args=(target_id,))
        target.thread.daemon = True
        target.thread.start()
        target.config["is_running"] = True
        logger.info(f"Ping service started for {target.config['url']}")
        return True
        
    def stop_target(self, target_id):
        """
        Stop pinging a specific target.
        
        Args:
            target_id (str): ID of the target to stop
            
        Returns:
            bool: True if target was stopped, False otherwise
        """
        target = self.targets.get(target_id)
        if not target:
            logger.error(f"Target with ID {target_id} not found")
            return False
            
        if not target.thread or not target.thread.is_alive():
            logger.info(f"No ping service running for {target.config['url']}")
            return False
        
        target.stop_event.set()
        target.thread.join(timeout=5)
        target.config["is_running"] = False
        logger.info(f"Ping service stopped for {target.config['url']}")
        return True
        
    def get_target_history(self, target_id):
        """
        Get the ping history for a specific target.
        
        Args:
            target_id (str): ID of the target
            
        Returns:
            list: List of ping records for the target
        """
        target = self.targets.get(target_id)
        if not target:
            return []
            
        return list(target.history)
        
    def get_all_history(self):
        """
        Get ping history for all targets.
        
        Returns:
            list: Combined list of ping records from all targets
        """
        all_history = []
        for target_id, target in self.targets.items():
            history = list(target.history)
            all_history.extend(history)
            
        # Sort by timestamp, newest first
        all_history.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_history
        
    def get_target_stats(self, target_id):
        """
        Get ping statistics for a specific target.
        
        Args:
            target_id (str): ID of the target
            
        Returns:
            dict: Ping statistics for the target
        """
        target = self.targets.get(target_id)
        if not target:
            return {}
            
        return target.stats
        
    def get_target_status(self, target_id):
        """
        Get the current status of a specific target.
        
        Args:
            target_id (str): ID of the target
            
        Returns:
            dict: Service status information for the target
        """
        target = self.targets.get(target_id)
        if not target:
            return {}
            
        return {
            "id": target_id,
            "status": "running" if target.config["is_running"] else "stopped",
            "config": target.config,
            "stats": target.stats
        }
        
    def get_all_targets(self):
        """
        Get information about all targets.
        
        Returns:
            list: List of target information dictionaries
        """
        return [self.get_target_status(target_id) for target_id in self.targets.keys()]

    # Legacy methods for backward compatibility
    
    def start(self, url=None, interval=None, **kwargs):
        """
        Start the ping service for the default target (legacy method).
        
        Args:
            url (str, optional): URL to ping. If None, use the current URL.
            interval (float, optional): Interval in minutes. If None, use the current interval.
            **kwargs: Additional configuration options
        """
        # Use the first target by default
        if not self.targets:
            self.add_target(url or "https://www.google.com", interval or 5, **kwargs)
            target_id = next(iter(self.targets))
        else:
            target_id = next(iter(self.targets))
        
        self.start_target(target_id, url, interval, **kwargs)
        
    def stop(self):
        """
        Stop the ping service for the default target (legacy method).
        """
        # Use the first target by default
        if not self.targets:
            return
            
        target_id = next(iter(self.targets))
        self.stop_target(target_id)
        
    def get_history(self):
        """
        Get ping history (legacy method).
        
        Returns:
            list: Combined ping history from all targets
        """
        return self.get_all_history()
        
    def get_stats(self):
        """
        Get ping statistics (legacy method).
        
        Returns:
            dict: Ping statistics from the first target
        """
        if not self.targets:
            return {
                "total_pings": 0,
                "successful_pings": 0,
                "failed_pings": 0,
                "retry_pings": 0
            }
            
        target_id = next(iter(self.targets))
        return self.get_target_stats(target_id)
        
    # Legacy property for backward compatibility
    @property
    def config(self):
        """Legacy property for backward compatibility"""
        if not self.targets:
            return {
                "url": "https://www.google.com",
                "interval": 5,
                "is_running": False,
                "discord_webhook_url": "",
                "retry_on_failure": True,
                "max_retries": 3,
                "retry_delay": 10,
                "send_discord_on_success": False,
                "send_discord_on_failure": True
            }
        
        target_id = next(iter(self.targets))
        return self.targets[target_id].config
    
    def get_status(self):
        """
        Get the current status (legacy method).
        
        Returns:
            dict: Service status information from the first target
        """
        if not self.targets:
            return {
                "status": "stopped",
                "config": self.config,
                "stats": {
                    "total_pings": 0,
                    "successful_pings": 0,
                    "failed_pings": 0,
                    "retry_pings": 0
                }
            }
            
        target_id = next(iter(self.targets))
        return self.get_target_status(target_id)
import os
import logging
import threading
import time
from datetime import datetime
from collections import deque
import json

from flask import Flask, render_template, request, jsonify
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# In-memory storage for ping history (limited to last 100 entries)
ping_history = deque(maxlen=100)
ping_stats = {
    "total_pings": 0,
    "successful_pings": 0,
    "failed_pings": 0
}

# Configuration
ping_config = {
    "url": "https://www.google.com",  # Default URL to ping
    "interval": 5,  # Default interval in minutes
    "is_running": False  # Flag to check if the ping service is running
}

# Thread for background pinging
ping_thread = None
stop_event = threading.Event()

def ping_website():
    """
    Function to ping the website at the configured interval
    """
    logger.info(f"Starting ping service for {ping_config['url']} every {ping_config['interval']} minutes")
    
    while not stop_event.is_set():
        try:
            # Send ping request
            start_time = time.time()
            response = requests.get(
                ping_config['url'], 
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
                "url": ping_config['url'],
                "status_code": response.status_code,
                "success": success,
                "response_time": response_time
            }
            
            ping_history.appendleft(ping_entry)
            ping_stats["total_pings"] += 1
            if success:
                ping_stats["successful_pings"] += 1
                logger.info(f"Ping successful: {ping_config['url']} - Status: {response.status_code} - Time: {response_time}ms")
            else:
                ping_stats["failed_pings"] += 1
                logger.warning(f"Ping failed: {ping_config['url']} - Status: {response.status_code}")
                
        except Exception as e:
            # Handle connection errors
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ping_entry = {
                "timestamp": timestamp,
                "url": ping_config['url'],
                "status_code": 0,
                "success": False,
                "error": str(e),
                "response_time": 0
            }
            ping_history.appendleft(ping_entry)
            ping_stats["total_pings"] += 1
            ping_stats["failed_pings"] += 1
            logger.error(f"Ping error: {ping_config['url']} - Error: {str(e)}")
        
        # Wait for the configured interval
        # Convert minutes to seconds and use small intervals to check for stop event
        for _ in range(int(ping_config['interval'] * 60)):
            if stop_event.is_set():
                break
            time.sleep(1)
    
    logger.info("Ping service stopped")

def start_ping_service():
    """
    Start the ping service in a background thread
    """
    global ping_thread, stop_event
    
    if ping_thread and ping_thread.is_alive():
        logger.info("Ping service already running")
        return
    
    stop_event.clear()
    ping_thread = threading.Thread(target=ping_website)
    ping_thread.daemon = True
    ping_thread.start()
    ping_config["is_running"] = True
    logger.info(f"Ping service started for {ping_config['url']}")

def stop_ping_service():
    """
    Stop the ping service
    """
    global ping_thread, stop_event
    
    if not ping_thread or not ping_thread.is_alive():
        logger.info("No ping service running to stop")
        return
    
    stop_event.set()
    ping_thread.join(timeout=5)
    ping_config["is_running"] = False
    logger.info("Ping service stopped")

@app.route('/')
def index():
    """
    Main page that displays the ping service UI
    """
    return render_template('index.html', config=ping_config)

@app.route('/api/start', methods=['POST'])
def api_start():
    """
    API endpoint to start the ping service
    """
    data = request.json
    if 'url' in data:
        ping_config['url'] = data['url']
    if 'interval' in data:
        try:
            interval = float(data['interval'])
            if interval < 0.5:
                interval = 0.5  # Minimum interval of 30 seconds
            ping_config['interval'] = interval
        except ValueError:
            return jsonify({"error": "Invalid interval value"}), 400
    
    start_ping_service()
    return jsonify({"status": "success", "message": "Ping service started", "config": ping_config})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """
    API endpoint to stop the ping service
    """
    stop_ping_service()
    return jsonify({"status": "success", "message": "Ping service stopped", "config": ping_config})

@app.route('/api/status', methods=['GET'])
def api_status():
    """
    API endpoint to get the current status of the ping service
    """
    return jsonify({
        "status": "running" if ping_config["is_running"] else "stopped",
        "config": ping_config,
        "stats": ping_stats
    })

@app.route('/api/history', methods=['GET'])
def api_history():
    """
    API endpoint to get the ping history
    """
    return jsonify(list(ping_history))

@app.route('/api/ping_now', methods=['POST'])
def api_ping_now():
    """
    API endpoint to trigger an immediate ping
    """
    data = request.json
    url = data.get('url', ping_config['url'])
    
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
        
        ping_history.appendleft(ping_entry)
        ping_stats["total_pings"] += 1
        if success:
            ping_stats["successful_pings"] += 1
        else:
            ping_stats["failed_pings"] += 1
            
        return jsonify({
            "status": "success",
            "message": "Ping sent",
            "result": ping_entry
        })
        
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ping_entry = {
            "timestamp": timestamp,
            "url": url,
            "status_code": 0,
            "success": False,
            "error": str(e),
            "response_time": 0
        }
        ping_history.appendleft(ping_entry)
        ping_stats["total_pings"] += 1
        ping_stats["failed_pings"] += 1
        
        return jsonify({
            "status": "error",
            "message": f"Error pinging website: {str(e)}",
            "result": ping_entry
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

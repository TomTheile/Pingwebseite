import os
import secrets
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.security import check_password_hash

from forms import LoginForm
from multi_ping_service import MultiPingService
from user import User

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(16))

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Initialize ping service
ping_service = MultiPingService()

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login page
    """
    if current_user.is_authenticated:
        return redirect(url_for("index"))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember_me.data
        
        user = User.find_by_username(username)
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get("next", url_for("index"))
            return redirect(next_page)
        else:
            flash("Invalid username or password", "danger")
    
    return render_template("login.html", form=form, title="Login")

@app.route("/logout")
@login_required
def logout():
    """
    Logout route
    """
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    """
    Main page that displays the ping service UI
    """
    return render_template("index_multi.html", title="Website Ping Service")

# API Endpoints for Multiple Targets

@app.route('/api/targets', methods=['GET'])
@login_required
def api_get_targets():
    """
    API endpoint to get all ping targets
    """
    return jsonify(ping_service.get_all_targets())

@app.route('/api/targets', methods=['POST'])
@login_required
def api_add_target():
    """
    API endpoint to add a new ping target
    """
    data = request.json
    url = data.get('url')
    interval = data.get('interval', 5)
    
    if not url:
        return jsonify({"status": "error", "message": "URL is required"}), 400
    
    # Extract additional configuration options
    kwargs = {}
    
    if 'discord_webhook_url' in data:
        kwargs['discord_webhook_url'] = data['discord_webhook_url']
    
    if 'retry_on_failure' in data:
        kwargs['retry_on_failure'] = bool(data['retry_on_failure'])
    
    if 'max_retries' in data:
        kwargs['max_retries'] = int(data['max_retries'])
    
    if 'retry_delay' in data:
        kwargs['retry_delay'] = int(data['retry_delay'])
    
    if 'send_discord_on_success' in data:
        kwargs['send_discord_on_success'] = bool(data['send_discord_on_success'])
    
    if 'send_discord_on_failure' in data:
        kwargs['send_discord_on_failure'] = bool(data['send_discord_on_failure'])
    
    # Add the target
    target_id = ping_service.add_target(url=url, interval=interval, **kwargs)
    
    return jsonify({
        "status": "success", 
        "message": "Target added successfully", 
        "target_id": target_id,
        "target": ping_service.get_target_status(target_id)
    })

@app.route('/api/targets/<target_id>', methods=['GET'])
@login_required
def api_get_target(target_id):
    """
    API endpoint to get information about a specific target
    """
    target_status = ping_service.get_target_status(target_id)
    
    if not target_status:
        return jsonify({"status": "error", "message": f"Target with ID {target_id} not found"}), 404
        
    return jsonify(target_status)

@app.route('/api/targets/<target_id>', methods=['DELETE'])
@login_required
def api_remove_target(target_id):
    """
    API endpoint to remove a ping target
    """
    success = ping_service.remove_target(target_id)
    
    if not success:
        return jsonify({"status": "error", "message": f"Target with ID {target_id} not found"}), 404
        
    return jsonify({"status": "success", "message": "Target removed successfully"})

@app.route('/api/targets/<target_id>/start', methods=['POST'])
@login_required
def api_start_target(target_id):
    """
    API endpoint to start a ping target
    """
    data = request.json or {}
    url = data.get('url')
    interval = data.get('interval')
    
    # Extract additional configuration options
    kwargs = {}
    
    if 'discord_webhook_url' in data:
        kwargs['discord_webhook_url'] = data['discord_webhook_url']
    
    if 'retry_on_failure' in data:
        kwargs['retry_on_failure'] = bool(data['retry_on_failure'])
    
    if 'max_retries' in data:
        kwargs['max_retries'] = int(data['max_retries'])
    
    if 'retry_delay' in data:
        kwargs['retry_delay'] = int(data['retry_delay'])
    
    if 'send_discord_on_success' in data:
        kwargs['send_discord_on_success'] = bool(data['send_discord_on_success'])
    
    if 'send_discord_on_failure' in data:
        kwargs['send_discord_on_failure'] = bool(data['send_discord_on_failure'])
    
    # Start the target
    success = ping_service.start_target(target_id, url=url, interval=interval, **kwargs)
    
    if not success:
        return jsonify({"status": "error", "message": f"Failed to start target with ID {target_id}"}), 404
        
    return jsonify({
        "status": "success", 
        "message": "Target started successfully", 
        "target": ping_service.get_target_status(target_id)
    })

@app.route('/api/targets/<target_id>/stop', methods=['POST'])
@login_required
def api_stop_target(target_id):
    """
    API endpoint to stop a ping target
    """
    success = ping_service.stop_target(target_id)
    
    if not success:
        return jsonify({"status": "error", "message": f"Failed to stop target with ID {target_id}"}), 404
        
    return jsonify({
        "status": "success", 
        "message": "Target stopped successfully", 
        "target": ping_service.get_target_status(target_id)
    })

@app.route('/api/targets/<target_id>/history', methods=['GET'])
@login_required
def api_get_target_history(target_id):
    """
    API endpoint to get the ping history for a specific target
    """
    history = ping_service.get_target_history(target_id)
    return jsonify(history)

@app.route('/api/targets/<target_id>/ping', methods=['POST'])
@login_required
def api_ping_target(target_id):
    """
    API endpoint to ping a specific target immediately
    """
    data = request.json or {}
    url = data.get('url')
    
    try:
        # Send a ping using the ping service
        ping_result = ping_service.ping(target_id=target_id, url=url)
        
        if "error" in ping_result and not ping_result.get("success", False):
            return jsonify({
                "status": "error",
                "message": ping_result["error"],
                "result": ping_result
            }), 400
        
        return jsonify({
            "status": "success",
            "message": "Ping sent",
            "result": ping_result
        })
        
    except Exception as e:
        logger.exception(f"Error in api_ping_target: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error pinging website: {str(e)}"
        }), 500

@app.route('/api/history', methods=['GET'])
@login_required
def api_history():
    """
    API endpoint to get the ping history for all targets
    """
    return jsonify(ping_service.get_all_history())

# Legacy API Endpoints for Backward Compatibility

@app.route('/api/start', methods=['POST'])
@login_required
def api_start():
    """
    API endpoint to start the ping service (legacy method)
    """
    data = request.json
    url = data.get('url')
    interval = data.get('interval')
    
    # Extract additional configuration options
    kwargs = {}
    
    if 'discord_webhook_url' in data:
        kwargs['discord_webhook_url'] = data['discord_webhook_url']
    
    if 'retry_on_failure' in data:
        kwargs['retry_on_failure'] = bool(data['retry_on_failure'])
    
    if 'max_retries' in data:
        kwargs['max_retries'] = int(data['max_retries'])
    
    if 'retry_delay' in data:
        kwargs['retry_delay'] = int(data['retry_delay'])
    
    if 'send_discord_on_success' in data:
        kwargs['send_discord_on_success'] = bool(data['send_discord_on_success'])
    
    if 'send_discord_on_failure' in data:
        kwargs['send_discord_on_failure'] = bool(data['send_discord_on_failure'])
    
    # Start the ping service with the provided configuration
    ping_service.start(url=url, interval=interval, **kwargs)
    
    return jsonify({
        "status": "success", 
        "message": "Ping service started", 
        "config": ping_service.get_status()['config']
    })

@app.route('/api/stop', methods=['POST'])
@login_required
def api_stop():
    """
    API endpoint to stop the ping service (legacy method)
    """
    ping_service.stop()
    return jsonify({
        "status": "success", 
        "message": "Ping service stopped", 
        "config": ping_service.get_status()['config']
    })

@app.route('/api/status', methods=['GET'])
@login_required
def api_status():
    """
    API endpoint to get the current status of the ping service (legacy method)
    """
    return jsonify(ping_service.get_status())

@app.route('/api/ping_now', methods=['POST'])
@login_required
def api_ping_now():
    """
    API endpoint to trigger an immediate ping (legacy method)
    """
    data = request.json
    url = data.get('url')
    
    try:
        # Send a ping using the ping service
        ping_result = ping_service.ping(url=url)
        
        return jsonify({
            "status": "success",
            "message": "Ping sent",
            "result": ping_result
        })
        
    except Exception as e:
        logger.exception(f"Error in api_ping_now: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error pinging website: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
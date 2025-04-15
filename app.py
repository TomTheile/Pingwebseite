import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from multi_ping_service import MultiPingService
from user import User
from forms import LoginForm

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create ping service instance
ping_service = MultiPingService()

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_username(form.username.data)
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """
    Logout route
    """
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """
    Main page that displays the ping service UI
    """
    return render_template('index.html', config=ping_service.config)

@app.route('/api/start', methods=['POST'])
@login_required
def api_start():
    """
    API endpoint to start the ping service
    """
    data = request.json
    kwargs = {}
    
    # Extract configuration parameters
    url = data.get('url')
    interval = None
    
    if 'interval' in data:
        try:
            interval = float(data['interval'])
            if interval < 0.5:
                interval = 0.5  # Minimum interval of 30 seconds
        except ValueError:
            return jsonify({"error": "Invalid interval value"}), 400
    
    # Extract additional configuration options
    if 'discord_webhook_url' in data:
        kwargs['discord_webhook_url'] = data['discord_webhook_url']
    
    if 'retry_on_failure' in data:
        kwargs['retry_on_failure'] = data['retry_on_failure']
    
    if 'max_retries' in data:
        try:
            kwargs['max_retries'] = int(data['max_retries'])
        except ValueError:
            return jsonify({"error": "Invalid max_retries value"}), 400
    
    if 'retry_delay' in data:
        try:
            kwargs['retry_delay'] = int(data['retry_delay'])
        except ValueError:
            return jsonify({"error": "Invalid retry_delay value"}), 400
    
    if 'send_discord_on_success' in data:
        kwargs['send_discord_on_success'] = bool(data['send_discord_on_success'])
    
    if 'send_discord_on_failure' in data:
        kwargs['send_discord_on_failure'] = bool(data['send_discord_on_failure'])
    

    
    # Start the ping service with the provided configuration
    ping_service.start(url=url, interval=interval, **kwargs)
    
    return jsonify({
        "status": "success", 
        "message": "Ping service started", 
        "config": ping_service.config
    })

@app.route('/api/stop', methods=['POST'])
@login_required
def api_stop():
    """
    API endpoint to stop the ping service
    """
    ping_service.stop()
    return jsonify({
        "status": "success", 
        "message": "Ping service stopped", 
        "config": ping_service.config
    })

@app.route('/api/status', methods=['GET'])
@login_required
def api_status():
    """
    API endpoint to get the current status of the ping service
    """
    return jsonify(ping_service.get_status())

@app.route('/api/history', methods=['GET'])
@login_required
def api_history():
    """
    API endpoint to get the ping history
    """
    return jsonify(ping_service.get_history())

@app.route('/api/ping_now', methods=['POST'])
@login_required
def api_ping_now():
    """
    API endpoint to trigger an immediate ping
    """
    data = request.json
    url = data.get('url', ping_service.config['url'])
    
    try:
        # Send a ping using the ping service
        ping_result = ping_service.ping(url)
        
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

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const urlInput = document.getElementById('urlInput');
    const intervalInput = document.getElementById('intervalInput');
    const userAgentInput = document.getElementById('userAgentInput');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const pingNowBtn = document.getElementById('pingNowBtn');
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');
    const statusBadge = document.getElementById('statusBadge');
    const totalPings = document.getElementById('totalPings');
    const successfulPings = document.getElementById('successfulPings');
    const failedPings = document.getElementById('failedPings');
    const historyTableBody = document.getElementById('historyTableBody');

    // Initialize the UI
    getStatus();
    getHistory();

    // Set up auto-refresh for status and history (every 30 seconds)
    setInterval(() => {
        getStatus();
        getHistory();
    }, 30000);

    // Event Listeners
    startBtn.addEventListener('click', startPinging);
    stopBtn.addEventListener('click', stopPinging);
    pingNowBtn.addEventListener('click', pingNow);
    refreshHistoryBtn.addEventListener('click', getHistory);

    // Functions
    async function getStatus() {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) {
                throw new Error('Failed to get status');
            }
            
            const data = await response.json();
            updateStatusUI(data);
        } catch (error) {
            console.error('Error getting status:', error);
            showAlert('Error getting status: ' + error.message, 'danger');
        }
    }

    async function getHistory() {
        try {
            const response = await fetch('/api/history');
            if (!response.ok) {
                throw new Error('Failed to get history');
            }
            
            const data = await response.json();
            updateHistoryUI(data);
        } catch (error) {
            console.error('Error getting history:', error);
            showAlert('Error getting history: ' + error.message, 'danger');
        }
    }

    async function startPinging() {
        // Validate inputs
        const url = urlInput.value.trim();
        const interval = parseFloat(intervalInput.value);
        const userAgent = userAgentInput.value.trim();
        
        // Get advanced options
        const retryOnFailure = document.getElementById('retryOnFailureSwitch').checked;
        const maxRetries = parseInt(document.getElementById('maxRetriesInput').value) || 3;
        const retryDelay = parseInt(document.getElementById('retryDelayInput').value) || 10;
        
        // Get notification options
        const discordWebhookUrl = document.getElementById('discordWebhookInput').value.trim();
        const sendDiscordOnSuccess = document.getElementById('discordOnSuccessSwitch').checked;
        const sendDiscordOnFailure = document.getElementById('discordOnFailureSwitch').checked;

        if (!url) {
            showAlert('Please enter a valid URL', 'warning');
            return;
        }

        if (isNaN(interval) || interval < 0.5) {
            showAlert('Interval must be at least 0.5 minutes', 'warning');
            return;
        }
        
        // Create request body with all configuration options
        const requestBody = {
            url: url,
            interval: interval,
            user_agent: userAgent,
            retry_on_failure: retryOnFailure,
            max_retries: maxRetries,
            retry_delay: retryDelay,
            discord_webhook_url: discordWebhookUrl,
            send_discord_on_success: sendDiscordOnSuccess,
            send_discord_on_failure: sendDiscordOnFailure
        };

        try {
            startBtn.disabled = true;
            startBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';
            
            const response = await fetch('/api/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error('Failed to start ping service');
            }

            const data = await response.json();
            showAlert('Ping service started successfully', 'success');
            getStatus();
        } catch (error) {
            console.error('Error starting ping service:', error);
            showAlert('Error starting ping service: ' + error.message, 'danger');
        } finally {
            startBtn.disabled = false;
            startBtn.innerHTML = '<i class="bi bi-play-fill"></i> Start Pinging';
        }
    }

    async function stopPinging() {
        try {
            const response = await fetch('/api/stop', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to stop ping service');
            }

            const data = await response.json();
            showAlert('Ping service stopped successfully', 'success');
            getStatus();
        } catch (error) {
            console.error('Error stopping ping service:', error);
            showAlert('Error stopping ping service: ' + error.message, 'danger');
        }
    }

    async function pingNow() {
        const url = urlInput.value.trim();
        if (!url) {
            showAlert('Please enter a valid URL', 'warning');
            return;
        }

        try {
            pingNowBtn.disabled = true;
            pingNowBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Pinging...';
            
            const response = await fetch('/api/ping_now', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url
                })
            });

            if (!response.ok) {
                throw new Error('Failed to ping website');
            }

            const data = await response.json();
            showAlert('Website pinged successfully', 'success');
            getStatus();
            getHistory();
        } catch (error) {
            console.error('Error pinging website:', error);
            showAlert('Error pinging website: ' + error.message, 'danger');
        } finally {
            pingNowBtn.disabled = false;
            pingNowBtn.innerHTML = '<i class="bi bi-send"></i> Ping Now';
        }
    }

    function updateStatusUI(data) {
        // Update status badge
        if (data.status === 'running') {
            statusBadge.textContent = 'Running';
            statusBadge.className = 'badge rounded-pill bg-success';
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            statusBadge.textContent = 'Stopped';
            statusBadge.className = 'badge rounded-pill bg-danger';
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }

        // Update basic config values
        urlInput.value = data.config.url;
        intervalInput.value = data.config.interval;
        
        // Update User Agent
        const userAgentInput = document.getElementById('userAgentInput');
        if (userAgentInput && data.config.user_agent) {
            userAgentInput.value = data.config.user_agent;
        }
        
        // Update advanced settings
        const retryOnFailureSwitch = document.getElementById('retryOnFailureSwitch');
        if (retryOnFailureSwitch) {
            retryOnFailureSwitch.checked = data.config.retry_on_failure;
        }
        
        const maxRetriesInput = document.getElementById('maxRetriesInput');
        if (maxRetriesInput && data.config.max_retries) {
            maxRetriesInput.value = data.config.max_retries;
        }
        
        const retryDelayInput = document.getElementById('retryDelayInput');
        if (retryDelayInput && data.config.retry_delay) {
            retryDelayInput.value = data.config.retry_delay;
        }
        
        // Update notification settings
        const discordWebhookInput = document.getElementById('discordWebhookInput');
        if (discordWebhookInput && data.config.discord_webhook_url) {
            discordWebhookInput.value = data.config.discord_webhook_url;
        }
        
        const discordOnSuccessSwitch = document.getElementById('discordOnSuccessSwitch');
        if (discordOnSuccessSwitch) {
            discordOnSuccessSwitch.checked = data.config.send_discord_on_success;
        }
        
        const discordOnFailureSwitch = document.getElementById('discordOnFailureSwitch');
        if (discordOnFailureSwitch) {
            discordOnFailureSwitch.checked = data.config.send_discord_on_failure;
        }

        // Update stats
        totalPings.textContent = data.stats.total_pings;
        successfulPings.textContent = data.stats.successful_pings;
        failedPings.textContent = data.stats.failed_pings;
        
        // Add retry stats if available
        if (data.stats.retry_pings !== undefined) {
            // Check if retry stats element exists, if not create it
            let retryStatsElement = document.getElementById('retryPings');
            if (!retryStatsElement) {
                // Create a new column for retry pings
                const retryColumn = document.createElement('div');
                retryColumn.className = 'col-md-3';
                retryColumn.innerHTML = `
                    <div class="card bg-dark mb-3">
                        <div class="card-body">
                            <h2 id="retryPings">0</h2>
                            <p class="mb-0">Retry Pings</p>
                        </div>
                    </div>
                `;
                
                // Adjust layout - change existing columns from col-md-4 to col-md-3
                const statsContainer = document.querySelector('.card-body .row');
                const existingColumns = statsContainer.querySelectorAll('.col-md-4');
                existingColumns.forEach(col => {
                    col.className = 'col-md-3';
                });
                
                // Add the new column
                statsContainer.appendChild(retryColumn);
                retryStatsElement = document.getElementById('retryPings');
            }
            
            // Update the retry stats
            retryStatsElement.textContent = data.stats.retry_pings;
        }
    }

    function updateHistoryUI(history) {
        if (!history || history.length === 0) {
            historyTableBody.innerHTML = `<tr><td colspan="5" class="text-center">No ping history yet</td></tr>`;
            return;
        }

        historyTableBody.innerHTML = '';
        
        history.forEach(entry => {
            const row = document.createElement('tr');
            
            if (entry.success) {
                row.className = 'table-success';
            } else {
                row.className = 'table-danger';
            }
            
            // Create status badge with additional info
            let statusBadge = '';
            if (entry.success) {
                statusBadge = '<span class="badge bg-success">Success</span>';
                
                // Add recovery badge if this was a successful retry
                if (entry.retry_count) {
                    statusBadge += ` <span class="badge bg-info ms-1">Recovered after ${entry.retry_count} ${entry.retry_count === 1 ? 'retry' : 'retries'}</span>`;
                }
            } else {
                statusBadge = '<span class="badge bg-danger">Failed</span>';
                
                // Add error message if available
                if (entry.error) {
                    statusBadge += `<span class="ms-2 text-danger">${entry.error}</span>`;
                }
                
                // Add retry badge if this was a retry attempt
                if (entry.is_retry) {
                    statusBadge += ' <span class="badge bg-warning text-dark ms-1">Retry</span>';
                }
            }
            
            row.innerHTML = `
                <td>${entry.timestamp}</td>
                <td>${truncateText(entry.url, 30)}</td>
                <td>${entry.status_code}</td>
                <td>${entry.response_time ? entry.response_time + 'ms' : 'N/A'}</td>
                <td>${statusBadge}</td>
            `;
            
            historyTableBody.appendChild(row);
        });
    }

    function showAlert(message, type) {
        // Remove any existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());
        
        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert alert at the top of the container
        const container = document.querySelector('.container');
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    }

    function truncateText(text, maxLength) {
        if (text.length <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength) + '...';
    }
});

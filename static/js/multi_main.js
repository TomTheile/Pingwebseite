document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const targetsContainer = document.getElementById('targetsContainer');
    const emptyState = document.getElementById('emptyState');
    const historyTableBody = document.getElementById('historyTableBody');
    const refreshAllBtn = document.getElementById('refreshAllBtn');
    const urlInputsContainer = document.getElementById('urlInputsContainer');
    const addUrlBtn = document.getElementById('addUrlBtn');

    // URL Input Field Management
    function addUrlInput() {
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.innerHTML = `
            <input type="url" class="form-control url-input" placeholder="https://example.com" required>
            <button class="btn btn-outline-danger remove-url" type="button">
                <i class="bi bi-trash"></i>
            </button>
        `;
        
        urlInputsContainer.appendChild(div);
        const input = div.querySelector('input');
        input.focus();
        
        // Add event listeners
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addUrlInput();
            }
        });
        
        div.querySelector('.remove-url').addEventListener('click', (e) => {
            const button = e.target.closest('.btn');
            if (button && urlInputsContainer.children.length > 1) {
                button.closest('.input-group').remove();
            }
        });
    }

    // Initialize event listeners for both initial URL inputs
    const initialUrlInputs = urlInputsContainer.querySelectorAll('input');
    initialUrlInputs.forEach(input => {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addUrlInput();
            }
        });
    });

    // Add URL button listener
    addUrlBtn.addEventListener('click', () => {
        addUrlInput();
    });

    // Add click handler to initial remove button
    const initialRemoveBtn = urlInputsContainer.querySelector('.remove-url');
    if (initialRemoveBtn) {
        initialRemoveBtn.addEventListener('click', (e) => {
            const button = e.target.closest('.btn');
            if (button && urlInputsContainer.children.length > 1) {
                button.closest('.input-group').remove();
            }
        });
    }

    // Function to get all URLs from inputs
    function getAllUrls() {
        const urls = [];
        document.querySelectorAll('.url-input').forEach(input => {
            const url = input.value.trim();
            if (url) urls.push(url);
        });
        return urls;
    }
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');
    const addNewTargetBtn = document.getElementById('addNewTargetBtn');
    const emptyStateAddBtn = document.getElementById('emptyStateAddBtn');
    const saveTargetBtn = document.getElementById('saveTargetBtn');
    
    // Statistics Elements
    const totalTargetsEl = document.getElementById('totalTargets');
    const activeTargetsEl = document.getElementById('activeTargets');
    const totalSuccessfulPingsEl = document.getElementById('totalSuccessfulPings');
    const totalFailedPingsEl = document.getElementById('totalFailedPings');

    // Form Elements
    const targetForm = document.getElementById('targetForm');
    const targetIdInput = document.getElementById('targetId');
    const urlInput = document.getElementById('urlInput');
    const intervalInput = document.getElementById('intervalInput');
    const retryOnFailureSwitch = document.getElementById('retryOnFailureSwitch');
    const maxRetriesInput = document.getElementById('maxRetriesInput');
    const retryDelayInput = document.getElementById('retryDelayInput');
    const discordWebhookInput = document.getElementById('discordWebhookInput');
    const discordOnSuccessSwitch = document.getElementById('discordOnSuccessSwitch');
    const discordOnFailureSwitch = document.getElementById('discordOnFailureSwitch');
    
    // Bootstrap Modals
    const targetModal = new bootstrap.Modal(document.getElementById('targetModal'));
    const confirmationModal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    const confirmActionBtn = document.getElementById('confirmActionBtn');
    const confirmationMessage = document.getElementById('confirmationMessage');
    
    // Current targets data cache
    let targetsData = [];
    
    // Initialize the page
    initialize();
    
    // Button click events
    refreshAllBtn.addEventListener('click', loadTargets);
    refreshHistoryBtn.addEventListener('click', loadHistory);
    addNewTargetBtn.addEventListener('click', showAddTargetModal);
    emptyStateAddBtn.addEventListener('click', showAddTargetModal);
    saveTargetBtn.addEventListener('click', saveTarget);

    /**
     * Initialize the page
     */
    function initialize() {
        loadTargets();
        loadHistory();
        
        // Set up periodic refresh (every 30 seconds)
        setInterval(() => {
            loadTargets(false); // Silent refresh (no loading indicator)
            loadHistory(false); // Silent refresh (no loading indicator)
        }, 30000);
    }
    
    /**
     * Load all ping targets
     */
    async function loadTargets(showLoading = true) {
        if (showLoading) {
            // Show loading state
            targetsContainer.innerHTML = `
                <div class="col-12 loader">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
        }
        
        try {
            const response = await fetch('/api/targets');
            
            if (!response.ok) {
                throw new Error('Failed to load targets');
            }
            
            targetsData = await response.json();
            renderTargets();
            updateStatistics();
            
        } catch (error) {
            console.error('Error loading targets:', error);
            showAlert('Error loading targets: ' + error.message, 'danger');
            
            // Show error state
            targetsContainer.innerHTML = `
                <div class="col-12 text-center py-5">
                    <div class="py-5">
                        <i class="bi bi-exclamation-triangle" style="font-size: 4rem;"></i>
                        <h3 class="mt-3">Failed to load targets</h3>
                        <p class="text-muted">${error.message}</p>
                        <button onclick="loadTargets()" class="btn btn-primary mt-2">
                            <i class="bi bi-arrow-clockwise"></i> Try Again
                        </button>
                    </div>
                </div>
            `;
        }
    }
    
    /**
     * Render target cards
     */
    function renderTargets() {
        // Clear the container
        targetsContainer.innerHTML = '';
        
        if (targetsData.length === 0) {
            // Show empty state
            emptyState.classList.remove('d-none');
        } else {
            // Hide empty state
            emptyState.classList.add('d-none');
            
            // Render targets
            targetsData.forEach(target => {
                const isRunning = target.status === 'running';
                const statusBadgeClass = isRunning ? 'bg-success' : 'bg-danger';
                const statusText = isRunning ? 'Running' : 'Stopped';
                
                const card = document.createElement('div');
                card.className = 'col-lg-4 col-md-6 mb-4';
                card.innerHTML = `
                    <div class="card bg-dark ping-target">
                        <div class="card-header">
                            <div class="card-header-actions">
                                <h5 class="mb-0 text-truncate" title="${target.config.url}">
                                    ${truncateText(target.config.url, 20)}
                                </h5>
                                <span class="badge ${statusBadgeClass} site-badge">${statusText}</span>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="d-flex justify-content-between mb-3">
                                <div>
                                    <p class="mb-1"><strong>Interval:</strong> ${target.config.interval} min</p>
                                    <p class="mb-0"><strong>Auto-retry:</strong> ${target.config.retry_on_failure ? 'Yes' : 'No'}</p>
                                </div>
                                <div class="text-end">
                                    <p class="mb-1"><strong>Success:</strong> ${target.stats.successful_pings}</p>
                                    <p class="mb-0"><strong>Failed:</strong> ${target.stats.failed_pings}</p>
                                </div>
                            </div>
                            
                            <div class="d-grid gap-2">
                                ${isRunning ? 
                                    `<button class="btn btn-danger stop-btn" data-id="${target.id}">
                                        <i class="bi bi-stop-fill"></i> Stop Pinging
                                    </button>` : 
                                    `<button class="btn btn-success start-btn" data-id="${target.id}">
                                        <i class="bi bi-play-fill"></i> Start Pinging
                                    </button>`
                                }
                                <button class="btn btn-primary ping-now-btn" data-id="${target.id}">
                                    <i class="bi bi-send"></i> Ping Now
                                </button>
                            </div>
                        </div>
                        <div class="card-footer">
                            <div class="btn-group w-100" role="group">
                                <button class="btn btn-outline-secondary edit-btn" data-id="${target.id}">
                                    <i class="bi bi-pencil"></i> Edit
                                </button>
                                <button class="btn btn-outline-danger delete-btn" data-id="${target.id}">
                                    <i class="bi bi-trash"></i> Delete
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                
                // Add the card to the container
                targetsContainer.appendChild(card);
            });
            
            // Add event listeners to buttons
            document.querySelectorAll('.start-btn').forEach(btn => {
                btn.addEventListener('click', startTarget);
            });
            
            document.querySelectorAll('.stop-btn').forEach(btn => {
                btn.addEventListener('click', stopTarget);
            });
            
            document.querySelectorAll('.ping-now-btn').forEach(btn => {
                btn.addEventListener('click', pingNowTarget);
            });
            
            document.querySelectorAll('.edit-btn').forEach(btn => {
                btn.addEventListener('click', editTarget);
            });
            
            document.querySelectorAll('.delete-btn').forEach(btn => {
                btn.addEventListener('click', deleteTarget);
            });
        }
    }
    
    /**
     * Update dashboard statistics
     */
    function updateStatistics() {
        let totalTargets = targetsData.length;
        let activeTargets = targetsData.filter(target => target.status === 'running').length;
        let totalSuccessfulPings = targetsData.reduce((sum, target) => sum + target.stats.successful_pings, 0);
        let totalFailedPings = targetsData.reduce((sum, target) => sum + target.stats.failed_pings, 0);
        
        totalTargetsEl.textContent = totalTargets;
        activeTargetsEl.textContent = activeTargets;
        totalSuccessfulPingsEl.textContent = totalSuccessfulPings;
        totalFailedPingsEl.textContent = totalFailedPings;
    }
    
    /**
     * Load ping history
     */
    async function loadHistory(showLoading = true) {
        if (showLoading) {
            historyTableBody.innerHTML = `<tr><td colspan="5" class="text-center">Loading history...</td></tr>`;
        }
        
        try {
            const response = await fetch('/api/history');
            
            if (!response.ok) {
                throw new Error('Failed to load history');
            }
            
            const history = await response.json();
            updateHistoryUI(history);
            
        } catch (error) {
            console.error('Error loading history:', error);
            historyTableBody.innerHTML = `
                <tr><td colspan="5" class="text-center text-danger">
                    Error loading history: ${error.message}
                </td></tr>
            `;
        }
    }
    
    /**
     * Show the add target modal
     */
    function showAddTargetModal() {
        // Reset the form
        targetForm.reset();
        targetIdInput.value = '';
        
        // Update modal title
        document.getElementById('targetModalLabel').textContent = 'Add New Ping Target';
        
        // Set default values
        intervalInput.value = '5';
        retryOnFailureSwitch.checked = true;
        maxRetriesInput.value = '3';
        retryDelayInput.value = '10';
        discordOnSuccessSwitch.checked = false;
        discordOnFailureSwitch.checked = true;
        
        // Show the modal
        targetModal.show();
    }
    
    /**
     * Edit an existing target
     */
    function editTarget(e) {
        const targetId = e.currentTarget.dataset.id;
        const target = targetsData.find(t => t.id === targetId);
        
        if (!target) {
            showAlert('Target not found', 'danger');
            return;
        }
        
        // Fill the form with target data
        targetIdInput.value = target.id;
        urlInput.value = target.config.url;
        intervalInput.value = target.config.interval;
        retryOnFailureSwitch.checked = target.config.retry_on_failure;
        maxRetriesInput.value = target.config.max_retries;
        retryDelayInput.value = target.config.retry_delay;
        discordWebhookInput.value = target.config.discord_webhook_url;
        discordOnSuccessSwitch.checked = target.config.send_discord_on_success;
        discordOnFailureSwitch.checked = target.config.send_discord_on_failure;
        
        // Update modal title
        document.getElementById('targetModalLabel').textContent = 'Edit Ping Target';
        
        // Show the modal
        targetModal.show();
    }
    
    /**
     * Save a target (add new or update existing)
     */
    async function saveTarget() {
        // Validate inputs
        const url = urlInput.value.trim();
        const interval = parseFloat(intervalInput.value);
        
        if (!url) {
            showAlert('Please enter a valid URL', 'warning');
            return;
        }
        
        if (isNaN(interval) || interval < 0.5) {
            showAlert('Interval must be at least 0.5 minutes', 'warning');
            return;
        }
        
        // Get advanced options
        const retryOnFailure = retryOnFailureSwitch.checked;
        const maxRetries = parseInt(maxRetriesInput.value) || 3;
        const retryDelay = parseInt(retryDelayInput.value) || 10;
        
        // Get notification options
        const discordWebhookUrl = discordWebhookInput.value.trim();
        const sendDiscordOnSuccess = discordOnSuccessSwitch.checked;
        const sendDiscordOnFailure = discordOnFailureSwitch.checked;
        
        // Create request payload
        const payload = {
            url: url,
            interval: interval,
            retry_on_failure: retryOnFailure,
            max_retries: maxRetries,
            retry_delay: retryDelay,
            discord_webhook_url: discordWebhookUrl,
            send_discord_on_success: sendDiscordOnSuccess,
            send_discord_on_failure: sendDiscordOnFailure
        };
        
        try {
            // Disable save button during operation
            saveTargetBtn.disabled = true;
            saveTargetBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
            
            let response;
            
            if (targetIdInput.value) {
                // Update existing target
                response = await fetch(`/api/targets/${targetIdInput.value}/start`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
            } else {
                // Add new target
                response = await fetch('/api/targets', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
            }
            
            if (!response.ok) {
                throw new Error('Failed to save target');
            }
            
            const data = await response.json();
            
            // Close the modal
            targetModal.hide();
            
            // Show success message
            showAlert(data.message, 'success');
            
            // Reload targets
            loadTargets();
            
        } catch (error) {
            console.error('Error saving target:', error);
            showAlert('Error saving target: ' + error.message, 'danger');
        } finally {
            // Re-enable save button
            saveTargetBtn.disabled = false;
            saveTargetBtn.textContent = 'Save Target';
        }
    }
    
    /**
     * Start a target
     */
    async function startTarget(e) {
        const targetId = e.currentTarget.dataset.id;
        const target = targetsData.find(t => t.id === targetId);
        
        if (!target) {
            showAlert('Target not found', 'danger');
            return;
        }
        
        try {
            // Disable button during operation
            e.currentTarget.disabled = true;
            e.currentTarget.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';
            
            const response = await fetch(`/api/targets/${targetId}/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            if (!response.ok) {
                throw new Error('Failed to start target');
            }
            
            const data = await response.json();
            
            // Show success message
            showAlert(data.message, 'success');
            
            // Reload targets
            loadTargets();
            
        } catch (error) {
            console.error('Error starting target:', error);
            showAlert('Error starting target: ' + error.message, 'danger');
            
            // Re-enable button
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = '<i class="bi bi-play-fill"></i> Start Pinging';
        }
    }
    
    /**
     * Stop a target
     */
    async function stopTarget(e) {
        const targetId = e.currentTarget.dataset.id;
        const target = targetsData.find(t => t.id === targetId);
        
        if (!target) {
            showAlert('Target not found', 'danger');
            return;
        }
        
        try {
            // Disable button during operation
            e.currentTarget.disabled = true;
            e.currentTarget.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Stopping...';
            
            const response = await fetch(`/api/targets/${targetId}/stop`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error('Failed to stop target');
            }
            
            const data = await response.json();
            
            // Show success message
            showAlert(data.message, 'success');
            
            // Reload targets
            loadTargets();
            
        } catch (error) {
            console.error('Error stopping target:', error);
            showAlert('Error stopping target: ' + error.message, 'danger');
            
            // Re-enable button
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = '<i class="bi bi-stop-fill"></i> Stop Pinging';
        }
    }
    
    /**
     * Ping a target immediately
     */
    async function pingNowTarget(e) {
        const targetId = e.currentTarget.dataset.id;
        const target = targetsData.find(t => t.id === targetId);
        
        if (!target) {
            showAlert('Target not found', 'danger');
            return;
        }
        
        try {
            // Disable button during operation
            e.currentTarget.disabled = true;
            e.currentTarget.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Pinging...';
            
            const response = await fetch(`/api/targets/${targetId}/ping`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            if (!response.ok) {
                throw new Error('Failed to ping target');
            }
            
            const data = await response.json();
            
            // Show success message
            showAlert('Website pinged successfully', 'success');
            
            // Reload targets and history
            loadTargets();
            loadHistory();
            
        } catch (error) {
            console.error('Error pinging target:', error);
            showAlert('Error pinging target: ' + error.message, 'danger');
            
        } finally {
            // Re-enable button
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = '<i class="bi bi-send"></i> Ping Now';
        }
    }
    
    /**
     * Delete a target
     */
    function deleteTarget(e) {
        const targetId = e.currentTarget.dataset.id;
        const target = targetsData.find(t => t.id === targetId);
        
        if (!target) {
            showAlert('Target not found', 'danger');
            return;
        }
        
        // Configure the confirmation modal
        confirmationMessage.textContent = `Are you sure you want to delete the target "${truncateText(target.config.url, 30)}"?`;
        
        // Set up the confirmation button
        confirmActionBtn.onclick = async () => {
            confirmationModal.hide();
            
            try {
                const response = await fetch(`/api/targets/${targetId}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) {
                    throw new Error('Failed to delete target');
                }
                
                const data = await response.json();
                
                // Show success message
                showAlert(data.message, 'success');
                
                // Reload targets
                loadTargets();
                
            } catch (error) {
                console.error('Error deleting target:', error);
                showAlert('Error deleting target: ' + error.message, 'danger');
            }
        };
        
        // Show the confirmation modal
        confirmationModal.show();
    }
    
    /**
     * Update the history table
     */
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
    
    /**
     * Show alert message
     */
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
    
    /**
     * Truncate text to a maximum length
     */
    function truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength) + '...';
    }
});
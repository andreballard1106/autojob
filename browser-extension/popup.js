const API_BASE_URL = 'http://localhost:8000';

async function checkConnection() {
  const dot = document.getElementById('connectionDot');
  const status = document.getElementById('connectionStatus');

  try {
    const response = await fetch(`${API_BASE_URL}/health`, { method: 'GET' });
    if (response.ok) {
      dot.className = 'status-dot active';
      status.textContent = 'Connected';
      return true;
    }
  } catch (error) {
    // API might not have /health endpoint, try notifications
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/jobs/notifications/pending`);
    if (response.ok) {
      dot.className = 'status-dot active';
      status.textContent = 'Connected';
      return true;
    }
  } catch (error) {
    dot.className = 'status-dot';
    status.textContent = 'Disconnected';
    return false;
  }

  dot.className = 'status-dot';
  status.textContent = 'Disconnected';
  return false;
}

async function loadPendingActions() {
  const listEl = document.getElementById('pendingList');

  try {
    const response = await fetch(`${API_BASE_URL}/api/jobs/notifications/pending`);
    if (!response.ok) {
      listEl.innerHTML = '<div class="no-pending">Failed to load</div>';
      return;
    }

    const data = await response.json();
    const notifications = data.notifications || [];

    if (notifications.length === 0) {
      listEl.innerHTML = '<div class="no-pending">No pending actions</div>';
      return;
    }

    listEl.innerHTML = notifications.map(n => `
      <div class="pending-item">
        <div class="title">${n.title}</div>
        <div class="message">${n.message}</div>
        ${n.job_id ? `
          <button class="btn btn-primary" onclick="resumeJob('${n.job_id}')">
            Continue Processing
          </button>
        ` : ''}
      </div>
    `).join('');

  } catch (error) {
    listEl.innerHTML = '<div class="no-pending">Error loading actions</div>';
  }
}

async function resumeJob(jobId) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    if (response.ok) {
      await fetch(`${API_BASE_URL}/api/jobs/notifications/clear?job_id=${jobId}`, {
        method: 'DELETE',
      });
      loadPendingActions();
    } else {
      const error = await response.json();
      alert(`Failed: ${error.detail || 'Unknown error'}`);
    }
  } catch (error) {
    alert(`Error: ${error.message}`);
  }
}

window.resumeJob = resumeJob;

document.getElementById('refreshBtn').addEventListener('click', () => {
  checkConnection();
  loadPendingActions();
});

document.addEventListener('DOMContentLoaded', () => {
  checkConnection();
  loadPendingActions();
});


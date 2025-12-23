const API_BASE_URL = 'http://localhost:8000';
const CHECK_INTERVAL = 2000;

let currentJobId = null;
let continueButton = null;
let statusIndicator = null;
let checkInterval = null;

function createContinueButton() {
  if (continueButton) return;

  const container = document.createElement('div');
  container.id = 'job-assistant-container';
  container.innerHTML = `
    <div id="job-assistant-panel">
      <div id="job-assistant-status">
        <span id="job-assistant-status-dot"></span>
        <span id="job-assistant-status-text">Checking...</span>
      </div>
      <button id="job-assistant-continue" style="display: none;">
        Continue Processing
      </button>
      <button id="job-assistant-minimize">-</button>
    </div>
  `;

  document.body.appendChild(container);

  continueButton = document.getElementById('job-assistant-continue');
  statusIndicator = document.getElementById('job-assistant-status-text');
  const statusDot = document.getElementById('job-assistant-status-dot');
  const minimizeBtn = document.getElementById('job-assistant-minimize');
  const panel = document.getElementById('job-assistant-panel');

  continueButton.addEventListener('click', handleContinueClick);

  minimizeBtn.addEventListener('click', () => {
    panel.classList.toggle('minimized');
    minimizeBtn.textContent = panel.classList.contains('minimized') ? '+' : '-';
  });

  return { continueButton, statusIndicator, statusDot };
}

async function checkJobStatus() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/jobs/notifications/pending`);
    if (!response.ok) return;

    const data = await response.json();
    const notifications = data.notifications || [];

    const captchaNotification = notifications.find(n => 
      n.type === 'captcha_detected' && n.requires_action
    );

    if (captchaNotification) {
      currentJobId = captchaNotification.job_id;
      showContinueButton(captchaNotification);
    } else {
      hideContinueButton();
    }
  } catch (error) {
    console.log('Job Assistant: API not available');
  }
}

function showContinueButton(notification) {
  if (!continueButton) createContinueButton();

  const statusDot = document.getElementById('job-assistant-status-dot');
  const panel = document.getElementById('job-assistant-panel');

  statusIndicator.textContent = 'CAPTCHA Detected - Solve & Continue';
  statusDot.className = 'status-waiting';
  continueButton.style.display = 'block';
  panel.classList.remove('minimized');
  panel.classList.add('visible');
}

function hideContinueButton() {
  if (!continueButton) return;

  const statusDot = document.getElementById('job-assistant-status-dot');
  const panel = document.getElementById('job-assistant-panel');

  statusIndicator.textContent = 'No pending actions';
  statusDot.className = 'status-idle';
  continueButton.style.display = 'none';
}

async function handleContinueClick() {
  if (!currentJobId) {
    alert('No job ID found. Please refresh the page.');
    return;
  }

  continueButton.disabled = true;
  continueButton.textContent = 'Resuming...';

  try {
    const response = await fetch(`${API_BASE_URL}/api/jobs/${currentJobId}/resume`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const statusDot = document.getElementById('job-assistant-status-dot');
      statusIndicator.textContent = 'Resumed! Processing...';
      statusDot.className = 'status-active';
      continueButton.style.display = 'none';

      await fetch(`${API_BASE_URL}/api/jobs/notifications/clear?job_id=${currentJobId}`, {
        method: 'DELETE',
      });

      currentJobId = null;

      setTimeout(() => {
        hideContinueButton();
      }, 3000);
    } else {
      const error = await response.json();
      alert(`Failed to resume: ${error.detail || 'Unknown error'}`);
      continueButton.disabled = false;
      continueButton.textContent = 'Continue Processing';
    }
  } catch (error) {
    alert(`Error: ${error.message}`);
    continueButton.disabled = false;
    continueButton.textContent = 'Continue Processing';
  }
}

function init() {
  createContinueButton();
  checkJobStatus();
  checkInterval = setInterval(checkJobStatus, CHECK_INTERVAL);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

window.addEventListener('unload', () => {
  if (checkInterval) {
    clearInterval(checkInterval);
  }
});


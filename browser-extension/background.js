const API_BASE_URL = 'http://localhost:8000';

chrome.runtime.onInstalled.addListener(() => {
  console.log('Job Application Assistant installed');
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'checkStatus') {
    fetch(`${API_BASE_URL}/api/jobs/notifications/pending`)
      .then(response => response.json())
      .then(data => {
        sendResponse({ success: true, data });
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });
    return true;
  }

  if (request.action === 'resumeJob') {
    fetch(`${API_BASE_URL}/api/jobs/${request.jobId}/resume`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        sendResponse({ success: true, data });
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });
    return true;
  }
});


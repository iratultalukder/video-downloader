// JavaScript code for handling download requests, form validation, file downloads, status display, and API communication

// Function to handle download requests
function handleDownloadRequest(videoUrl) {
    // Validate the video URL
    if (!isValidUrl(videoUrl)) {
        displayStatus('Invalid URL', 'error');
        return;
    }

    // Show status while downloading
    displayStatus('Downloading...', 'info');
    downloadFile(videoUrl)
        .then(response => {
            // Handle the successful download
            displayStatus('Download successful!', 'success');
        })
        .catch(error => {
            // Handle download error
            displayStatus('Download failed: ' + error.message, 'error');
        });
}

// Function to validate URL
function isValidUrl(url) {
    const urlPattern = /^(https?:\/\/)?([\w-]+\.)+[\w-]+(\/[\w- ./?%&=]*)?$/;
    return urlPattern.test(url);
}

// Function to download the file
async function downloadFile(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error('Network response was not ok');
    }
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.download = 'video.mp4'; // Set default file name
    link.click();
}

// Function to display status messages
function displayStatus(message, type) {
    const statusElement = document.getElementById('status');
    statusElement.innerText = message;
    statusElement.className = type; // Add class based on type
}
// config.js
const CONFIG = {
    // Use your actual backend URL
    API_BASE_URL: 'https://curralms-backend.onrender.com',
    
    // Fallback for local development
    LOCAL_API_URL: 'http://localhost:8000'
};

// Determine which URL to use
function getApiBaseUrl() {
    // If we're on the frontend domain, use the deployed backend
    if (window.location.hostname === 'curralms-frontend.onrender.com') {
        return CONFIG.API_BASE_URL;
    }
    // For local development
    return CONFIG.LOCAL_API_URL;
}

// Make it globally available
window.API_BASE_URL = getApiBaseUrl();
console.log('API Base URL:', window.API_BASE_URL);

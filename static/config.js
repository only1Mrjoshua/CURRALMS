// config.js - ENHANCED FOR RENDER DEPLOYMENT
const CONFIG = {
    // Production URLs
    PRODUCTION: {
        API_BASE_URL: 'https://curralms-backend.onrender.com',
        FRONTEND_URL: 'https://curralms.onrender.com'
    },
    
    // Development URLs
    DEVELOPMENT: {
        API_BASE_URL: 'http://localhost:8000',
        FRONTEND_URL: 'http://localhost:3000'
    }
};

// Environment detection
function getEnvironment() {
    const hostname = window.location.hostname;
    
    if (hostname.includes('onrender.com')) {
        return 'production';
    }
    return 'development';
}

// Get API base URL
function getApiBaseUrl() {
    const env = getEnvironment();
    return CONFIG[env.toUpperCase()].API_BASE_URL;
}

// Get frontend base URL
function getFrontendBaseUrl() {
    const env = getEnvironment();
    return CONFIG[env.toUpperCase()].FRONTEND_URL;
}

// Get environment name
function getEnvironmentName() {
    return getEnvironment();
}

// Make it globally available
window.API_BASE_URL = getApiBaseUrl();
window.FRONTEND_BASE_URL = getFrontendBaseUrl();
window.ENVIRONMENT = getEnvironmentName();

console.log('🌐 Environment:', window.ENVIRONMENT);
console.log('🔌 API Base URL:', window.API_BASE_URL);
console.log('🏠 Frontend URL:', window.FRONTEND_BASE_URL);

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getApiBaseUrl,
        getFrontendBaseUrl,
        getEnvironmentName,
        CONFIG
    };
}
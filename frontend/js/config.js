/**
 * AlphaPass Global Frontend Configuration
 * Dynamically generated on 2026-07-25T20:47:09Z
 * Active API Endpoint: https://yrn3zdmv50.execute-api.us-east-1.amazonaws.com/dev
 */
if (typeof window.ALPHAPASS_API_URL === 'undefined' || !window.ALPHAPASS_API_URL) {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        window.ALPHAPASS_API_URL = 'http://127.0.0.1:8000';
    } else {
        window.ALPHAPASS_API_URL = 'https://yrn3zdmv50.execute-api.us-east-1.amazonaws.com/dev';
    }
}

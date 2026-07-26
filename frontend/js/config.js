/**
 * AlphaPass Global Frontend Configuration
 * Dynamically generated on 2026-07-26T18:47:12Z
 * Active API Endpoint: https://5pk6j1j5bj.execute-api.us-east-1.amazonaws.com/dev
 */
if (typeof window.ALPHAPASS_API_URL === 'undefined' || !window.ALPHAPASS_API_URL) {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        window.ALPHAPASS_API_URL = 'http://127.0.0.1:8000';
    } else {
        window.ALPHAPASS_API_URL = 'https://5pk6j1j5bj.execute-api.us-east-1.amazonaws.com/dev';
    }
}

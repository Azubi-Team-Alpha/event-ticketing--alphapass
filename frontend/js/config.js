/**
 * AlphaPass Global Frontend Configuration
 * ⚠️  This file is AUTO-GENERATED during CI/CD deployment.
 *     Do NOT commit hardcoded API endpoints here.
 *     The correct endpoint is injected by deploy.yml after terraform apply.
 */
if (typeof window.ALPHAPASS_API_URL === 'undefined' || !window.ALPHAPASS_API_URL) {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        window.ALPHAPASS_API_URL = 'http://127.0.0.1:8000';
    } else {
        // Populated by CI/CD pipeline — leave blank in source control
        window.ALPHAPASS_API_URL = '';
    }
}

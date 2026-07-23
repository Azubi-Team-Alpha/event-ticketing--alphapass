if (typeof window.apiFetch === 'undefined') {
  window.apiFetch = async function (path, options = {}) {
    const baseUrl = window.ALPHAPASS_API_URL || '';
    const token = localStorage.getItem('access_token') || localStorage.getItem('organizer_token') || localStorage.getItem('admin_token');
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...options.headers,
    };

    const response = await fetch(`${baseUrl}${path}`, { ...options, headers });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let errMsg = errorData.detail || `HTTP Error ${response.status}`;
      if (Array.isArray(errorData.detail)) {
        errMsg = errorData.detail.map(d => `${d.loc ? d.loc.join('.') : ''}: ${d.msg}`).join(', ');
      }
      throw new Error(errMsg);
    }
    return response.json();
  };
}


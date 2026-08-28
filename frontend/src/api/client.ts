import axios from 'axios';

export const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  // Django CSRF cookie/header names
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401 || status === 403) {
      // Session expired / not logged in: hand over to the SSO login flow
      // (igrestlogin's !redirect view; matches LOGIN_URL in ltc/settings.py).
      const next = encodeURIComponent(window.location.pathname);
      window.location.assign(`/loginapi/!redirect?next=${next}`);
    }
    return Promise.reject(error);
  },
);

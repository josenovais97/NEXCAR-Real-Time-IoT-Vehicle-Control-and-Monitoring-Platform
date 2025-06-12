// static/js/auth.js
export function getToken() {
  return localStorage.getItem("jwt");
}

export function saveToken(t) {
  localStorage.setItem("jwt", t);
}

export function clearToken() {
  localStorage.removeItem("jwt");
}

export function authHeader() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export function requireAuth() {
  if (!getToken()) window.location.href = "/login";
}

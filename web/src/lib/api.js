// Single place that talks to the backend. Every request carries the role.

const BASE = import.meta.env.VITE_API_URL || "";

function session() {
  try {
    return JSON.parse(sessionStorage.getItem("ost.user") || "{}");
  } catch {
    return {};
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Role": session().role || "",
      "X-User": session().name || session().username || "",
      ...(options.headers || {}),
    },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
  return body;
}

export const api = {
  login:       (username, password) =>
                 request("/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  kpis:        () => request("/kpis"),
  sites:       () => request("/sites"),
  questions:   () => request("/questions"),
  ask:         (key) => request(`/ask/${key}`),
  askFree:     (question) =>
                 request("/ask", { method: "POST", body: JSON.stringify({ question }) }),
  nlAvailable: () => request("/nl-available"),
  lineage:     (siteId) => request(`/lineage/${siteId}`),
  catalog:     (q = "") => request(`/catalog?q=${encodeURIComponent(q)}`),
  conceptMap:  () => request("/concept-map"),
  review:      () => request("/review"),
  decide:      (payload) =>
                 request("/review/decide", { method: "POST", body: JSON.stringify(payload) }),
  revert:      (system, source_value) =>
                 request("/review/revert", {
                   method: "POST",
                   body: JSON.stringify({ system, source_value }),
                 }),
  quality:     () => request("/quality"),
  graphStats:  () => request("/graph/stats"),
  graphSite:   (siteId) => request(`/graph/site/${siteId}`),
};

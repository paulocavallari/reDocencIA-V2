import axios from "axios";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").trim();

const api = axios.create({
  baseURL: apiBaseUrl,
});

api.interceptors.request.use((config) => {
  const token = window.localStorage.getItem("redocencia-token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.localStorage.removeItem("redocencia-token");
      // Only redirect if not already on the login page to avoid redirect loops.
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export async function downloadPlanFile(planId, format, fallbackTitle = "plano") {
  const response = await api.get(`/api/plans/${planId}/export`, {
    params: { format },
    responseType: "blob",
  });

  const disposition = response.headers["content-disposition"] || "";
  const matchedFilename = disposition.match(/filename="?([^";]+)"?/i);
  const filename = matchedFilename?.[1] || `${fallbackTitle}.${format}`;

  const url = window.URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export default api;

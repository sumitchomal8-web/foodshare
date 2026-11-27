import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";
export const TOKEN_STORAGE_KEY = "foodshare_token";

const CODE_MESSAGES = {
  INVALID_CREDENTIALS: "Invalid email or password.",
  EMAIL_EXISTS: "An account with this email already exists.",
  ACCOUNT_DISABLED: "Your account has been disabled. Contact an administrator.",
  TOKEN_INVALID: "Your session has expired. Please log in again.",
  FORBIDDEN: "You do not have permission to perform this action.",
  NGO_NOT_VERIFIED: "Your NGO account must be verified before accepting donations.",
  NOT_FOUND: "The requested item was not found.",
  INVALID_STATUS_TRANSITION: "This action is not allowed for the current status.",
  ALREADY_ACCEPTED: "This donation was just accepted by another NGO.",
  VALIDATION_ERROR: "Please check your input and try again.",
};

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const code = error.response?.data?.code;

    if (status === 401 && code === "TOKEN_INVALID") {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

export function formatApiError(error) {
  const data = error.response?.data;
  if (!data) {
    return error.message || "Network error. Please check if the server is running.";
  }

  const friendly = CODE_MESSAGES[data.code];
  if (Array.isArray(data.detail)) {
    const details = data.detail
      .map((item) => {
        const field = item.loc ? item.loc[item.loc.length - 1] : "field";
        return `${field}: ${item.msg}`;
      })
      .join(" | ");
    return details || friendly || "Validation error.";
  }

  if (typeof data.detail === "string" && data.detail.trim()) {
    return friendly && data.code !== "VALIDATION_ERROR"
      ? `${friendly} (${data.detail})`
      : data.detail;
  }

  return friendly || "Something went wrong. Please try again.";
}

export default apiClient;

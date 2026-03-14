import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem("refresh_token");
        const response = await axios.post(`${API_URL}/api/auth/refresh`, null, {
          headers: {
            Authorization: `Bearer ${refreshToken}`,
          },
        });

        const { access_token, refresh_token } = response.data;
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/auth/login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post("/api/auth/register", data),
  login: (data: { email: string; password: string }) =>
    api.post("/api/auth/login", data),
  refreshToken: () =>
    api.post("/api/auth/refresh"),
  getMe: () => api.get("/api/auth/me"),
};

// Leads API
export const leadsApi = {
  list: (params?: {
    page?: number;
    per_page?: number;
    status?: string;
    industry?: string;
    city?: string;
    min_score?: number;
    search?: string;
  }) => api.get("/api/leads", { params }),
  get: (id: number) => api.get(`/api/leads/${id}`),
  create: (data: any) => api.post("/api/leads", data),
  update: (id: number, data: any) => api.put(`/api/leads/${id}`, data),
  delete: (id: number) => api.delete(`/api/leads/${id}`),
  addTags: (id: number, tagIds: number[]) =>
    api.post(`/api/leads/${id}/tags`, { lead_id: id, tag_ids: tagIds }),
  removeTag: (id: number, tagId: number) =>
    api.delete(`/api/leads/${id}/tags/${tagId}`),
};

// Pipeline API
export const pipelineApi = {
  getStages: () => api.get("/api/pipeline/stages"),
  createStage: (data: { name: string; order?: number; color?: string }) =>
    api.post("/api/pipeline/stages", data),
  updateStage: (id: number, data: any) =>
    api.put(`/api/pipeline/stages/${id}`, data),
  deleteStage: (id: number) => api.delete(`/api/pipeline/stages/${id}`),
  moveLead: (leadId: number, stageId: number) =>
    api.post("/api/pipeline/move", { lead_id: leadId, stage_id: stageId }),
  getLeadsInStage: (stageId: number) =>
    api.get(`/api/pipeline/leads/${stageId}`),
  initialize: () => api.post("/api/pipeline/initialize"),
};

// Analytics API
export const analyticsApi = {
  getSummary: () => api.get("/api/analytics/summary"),
  getFull: () => api.get("/api/analytics"),
  getTrends: (days: number = 30) =>
    api.get("/api/analytics/trends/leads-by-day", { params: { days } }),
  getScoreDistribution: () => api.get("/api/analytics/trends/score-distribution"),
  getFunnel: () => api.get("/api/analytics/conversion-funnel"),
};

// Scraper API
export const scraperApi = {
  startJob: (data: { source: string; search_params?: any }) =>
    api.post("/api/scrape/start", data),
  getJobStatus: (jobId: string) =>
    api.get(`/api/scrape/status/${jobId}`),
};

// Outreach API
export const outreachApi = {
  createCampaign: (data: any) =>
    api.post("/api/outreach/campaigns", data),
  getCampaigns: () => api.get("/api/outreach/campaigns"),
  sendEmail: (data: { lead_id: number; campaign_id: number }) =>
    api.post("/api/outreach/send", data),
};

export default api;

/**
 * API client for FameShield backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired, try to refresh
          const refreshed = await this.refreshToken();
          if (refreshed && error.config) {
            return this.client.request(error.config);
          }
        }
        return Promise.reject(error);
      }
    );
  }

  setAccessToken(token: string) {
    this.accessToken = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('accessToken', token);
    }
  }

  getAccessToken(): string | null {
    if (!this.accessToken && typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('accessToken');
    }
    return this.accessToken;
  }

  clearTokens() {
    this.accessToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
    }
  }

  async refreshToken(): Promise<boolean> {
    try {
      if (typeof window === 'undefined') return false;

      const refreshToken = localStorage.getItem('refreshToken');
      if (!refreshToken) return false;

      const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });

      this.setAccessToken(response.data.access_token);
      localStorage.setItem('refreshToken', response.data.refresh_token);
      return true;
    } catch (error) {
      this.clearTokens();
      return false;
    }
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await this.client.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    this.setAccessToken(response.data.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('refreshToken', response.data.refresh_token);
    }

    return response.data;
  }

  async register(data: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    organization_name: string;
  }) {
    const response = await this.client.post('/auth/register', data);
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  async logout() {
    await this.client.post('/auth/logout');
    this.clearTokens();
  }

  // Athlete endpoints
  async getAthletes(params?: Record<string, any>) {
    const response = await this.client.get('/athletes', { params });
    return response.data;
  }

  async getAthlete(id: string) {
    const response = await this.client.get(`/athletes/${id}`);
    return response.data;
  }

  async createAthlete(data: any) {
    const response = await this.client.post('/athletes', data);
    return response.data;
  }

  async updateAthlete(id: string, data: any) {
    const response = await this.client.patch(`/athletes/${id}`, data);
    return response.data;
  }

  async deleteAthlete(id: string) {
    await this.client.delete(`/athletes/${id}`);
  }

  // Content endpoints
  async getContent(params?: Record<string, any>) {
    const response = await this.client.get('/content', { params });
    return response.data;
  }

  async getContentItem(id: string) {
    const response = await this.client.get(`/content/${id}`);
    return response.data;
  }

  async hideContent(id: string) {
    const response = await this.client.post(`/content/${id}/hide`);
    return response.data;
  }

  async markFalsePositive(id: string) {
    const response = await this.client.post(`/content/${id}/mark-false-positive`);
    return response.data;
  }

  async getContentTimeline(id: string) {
    const response = await this.client.get(`/content/${id}/timeline`);
    return response.data;
  }

  // Classification endpoints
  async getClassifications(params?: Record<string, any>) {
    const response = await this.client.get('/classifications', { params });
    return response.data;
  }

  async getClassification(id: string) {
    const response = await this.client.get(`/classifications/${id}`);
    return response.data;
  }

  async reviewClassification(id: string, review: { status: string; override_category?: string }) {
    const response = await this.client.patch(`/classifications/${id}/review`, review);
    return response.data;
  }

  async escalateClassification(id: string) {
    const response = await this.client.post(`/classifications/${id}/escalate`);
    return response.data;
  }

  async reclassifyContent(id: string) {
    const response = await this.client.post(`/classifications/${id}/reclassify`);
    return response.data;
  }

  async getClassificationStatistics(params?: Record<string, any>) {
    const response = await this.client.get('/classifications/statistics/summary', { params });
    return response.data;
  }

  // Athlete self-serve auth
  async athleteRegister(data: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    date_of_birth: string;
    sport: string;
    phone?: string;
  }) {
    const response = await this.client.post('/athlete-auth/register', data);
    this.setAccessToken(response.data.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('refreshToken', response.data.refresh_token);
      localStorage.setItem('athleteId', response.data.athlete_id);
    }
    return response.data;
  }

  async athleteLogin(email: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    const response = await this.client.post('/athlete-auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    this.setAccessToken(response.data.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('refreshToken', response.data.refresh_token);
      localStorage.setItem('athleteId', response.data.athlete_id);
    }
    return response.data;
  }

  athleteLogout() {
    this.clearTokens();
    if (typeof window !== 'undefined') {
      localStorage.removeItem('athleteId');
    }
  }

  // Athlete portal
  async getMe() {
    const response = await this.client.get('/me');
    return response.data;
  }

  async updateMyProfile(data: Record<string, any>) {
    const response = await this.client.patch('/me/profile', data);
    return response.data;
  }

  async getMySocialAccounts() {
    const response = await this.client.get('/me/social-accounts');
    return response.data;
  }

  async addMySocialAccount(data: {
    platform: string;
    username: string;
    display_name?: string;
    profile_url?: string;
  }) {
    const response = await this.client.post('/me/social-accounts', data);
    return response.data;
  }

  async removeMySocialAccount(id: string) {
    await this.client.delete(`/me/social-accounts/${id}`);
  }

  async getMyAppearances() {
    const response = await this.client.get('/me/appearances');
    return response.data;
  }

  async getMyViolations(params?: Record<string, any>) {
    const response = await this.client.get('/me/violations', { params });
    return response.data;
  }

  // Subscriptions
  async getProducts() {
    const response = await this.client.get('/products');
    return response.data;
  }

  async getMySubscription() {
    const response = await this.client.get('/me/subscription');
    return response.data;
  }

  async subscribe(product_id: string, billing_interval: 'month' | 'year') {
    const response = await this.client.post('/me/subscription', {
      product_id,
      billing_interval,
    });
    return response.data;
  }

  async changeSubscription(product_id: string, billing_interval: 'month' | 'year') {
    const response = await this.client.patch('/me/subscription', {
      product_id,
      billing_interval,
    });
    return response.data;
  }

  async cancelSubscription(atPeriodEnd = true) {
    const response = await this.client.delete('/me/subscription', {
      params: { at_period_end: atPeriodEnd },
    });
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;

import api from './api';

export interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  description?: string;
  is_active: boolean;
  expires_at?: string;
  last_used_at?: string;
  created_at: string;
}

export interface APIKeyCreate {
  name: string;
  description?: string;
  expires_in_days?: number;
  scopes?: string[];
}

export interface APIKeyCreateResponse {
  api_key: APIKey;
  full_key: string;
}

export const apiKeysService = {
  async getApiKeys(): Promise<APIKey[]> {
    const response = await api.get('/api-keys');
    return response.data;
  },

  async getApiKey(id: string): Promise<APIKey> {
    const response = await api.get(`/api-keys/${id}`);
    return response.data;
  },

  async createApiKey(data: APIKeyCreate): Promise<APIKeyCreateResponse> {
    const response = await api.post('/api-keys', data);
    return response.data;
  },

  async deleteApiKey(id: string): Promise<void> {
    await api.delete(`/api-keys/${id}`);
  },
};
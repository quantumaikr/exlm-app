import api from './api';

export enum ModelStatus {
  PENDING = 'pending',
  TRAINING = 'training',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface Model {
  id: string;
  name: string;
  base_model: string;
  description?: string;
  project_id: string;
  dataset_id?: string;
  status: ModelStatus;
  config?: Record<string, any>;
  metrics?: Record<string, any>;
  model_path?: string;
  created_at: string;
  updated_at?: string;
}

export interface ModelListResponse {
  items: Model[];
  total: number;
  page: number;
  pages: number;
}

export interface CreateModelRequest {
  name: string;
  base_model: string;
  description?: string;
  project_id: string;
  dataset_id?: string;
  config?: Record<string, any>;
}

export interface UpdateModelRequest {
  name?: string;
  description?: string;
  config?: Record<string, any>;
}

export const modelsService = {
  async getModels(params?: {
    project_id?: string;
    status?: ModelStatus;
    page?: number;
    limit?: number;
    search?: string;
  }): Promise<ModelListResponse> {
    const response = await api.get<ModelListResponse>('/models', { params });
    return response.data;
  },

  async getModel(id: string): Promise<Model> {
    const response = await api.get<Model>(`/models/${id}`);
    return response.data;
  },

  async createModel(data: CreateModelRequest): Promise<Model> {
    const response = await api.post<Model>('/models', data);
    return response.data;
  },

  async updateModel(id: string, data: UpdateModelRequest): Promise<Model> {
    const response = await api.put<Model>(`/models/${id}`, data);
    return response.data;
  },

  async deleteModel(id: string): Promise<void> {
    await api.delete(`/models/${id}`);
  },

  async startTraining(id: string): Promise<{ message: string; model_id: string }> {
    const response = await api.post(`/models/${id}/train`);
    return response.data;
  },
};
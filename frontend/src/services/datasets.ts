import api from './api';

export enum DatasetType {
  UPLOADED = 'uploaded',
  GENERATED = 'generated',
  MIXED = 'mixed',
}

export enum DatasetStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  READY = 'ready',
  FAILED = 'failed',
}

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  project_id: string;
  type: DatasetType;
  status: DatasetStatus;
  size?: number;
  file_path?: string;
  generation_config?: Record<string, any>;
  statistics?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface DatasetListResponse {
  items: Dataset[];
  total: number;
  page: number;
  pages: number;
}

export interface CreateDatasetRequest {
  name: string;
  description?: string;
  project_id: string;
  type: DatasetType;
  generation_config?: Record<string, any>;
}

export interface UpdateDatasetRequest {
  name?: string;
  description?: string;
}

export interface DataGenerationConfig {
  provider: 'openai' | 'anthropic' | 'google';
  model: string;
  prompt_template: string;
  num_samples: number;
  temperature?: number;
  max_tokens?: number;
  domain_keywords?: string[];
}

export const datasetsService = {
  async getDatasets(params?: {
    project_id?: string;
    type?: DatasetType;
    status?: DatasetStatus;
    page?: number;
    limit?: number;
    search?: string;
  }): Promise<DatasetListResponse> {
    const response = await api.get<DatasetListResponse>('/datasets', { params });
    return response.data;
  },

  async getDataset(id: string): Promise<Dataset> {
    const response = await api.get<Dataset>(`/datasets/${id}`);
    return response.data;
  },

  async createDataset(data: CreateDatasetRequest): Promise<Dataset> {
    const response = await api.post<Dataset>('/datasets', data);
    return response.data;
  },

  async updateDataset(id: string, data: UpdateDatasetRequest): Promise<Dataset> {
    const response = await api.put<Dataset>(`/datasets/${id}`, data);
    return response.data;
  },

  async deleteDataset(id: string): Promise<void> {
    await api.delete(`/datasets/${id}`);
  },

  async uploadDataset(id: string, file: File): Promise<{ message: string; path: string }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post(`/datasets/${id}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async generateDataset(id: string, config: DataGenerationConfig): Promise<{ message: string; dataset_id: string }> {
    const response = await api.post(`/datasets/${id}/generate`, config);
    return response.data;
  },
};
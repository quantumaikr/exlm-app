// Global type definitions

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface Model {
  id: string;
  name: string;
  description?: string;
  path: string;
  base_model: string;
  training_method: string;
  status: string;
  latest_version?: string;
  total_versions: number;
  config?: Record<string, any>;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  size: number;
  format: string;
  path: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface TrainingJob {
  id: string;
  project_id: string;
  model_id?: string;
  dataset_id: string;
  config: Record<string, any>;
  training_type: string;
  status: string;
  celery_task_id?: string;
  output_path?: string;
  metrics?: Record<string, any>;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  updated_at: string;
  created_by: string;
}

export interface ModelEvaluation {
  id: string;
  model_id: string;
  dataset_id?: string;
  metrics: string[];
  config?: Record<string, any>;
  status: string;
  celery_task_id?: string;
  results?: Record<string, any>;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  created_by: string;
}

export interface ModelVersion {
  id: string;
  model_id: string;
  version: string;
  description?: string;
  path: string;
  model_hash?: string;
  commit_hash?: string;
  training_job_id?: string;
  metrics?: Record<string, any>;
  metadata?: Record<string, any>;
  created_at: string;
  created_by: string;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

// Form Types
export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  email: string;
  password: string;
  name: string;
  confirmPassword: string;
}

export interface ProjectForm {
  name: string;
  description?: string;
}

export interface ModelForm {
  name: string;
  description?: string;
  base_model: string;
  training_method: string;
}

export interface DatasetForm {
  name: string;
  description?: string;
  format: string;
}

// Training Configuration Types
export interface TrainingConfig {
  model_name: string;
  dataset_id: string;
  training_type: string;
  num_train_epochs: number;
  per_device_train_batch_size: number;
  per_device_eval_batch_size: number;
  gradient_accumulation_steps: number;
  gradient_checkpointing: boolean;
  learning_rate: number;
  weight_decay: number;
  warmup_ratio: number;
  max_grad_norm: number;
  max_seq_length: number;
  validation_split_percentage: number;
  lora_config?: Record<string, any>;
  dpo_config?: Record<string, any>;
  orpo_config?: Record<string, any>;
  use_wandb: boolean;
  early_stopping: boolean;
}

// UI State Types
export interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  loading: boolean;
  error?: string;
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}
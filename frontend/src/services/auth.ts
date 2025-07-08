import api from './api';
import Cookies from 'js-cookie';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    name: string;
  };
}

export const authService = {
  async login(data: LoginRequest): Promise<AuthResponse> {
    // OAuth2 compatible login - use form data
    const formData = new URLSearchParams();
    formData.append('username', data.email);
    formData.append('password', data.password);
    
    const response = await api.post<AuthResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    const { access_token } = response.data;
    
    // Store token in cookie
    Cookies.set('access_token', access_token, {
      expires: 7, // 7 days
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
    });
    
    // Get user info
    const userResponse = await api.get('/auth/me');
    
    return {
      ...response.data,
      user: userResponse.data,
    };
  },

  async signup(data: SignupRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/signup', data);
    const { access_token } = response.data;
    
    // Store token in cookie
    Cookies.set('access_token', access_token, {
      expires: 7,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
    });
    
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } finally {
      Cookies.remove('access_token');
      window.location.href = '/login';
    }
  },

  async getCurrentUser() {
    const response = await api.get('/auth/me');
    return response.data;
  },

  isAuthenticated(): boolean {
    return !!Cookies.get('access_token');
  },
};
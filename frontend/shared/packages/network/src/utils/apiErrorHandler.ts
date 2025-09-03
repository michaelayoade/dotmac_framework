export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: any;
}

export class NetworkApiError extends Error {
  code?: string;
  status?: number;
  details?: any;

  constructor(message: string, code?: string, status?: number, details?: any) {
    super(message);
    this.name = 'NetworkApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export const handleApiError = (error: any): ApiError => {
  let apiError: ApiError = {
    message: 'An unexpected error occurred',
  };

  if (error.response) {
    // HTTP error response
    apiError = {
      message: error.response.data?.message || `HTTP ${error.response.status} Error`,
      code: error.response.data?.code || 'HTTP_ERROR',
      status: error.response.status,
      details: error.response.data,
    };
  } else if (error.request) {
    // Network error
    apiError = {
      message: 'Network connection failed',
      code: 'NETWORK_ERROR',
      details: { request: error.request },
    };
  } else if (error.message) {
    // JavaScript error
    apiError = {
      message: error.message,
      code: 'CLIENT_ERROR',
      details: error,
    };
  }

  return apiError;
};

export const logApiError = (context: string, error: ApiError): void => {
  console.error(`[NetworkAPI:${context}]`, {
    message: error.message,
    code: error.code,
    status: error.status,
    timestamp: new Date().toISOString(),
  });

  if (error.details) {
    console.error(`[NetworkAPI:${context}:Details]`, error.details);
  }
};

export const createApiErrorHandler = (context: string) => {
  return (error: any): ApiError => {
    const apiError = handleApiError(error);
    logApiError(context, apiError);
    return apiError;
  };
};

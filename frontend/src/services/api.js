const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Checks the operational health of the FastAPI backend.
 * @returns {Promise<{ status: string, service: string, version: string, timestamp?: string }>}
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

export { API_BASE_URL };

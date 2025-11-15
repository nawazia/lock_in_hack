import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api";

/**
 * Fetch all available trace runs from the backend
 */
export const fetchTraceRuns = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/traces`);
    return response.data;
  } catch (error) {
    console.error("Error fetching trace runs:", error);
    throw error;
  }
};

/**
 * Fetch detailed trace data for a specific run ID
 */
export const fetchTraceDetails = async (runId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/traces/${runId}`);
    return response.data;
  } catch (error) {
    console.error("Error fetching trace details:", error);
    throw error;
  }
};

/**
 * Fetch the latest trace
 */
export const fetchLatestTrace = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/traces/latest`);
    return response.data;
  } catch (error) {
    console.error("Error fetching latest trace:", error);
    throw error;
  }
};

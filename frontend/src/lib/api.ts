const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `API request to ${endpoint} failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err: any) {
    console.error(`[API Error] ${endpoint}:`, err.message);
    throw err;
  }
}

export const api = {
  // Analytics
  getDashboardSummary: () => fetchApi<any>("/analytics/summary"),
  getDemandSavings: () => fetchApi<any[]>("/analytics/demand-savings"),
  getQualityHeatmap: () => fetchApi<any[]>("/analytics/quality-heatmap"),
  getVennOverlap: () => fetchApi<any>("/analytics/venn-overlap"),

  // Ingestion
  detectColumns: async (file: File, cpseCode: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("cpse_code", cpseCode);
    const res = await fetch(`${API_BASE_URL}/ingestion/detect-columns`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Column detection failed" }));
      throw new Error(err.detail || "Column detection failed");
    }
    return await res.json();
  },
  startBatch: async (file: File, cpseCode: string, mappingJson: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("cpse_code", cpseCode);
    formData.append("mapping_config_json", mappingJson);
    const res = await fetch(`${API_BASE_URL}/ingestion/start-batch`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Batch start failed" }));
      throw new Error(err.detail || "Batch start failed");
    }
    return await res.json();
  },
  getBatches: () => fetchApi<any[]>("/ingestion/batches"),

  // Materials Catalog
  getMaterials: (params: { cpse_code?: string; search?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.cpse_code) q.append("cpse_code", params.cpse_code);
    if (params.search) q.append("search", params.search);
    if (params.limit) q.append("limit", params.limit.toString());
    return fetchApi<any[]>(`/materials?${q.toString()}`);
  },

  // Matching Engine & Review Queue
  triggerMatching: () => fetchApi<any>("/matching/trigger", { method: "POST" }),
  getReviewQueue: (statusFilter = "PENDING") =>
    fetchApi<any[]>(`/review/queue?status_filter=${statusFilter}`),
  getClusterDetails: (clusterGroupId: string) =>
    fetchApi<any>(`/review/cluster/${clusterGroupId}`),
  executeReviewAction: (actionData: {
    cluster_group_id: string;
    decision_type: string;
    custom_golden_description?: string;
    selected_material_ids?: number[];
    reviewer_notes?: string;
  }) =>
    fetchApi<any>("/review/action", {
      method: "POST",
      body: JSON.stringify(actionData),
    }),
  bulkApprove: (clusterGroupIds: string[], reviewerNotes = "Bulk approved high-confidence matches") =>
    fetchApi<any>("/review/bulk-approve", {
      method: "POST",
      body: JSON.stringify(clusterGroupIds),
    }),
  fileDispute: (clusterGroupId: string, disputeReason: string, dissentingCpse?: string) => {
    const q = new URLSearchParams({
      cluster_group_id: clusterGroupId,
      dispute_reason: disputeReason,
    });
    if (dissentingCpse) q.append("dissenting_cpse_code", dissentingCpse);
    return fetchApi<any>(`/review/dispute?${q.toString()}`, { method: "POST" });
  },

  // Crosswalk & Reverse Lookup
  reverseLookup: (localCode: string, cpseCode?: string) => {
    const q = new URLSearchParams();
    q.append("local_code", localCode);
    if (cpseCode) q.append("cpse_code", cpseCode);
    return fetchApi<any>(`/crosswalk/lookup?${q.toString()}`);
  },
  getCrosswalkRegistry: () => fetchApi<any[]>("/crosswalk/registry"),
};

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getAuthHeaders(): Record<string, string> {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  }
  return {};
}

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeaders(),
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
  getCpses: () => fetchApi<{ id: number; code: string; name: string; sector?: string }[]>("/ingestion/cpses"),
  detectColumns: async (file: File, cpseCode: string) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("cpse_code", cpseCode);
    const res = await fetch(`${API_BASE_URL}/ingestion/detect-columns`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Column detection failed" }));
      throw new Error(err.detail || "Column detection failed");
    }
    return await res.json();
  },
  startBatch: async (
    fileOrNull: File | null, 
    cpseCode: string, 
    mappingJson: string, 
    uploadId?: string
  ) => {
    const formData = new FormData();
    if (uploadId) {
      formData.append("upload_id", uploadId);
    } else if (fileOrNull) {
      formData.append("file", fileOrNull);
    }
    formData.append("cpse_code", cpseCode);
    formData.append("mapping_config_json", mappingJson);
    const res = await fetch(`${API_BASE_URL}/ingestion/start-batch`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Batch start failed" }));
      throw new Error(err.detail || "Batch start failed");
    }
    return await res.json();
  },
  getBatchStatus: (batchId: number) => fetchApi<any>(`/ingestion/batch/${batchId}/status`),
  getBatches: () => fetchApi<any[]>("/ingestion/batches"),
  getSamples: () => fetchApi<Record<string, any>>("/ingestion/samples"),
  recalculatePreview: (previewRows: any[], mappingConfig: Record<string, string>) =>
    fetchApi<any>("/ingestion/preview", {
      method: "POST",
      body: JSON.stringify({ preview_rows: previewRows, mapping_config: mappingConfig }),
    }),

  // Materials Catalog
  getMaterials: (params: { cpse_code?: string; search?: string; item_noun?: string; page?: number; page_size?: number; limit?: number; offset?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.cpse_code) q.append("cpse_code", params.cpse_code);
    if (params.search) q.append("search", params.search);
    if (params.item_noun) q.append("item_noun", params.item_noun);
    if (params.page) q.append("page", params.page.toString());
    if (params.page_size) q.append("page_size", params.page_size.toString());
    if (params.limit) q.append("limit", params.limit.toString());
    if (params.offset !== undefined) q.append("offset", params.offset.toString());
    return fetchApi<{
      items: any[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    }>(`/materials?${q.toString()}`);
  },
  getMaterialDetail: (materialId: number) => fetchApi<any>(`/materials/${materialId}`),
  getRefineries: () => fetchApi<{ id: number; code: string; name: string }[]>("/materials/refineries/list"),

  // Matching Engine & Review Queue
  triggerMatching: (payload?: { scope?: string; target_cpse_id?: number }) =>
    fetchApi<any>("/matching/trigger", {
      method: "POST",
      body: payload ? JSON.stringify(payload) : undefined
    }),
  promoteSingletons: (cpse_id?: number) =>
    fetchApi<any>("/review/promote-singletons", {
      method: "POST",
      body: JSON.stringify({ cpse_id })
    }),
  getReviewQueue: (
    params:
      | string
      | {
          statusFilter?: string;
          confidenceTier?: string;
          limit?: number;
          offset?: number;
        } = "PENDING"
  ) => {
    let sf = "PENDING";
    let ct: string | undefined;
    let lim = 50;
    let off = 0;
    if (typeof params === "string") {
      sf = params;
    } else if (params) {
      if (params.statusFilter) sf = params.statusFilter;
      if (params.confidenceTier) ct = params.confidenceTier;
      if (params.limit !== undefined) lim = params.limit;
      if (params.offset !== undefined) off = params.offset;
    }
    const q = new URLSearchParams({ status_filter: sf, limit: lim.toString(), offset: off.toString() });
    if (ct) q.append("confidence_tier", ct);
    return fetchApi<any[]>(`/review/queue?${q.toString()}`);
  },
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

  // Enterprise Integrations (SAP & GeM)
  syncGeMCatalog: (cnmcCodes?: string[]) =>
    fetchApi<any>("/integration/gem/catalog-sync", {
      method: "POST",
      body: JSON.stringify(cnmcCodes || []),
    }),
  exportSapIDoc: (cnmcCodes?: string[]) =>
    fetchApi<any>("/integration/sap/idoc-export", {
      method: "POST",
      body: JSON.stringify(cnmcCodes || []),
    }),

  // Cryptographic Audit & Lineage
  getAuditLogs: (params: { limit?: number; offset?: number; action?: string; entity_type?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.append("limit", params.limit.toString());
    if (params.offset) q.append("offset", params.offset.toString());
    if (params.action) q.append("action", params.action);
    if (params.entity_type) q.append("entity_type", params.entity_type);
    return fetchApi<any[]>(`/audit/logs?${q.toString()}`);
  },
  verifyAuditChain: () => fetchApi<any>("/audit/verify-chain"),
};

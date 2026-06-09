const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(detail.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface DomainInfo {
  name: string;
  source_count: number;
  has_instructions: boolean;
}

export interface SourceInfo {
  name: string;
  domain: string;
  has_spec: boolean;
}

export interface InputTreeNode {
  domain: string;
  sources: string[];
}

export interface ContentResponse {
  content: string;
}

export interface OKResponse {
  ok: boolean;
}

export interface FeedbackRound {
  round: number;
  timestamp: string;
  feedback_text: string;
  decision: string;
}

export interface SessionInfo {
  session_id: string;
  domain: string;
  source: string;
  status: string;
  created_at: string;
  last_modified_at: string;
  feedback_rounds: FeedbackRound[];
  accumulated_instructions: string;
}

export interface ReviewSubmit {
  decision: string;
  feedback: string;
}

export interface ExtractionResult {
  file_metadata: Record<string, string | null>;
  fields: Array<Record<string, unknown>>;
  warnings: string[];
  feedback_rounds?: FeedbackRound[];
}

export interface ReviewData {
  session_id: string;
  domain: string;
  source: string;
  status: string;
  result: ExtractionResult;
  feedback_rounds: FeedbackRound[];
}

export interface SSEEvent {
  type: string;
  phase?: string;
  chunks?: number;
  chunk?: number;
  total?: number;
  session_id?: string;
  status?: string;
  message?: string;
}

export interface SourceSummary {
  name: string;
  latest_version: number;
  total_versions: number;
}

export interface OutputTreeNode {
  domain: string;
  sources: SourceSummary[];
}

export interface VersionEntry {
  version: number;
  session_id: string;
  created_at: string;
  filename: string;
  based_on_version: number | null;
  feedback_rounds: number;
}

export interface VersionFileList {
  domain: string;
  source: string;
  latest_version: number;
  versions: VersionEntry[];
}

export interface OutputWithVersion {
  version: number;
  session_id: string;
  created_at: string;
  based_on_version: number | null;
  data: Record<string, unknown>;
}

export interface MetadataDiff {
  added: Record<string, unknown>;
  removed: Record<string, unknown>;
  changed: Record<string, { old: unknown; new: unknown }>;
}

export interface FieldDiffItem {
  key: { field_group: string; field_index: number | null; field_name: string };
  changes: Record<string, { old: unknown; new: unknown }>;
}

export interface FieldsDiff {
  added: Array<Record<string, unknown>>;
  removed: Array<Record<string, unknown>>;
  changed: FieldDiffItem[];
}

export interface WarningsDiff {
  added: string[];
  removed: string[];
}

export interface VersionDiff {
  v1: number;
  v2: number;
  v1_session_id: string;
  v2_session_id: string;
  v1_created_at: string;
  v2_created_at: string;
  file_metadata: MetadataDiff;
  fields: FieldsDiff;
  warnings: WarningsDiff;
}

export interface VersionChainItem {
  version: number;
  session_id: string;
  created_at: string;
  feedback_rounds: number;
  is_based_on_feedback: boolean;
}

export interface VersionChainResponse {
  domain: string;
  source: string;
  chain: VersionChainItem[];
}

export const api = {
  listDomains: () => request<DomainInfo[]>('/domains'),

  createDomain: (name: string) =>
    request<DomainInfo>('/domains', { method: 'POST', body: JSON.stringify({ name }) }),

  deleteDomain: (name: string) =>
    request<OKResponse>(`/domains/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  getInstructions: (domain: string) =>
    request<ContentResponse>(`/domains/${encodeURIComponent(domain)}/instructions`),

  saveInstructions: (domain: string, content: string) =>
    request<OKResponse>(`/domains/${encodeURIComponent(domain)}/instructions`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),

  listSources: (domain: string) =>
    request<SourceInfo[]>(`/domains/${encodeURIComponent(domain)}/sources`),

  createSource: (domain: string, name: string) =>
    request<SourceInfo>(`/domains/${encodeURIComponent(domain)}/sources`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  deleteSource: (domain: string, name: string) =>
    request<OKResponse>(`/domains/${encodeURIComponent(domain)}/sources/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    }),

  uploadSpec: (domain: string, source: string, content: string, stripEmptyLines?: boolean) => {
    const params = new URLSearchParams();
    if (stripEmptyLines !== undefined) params.set('strip_empty_lines', String(stripEmptyLines));
    const qs = params.toString();
    return request<OKResponse>(
      `/domains/${encodeURIComponent(domain)}/sources/${encodeURIComponent(source)}/upload-spec${qs ? `?${qs}` : ''}`,
      {
        method: 'POST',
        body: JSON.stringify({ content }),
      },
    );
  },

  getSpec: (domain: string, source: string) =>
    request<ContentResponse>(`/domains/${encodeURIComponent(domain)}/sources/${encodeURIComponent(source)}/spec`),

  getInputTree: () => request<InputTreeNode[]>('/input-tree'),

  listSessions: (status?: string, domain?: string) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (domain) params.set('domain', domain);
    const qs = params.toString();
    return request<SessionInfo[]>(`/sessions${qs ? '?' + qs : ''}`);
  },

  createSession: (domain: string, source: string) =>
    request<SessionInfo>('/sessions', {
      method: 'POST',
      body: JSON.stringify({ domain, source }),
    }),

  getSession: (id: string) => request<SessionInfo>(`/sessions/${encodeURIComponent(id)}`),

  deleteSession: (id: string) =>
    request<OKResponse>(`/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  startExtraction: (sessionId: string, domain?: string, source?: string) => {
    const params = new URLSearchParams();
    if (domain) params.set('domain', domain);
    if (source) params.set('source', source);
    const qs = params.toString();
    return fetch(`/api/sessions/${encodeURIComponent(sessionId)}/start${qs ? '?' + qs : ''}`, { method: 'POST' });
  },

  getReviewData: (sessionId: string) =>
    request<ReviewData>(`/sessions/${encodeURIComponent(sessionId)}/review`),

  submitReview: (sessionId: string, decision: string, feedback: string) =>
    request<OKResponse>(`/sessions/${encodeURIComponent(sessionId)}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, feedback }),
    }),

  listOutputTree: () => request<OutputTreeNode[]>('/outputs'),

  listOutputVersions: (domain: string, source: string) =>
    request<VersionFileList>(`/outputs/${encodeURIComponent(domain)}/${encodeURIComponent(source)}`),

  getLatestOutput: (domain: string, source: string) =>
    request<OutputWithVersion>(`/outputs/${encodeURIComponent(domain)}/${encodeURIComponent(source)}/latest`),

  getOutputByVersion: (domain: string, source: string, version: number) =>
    request<OutputWithVersion>(`/outputs/${encodeURIComponent(domain)}/${encodeURIComponent(source)}/versions/${version}`),

  diffOutputs: (domain: string, source: string, v1: number, v2: number) =>
    request<VersionDiff>(`/outputs/${encodeURIComponent(domain)}/${encodeURIComponent(source)}/diff?v1=${v1}&v2=${v2}`),

  getVersionChain: (domain: string, source: string, version?: number) => {
    const qs = version !== undefined ? `?version=${version}` : '';
    return request<VersionChainResponse>(`/outputs/${encodeURIComponent(domain)}/${encodeURIComponent(source)}/chain${qs}`);
  },

  getManifest: (domain: string, source: string) =>
    request<{ domain: string; source: string; latest_version: number; versions: VersionEntry[] }>(
      `/outputs/${encodeURIComponent(domain)}/${encodeURIComponent(source)}/manifest`
    ),

  getOutput: (domain: string, source: string, filename: string) =>
    request<Record<string, unknown>>(`/outputs/${encodeURIComponent(domain)}/${encodeURIComponent(source)}/${encodeURIComponent(filename)}`),
};

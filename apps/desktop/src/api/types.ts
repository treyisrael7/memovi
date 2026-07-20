export interface HealthResponse {
  status: string;
}

export interface ReadyComponent {
  name: string;
  status: string;
  detail?: string;
}

export interface ReadyResponse {
  status: "ready" | "not_ready" | string;
  components: ReadyComponent[];
  environment: string;
}

export interface WorkspaceResponse {
  id: string;
  name: string;
  created_at: string;
}

export interface WorkspaceListResponse {
  workspaces: WorkspaceResponse[];
  count: number;
}

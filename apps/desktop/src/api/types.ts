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

export interface ConversationSummary {
  conversation_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}

export interface ConversationMetadata {
  conversation_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Citation {
  document_id: string;
  chunk_id: string;
  document_title?: string | null;
  score?: number | null;
}

export interface ConversationMessage {
  role: "user" | "assistant" | string;
  content: string;
  timestamp: string;
  citations: Citation[];
}

export interface ConversationMessagesResponse {
  conversation_id: string;
  messages: ConversationMessage[];
}

export interface CreateConversationResponse {
  conversation_id: string;
  title: string;
  created_at: string;
}

export interface SendMessageResponse {
  conversation_id: string;
  assistant_message: string;
  citations: Citation[];
  provider: string;
  model: string;
  title?: string | null;
  execution: {
    execution_time: number;
    stages: Array<{
      stage: string;
      started_at: string;
      finished_at: string;
      duration: number;
    }>;
    metrics: {
      provider: string;
      model: string;
      estimated_input_tokens: number;
      output_tokens: number | null;
      retrieved_knowledge_count: number;
      document_count: number;
      citation_count: number;
    };
    metadata: Record<string, unknown>;
  };
}

export interface AvailableModel {
  provider: string;
  model: string;
  label: string;
}

export interface AvailableModelsResponse {
  default_provider: string;
  default_model: string;
  models: AvailableModel[];
}

export interface SearchResultItem {
  search_document_id: string;
  knowledge_item_id: string;
  document_id: string;
  score: number;
  text: string;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchResultItem[];
}

export interface DocumentSummary {
  id: string;
  name: string;
  mime_type: string;
  source_type: string;
  created_at: string;
}

export interface DocumentListResponse {
  items: DocumentSummary[];
}

export interface KnowledgeChunk {
  id: string;
  knowledge_item_id: string | null;
  document_id: string;
  document_version_id: string;
  chunk_index: number;
  text: string;
  created_at: string;
}

export interface KnowledgeSummary {
  id: string;
  workspace_id: string;
  document_id: string;
  document_version_id: string;
  source_type: string;
  mime_type: string;
  created_at: string;
  updated_at: string;
  chunk_count: number;
  summary: string;
  confidence: number | null;
}

export interface KnowledgeSummaryListResponse {
  items: KnowledgeSummary[];
  count: number;
}

export interface KnowledgeDetail extends KnowledgeSummary {
  chunks: KnowledgeChunk[];
}

export interface ConceptSummary {
  id: string;
  kind: string;
  label: string;
  knowledge_item_count: number;
  knowledge_item_ids: string[];
}

export interface ConceptListResponse {
  items: ConceptSummary[];
  count: number;
}

export interface RelationshipSummary {
  id: string;
  relationship_type: string;
  from_kind: string;
  from_id: string;
  to_kind: string;
  to_id: string;
  workspace_id: string;
  document_id: string;
  knowledge_item_id: string | null;
  created_at: string;
}

export interface RelationshipListResponse {
  items: RelationshipSummary[];
  count: number;
}

export interface KnowledgeDashboard {
  workspace_id: string;
  knowledge_item_count: number;
  chunk_count: number;
  source_document_count: number;
  concept_count: number;
  relationship_count: number;
  source_type_counts: Record<string, number>;
  mime_type_counts: Record<string, number>;
}

export type CapabilityExecutionStatus =
  | "pending_approval"
  | "executing"
  | "completed"
  | "failed"
  | "cancelled"
  | string;

export type PermissionMode =
  | "always_allow"
  | "ask_every_time"
  | "deny"
  | string;

export interface CapabilityExecution {
  execution_id: string;
  capability_id: string;
  workspace_id: string;
  status: CapabilityExecutionStatus;
  permission_mode: PermissionMode;
  output?: unknown;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
  error_code?: string | null;
  error_message?: string | null;
  duration: number;
  conversation_id?: string | null;
  correlation_id?: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface CapabilityExecutionListResponse {
  items: CapabilityExecution[];
  count: number;
}

export interface ConversationCapabilityExecutionListResponse {
  conversation_id: string;
  items: CapabilityExecution[];
  count: number;
}

export interface CapabilityMetadata {
  id: string;
  description: string;
  permissions: string[];
  parameters: Array<{
    name: string;
    type: string;
    description: string;
    required: boolean;
  }>;
  permission_mode: PermissionMode;
}

export interface CapabilityListResponse {
  items: CapabilityMetadata[];
  count: number;
}

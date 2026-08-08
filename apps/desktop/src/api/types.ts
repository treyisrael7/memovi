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
  role?: string | null;
}

export interface WorkspaceListResponse {
  workspaces: WorkspaceResponse[];
  count: number;
}

export interface WorkspaceMembership {
  id: string;
  workspace_id: string;
  user_id: string;
  role: string;
  created_at: string;
  email?: string | null;
}

export interface WorkspaceMembershipListResponse {
  items: WorkspaceMembership[];
  count: number;
}

export interface TransferWorkspaceOwnershipResponse {
  previous_owner: WorkspaceMembership;
  new_owner: WorkspaceMembership;
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

export type ProcessingStatus =
  | "pending"
  | "extracting"
  | "normalizing"
  | "completed"
  | "failed"
  | "cancelled"
  | string;

export interface DocumentSummary {
  id: string;
  name: string;
  mime_type: string;
  source_type: string;
  created_at: string;
  processing_status?: ProcessingStatus | null;
  processing_failure_reason?: string | null;
  processing_updated_at?: string | null;
  processing_attempt?: number | null;
  processing_started_at?: string | null;
  processing_completed_at?: string | null;
}

export interface DocumentListResponse {
  items: DocumentSummary[];
}

export interface ConnectorMetadata {
  connector_id: string;
  display_name: string;
  description: string;
  source_category: string;
  auth_methods: string[];
  supports_incremental_sync: boolean;
  supports_delete_detection: boolean;
}

export interface ConnectorListResponse {
  items: ConnectorMetadata[];
  count: number;
}

export interface FilesystemFolder {
  id: string;
  workspace_id: string;
  root_path: string;
  display_name: string;
  sync_status: string;
  last_error?: string | null;
  imported_document_count: number;
  last_synchronized_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FilesystemFolderListResponse {
  items: FilesystemFolder[];
  count: number;
}

export interface SyncFilesystemFolderResponse {
  folder: FilesystemFolder;
  success: boolean;
  sync_mode: string;
  imported_count: number;
  updated_count: number;
  deleted_count: number;
  skipped_count: number;
  error_code?: string | null;
  error_message?: string | null;
}

export interface IngestDocumentResponse {
  document_id: string;
  processing_job_id: string;
  processing_status: ProcessingStatus;
}

export interface ReprocessDocumentResponse {
  document_id: string;
  processing_job_id: string;
  processing_status: ProcessingStatus;
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

export interface CollectionListItem {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  item_count: number;
  counts_by_kind: Record<string, number>;
}

export interface CollectionListResponse {
  items: CollectionListItem[];
  count: number;
}

export interface CollectionResponse {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface CollectionActivityEntry {
  activity_type: string;
  occurred_at: string;
  member_kind: string | null;
  member_id: string | null;
  detail: string;
}

export interface CollectionSummaryResponse {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  item_count: number;
  counts_by_kind: Record<string, number>;
  recent_activity: CollectionActivityEntry[];
}

export interface CollectionMembershipResponse {
  id: string;
  collection_id: string;
  member_kind: string;
  member_id: string;
  reason: string;
  added_at: string;
}

export interface CollectionMembershipListResponse {
  items: CollectionMembershipResponse[];
  count: number;
}

export interface TagResponse {
  id: string;
  workspace_id: string;
  name: string;
  color: string | null;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface TagListItem {
  id: string;
  workspace_id: string;
  name: string;
  color: string | null;
  description: string;
  created_at: string;
  updated_at: string;
  assignment_count: number;
  counts_by_kind: Record<string, number>;
}

export interface TagListResponse {
  items: TagListItem[];
  count: number;
}

export interface TagSuggestResponse {
  items: TagResponse[];
  count: number;
}

export interface TagAssignmentResponse {
  id: string;
  tag_id: string;
  member_kind: string;
  member_id: string;
  assigned_at: string;
}

export interface TagAssignmentListResponse {
  items: TagAssignmentResponse[];
  count: number;
}

export interface ResourceMetadataResponse {
  workspace_id: string;
  member_kind: string;
  member_id: string;
  title: string | null;
  description: string | null;
  notes: string | null;
  updated_at: string;
}

export type CapabilityExecutionStatus =
  | "pending_approval"
  | "executing"
  | "completed"
  | "failed"
  | "cancelled"
  | string;

export type PermissionMode =
  "always_allow" | "ask_every_time" | "deny" | string;

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

export interface ExecutionAuditEntry {
  id: string;
  execution_id: string;
  workspace_id: string;
  user_id: string;
  capability_id: string;
  operation: string;
  status: CapabilityExecutionStatus;
  permission_mode: PermissionMode;
  arguments: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  duration: number;
  timestamp: string;
  conversation_id?: string | null;
  correlation_id?: string | null;
  source: string;
}

export interface ExecutionAuditListResponse {
  items: ExecutionAuditEntry[];
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

export interface PermissionModeResponse {
  capability_id: string;
  permission_mode: PermissionMode;
}

export type WorkflowExecutionStatus =
  | "completed"
  | "failed"
  | "awaiting_approval"
  | "cancelled"
  | "running"
  | string;

export interface WorkflowVariable {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: unknown;
}

export interface WorkflowStepDefinition {
  step_id: string;
  capability_id: string;
  operation: string;
  input_mapping: Record<string, unknown>;
  output_mapping: Record<string, string>;
  expected_result?: string | null;
  description: string;
}

export interface WorkflowDefinition {
  workflow_id: string;
  name: string;
  description: string;
  steps: WorkflowStepDefinition[];
  variables: WorkflowVariable[];
  required_capabilities: string[];
  expected_outputs: string[];
  metadata: Record<string, unknown>;
}

export interface WorkflowListResponse {
  items: WorkflowDefinition[];
  count: number;
}

export interface WorkflowStepResult {
  step_id: string;
  capability_id: string;
  operation: string;
  execution_id: string | null;
  status: string;
  output?: unknown;
  error_code?: string | null;
  error_message?: string | null;
  duration: number;
  plan_id?: string | null;
}

export interface WorkflowExecutionResult {
  instance_id: string;
  workflow_id: string;
  workflow_name: string;
  workspace_id: string;
  status: WorkflowExecutionStatus;
  completed_steps: string[];
  failed_steps: string[];
  step_results: WorkflowStepResult[];
  duration: number;
  outputs: Record<string, unknown>;
  errors: string[];
  audit_references: string[];
  started_at: string;
  finished_at?: string | null;
  metadata: Record<string, unknown>;
}

export interface WorkflowHistoryEntry {
  instance_id: string;
  workflow_id: string;
  workflow_name: string;
  workspace_id: string;
  status: WorkflowExecutionStatus;
  executed_at: string;
  duration: number;
  result_summary: Record<string, unknown>;
  executed_capabilities: string[];
  audit_references: string[];
}

export interface WorkflowHistoryListResponse {
  items: WorkflowHistoryEntry[];
  count: number;
}

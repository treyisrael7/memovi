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

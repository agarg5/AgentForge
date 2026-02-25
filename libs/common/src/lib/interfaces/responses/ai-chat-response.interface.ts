export interface AiVerificationCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface AiCostMetrics {
  model: string;
  input_cost_usd: number;
  output_cost_usd: number;
  total_cost_usd: number;
}

export interface AiMetrics {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  tool_call_count: number;
  latency_seconds: number;
  cost: AiCostMetrics;
  verification: AiVerificationCheck[];
}

export interface AiChatResponse {
  role: 'agent';
  content: string;
  tools_used?: string[];
  tool_count?: number;
  run_id?: string;
  metrics?: AiMetrics;
}

export interface AiFeedbackRequest {
  run_id: string;
  score: number;
  comment?: string;
}

export interface AiToolInfo {
  name: string;
  description: string;
  type: 'read' | 'write';
}

export interface AiVerificationInfo {
  name: string;
  description: string;
}

export interface AiEvalStats {
  total_cases: number;
  categories: Record<string, number>;
  scorers: string[];
}

export interface AiCostModel {
  model: string;
  pricing: {
    input_per_1m_tokens_usd: number;
    output_per_1m_tokens_usd: number;
  };
  projections: {
    avg_tokens_per_request: { input: number; output: number };
    cost_per_request_usd: number;
    daily_100_requests_usd: number;
    monthly_3000_requests_usd: number;
  };
}

export interface AiPerformanceTargets {
  latency_seconds: number;
  multi_step_latency_seconds: number;
  tool_success_rate: number;
  eval_pass_rate: number;
  hallucination_rate: number;
  verification_accuracy: number;
}

export interface AiAgentConfig {
  model: string;
  max_agent_steps: number;
  max_history_messages: number;
  tracing_enabled: boolean;
  memory_backend: string;
  chat_history_backend: string;
}

export interface AiAdminOverviewResponse {
  tools: AiToolInfo[];
  verification: {
    checks: AiVerificationInfo[];
    total_checks: number;
  };
  evals: AiEvalStats;
  cost: AiCostModel;
  performance_targets: AiPerformanceTargets;
  observability?: Record<string, string>;
  config: AiAgentConfig;
}

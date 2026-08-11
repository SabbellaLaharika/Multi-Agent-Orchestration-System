export type TaskStatus = 'IDLE' | 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';

export interface AgentEventPayload {
  thought?: string;
  plan?: string[];
  tool?: string;
  input?: Record<string, any>;
  purpose?: string;
  result?: string;
  final_result?: string;
  message?: string;
}

export interface AgentEvent {
  task_id: string;
  event_type: 'CONNECTION_ESTABLISHED' | 'AGENT_THOUGHT' | 'TOOL_INVOCATION' | 'TOOL_RESULT' | 'ERROR' | 'COMPLETED';
  agent: string;
  payload: AgentEventPayload;
  timestamp: string;
  status?: string;
  final_result?: string;
}

export interface TaskRun {
  task_id: string;
  prompt: string;
  status: TaskStatus;
  final_result?: string;
  events: AgentEvent[];
}

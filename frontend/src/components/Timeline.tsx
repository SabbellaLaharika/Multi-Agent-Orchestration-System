import React from 'react';
import { AgentEvent } from '../types';
import { Brain, Search, Wrench, Sparkles, AlertTriangle, CheckCircle2, Terminal } from 'lucide-react';

interface TimelineProps {
  events: AgentEvent[];
  isConnected: boolean;
}

export const Timeline: React.FC<TimelineProps> = ({ events, isConnected }) => {
  if (events.length === 0) {
    return (
      <div className="timeline-empty-state">
        <Terminal size={36} className="text-secondary opacity-50" />
        <p>No active workflow stream yet. Submit a prompt above to visualize real-time agent execution.</p>
      </div>
    );
  }

  const getAgentTheme = (agent: string, eventType: string) => {
    switch (agent) {
      case 'Planner':
        return { icon: Brain, color: 'cyan', badge: 'Planner Agent' };
      case 'Researcher':
        return eventType === 'TOOL_INVOCATION' || eventType === 'TOOL_RESULT'
          ? { icon: Wrench, color: 'amber', badge: 'Tool Execution' }
          : { icon: Search, color: 'purple', badge: 'Researcher Agent' };
      case 'Synthesizer':
        return { icon: Sparkles, color: 'green', badge: 'Synthesizer Agent' };
      default:
        return { icon: CheckCircle2, color: 'blue', badge: agent || 'System' };
    }
  };

  return (
    <div className="timeline-container">
      <div className="timeline-header">
        <h3>Live Event Trace Log</h3>
        <span className={`ws-badge ${isConnected ? 'connected' : 'connecting'}`}>
          {isConnected ? '• WebSocket Live Stream' : '• Connecting...'}
        </span>
      </div>

      <div className="timeline-list">
        {events.map((evt, idx) => {
          const { icon: Icon, color, badge } = getAgentTheme(evt.agent, evt.event_type);
          const timeStr = new Date(evt.timestamp || Date.now()).toLocaleTimeString();

          return (
            <div key={idx} className={`timeline-item theme-${color}`}>
              <div className="timeline-icon">
                <Icon size={18} />
              </div>

              <div className="timeline-content">
                <div className="timeline-meta">
                  <span className={`agent-badge badge-${color}`}>{badge}</span>
                  <span className="event-type">{evt.event_type}</span>
                  <span className="timestamp">{timeStr}</span>
                </div>

                {evt.payload?.thought && (
                  <div className="thought-box">
                    <p className="thought-text">💭 {evt.payload.thought}</p>
                  </div>
                )}

                {evt.payload?.plan && (
                  <div className="plan-box">
                    <span className="box-title">Formulated Action Plan:</span>
                    <ol>
                      {evt.payload.plan.map((step, sIdx) => (
                        <li key={sIdx}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {evt.event_type === 'TOOL_INVOCATION' && (
                  <div className="tool-call-box">
                    <div className="box-title">
                      <span>Invoking Tool: <code>{evt.payload.tool}</code></span>
                    </div>
                    {evt.payload.purpose && <p className="purpose-text">Purpose: {evt.payload.purpose}</p>}
                    {evt.payload.input && (
                      <pre className="code-snippet">{JSON.stringify(evt.payload.input, null, 2)}</pre>
                    )}
                  </div>
                )}

                {evt.event_type === 'TOOL_RESULT' && (
                  <div className="tool-result-box">
                    <div className="box-title">
                      <span>Tool Output: <code>{evt.payload.tool}</code></span>
                    </div>
                    <pre className="result-text">{evt.payload.result}</pre>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

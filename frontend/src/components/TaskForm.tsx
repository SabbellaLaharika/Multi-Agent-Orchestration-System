import React, { useState } from 'react';
import { Play, Sparkles, CloudSun, Calculator, Newspaper } from 'lucide-react';

interface TaskFormProps {
  onSubmit: (prompt: string) => Promise<void>;
  isLoading: boolean;
}

const SAMPLE_PROMPTS = [
  {
    label: 'Weather & Travel Planner',
    icon: CloudSun,
    prompt: 'What is the current weather in Tokyo, and based on that, what should I pack for a 3-day trip?',
  },
  {
    label: 'Data & Arithmetic Calculation',
    icon: Calculator,
    prompt: 'Calculate (45 * 12) + (350 / 5) and analyze the data trend impact for tech budgets.',
  },
  {
    label: 'News & Web Research',
    icon: Newspaper,
    prompt: 'Search latest news updates on multi-agent AI framework benchmarks and summarize top findings.',
  },
];

export const TaskForm: React.FC<TaskFormProps> = ({ onSubmit, isLoading }) => {
  const [prompt, setPrompt] = useState<string>('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;
    onSubmit(prompt);
  };

  const handleSelectPreset = (presetPrompt: string) => {
    setPrompt(presetPrompt);
  };

  return (
    <div className="task-form-card">
      <div className="card-header">
        <Sparkles className="icon-gold" size={20} />
        <h2>Initiate Multi-Agent Workflow</h2>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="prompt-input">Enter Complex Problem Prompt:</label>
          <textarea
            id="prompt-input"
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. What is the current weather in Tokyo, and based on that, what should I pack?"
            disabled={isLoading}
            required
          />
        </div>

        <div className="preset-container">
          <span className="preset-label">Quick Prompts:</span>
          <div className="preset-buttons">
            {SAMPLE_PROMPTS.map((item, idx) => {
              const Icon = item.icon;
              return (
                <button
                  key={idx}
                  type="button"
                  className="preset-btn"
                  onClick={() => handleSelectPreset(item.prompt)}
                  disabled={isLoading}
                >
                  <Icon size={14} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="submit-btn"
            disabled={isLoading || !prompt.trim()}
          >
            <Play size={18} />
            <span>{isLoading ? 'Dispatching Agents...' : 'Start Orchestration Workflow'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

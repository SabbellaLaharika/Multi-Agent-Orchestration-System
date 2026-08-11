import React from 'react';
import { Bot, Cpu, Activity } from 'lucide-react';

interface NavbarProps {
  status: string;
}

export const Navbar: React.FC<NavbarProps> = ({ status }) => {
  return (
    <header className="navbar-container">
      <div className="navbar-brand">
        <div className="navbar-logo-icon">
          <Cpu className="icon-pulse" size={24} />
        </div>
        <div>
          <h1 className="navbar-title">Multi-Agent AI Orchestration</h1>
          <p className="navbar-subtitle">LangGraph • FastAPI • Celery • PostgreSQL • React</p>
        </div>
      </div>
      <div className="navbar-status-badge">
        <Activity size={16} className={status === 'IN_PROGRESS' ? 'animate-spin text-cyan' : ''} />
        <span className="status-text">{status}</span>
      </div>
    </header>
  );
};

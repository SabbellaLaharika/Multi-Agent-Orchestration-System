import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { TaskForm } from './components/TaskForm';
import { Timeline } from './components/Timeline';
import { FinalResultCard } from './components/FinalResultCard';
import { useAgentWebSocket } from './hooks/useAgentWebSocket';
import { TaskStatus } from './types';

export default function App() {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus>('IDLE');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { events, isConnected, resetEvents } = useAgentWebSocket(currentTaskId);

  const handleTaskSubmit = async (prompt: string) => {
    setIsSubmitting(true);
    setErrorMsg(null);
    setTaskStatus('PENDING');
    resetEvents();

    try {
      const response = await fetch('http://localhost:8000/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: Unable to create task.`);
      }

      const data = await response.json();
      setCurrentTaskId(data.task_id);
      setTaskStatus('IN_PROGRESS');
    } catch (err: any) {
      console.error('Task submission failed:', err);
      setErrorMsg(err.message || 'Failed to submit task to backend.');
      setTaskStatus('FAILED');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Find final synthesized output from events if completed
  const lastEvent = events[events.length - 1];
  const finalResult = events.find((e) => e.final_result)?.final_result || lastEvent?.payload?.final_result;
  const currentStatus = lastEvent?.status || (finalResult ? 'COMPLETED' : taskStatus);

  return (
    <div className="app-main-layout">
      <Navbar status={currentStatus} />

      <main className="main-content-container">
        {errorMsg && (
          <div className="error-alert">
            <span>⚠️ {errorMsg}</span>
          </div>
        )}

        <TaskForm onSubmit={handleTaskSubmit} isLoading={isSubmitting} />

        {currentTaskId && (
          <div className="task-id-bar">
            <span>Active Task ID: <code>{currentTaskId}</code></span>
          </div>
        )}

        <Timeline events={events} isConnected={isConnected} />

        {finalResult && <FinalResultCard result={finalResult} />}
      </main>
    </div>
  );
}

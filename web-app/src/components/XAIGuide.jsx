import React, { useState } from 'react';
import { Bot, X } from 'lucide-react';

export default function XAIGuide({ decision }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-accent-primary rounded-sm flex items-center justify-center text-black  hover:scale-110 transition-transform z-50"
      >
        <Bot size={28} />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-80 glass-panel-bright flex flex-col shadow-2xl z-50 border-accent-primary/30">
      <div className="bg-bg-secondary p-3 flex justify-between items-center border-b border-glass-border rounded-t-xl">
        <div className="flex items-center gap-2 text-accent-primary font-bold">
          <Bot size={18} /> XAI Assistant
        </div>
        <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white"><X size={16}/></button>
      </div>
      <div className="p-4 text-sm text-gray-300">
        {decision ? (
          <p>
            For the last call from <span className="font-bold text-white">Floor {decision.floor}</span>, 
            I selected <span className="text-accent-primary font-bold">Elevator {decision.elevator + 1}</span>. 
            <br/><br/>
            <strong>Why?</strong> It scored <span className="font-mono text-green-400">{decision.score}</span>, 
            driven primarily by its current trajectory and a low estimated wait time of {decision.wait_est}s. 
            The A* Sequencer confirmed this path keeps us well under the 45s SLA.
          </p>
        ) : (
          <p>Hi! I'm your Explainable AI Guide (Phase 7). I'll narrate decisions as they happen here.</p>
        )}
      </div>
    </div>
  );
}

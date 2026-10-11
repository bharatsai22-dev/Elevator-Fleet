import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function WeightsPanel({ weights = {} }) {
  // Convert weights object to array for recharts
  const data = Object.keys(weights).map(key => ({
    name: key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value: parseFloat((weights[key] * 100).toFixed(1)),
    originalKey: key
  }));

  // Define colors for different weights
  const getBarColor = (key) => {
    const colors = {
      direction_bias: '#3b82f6', // blue
      load_balance: '#10b981',   // green
      distance: '#a855f7',       // purple
      wait_time: '#FFB300',      // amber
      emergency_bonus: '#ef4444', // red
      fairness: '#06b6d4'        // cyan
    };
    return colors[key] || '#FFB300';
  };

  return (
    <div className="glass-panel p-5 h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
          GBFS Dynamic Weights
        </h3>
        <span className="badge badge-amber">Live Updates</span>
      </div>
      
      <div className="flex-1 min-h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis 
              dataKey="name" 
              type="category" 
              axisLine={false} 
              tickLine={false}
              tick={{ fill: '#94a3b8', fontSize: 12 }}
              width={120}
            />
            <Tooltip 
              cursor={{ fill: 'rgba(255,255,255,0.05)' }}
              contentStyle={{ backgroundColor: '#0c1222', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
              itemStyle={{ color: '#fff', fontWeight: 'bold' }}
              formatter={(value) => [`${value}%`, 'Weight']}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.originalKey)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

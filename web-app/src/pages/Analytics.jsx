import React, { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import { Activity, BarChart2, Route } from 'lucide-react';
import { MetricCard } from '../components/MetricsBar';
import PageHeader from '../components/PageHeader';

const HISTORY_LIMIT = 60;

const tooltipStyle = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  color: 'var(--text)',
  fontSize: 12
};
const axisTick = { fill: 'var(--muted)', fontSize: 11 };

export default function Analytics({ simState }) {
  const [waitHistory, setWaitHistory] = useState([]);

  useEffect(() => {
    if (!simState?.metrics || !simState.running) return;
    setWaitHistory((prev) => {
      const last = prev[prev.length - 1];
      // A lower step than the last point means the simulation was reset
      const base = last && simState.step < last.step ? [] : prev;
      if (base.length && base[base.length - 1].step === simState.step) return base;
      return [...base, { step: simState.step, wait: simState.metrics.avg_wait || 0 }].slice(-HISTORY_LIMIT);
    });
  }, [simState?.step]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!simState) {
    return (
      <div className="flex-1 flex items-center justify-center" role="status">
        <p className="muted text-sm">Connecting to analytics…</p>
      </div>
    );
  }

  const { metrics, elevators } = simState;
  const completionRate = metrics.total_calls
    ? Math.round(((metrics.completed || 0) / metrics.total_calls) * 100)
    : null;

  const distanceData = elevators.map((e) => ({
    name: `E${e.id + 1}`,
    distance: e.distance,
    offline: !e.operational
  }));

  return (
    <div className="page custom-scrollbar">
      <PageHeader
        icon={BarChart2}
        title="System analytics"
        description="Performance telemetry and SLA compliance for the current simulation run."
        badge={
          <span className={`badge ${metrics.sla_met ? 'badge-success' : 'badge-critical'}`}>
            {metrics.sla_met ? 'Within SLA' : 'SLA breached'}
          </span>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Avg wait" value={metrics.avg_wait || '—'} unit="s" color={metrics.sla_met ? 'green' : 'red'} />
        <MetricCard label="Total calls" value={metrics.total_calls || 0} color="blue" />
        <MetricCard label="Completed" value={metrics.completed || 0} color="green" />
        <MetricCard label="Rejections" value={metrics.rejections || 0} color="red" />
      </div>

      <p className="muted text-sm -mt-2">
        SLA target: <span className="num">{metrics.sla_target}s</span> average wait
        {completionRate !== null && (
          <> · Completion rate: <span className="num">{completionRate}%</span></>
        )}
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="panel panel-pad flex flex-col h-[360px]">
          <h3 className="panel-title">
            <Activity size={16} style={{ color: 'var(--accent)' }} aria-hidden="true" />
            Average wait over time
          </h3>
          <div className="flex-1 min-h-0 w-full">
            {waitHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={waitHistory} margin={{ top: 10, right: 12, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="waitFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" style={{ stopColor: 'var(--accent)', stopOpacity: 0.35 }} />
                      <stop offset="95%" style={{ stopColor: 'var(--accent)', stopOpacity: 0 }} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
                  <XAxis dataKey="step" tick={axisTick} stroke="var(--border)" />
                  <YAxis tick={axisTick} stroke="var(--border)" unit="s" />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}s`, 'Avg wait']} labelFormatter={(s) => `Step ${s}`} />
                  {metrics.sla_target && (
                    <ReferenceLine
                      y={metrics.sla_target}
                      stroke="var(--warning)"
                      strokeDasharray="4 4"
                      label={{ value: 'SLA target', position: 'insideTopRight', fill: 'var(--warning)', fontSize: 11 }}
                    />
                  )}
                  <Area type="monotone" dataKey="wait" stroke="var(--accent)" strokeWidth={2} fill="url(#waitFill)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty h-full flex items-center justify-center">
                Start the simulation to begin collecting data.
              </div>
            )}
          </div>
        </section>

        <section className="panel panel-pad flex flex-col h-[360px]">
          <h3 className="panel-title">
            <Route size={16} style={{ color: 'var(--primary)' }} aria-hidden="true" />
            Distance travelled per car (floors)
          </h3>
          <div className="flex-1 min-h-0 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distanceData} margin={{ top: 10, right: 12, left: -16, bottom: 0 }}>
                <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
                <XAxis dataKey="name" tick={axisTick} stroke="var(--border)" />
                <YAxis tick={axisTick} stroke="var(--border)" />
                <Tooltip
                  cursor={{ fill: 'var(--surface-2)' }}
                  contentStyle={tooltipStyle}
                  formatter={(v) => [`${v} floors`, 'Distance']}
                />
                <Bar dataKey="distance" radius={[6, 6, 0, 0]}>
                  {distanceData.map((d) => (
                    <Cell key={d.name} fill={d.offline ? 'var(--critical)' : 'var(--primary)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </div>
  );
}

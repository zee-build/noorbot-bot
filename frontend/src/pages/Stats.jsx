import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { useApi } from '../hooks/useApi';
import { api } from '../lib/api';

const DEED_EMOJIS = {
  fajr: '🌙',
  dhuhr: '☀️',
  asr: '🌤️',
  maghrib: '🌅',
  isha: '🌃',
  quran: '📖',
  dhikr_am: '🌅',
  dhikr_pm: '🌆',
  dhikr: '🤲',
  dhikr_nawm: '🌙',
  sadaqah: '💝',
  fast: '🌛',
};

function pctToColor(pct) {
  if (pct === 0) return 'rgba(14,42,30,0.5)';
  if (pct < 25) return 'rgba(201,168,76,0.15)';
  if (pct < 50) return 'rgba(201,168,76,0.3)';
  if (pct < 75) return 'rgba(201,168,76,0.55)';
  return 'rgba(201,168,76,0.85)';
}

function MonthlyHeatmap({ monthlyData }) {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();

  // Build data map
  const dataMap = {};
  for (const d of (monthlyData || [])) {
    dataMap[d.date] = d.pct || 0;
  }

  // Generate 13 weeks of cells ending today
  const cells = [];
  const endDate = new Date(today);
  endDate.setHours(0, 0, 0, 0);
  const startDate = new Date(endDate);
  startDate.setDate(startDate.getDate() - 90); // ~13 weeks

  const cur = new Date(startDate);
  while (cur <= endDate) {
    const ds = cur.toISOString().split('T')[0];
    cells.push({ date: ds, pct: dataMap[ds] || 0 });
    cur.setDate(cur.getDate() + 1);
  }

  // Pad start to Sunday
  const firstDay = new Date(cells[0].date).getDay();
  const paddedCells = [
    ...Array(firstDay).fill(null),
    ...cells,
  ];

  // Group into weeks
  const weeks = [];
  for (let i = 0; i < paddedCells.length; i += 7) {
    weeks.push(paddedCells.slice(i, i + 7));
  }

  const [tooltip, setTooltip] = useState(null);

  return (
    <div>
      <div className="flex gap-0.5 overflow-x-auto pb-2">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-0.5">
            {week.map((cell, di) => {
              if (!cell) {
                return <div key={di} style={{ width: 12, height: 12 }} />;
              }
              return (
                <div
                  key={di}
                  onMouseEnter={() => setTooltip(cell)}
                  onMouseLeave={() => setTooltip(null)}
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: 2,
                    background: pctToColor(cell.pct),
                    cursor: 'pointer',
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>
      {tooltip && (
        <div
          className="text-xs font-body text-cream-dim mt-1"
        >
          {tooltip.date}: {tooltip.pct}%
        </div>
      )}
      <div className="flex items-center gap-2 mt-2">
        <span className="text-[10px] font-body text-muted">Less</span>
        {[0, 25, 50, 75, 100].map((p) => (
          <div
            key={p}
            style={{ width: 10, height: 10, borderRadius: 2, background: pctToColor(p) }}
          />
        ))}
        <span className="text-[10px] font-body text-muted">More</span>
      </div>
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div
        className="px-3 py-2 rounded-xl text-xs font-body"
        style={{ background: '#0e2a1e', border: '1px solid rgba(201,168,76,0.3)', color: '#f0ede0' }}
      >
        <p className="text-muted mb-1">{label}</p>
        <p className="text-gold font-semibold">{payload[0].value}%</p>
      </div>
    );
  }
  return null;
}

export default function Stats({ userId }) {
  const { data: weekly } = useApi(() => api.getWeekly(userId), [userId]);
  const { data: monthly } = useApi(() => api.getMonthly(userId), [userId]);
  const { data: streaks } = useApi(() => api.getStreaks(userId), [userId]);

  const weeklyData = (weekly || []).map((d) => ({
    date: d.date ? d.date.slice(5) : '',
    pct: d.pct || 0,
  }));

  const bestDay = weekly ? [...weekly].sort((a, b) => (b.pct || 0) - (a.pct || 0))[0] : null;
  const worstDay = weekly ? [...weekly].sort((a, b) => (a.pct || 0) - (b.pct || 0))[0] : null;

  return (
    <div className="min-h-screen bg-bg pb-20 relative z-10">
      <div className="px-4 pt-6 space-y-5">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-gold text-2xl font-bold">Stats</h1>
          <p className="text-xs font-body text-muted mt-1">Your spiritual progress</p>
        </motion.div>

        {/* Monthly Heatmap */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl p-5"
          style={{
            background: 'rgba(14,42,30,0.7)',
            border: '1px solid rgba(201,168,76,0.12)',
          }}
        >
          <h3 className="font-body font-semibold text-cream text-sm mb-4">Activity (last 3 months)</h3>
          <MonthlyHeatmap monthlyData={monthly} />
        </motion.div>

        {/* Weekly Trend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="rounded-2xl p-5"
          style={{
            background: 'rgba(14,42,30,0.7)',
            border: '1px solid rgba(201,168,76,0.12)',
          }}
        >
          <h3 className="font-body font-semibold text-cream text-sm mb-4">7-Day Trend</h3>
          {weeklyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={weeklyData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,168,76,0.08)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: '#7a9a82', fontFamily: 'DM Sans' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: '#7a9a82', fontFamily: 'DM Sans' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="pct"
                  stroke="#c9a84c"
                  strokeWidth={2.5}
                  dot={{ fill: '#c9a84c', r: 4, strokeWidth: 0 }}
                  activeDot={{ fill: '#e0bc6a', r: 5, strokeWidth: 0 }}
                  isAnimationActive={true}
                  animationDuration={1000}
                  style={{ filter: 'drop-shadow(0 0 4px rgba(201,168,76,0.5))' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-40 flex items-center justify-center">
              <p className="text-xs font-body text-muted">No data yet.</p>
            </div>
          )}
        </motion.div>

        {/* Best/Worst Day */}
        {weekly && weekly.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-2 gap-3"
          >
            <div
              className="rounded-2xl p-4"
              style={{ background: 'rgba(14,42,30,0.7)', border: '1px solid rgba(201,168,76,0.12)' }}
            >
              <p className="text-xs font-body text-muted mb-1">Best Day</p>
              <p className="font-display text-gold font-bold text-xl">{bestDay?.pct || 0}%</p>
              <p className="text-[10px] font-body text-muted mt-0.5">{bestDay?.date || ''}</p>
            </div>
            <div
              className="rounded-2xl p-4"
              style={{ background: 'rgba(14,42,30,0.7)', border: '1px solid rgba(201,168,76,0.12)' }}
            >
              <p className="text-xs font-body text-muted mb-1">Lowest Day</p>
              <p className="font-display text-gold font-bold text-xl">{worstDay?.pct || 0}%</p>
              <p className="text-[10px] font-body text-muted mt-0.5">{worstDay?.date || ''}</p>
            </div>
          </motion.div>
        )}

        {/* Streaks */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="rounded-2xl p-5"
          style={{
            background: 'rgba(14,42,30,0.7)',
            border: '1px solid rgba(201,168,76,0.12)',
          }}
        >
          <h3 className="font-body font-semibold text-cream text-sm mb-4">Streak Breakdown</h3>
          {streaks && streaks.length > 0 ? (
            <div className="space-y-3">
              {streaks.map((s, i) => (
                <motion.div
                  key={s.deed_key}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06 }}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-base">
                      {DEED_EMOJIS[s.deed_key] || '⭐'}
                    </span>
                    <span className="text-sm font-body text-cream-dim">{s.deed_label}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-display text-gold font-bold text-base">{s.streak}</span>
                    <span className="text-xs font-body text-muted">days</span>
                    {s.streak >= 7 && <span>🔥</span>}
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="text-xs font-body text-muted text-center py-4">
              Set up goals in the bot to see your streaks.
            </p>
          )}
        </motion.div>

      </div>
    </div>
  );
}

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApi } from '../hooks/useApi';
import { api } from '../lib/api';

const RANK_MEDALS = { 1: '🥇', 2: '🥈', 3: '🥉' };

function useCountUp(target, duration = 800) {
  const [value, setValue] = useState(0);
  const prevTarget = useRef(target);

  useEffect(() => {
    if (target === prevTarget.current && value !== 0) return;
    prevTarget.current = target;
    let start = 0;
    const startTime = performance.now();
    const animate = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 2);
      setValue(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  return value;
}

function LeaderboardRow({ entry, userId, index }) {
  const points = useCountUp(entry.points);
  const isMe = entry.user_id === userId;
  const medal = RANK_MEDALS[entry.rank];

  return (
    <motion.div
      initial={{ opacity: 0, x: 30 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
      className="flex items-center gap-3 px-4 py-3 rounded-xl"
      style={{
        background: isMe
          ? 'linear-gradient(90deg, rgba(201,168,76,0.12) 0%, rgba(201,168,76,0.04) 100%)'
          : index % 2 === 0
            ? 'rgba(14,42,30,0.5)'
            : 'rgba(14,42,30,0.3)',
        border: isMe ? '1px solid rgba(201,168,76,0.3)' : '1px solid transparent',
        borderLeft: isMe ? '3px solid #c9a84c' : '3px solid transparent',
      }}
    >
      {/* Rank */}
      <div className="w-8 flex-shrink-0 text-center">
        {medal ? (
          <span className="text-lg">{medal}</span>
        ) : (
          <span className="text-xs font-body font-bold text-muted">#{entry.rank}</span>
        )}
      </div>

      {/* Name + level */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={`text-sm font-body font-semibold truncate ${isMe ? 'text-gold' : 'text-cream'}`}
          >
            {entry.first_name}
            {isMe && <span className="text-xs text-gold opacity-70 ml-1">(you)</span>}
          </span>
        </div>
        <div className="flex items-center gap-1 mt-0.5">
          <span
            className="text-[10px] font-body px-1.5 py-0.5 rounded-full"
            style={{ background: 'rgba(201,168,76,0.12)', color: '#c9a84c', border: '1px solid rgba(201,168,76,0.2)' }}
          >
            Lvl {entry.level}
          </span>
        </div>
      </div>

      {/* Points */}
      <div className="flex-shrink-0 text-right">
        <span className="font-display text-gold font-bold text-base">{points}</span>
        <p className="text-[10px] font-body text-muted">pts</p>
      </div>
    </motion.div>
  );
}

export default function Leaderboard({ userId }) {
  const [period, setPeriod] = useState('week');
  const [groupTab, setGroupTab] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState(null);

  const { data: groups } = useApi(() => api.getUserGroups(userId), [userId]);

  const { data: globalData, loading: globalLoading } = useApi(
    () => api.getLeaderboard(period),
    [period]
  );

  const { data: groupData, loading: groupLoading } = useApi(
    () => selectedGroup ? api.getGroupLeaderboard(selectedGroup) : Promise.resolve([]),
    [selectedGroup]
  );

  useEffect(() => {
    if (groups && groups.length > 0 && !selectedGroup) {
      setSelectedGroup(groups[0].id);
    }
  }, [groups, selectedGroup]);

  const tabs = [
    { key: 'week', label: 'This Week' },
    { key: 'month', label: 'This Month' },
    { key: 'alltime', label: 'All Time' },
    { key: 'group', label: 'My Group' },
  ];

  const isGroupTab = period === 'group';
  const data = isGroupTab ? (groupData || []) : (globalData || []);
  const loading = isGroupTab ? groupLoading : globalLoading;

  return (
    <div className="min-h-screen bg-bg pb-20 relative z-10">
      <div className="px-4 pt-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-5"
        >
          <h1 className="font-display text-gold text-2xl font-bold">Leaderboard</h1>
          <p className="text-xs font-body text-muted mt-1">Compete with brothers & sisters</p>
        </motion.div>

        {/* Period Tabs */}
        <div
          className="flex gap-1 p-1 rounded-xl mb-4"
          style={{ background: 'rgba(14,42,30,0.6)', border: '1px solid rgba(201,168,76,0.1)' }}
        >
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setPeriod(tab.key)}
              className="flex-1 py-1.5 rounded-lg text-xs font-body font-medium transition-all duration-200 focus:outline-none"
              style={{
                background: period === tab.key ? 'rgba(201,168,76,0.2)' : 'transparent',
                color: period === tab.key ? '#c9a84c' : 'rgba(240,237,224,0.4)',
                border: period === tab.key ? '1px solid rgba(201,168,76,0.3)' : '1px solid transparent',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Group selector if group tab */}
        {isGroupTab && groups && groups.length > 1 && (
          <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
            {groups.map((g) => (
              <button
                key={g.id}
                onClick={() => setSelectedGroup(g.id)}
                className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-body font-medium focus:outline-none"
                style={{
                  background: selectedGroup === g.id ? 'rgba(201,168,76,0.2)' : 'rgba(14,42,30,0.5)',
                  color: selectedGroup === g.id ? '#c9a84c' : 'rgba(240,237,224,0.5)',
                  border: `1px solid ${selectedGroup === g.id ? 'rgba(201,168,76,0.4)' : 'rgba(201,168,76,0.1)'}`,
                }}
              >
                {g.name}
              </button>
            ))}
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex gap-1.5">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 rounded-full bg-gold"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </div>
          </div>
        ) : isGroupTab && (!groups || groups.length === 0) ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-20 gap-4"
          >
            <span className="text-5xl">🕌</span>
            <p className="font-body text-cream-dim text-center text-sm leading-relaxed">
              You're not in any groups yet.
              <br />
              Create or join a group in the bot chat.
            </p>
          </motion.div>
        ) : data.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <span className="text-4xl">📊</span>
            <p className="font-body text-muted text-sm">No data yet for this period.</p>
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={`${period}-${selectedGroup}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-2"
            >
              {data.map((entry, i) => (
                <LeaderboardRow
                  key={entry.user_id}
                  entry={entry}
                  userId={userId}
                  index={i}
                />
              ))}
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}

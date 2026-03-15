import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApi } from '../hooks/useApi';
import { api } from '../lib/api';
import Toast from '../components/Toast';

function Toggle({ on, onToggle }) {
  return (
    <motion.button
      onClick={onToggle}
      className="focus:outline-none"
      style={{
        width: 48,
        height: 26,
        borderRadius: 13,
        background: on
          ? 'linear-gradient(90deg, #c9a84c, #e0bc6a)'
          : 'rgba(14,42,30,0.8)',
        border: on ? 'none' : '1.5px solid rgba(201,168,76,0.25)',
        position: 'relative',
        flexShrink: 0,
        boxShadow: on ? '0 0 12px rgba(201,168,76,0.4)' : 'none',
      }}
    >
      <motion.div
        animate={{ x: on ? 22 : 2 }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        style={{
          position: 'absolute',
          top: 2,
          width: 22,
          height: 22,
          borderRadius: 11,
          background: on ? '#050e0e' : 'rgba(201,168,76,0.5)',
        }}
      />
    </motion.button>
  );
}

function CopyChip({ text, label }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // fallback
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  };

  return (
    <motion.button
      whileTap={{ scale: 0.96 }}
      onClick={handleCopy}
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full focus:outline-none transition-all duration-200"
      style={{
        background: copied ? 'rgba(34,197,94,0.15)' : 'rgba(201,168,76,0.1)',
        border: `1px solid ${copied ? 'rgba(34,197,94,0.4)' : 'rgba(201,168,76,0.25)'}`,
      }}
    >
      <span
        className="text-xs font-body font-mono"
        style={{ color: copied ? '#4ade80' : '#c9a84c' }}
      >
        {label}: {text}
      </span>
      <span className="text-[10px]">{copied ? '✓' : '📋'}</span>
    </motion.button>
  );
}

export default function Settings({ userId, user: propUser }) {
  const { data: userData } = useApi(() => api.getUser(userId), [userId]);
  const { data: groups } = useApi(() => api.getUserGroups(userId), [userId]);
  const { data: todayData } = useApi(() => api.getToday(userId), [userId]);

  const user = userData || propUser || {};
  const [remindersOn, setRemindersOn] = useState(null);
  const [toast, setToast] = useState({ visible: false, message: '' });

  useEffect(() => {
    if (userData && remindersOn === null) {
      setRemindersOn(!!userData.reminders_on);
    }
  }, [userData, remindersOn]);

  const handleToggleReminders = async () => {
    const newVal = !remindersOn;
    setRemindersOn(newVal); // optimistic
    try {
      await api.updateUser(userId, { reminders_on: newVal });
      setToast({
        visible: true,
        message: newVal ? 'Reminders enabled' : 'Reminders disabled',
      });
    } catch {
      setRemindersOn(!newVal); // revert
      setToast({ visible: true, message: 'Failed to update settings' });
    }
  };

  const joinedDate = user.joined_at
    ? new Date(user.joined_at).toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
      })
    : 'Unknown';

  const goals = todayData?.goals || [];

  return (
    <div className="min-h-screen bg-bg pb-20 relative z-10">
      <div className="px-4 pt-6 space-y-4">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-gold text-2xl font-bold">Settings</h1>
          <p className="text-xs font-body text-muted mt-1">Manage your profile & preferences</p>
        </motion.div>

        {/* Profile Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="rounded-2xl p-5"
          style={{
            background: 'rgba(14,42,30,0.7)',
            border: '1px solid rgba(201,168,76,0.12)',
          }}
        >
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center font-display text-gold font-bold text-lg flex-shrink-0"
              style={{
                background: 'linear-gradient(135deg, rgba(201,168,76,0.2), rgba(201,168,76,0.05))',
                border: '2px solid rgba(201,168,76,0.3)',
              }}
            >
              {(user.first_name || 'U').split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-body font-semibold text-cream text-base">{user.first_name || '—'}</p>
              {user.username && (
                <p className="text-xs font-body text-muted">@{user.username}</p>
              )}
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span
                  className="text-[10px] font-body px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(201,168,76,0.15)', color: '#c9a84c', border: '1px solid rgba(201,168,76,0.2)' }}
                >
                  Level {user.level || 0}
                </span>
                {user.city && (
                  <span className="text-[10px] font-body text-muted">📍 {user.city}</span>
                )}
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-[rgba(201,168,76,0.08)]">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] font-body text-muted mb-0.5">Total XP</p>
                <p className="text-sm font-body font-semibold text-gold">{user.total_xp || 0} XP</p>
              </div>
              <div>
                <p className="text-[10px] font-body text-muted mb-0.5">Member Since</p>
                <p className="text-xs font-body text-cream-dim">{joinedDate}</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Reminders Toggle */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          className="rounded-2xl p-5"
          style={{
            background: 'rgba(14,42,30,0.7)',
            border: '1px solid rgba(201,168,76,0.12)',
          }}
        >
          <h3 className="font-body font-semibold text-cream text-sm mb-4">Notifications</h3>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-body text-cream">Prayer Reminders</p>
              <p className="text-xs font-body text-muted mt-0.5">
                Receive daily prayer time reminders
              </p>
            </div>
            <Toggle
              on={remindersOn === null ? (user.reminders_on ?? true) : remindersOn}
              onToggle={handleToggleReminders}
            />
          </div>
        </motion.div>

        {/* Active Goals */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.16 }}
          className="rounded-2xl p-5"
          style={{
            background: 'rgba(14,42,30,0.7)',
            border: '1px solid rgba(201,168,76,0.12)',
          }}
        >
          <h3 className="font-body font-semibold text-cream text-sm mb-3">Active Goals</h3>
          {goals.length > 0 ? (
            <div className="space-y-2">
              {goals.map((g) => (
                <div
                  key={g.deed_key || g.id}
                  className="flex items-center justify-between py-2 border-b border-[rgba(201,168,76,0.06)] last:border-0"
                >
                  <span className="text-sm font-body text-cream-dim">{g.deed_label || g.deed_key}</span>
                  <span
                    className="text-[10px] font-body px-2 py-0.5 rounded-full"
                    style={{ background: 'rgba(201,168,76,0.1)', color: '#c9a84c' }}
                  >
                    {g.points} pts/day
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs font-body text-muted">No active goals.</p>
          )}
          <p className="text-[10px] font-body text-muted mt-3">
            Manage goals in the bot chat ↗
          </p>
        </motion.div>

        {/* Groups */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl p-5"
          style={{
            background: 'rgba(14,42,30,0.7)',
            border: '1px solid rgba(201,168,76,0.12)',
          }}
        >
          <h3 className="font-body font-semibold text-cream text-sm mb-3">My Groups</h3>
          {groups && groups.length > 0 ? (
            <div className="space-y-2">
              {groups.map((g) => (
                <div key={g.id} className="space-y-1.5">
                  <p className="text-sm font-body text-cream">{g.name}</p>
                  {g.invite_code && (
                    <CopyChip text={g.invite_code} label="Code" />
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs font-body text-muted">You're not in any groups yet.</p>
          )}
          <p className="text-[10px] font-body text-muted mt-3">
            Create or join groups in the bot chat ↗
          </p>
        </motion.div>

        {/* App info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.24 }}
          className="pb-4 text-center"
        >
          <p className="font-display text-gold text-xs opacity-40">NoorBot v1.0</p>
          <p className="text-[10px] font-body text-muted mt-1 font-arabic" dir="rtl">
            رَبَّنَا تَقَبَّلْ مِنَّا
          </p>
        </motion.div>

      </div>

      <Toast
        message={toast.message}
        visible={toast.visible}
        onDismiss={() => setToast({ visible: false, message: '' })}
      />
    </div>
  );
}

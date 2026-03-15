import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { adminApi } from '../lib/api';

function StatCard({ label, value, sub }) {
  return (
    <div
      className="rounded-2xl p-4 flex flex-col gap-1"
      style={{ background: 'rgba(14,42,30,0.8)', border: '1px solid rgba(201,168,76,0.15)' }}
    >
      <p className="text-[10px] font-body text-muted uppercase tracking-wider">{label}</p>
      <p className="font-display text-gold text-2xl font-bold">{value ?? '—'}</p>
      {sub && <p className="text-[10px] font-body text-muted">{sub}</p>}
    </div>
  );
}

function LoginScreen({ onLogin }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await adminApi.login(password);
      onLogin(data.token);
    } catch {
      setError('Invalid password. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-sm rounded-2xl p-8"
        style={{ background: 'rgba(14,42,30,0.9)', border: '1px solid rgba(201,168,76,0.2)' }}
      >
        <div className="text-center mb-8">
          <p className="font-display text-gold text-3xl font-bold">🔐</p>
          <h1 className="font-display text-gold text-xl font-bold mt-2">Admin Panel</h1>
          <p className="text-xs font-body text-muted mt-1">NoorBot Management</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            placeholder="Admin password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl px-4 py-3 text-sm font-body text-cream focus:outline-none"
            style={{
              background: 'rgba(5,14,14,0.8)',
              border: '1px solid rgba(201,168,76,0.2)',
            }}
          />
          {error && <p className="text-xs text-red-400 font-body">{error}</p>}
          <motion.button
            type="submit"
            disabled={loading || !password}
            whileTap={{ scale: 0.97 }}
            className="w-full rounded-xl py-3 font-body font-semibold text-sm"
            style={{
              background: 'linear-gradient(90deg, #c9a84c, #e0bc6a)',
              color: '#050e0e',
              opacity: loading || !password ? 0.5 : 1,
            }}
          >
            {loading ? 'Checking...' : 'Sign In'}
          </motion.button>
        </form>
      </motion.div>
    </div>
  );
}

function UserRow({ user, token, onToggle }) {
  const [toggling, setToggling] = useState(false);

  const handleToggle = async () => {
    setToggling(true);
    try {
      await adminApi.toggleUser(token, user.user_id, !user.active);
      onToggle(user.user_id, !user.active);
    } catch {
      // ignore
    } finally {
      setToggling(false);
    }
  };

  return (
    <div
      className="flex items-center gap-3 py-3 border-b border-[rgba(201,168,76,0.06)] last:border-0"
    >
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center font-display text-gold font-bold text-xs flex-shrink-0"
        style={{ background: 'rgba(201,168,76,0.15)', border: '1px solid rgba(201,168,76,0.2)' }}
      >
        {(user.first_name || 'U')[0].toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-body text-cream truncate">
          {user.first_name}
          {user.username ? <span className="text-muted"> @{user.username}</span> : null}
        </p>
        <p className="text-[10px] font-body text-muted">
          Lvl {user.level} · {user.total_xp} XP · {user.city || '—'}
        </p>
        <p className="text-[10px] font-body text-muted">
          Logs today: {user.logs_today} · Pts this week: {user.pts_week}
        </p>
      </div>
      <div className="flex flex-col items-end gap-1 flex-shrink-0">
        <span
          className="text-[9px] font-body px-2 py-0.5 rounded-full"
          style={{
            background: user.active ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
            color: user.active ? '#4ade80' : '#f87171',
            border: `1px solid ${user.active ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
          }}
        >
          {user.active ? 'Active' : 'Paused'}
        </span>
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={handleToggle}
          disabled={toggling}
          className="text-[9px] font-body px-2 py-0.5 rounded-full focus:outline-none"
          style={{
            background: 'rgba(201,168,76,0.1)',
            color: '#c9a84c',
            border: '1px solid rgba(201,168,76,0.2)',
          }}
        >
          {toggling ? '...' : user.active ? 'Pause' : 'Resume'}
        </motion.button>
      </div>
    </div>
  );
}

export default function Admin() {
  const [token, setToken] = useState(() => sessionStorage.getItem('adminToken') || '');
  const [tab, setTab] = useState('stats');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [top10, setTop10] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = (tok) => {
    setToken(tok);
    sessionStorage.setItem('adminToken', tok);
  };

  const handleLogout = () => {
    setToken('');
    sessionStorage.removeItem('adminToken');
  };

  const loadStats = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const [s, u, t] = await Promise.all([
        adminApi.getStats(token),
        adminApi.getUsers(token),
        adminApi.getTop10(token),
      ]);
      setStats(s);
      setUsers(u);
      setTop10(t);
    } catch (e) {
      setError(`Failed to load data: ${e.message}. Check VITE_API_URL on Vercel.`);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) loadStats();
  }, [token, loadStats]);

  const handleToggleUser = (userId, newActive) => {
    setUsers((prev) =>
      prev.map((u) => (u.user_id === userId ? { ...u, active: newActive } : u))
    );
  };

  if (!token) return <LoginScreen onLogin={handleLogin} />;

  const medals = ['🥇', '🥈', '🥉', '🏅', '🏅', '🏅', '🏅', '🏅', '🏅', '🏅'];

  return (
    <div className="min-h-screen bg-bg pb-8">
      {/* Header */}
      <div
        className="px-4 py-4 flex items-center justify-between sticky top-0 z-20"
        style={{ background: 'rgba(5,14,14,0.95)', borderBottom: '1px solid rgba(201,168,76,0.1)' }}
      >
        <div>
          <h1 className="font-display text-gold text-xl font-bold">🔐 Admin</h1>
          <p className="text-[10px] font-body text-muted">NoorBot Management</p>
        </div>
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={handleLogout}
          className="text-xs font-body px-3 py-1.5 rounded-full"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.2)' }}
        >
          Sign Out
        </motion.button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 px-4 pt-4 pb-2">
        {['stats', 'users', 'top10'].map((t) => (
          <motion.button
            key={t}
            whileTap={{ scale: 0.95 }}
            onClick={() => setTab(t)}
            className="px-4 py-1.5 rounded-full text-xs font-body font-semibold capitalize"
            style={{
              background: tab === t ? 'linear-gradient(90deg,#c9a84c,#e0bc6a)' : 'rgba(14,42,30,0.7)',
              color: tab === t ? '#050e0e' : '#c9a84c',
              border: tab === t ? 'none' : '1px solid rgba(201,168,76,0.2)',
            }}
          >
            {t === 'top10' ? 'Top 10' : t.charAt(0).toUpperCase() + t.slice(1)}
          </motion.button>
        ))}
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={loadStats}
          className="ml-auto px-3 py-1.5 rounded-full text-xs font-body"
          style={{ background: 'rgba(14,42,30,0.7)', color: '#c9a84c', border: '1px solid rgba(201,168,76,0.15)' }}
        >
          ↻
        </motion.button>
      </div>

      {loading && (
        <div className="text-center py-8">
          <p className="text-muted font-body text-sm">Loading...</p>
        </div>
      )}

      {error && (
        <div className="mx-4 mt-3 rounded-xl p-4" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
          <p className="text-xs font-body text-red-400">{error}</p>
          <button onClick={loadStats} className="mt-2 text-xs font-body text-gold underline">Retry</button>
        </div>
      )}

      <AnimatePresence mode="wait">
        {tab === 'stats' && stats && (
          <motion.div
            key="stats"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="px-4 pt-2 grid grid-cols-2 gap-3"
          >
            <StatCard label="Total Users" value={stats.total_users} />
            <StatCard label="New Today" value={stats.new_today} />
            <StatCard label="Active Today" value={stats.active_today} />
            <StatCard label="Active This Week" value={stats.active_week} />
            <StatCard label="Total Deed Logs" value={stats.total_logs?.toLocaleString()} />
          </motion.div>
        )}

        {tab === 'users' && (
          <motion.div
            key="users"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="px-4 pt-2"
          >
            <div
              className="rounded-2xl p-4"
              style={{ background: 'rgba(14,42,30,0.7)', border: '1px solid rgba(201,168,76,0.12)' }}
            >
              <p className="text-xs font-body text-muted mb-3">{users.length} users (latest first)</p>
              {users.map((u) => (
                <UserRow key={u.user_id} user={u} token={token} onToggle={handleToggleUser} />
              ))}
            </div>
          </motion.div>
        )}

        {tab === 'top10' && (
          <motion.div
            key="top10"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="px-4 pt-2"
          >
            <div
              className="rounded-2xl p-4 space-y-3"
              style={{ background: 'rgba(14,42,30,0.7)', border: '1px solid rgba(201,168,76,0.12)' }}
            >
              <p className="text-xs font-body font-semibold text-cream mb-1">🏆 All-Time Top 10</p>
              {top10.map((u, i) => (
                <div key={u.user_id} className="flex items-center gap-3">
                  <span className="text-lg">{medals[i]}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-body text-cream truncate">
                      {u.first_name}
                      {u.username ? <span className="text-muted"> @{u.username}</span> : null}
                    </p>
                    <p className="text-[10px] font-body text-muted">
                      Lvl {u.level} · {u.total_pts?.toLocaleString()} pts
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

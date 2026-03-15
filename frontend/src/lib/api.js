import { getInitData } from './telegram';

const BASE = import.meta.env.VITE_API_URL || '';

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': getInitData(),
      ...options.headers,
    },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export const api = {
  getUser: (id) => req(`/api/user/${id}`),
  getToday: (id) => req(`/api/user/${id}/today`),
  getWeekly: (id) => req(`/api/user/${id}/weekly`),
  getMonthly: (id) => req(`/api/user/${id}/monthly`),
  getStreaks: (id) => req(`/api/user/${id}/streaks`),
  getLeaderboard: (period) => req(`/api/leaderboard?period=${period}`),
  getGroupLeaderboard: (groupId) => req(`/api/group/${groupId}/leaderboard`),
  getUserGroups: (id) => req(`/api/user/${id}/groups`),
  logDeed: (body) => req('/api/log', { method: 'POST', body: JSON.stringify(body) }),
  updateUser: (id, body) => req(`/api/user/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
};

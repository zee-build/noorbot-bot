import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useApi } from '../hooks/useApi';
import { api } from '../lib/api';
import XPBar from '../components/XPBar';
import ScoreRing from '../components/ScoreRing';
import PrayerCard from '../components/PrayerCard';
import StreakCard from '../components/StreakCard';
import LevelUpModal from '../components/LevelUpModal';
import Toast from '../components/Toast';

const PRAYERS = [
  { key: 'fajr', name: 'Fajr' },
  { key: 'dhuhr', name: 'Dhuhr' },
  { key: 'asr', name: 'Asr' },
  { key: 'maghrib', name: 'Maghrib' },
  { key: 'isha', name: 'Isha' },
];

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good Morning';
  if (h < 17) return 'Good Afternoon';
  return 'Good Evening';
}

function getHijriDate() {
  // Approximate Hijri date conversion
  const now = new Date();
  const jd = Math.floor((now.getTime() / 86400000) + 2440587.5);
  let l = jd - 1948440 + 10632;
  const n = Math.floor((l - 1) / 10631);
  l = l - 10631 * n + 354;
  const j = Math.floor((10985 - l) / 5316) * Math.floor((50 * l) / 17719) +
    Math.floor(l / 5670) * Math.floor((43 * l) / 15238);
  l = l - Math.floor((30 - j) / 15) * Math.floor((17719 * j) / 50) -
    Math.floor(j / 16) * Math.floor((15238 * j) / 43) + 29;
  const month = Math.floor((24 * l) / 709);
  const day = l - Math.floor((709 * month) / 24);
  const year = 30 * n + j - 30;
  const months = [
    'Muharram', 'Safar', "Rabi' al-Awwal", "Rabi' al-Thani",
    "Jumada al-Awwal", "Jumada al-Thani", 'Rajab', "Sha'ban",
    'Ramadan', 'Shawwal', "Dhu al-Qi'dah", 'Dhu al-Hijjah',
  ];
  return `${day} ${months[month - 1]} ${year} AH`;
}

function getGregorianDate() {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
}

function getInitials(name = '') {
  return name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2);
}

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.4, ease: 'easeOut' },
  }),
};

export default function Home({ userId, user: propUser }) {
  const [levelUpModal, setLevelUpModal] = useState(null);
  const [toast, setToast] = useState({ visible: false, message: '' });

  const { data: todayData, refetch: refetchToday } = useApi(
    () => api.getToday(userId),
    [userId]
  );
  const { data: userData, refetch: refetchUser } = useApi(
    () => api.getUser(userId),
    [userId]
  );

  const user = userData || propUser || {};
  const goals = todayData?.goals || [];
  const score = todayData?.score || 0;
  const maxScore = todayData?.max_score || 0;
  const pct = todayData?.pct || 0;

  const fajrGoal = goals.find((g) => g.deed_key === 'fajr');
  const dhuhrGoal = goals.find((g) => g.deed_key === 'dhuhr');
  const asrGoal = goals.find((g) => g.deed_key === 'asr');
  const maghribGoal = goals.find((g) => g.deed_key === 'maghrib');
  const ishaGoal = goals.find((g) => g.deed_key === 'isha');

  const prayerGoalMap = {
    fajr: fajrGoal,
    dhuhr: dhuhrGoal,
    asr: asrGoal,
    maghrib: maghribGoal,
    isha: ishaGoal,
  };

  const handleLog = useCallback(async (prayerKey) => {
    const goal = prayerGoalMap[prayerKey];
    if (!goal) return;
    try {
      const result = await api.logDeed({
        user_id: userId,
        deed_key: prayerKey,
        deed_label: goal.deed_label || prayerKey,
        points: goal.points || 1,
      });
      if (result.logged) {
        setToast({ visible: true, message: `+${result.xp_earned} XP earned!` });
        if (result.leveled_up) {
          setTimeout(() => setLevelUpModal(result.new_level), 600);
        }
        refetchToday();
        refetchUser();
      }
    } catch {
      setToast({ visible: true, message: 'Already logged today!' });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, goals]);

  return (
    <div className="min-h-screen bg-bg pb-20 relative z-10">
      <div className="px-4 pt-6 pb-4 space-y-4">

        {/* Header */}
        <motion.div custom={0} variants={fadeUp} initial="hidden" animate="visible">
          <h1 className="font-display text-gold text-xl font-bold leading-tight">
            {getGreeting()},
          </h1>
          <h2 className="font-display text-gold-light text-2xl font-bold leading-tight">
            {user.first_name || 'Friend'}!
          </h2>
          <div className="mt-1 space-y-0.5">
            <p className="text-xs font-arabic text-gold opacity-70 text-right" dir="rtl">
              {getHijriDate()}
            </p>
            <p className="text-xs font-body text-muted">{getGregorianDate()}</p>
          </div>
        </motion.div>

        {/* Profile Hero Card */}
        <motion.div
          custom={1} variants={fadeUp} initial="hidden" animate="visible"
          className="rounded-2xl p-5"
          style={{
            background: 'linear-gradient(135deg, #0e2a1e 0%, #112b1e 100%)',
            border: '1px solid rgba(201,168,76,0.12)',
            boxShadow: '0 0 20px rgba(201,168,76,0.08)',
          }}
        >
          <div className="flex items-center gap-4 mb-4">
            {/* Avatar */}
            <div
              className="flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center font-display text-gold font-bold text-lg"
              style={{
                background: 'linear-gradient(135deg, rgba(201,168,76,0.2), rgba(201,168,76,0.05))',
                border: '2px solid rgba(201,168,76,0.3)',
                boxShadow: '0 0 16px rgba(201,168,76,0.15)',
              }}
            >
              {getInitials(user.first_name || 'U')}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-body font-semibold text-cream text-base truncate">
                  {user.first_name || 'User'}
                </span>
                {user.username && (
                  <span className="text-xs font-body text-muted">@{user.username}</span>
                )}
              </div>
              {/* Level badge */}
              <div className="mt-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(201,168,76,0.15)', border: '1px solid rgba(201,168,76,0.25)' }}>
                <span className="text-xs font-body font-bold text-gold">Level {user.level || 0}</span>
              </div>
            </div>
            {/* Day streak badge */}
            <div className="flex flex-col items-center">
              <span className="text-xl">{(user.fajr_streak || 0) >= 7 ? '🔥' : '🌙'}</span>
              <span className="text-xs font-body font-bold text-gold">{user.fajr_streak || 0}</span>
              <span className="text-[9px] font-body text-muted">day streak</span>
            </div>
          </div>
          <XPBar xpIn={user.xp_in_level || 0} xpNeeded={user.xp_needed || 200} level={user.level || 0} />
        </motion.div>

        {/* Today's Score Ring */}
        <motion.div
          custom={2} variants={fadeUp} initial="hidden" animate="visible"
          className="rounded-2xl p-5 flex items-center gap-5"
          style={{
            background: 'rgba(14,42,30,0.7)',
            border: '1px solid rgba(201,168,76,0.12)',
          }}
        >
          <ScoreRing pct={pct} size={110} />
          <div className="flex-1">
            <p className="font-body font-semibold text-cream text-sm mb-1">Today's Score</p>
            <p className="font-display text-gold text-2xl font-bold leading-tight">
              {score}
            </p>
            <p className="text-xs font-body text-muted">out of {maxScore} pts</p>
            {maxScore > 0 && (
              <div className="mt-2 w-full rounded-full overflow-hidden" style={{ height: 4, background: 'rgba(201,168,76,0.1)' }}>
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: 'linear-gradient(90deg, #c9a84c, #e0bc6a)' }}
                  initial={{ width: '0%' }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                />
              </div>
            )}
          </div>
        </motion.div>

        {/* Prayer Section */}
        <motion.div custom={3} variants={fadeUp} initial="hidden" animate="visible">
          <h3 className="font-display text-gold text-sm font-bold mb-3 tracking-wide">
            Today's Prayers
          </h3>
          <div className="space-y-2">
            {PRAYERS.map((prayer) => {
              const goal = prayerGoalMap[prayer.key];
              return (
                <PrayerCard
                  key={prayer.key}
                  prayerKey={prayer.key}
                  name={prayer.name}
                  time="--:--"
                  logged={goal?.logged || false}
                  jamaah={goal?.jamaah || false}
                  onLog={goal ? handleLog : null}
                />
              );
            })}
          </div>
          {!fajrGoal && !dhuhrGoal && !asrGoal && !maghribGoal && !ishaGoal && (
            <p className="text-xs font-body text-muted text-center mt-3">
              Set up your prayer goals in the bot chat to track them here.
            </p>
          )}
        </motion.div>

        {/* Streak Cards */}
        <motion.div custom={4} variants={fadeUp} initial="hidden" animate="visible">
          <h3 className="font-display text-gold text-sm font-bold mb-3 tracking-wide">
            Your Streaks
          </h3>
          <div className="flex gap-3">
            <StreakCard label="Fajr Streak" streak={user.fajr_streak || 0} emoji="🌙" />
            <StreakCard label="Quran Streak" streak={user.quran_streak || 0} emoji="📖" />
          </div>
        </motion.div>

      </div>

      {/* Level Up Modal */}
      {levelUpModal && (
        <LevelUpModal level={levelUpModal} onDismiss={() => setLevelUpModal(null)} />
      )}

      {/* Toast */}
      <Toast
        message={toast.message}
        visible={toast.visible}
        onDismiss={() => setToast({ visible: false, message: '' })}
      />
    </div>
  );
}

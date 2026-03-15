import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { initTelegram, getUser } from './lib/telegram';
import { api } from './lib/api';
import BottomNav from './components/BottomNav';
import LoadingScreen from './components/LoadingScreen';
import Home from './pages/Home';
import Adhkar from './pages/Adhkar';
import Leaderboard from './pages/Leaderboard';
import Stats from './pages/Stats';
import Settings from './pages/Settings';
import Admin from './pages/Admin';

// Islamic geometric SVG pattern (16-pointed star base)
const GeometricBg = () => (
  <div
    className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
    style={{ opacity: 0.03 }}
  >
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 120, repeat: Infinity, ease: 'linear' }}
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        width: '140vmax',
        height: '140vmax',
        transform: 'translate(-50%, -50%)',
      }}
    >
      <svg viewBox="0 0 800 800" width="100%" height="100%">
        <defs>
          <pattern id="geo" x="0" y="0" width="200" height="200" patternUnits="userSpaceOnUse">
            {/* Outer octagon */}
            <polygon
              points="100,10 155,45 190,100 155,155 100,190 45,155 10,100 45,45"
              fill="none"
              stroke="#c9a84c"
              strokeWidth="0.8"
            />
            {/* Inner star */}
            <polygon
              points="100,30 115,70 155,70 122,93 134,133 100,110 66,133 78,93 45,70 85,70"
              fill="none"
              stroke="#c9a84c"
              strokeWidth="0.6"
            />
            {/* Center circle */}
            <circle cx="100" cy="100" r="10" fill="none" stroke="#c9a84c" strokeWidth="0.5" />
            {/* Cross lines */}
            <line x1="100" y1="0" x2="100" y2="200" stroke="#c9a84c" strokeWidth="0.3" />
            <line x1="0" y1="100" x2="200" y2="100" stroke="#c9a84c" strokeWidth="0.3" />
            <line x1="0" y1="0" x2="200" y2="200" stroke="#c9a84c" strokeWidth="0.25" />
            <line x1="200" y1="0" x2="0" y2="200" stroke="#c9a84c" strokeWidth="0.25" />
          </pattern>
        </defs>
        <rect width="800" height="800" fill="url(#geo)" />
      </svg>
    </motion.div>
  </div>
);

const PAGE_TRANSITION = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.25, ease: 'easeInOut' },
};

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [userId, setUserId] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initTelegram();
    const tgUser = getUser();
    const id = tgUser?.id;
    setUserId(id);

    if (id) {
      api.getUser(id)
        .then((data) => {
          setUser(data);
        })
        .catch(() => {
          // User might not exist yet — show app anyway
          setUser({ id, first_name: tgUser.first_name, username: tgUser.username });
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  if (loading) return <LoadingScreen />;

  // Admin panel — accessible at ?admin=1 or hash #admin
  const isAdminRoute =
    window.location.search.includes('admin') ||
    window.location.hash === '#admin';
  if (isAdminRoute) return <Admin />;

  const sharedProps = { userId, user };

  return (
    <div className="relative min-h-screen bg-bg font-body">
      <GeometricBg />

      <div className="relative z-10">
        <AnimatePresence mode="wait">
          {activeTab === 'home' && (
            <motion.div key="home" {...PAGE_TRANSITION}>
              <Home {...sharedProps} />
            </motion.div>
          )}
          {activeTab === 'adhkar' && (
            <motion.div key="adhkar" {...PAGE_TRANSITION}>
              <Adhkar {...sharedProps} />
            </motion.div>
          )}
          {activeTab === 'leaderboard' && (
            <motion.div key="leaderboard" {...PAGE_TRANSITION}>
              <Leaderboard {...sharedProps} />
            </motion.div>
          )}
          {activeTab === 'stats' && (
            <motion.div key="stats" {...PAGE_TRANSITION}>
              <Stats {...sharedProps} />
            </motion.div>
          )}
          {activeTab === 'settings' && (
            <motion.div key="settings" {...PAGE_TRANSITION}>
              <Settings {...sharedProps} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <BottomNav active={activeTab} onChange={setActiveTab} />
    </div>
  );
}

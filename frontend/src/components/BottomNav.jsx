import { motion } from 'framer-motion';

const TABS = [
  { key: 'home', label: 'Home', emoji: '🏠' },
  { key: 'adhkar', label: 'Adhkar', emoji: '📿' },
  { key: 'leaderboard', label: 'Ranks', emoji: '🏆' },
  { key: 'stats', label: 'Stats', emoji: '📊' },
  { key: 'settings', label: 'Settings', emoji: '⚙️' },
];

export default function BottomNav({ active, onChange }) {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around"
      style={{
        height: 64,
        background: 'rgba(14,42,30,0.92)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderTop: '1px solid rgba(201,168,76,0.18)',
      }}
    >
      {TABS.map((tab) => {
        const isActive = active === tab.key;
        return (
          <motion.button
            key={tab.key}
            whileTap={{ scale: 0.82 }}
            onClick={() => onChange(tab.key)}
            className="flex flex-col items-center justify-center flex-1 h-full gap-0.5 focus:outline-none select-none"
          >
            <span
              className="text-xl transition-all duration-200"
              style={{ filter: isActive ? 'drop-shadow(0 0 6px rgba(201,168,76,0.7))' : 'none' }}
            >
              {tab.emoji}
            </span>
            <span
              className="text-[10px] font-body font-medium transition-colors duration-200"
              style={{ color: isActive ? '#c9a84c' : 'rgba(240,237,224,0.35)' }}
            >
              {tab.label}
            </span>
            {isActive && (
              <motion.div
                layoutId="nav-indicator"
                className="absolute bottom-0 rounded-full"
                style={{
                  width: 32,
                  height: 2,
                  background: '#c9a84c',
                  boxShadow: '0 0 8px rgba(201,168,76,0.8)',
                }}
              />
            )}
          </motion.button>
        );
      })}
    </nav>
  );
}

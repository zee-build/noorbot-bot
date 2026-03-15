import { motion } from 'framer-motion';

export default function XPBar({ xpIn = 0, xpNeeded = 200, level = 0 }) {
  const pct = Math.min((xpIn / xpNeeded) * 100, 100);

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-body font-semibold text-gold">
          Lvl {level}
        </span>
        <span className="text-[10px] font-body text-muted">
          {xpIn} / {xpNeeded} XP
        </span>
      </div>
      <div
        className="w-full rounded-full overflow-hidden"
        style={{
          height: 6,
          background: 'rgba(201,168,76,0.12)',
        }}
      >
        <motion.div
          className="h-full rounded-full"
          style={{
            background: 'linear-gradient(90deg, #c9a84c 0%, #e0bc6a 100%)',
            boxShadow: '0 0 8px rgba(201,168,76,0.5)',
          }}
          initial={{ width: '0%' }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export default function StreakCard({ label, streak = 0, emoji = '⭐' }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (streak === 0) {
      setDisplay(0);
      return;
    }
    let start = 0;
    const duration = 800;
    const startTime = performance.now();

    const animate = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease out quad
      const eased = 1 - Math.pow(1 - progress, 2);
      setDisplay(Math.round(eased * streak));
      if (progress < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [streak]);

  const onFire = streak >= 7;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex-1 rounded-2xl p-4 flex flex-col items-center gap-1"
      style={{
        background: 'rgba(14,42,30,0.7)',
        border: '1px solid rgba(201,168,76,0.12)',
        boxShadow: onFire ? '0 0 20px rgba(201,168,76,0.15)' : 'none',
      }}
    >
      <span className="text-2xl">{onFire ? '🔥' : emoji}</span>
      <span
        className="font-display font-bold text-gold"
        style={{ fontSize: 28, lineHeight: 1 }}
      >
        {display}
      </span>
      <span className="text-[10px] font-body text-muted text-center leading-tight">
        {label}
        {onFire && (
          <span className="block text-gold text-[9px] font-semibold mt-0.5">On Fire!</span>
        )}
      </span>
    </motion.div>
  );
}

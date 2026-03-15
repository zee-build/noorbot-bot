import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function ParticleCanvas() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const particles = Array.from({ length: 60 }, () => ({
      x: canvas.width / 2,
      y: canvas.height / 2,
      vx: (Math.random() - 0.5) * 14,
      vy: (Math.random() - 0.5) * 14 - 4,
      size: Math.random() * 5 + 2,
      alpha: 1,
      color: Math.random() > 0.5 ? '#c9a84c' : '#e0bc6a',
      decay: Math.random() * 0.015 + 0.01,
    }));

    let animId;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      let alive = false;
      for (const p of particles) {
        if (p.alpha <= 0) continue;
        alive = true;
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.3; // gravity
        p.alpha -= p.decay;
        ctx.save();
        ctx.globalAlpha = Math.max(p.alpha, 0);
        ctx.fillStyle = p.color;
        ctx.shadowBlur = 8;
        ctx.shadowColor = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
      if (alive) animId = requestAnimationFrame(draw);
    };

    animId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animId);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-50"
      style={{ width: '100%', height: '100%' }}
    />
  );
}

export default function LevelUpModal({ level, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 2800);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <AnimatePresence>
      <motion.div
        key="levelup"
        className="fixed inset-0 z-50 flex flex-col items-center justify-center"
        style={{ background: 'rgba(5,14,14,0.88)' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onDismiss}
      >
        <ParticleCanvas />

        <motion.div
          initial={{ scale: 0.4, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 1.1, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
          className="flex flex-col items-center gap-4 z-10"
        >
          <motion.div
            animate={{ rotate: [0, -5, 5, -3, 3, 0] }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-6xl"
          >
            🌟
          </motion.div>
          <div className="text-center">
            <p className="font-display text-gold text-base font-bold tracking-widest uppercase mb-2">
              Level Up!
            </p>
            <p
              className="font-display text-gold-light"
              style={{ fontSize: 56, lineHeight: 1, textShadow: '0 0 30px rgba(201,168,76,0.8)' }}
            >
              {level}
            </p>
          </div>
          <p className="font-body text-cream-dim text-sm tracking-wide">
            Masha'Allah, keep going!
          </p>
          <p className="font-body text-muted text-xs mt-2">Tap to dismiss</p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

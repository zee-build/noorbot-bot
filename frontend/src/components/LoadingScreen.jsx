import { motion } from 'framer-motion';

export default function LoadingScreen() {
  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center bg-bg z-50">
      {/* Crescent moon SVG */}
      <motion.div
        animate={{ opacity: [0.6, 1, 0.6], scale: [0.97, 1.03, 0.97] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
        className="mb-6"
      >
        <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
          <path
            d="M54 36C54 45.941 45.941 54 36 54C26.059 54 18 45.941 18 36C18 26.059 26.059 18 36 18C29.373 18 24 26.059 24 36C24 45.941 29.373 54 36 54C36 54 36 54 36 54C29.373 54 18 45.941 18 36"
            stroke="#c9a84c"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <path
            d="M36 18C45.941 18 54 26.059 54 36C54 45.941 45.941 54 36 54"
            stroke="#c9a84c"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="48" cy="24" r="3" fill="#c9a84c" opacity="0.7" />
          <circle cx="54" cy="18" r="1.5" fill="#e0bc6a" opacity="0.5" />
          <circle cx="58" cy="28" r="1" fill="#c9a84c" opacity="0.4" />
        </svg>
      </motion.div>

      <motion.h1
        className="font-display text-gold text-2xl tracking-wide"
        animate={{ opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut', delay: 0.2 }}
      >
        NoorBot
      </motion.h1>

      <motion.div
        className="mt-8 flex gap-1.5"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-gold"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
      </motion.div>
    </div>
  );
}

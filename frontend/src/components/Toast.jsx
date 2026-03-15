import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Toast({ message, visible, onDismiss }) {
  useEffect(() => {
    if (visible && onDismiss) {
      const t = setTimeout(onDismiss, 2000);
      return () => clearTimeout(t);
    }
  }, [visible, onDismiss]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="toast"
          className="fixed top-4 left-1/2 z-50 pointer-events-none"
          style={{ transform: 'translateX(-50%)' }}
          initial={{ y: -60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -60, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 380, damping: 28 }}
        >
          <div
            className="px-5 py-2.5 rounded-full font-body text-sm font-semibold text-bg"
            style={{
              background: 'linear-gradient(90deg, #c9a84c, #e0bc6a)',
              boxShadow: '0 4px 20px rgba(201,168,76,0.4)',
              whiteSpace: 'nowrap',
            }}
          >
            {message}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

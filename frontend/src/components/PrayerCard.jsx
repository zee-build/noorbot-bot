import { motion } from 'framer-motion';

const ARABIC_NAMES = {
  fajr: 'فَجْر',
  dhuhr: 'ظُهْر',
  asr: 'عَصْر',
  maghrib: 'مَغْرِب',
  isha: 'عِشَاء',
};

const PRAYER_EMOJIS = {
  fajr: '🌙',
  dhuhr: '☀️',
  asr: '🌤️',
  maghrib: '🌅',
  isha: '🌃',
};

export default function PrayerCard({ prayerKey, name, time = '--:--', logged = false, jamaah = false, onLog }) {
  const arabicName = ARABIC_NAMES[prayerKey] || '';
  const emoji = PRAYER_EMOJIS[prayerKey] || '🕌';

  return (
    <div
      className="flex items-center justify-between px-4 py-3 rounded-2xl transition-all duration-200"
      style={{
        background: logged
          ? 'linear-gradient(135deg, rgba(201,168,76,0.12) 0%, rgba(14,42,30,0.9) 100%)'
          : 'rgba(14,42,30,0.7)',
        border: `1px solid ${logged ? 'rgba(201,168,76,0.3)' : 'rgba(201,168,76,0.1)'}`,
        boxShadow: logged ? '0 0 16px rgba(201,168,76,0.12)' : 'none',
      }}
    >
      {/* Left: emoji + names */}
      <div className="flex items-center gap-3">
        <span className="text-xl">{emoji}</span>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-body font-semibold text-cream">{name}</span>
            {jamaah && (
              <span className="text-xs text-gold" title="With Jamaah">🕌</span>
            )}
          </div>
          <div className="text-[13px] font-arabic text-gold-light opacity-80 text-right" dir="rtl">
            {arabicName}
          </div>
        </div>
      </div>

      {/* Right: time + check */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-body text-muted">{time}</span>
        {logged ? (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: [0, 1.3, 1] }}
            transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            className="w-7 h-7 rounded-full flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #c9a84c, #e0bc6a)',
              boxShadow: '0 0 12px rgba(201,168,76,0.5)',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M2.5 7L5.5 10L11.5 4"
                stroke="#050e0e"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.div>
        ) : (
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={() => onLog && onLog(prayerKey)}
            className="w-7 h-7 rounded-full flex items-center justify-center focus:outline-none"
            style={{
              border: '1.5px solid rgba(201,168,76,0.3)',
              background: 'transparent',
            }}
          >
            <div className="w-2 h-2 rounded-full" style={{ background: 'rgba(201,168,76,0.2)' }} />
          </motion.button>
        )}
      </div>
    </div>
  );
}

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../lib/api';
import Toast from '../components/Toast';

const ADHKAR_COLLECTIONS = {
  dhikr_am: {
    label: 'Morning Adhkar',
    emoji: '🌅',
    points: 2,
    arabicPreview: 'اللَّهُمَّ بِكَ أَصْبَحْنَا',
    items: [
      {
        arabic: 'اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ',
        transliteration: "Allahumma bika asbahna wa bika amsayna wa bika nahya wa bika namutu wa ilaykan-nushur",
        meaning: 'O Allah, by You we enter the morning and by You we enter the evening, by You we live and by You we die, and to You is the resurrection.',
        source: 'Abu Dawud 4/317',
        count: 1,
      },
      {
        arabic: 'أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ',
        transliteration: "Asbahna wa asbahal mulku lillah walhamdu lillah la ilaha illallah wahdahu la shareeka lah, lahul mulku walahul hamdu wahuwa 'ala kulli shay'in qadeer",
        meaning: 'We have reached the morning and at this very time all sovereignty belongs to Allah. All praise is for Allah. None has the right to be worshipped except Allah, alone, without any partner.',
        source: 'Abu Dawud 4/318',
        count: 1,
      },
      {
        arabic: 'اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ، وَأَنَا عَلَى عَهْدِكَ وَوَعْدِكَ مَا اسْتَطَعْتُ، أَعُوذُ بِكَ مِنْ شَرِّ مَا صَنَعْتُ، أَبُوءُ لَكَ بِنِعْمَتِكَ عَلَيَّ، وَأَبُوءُ بِذَنْبِي فَاغْفِرْ لِي فَإِنَّهُ لَا يَغْفِرُ الذُّنُوبَ إِلَّا أَنْتَ',
        transliteration: "Allahumma anta rabbi la ilaha illa anta, khalaqtani wa ana 'abduka, wa ana 'ala 'ahdika wa wa'dika mastata't, a'udhu bika min sharri ma sana't, abu'u laka bini'matika 'alayya, wa abu'u bidhanbi faghfir li fa'innahu la yaghfirudh-dhunuba illa anta",
        meaning: "O Allah, You are my Lord, none has the right to be worshipped except You, You created me and I am Your servant and I abide to Your covenant and promise as best I can, I take refuge in You from the evil of which I committed. I acknowledge Your favor upon me and I acknowledge my sin, so forgive me, for verily none can forgive sin except You.",
        source: 'Al-Bukhari 7/150 - Sayyid al-Istighfar',
        count: 1,
      },
      {
        arabic: 'سُبْحَانَ اللهِ وَبِحَمْدِهِ',
        transliteration: 'Subhanallahi wa bihamdih',
        meaning: 'Glory be to Allah and I praise Him.',
        source: 'Al-Bukhari, Muslim',
        count: 100,
      },
    ],
  },
  dhikr_pm: {
    label: 'Evening Adhkar',
    emoji: '🌆',
    points: 2,
    arabicPreview: 'اللَّهُمَّ بِكَ أَمْسَيْنَا',
    items: [
      {
        arabic: 'اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ',
        transliteration: "Allahumma bika amsayna wa bika asbahna wa bika nahya wa bika namutu wa ilaykal maseer",
        meaning: 'O Allah, by You we enter the evening and by You we enter the morning, by You we live and by You we die, and to You is the return.',
        source: 'Abu Dawud 4/317',
        count: 1,
      },
      {
        arabic: 'أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ',
        transliteration: "Amsayna wa amsal mulku lillah walhamdu lillah la ilaha illallah wahdahu la shareeka lah, lahul mulku walahul hamdu wahuwa 'ala kulli shay'in qadeer",
        meaning: 'We have reached the evening and at this very time all sovereignty belongs to Allah. All praise is for Allah. None has the right to be worshipped except Allah, alone, without partner.',
        source: 'Abu Dawud 4/318',
        count: 1,
      },
      {
        arabic: 'اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَفْوَ وَالْعَافِيَةَ فِي الدُّنْيَا وَالآخِرَةِ',
        transliteration: "Allahumma inni as'alukal-'afwa wal'afiyata fid-dunya wal-akhirah",
        meaning: 'O Allah, I ask You for pardon and well-being in this life and the next.',
        source: 'Ibn Majah 2/332',
        count: 1,
      },
      {
        arabic: 'اللَّهُمَّ عَافِنِي فِي بَدَنِي، اللَّهُمَّ عَافِنِي فِي سَمْعِي، اللَّهُمَّ عَافِنِي فِي بَصَرِي، لَا إِلَهَ إِلَّا أَنْتَ',
        transliteration: "Allahumma 'afini fi badani, Allahumma 'afini fi sam'i, Allahumma 'afini fi basari, la ilaha illa ant",
        meaning: 'O Allah, grant my body health, O Allah, grant my hearing health, O Allah, grant my sight health. None has the right to be worshipped except You.',
        source: 'Abu Dawud 4/324',
        count: 3,
      },
    ],
  },
  dhikr: {
    label: 'After Salah',
    emoji: '🤲',
    points: 1,
    arabicPreview: 'أَسْتَغْفِرُ اللَّهَ',
    items: [
      {
        arabic: 'أَسْتَغْفِرُ اللَّهَ',
        transliteration: 'Astaghfirullah',
        meaning: 'I seek forgiveness from Allah.',
        source: 'Muslim 1/414',
        count: 3,
      },
      {
        arabic: 'اللَّهُمَّ أَنْتَ السَّلَامُ، وَمِنْكَ السَّلَامُ، تَبَارَكْتَ يَا ذَا الْجَلَالِ وَالْإِكْرَامِ',
        transliteration: "Allahumma antas-salamu wa minkas-salamu, tabarakta ya dhal-jalali wal-ikram",
        meaning: 'O Allah, You are As-Salamu (The One free from defects) and from You is all peace, blessed are You O Possessor of majesty and honour.',
        source: 'Muslim 1/414',
        count: 1,
      },
      {
        arabic: 'سُبْحَانَ اللَّهِ',
        transliteration: 'SubhanAllah',
        meaning: 'Glory be to Allah.',
        source: 'Al-Bukhari, Muslim',
        count: 33,
      },
      {
        arabic: 'الْحَمْدُ لِلَّهِ',
        transliteration: 'Alhamdulillah',
        meaning: 'All praise is for Allah.',
        source: 'Al-Bukhari, Muslim',
        count: 33,
      },
      {
        arabic: 'اللَّهُ أَكْبَرُ',
        transliteration: 'Allahu Akbar',
        meaning: 'Allah is the greatest.',
        source: 'Al-Bukhari, Muslim',
        count: 33,
      },
      {
        arabic: 'لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ',
        transliteration: "La ilaha illallah wahdahu la shareeka lah, lahul mulku walahul hamdu wahuwa 'ala kulli shay'in qadeer",
        meaning: 'None has the right to be worshipped except Allah, alone, without partner, to Him belongs all sovereignty and praise and He is over all things omnipotent.',
        source: 'Muslim 1/418',
        count: 1,
      },
    ],
  },
  dhikr_nawm: {
    label: 'Sleep Adhkar',
    emoji: '🌙',
    points: 1,
    arabicPreview: 'بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا',
    items: [
      {
        arabic: 'بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا',
        transliteration: 'Bismika Allahumma amutu wa ahya',
        meaning: 'In Your name O Allah, I die and I live.',
        source: 'Al-Bukhari 11/113',
        count: 1,
      },
      {
        arabic: 'اللَّهُمَّ قِنِي عَذَابَكَ يَوْمَ تَبْعَثُ عِبَادَكَ',
        transliteration: "Allahumma qini 'adhabaka yawma tab'athu 'ibadak",
        meaning: 'O Allah, protect me from Your punishment on the day Your servants are resurrected.',
        source: 'Abu Dawud 4/311',
        count: 3,
      },
      {
        arabic: 'بِاسْمِكَ رَبِّي وَضَعْتُ جَنْبِي، وَبِكَ أَرْفَعُهُ، فَإِنْ أَمْسَكْتَ نَفْسِي فَارْحَمْهَا، وَإِنْ أَرْسَلْتَهَا فَاحْفَظْهَا بِمَا تَحْفَظُ بِهِ عِبَادَكَ الصَّالِحِينَ',
        transliteration: "Bismika rabbi wada'tu janbi, wa bika arfa'uh, fa'in amsakta nafsi farhamha, wa in arsaltaha fahfazha bima tahfazu bihi 'ibadakassalihin",
        meaning: 'In Your name my Lord, I lie down and in Your name I rise, so if You should take my soul then have mercy upon it, and if You should return my soul then protect it in the manner You do so with Your righteous servants.',
        source: 'Al-Bukhari 11/126, Muslim 4/2083',
        count: 1,
      },
      {
        arabic: 'اللَّهُمَّ أَسْلَمْتُ نَفْسِي إِلَيْكَ، وَفَوَّضْتُ أَمْرِي إِلَيْكَ، وَوَجَّهْتُ وَجْهِي إِلَيْكَ، وَأَلْجَأْتُ ظَهْرِي إِلَيْكَ، رَغْبَةً وَرَهْبَةً إِلَيْكَ، لَا مَلْجَأَ وَلَا مَنْجَا مِنْكَ إِلَّا إِلَيْكَ، آمَنْتُ بِكِتَابِكَ الَّذِي أَنْزَلْتَ، وَبِنَبِيِّكَ الَّذِي أَرْسَلْتَ',
        transliteration: "Allahumma aslamtu nafsi ilayk, wa fawwadtu amri ilayk, wa wajjahtu wajhi ilayk, wa alja'tu zahri ilayk, raghbatan wa rahbatan ilayk, la malja'a wa la manja minka illa ilayk, amantu bikitabikal-ladhi anzalt, wa nabiyyikal-ladhi arsalt",
        meaning: "O Allah, I submit myself to You, entrust my affairs to You, turn my face to You, and lay myself down depending upon You, hoping in You and fearing You. There is no refuge or escape from You except to You. I believed in Your Book which You have revealed and Your Prophet whom You have sent.",
        source: 'Al-Bukhari 11/113, Muslim 4/2081',
        count: 1,
      },
    ],
  },
};

function CollectionCard({ collKey, collection, onOpen }) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={() => onOpen(collKey)}
      className="w-full text-left rounded-2xl p-5 focus:outline-none"
      style={{
        background: 'rgba(14,42,30,0.7)',
        border: '1px solid rgba(201,168,76,0.12)',
        boxShadow: '0 0 20px rgba(201,168,76,0.04)',
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          {/* Gold crescent top-left */}
          <div className="flex-shrink-0">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <path d="M11 3C9.5 5.5 9.5 9 11 11.5C8.5 10.5 6.5 8 6.5 5C6.5 3.6 7 2.3 7.8 1.3C5 2.5 3 5.2 3 8.4C3 13.1 6.9 17 11.6 17C14.8 17 17.5 15 18.7 12.2C17.7 13 16.4 13.5 15 13.5C12 13.5 9.5 11 9.5 8C9.5 5.8 10.8 3.9 12.7 3C12.2 3 11.6 3 11 3Z" fill="#c9a84c" opacity="0.8" />
            </svg>
          </div>
          <span className="text-xl">{collection.emoji}</span>
        </div>
        <span
          className="text-[10px] font-body font-semibold px-2 py-0.5 rounded-full"
          style={{ background: 'rgba(201,168,76,0.15)', color: '#c9a84c', border: '1px solid rgba(201,168,76,0.2)' }}
        >
          +{collection.points} pts
        </span>
      </div>
      <p className="font-body font-semibold text-cream text-base mb-2">{collection.label}</p>
      <p className="font-body text-xs text-muted mb-3">{collection.items.length} adhkar</p>
      <p
        className="font-arabic text-gold-light text-base text-right leading-relaxed opacity-70"
        dir="rtl"
        style={{ fontFamily: 'Noto Naskh Arabic, serif' }}
      >
        {collection.arabicPreview}...
      </p>
    </motion.button>
  );
}

function BottomSheet({ collKey, collection, userId, onClose, onLogged }) {
  const [index, setIndex] = useState(0);
  const [tapCount, setTapCount] = useState(null);
  const [done, setDone] = useState(false);
  const [logging, setLogging] = useState(false);

  const item = collection.items[index];
  const total = collection.items.length;
  const isLast = index === total - 1;

  // init tap count on item change
  const currentTapCount = tapCount !== null ? tapCount : item.count;

  const handleTap = () => {
    if (currentTapCount > 0) {
      setTapCount(currentTapCount - 1);
    }
  };

  const handleNext = async () => {
    if (currentTapCount > 0) return;
    if (isLast) {
      if (!logging) {
        setLogging(true);
        try {
          await api.logDeed({
            user_id: userId,
            deed_key: collKey,
            deed_label: collection.label,
            points: collection.points,
          });
          onLogged(collection.points * 10);
        } catch {
          // already logged
        }
        setDone(true);
        setLogging(false);
      }
    } else {
      setIndex(index + 1);
      setTapCount(null);
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-40 flex flex-col"
      style={{ background: 'rgba(5,14,14,0.7)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        className="absolute bottom-0 left-0 right-0 rounded-t-3xl flex flex-col"
        style={{
          background: '#0e2a1e',
          border: '1px solid rgba(201,168,76,0.18)',
          borderBottom: 'none',
          maxHeight: '88vh',
        }}
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">{collection.emoji}</span>
            <span className="font-body font-semibold text-cream text-base">{collection.label}</span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center focus:outline-none"
            style={{ background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.2)' }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 1L13 13M13 1L1 13" stroke="#c9a84c" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-1.5 px-5 pb-3">
          {collection.items.map((_, i) => (
            <div
              key={i}
              className="rounded-full transition-all duration-300"
              style={{
                width: i === index ? 20 : 6,
                height: 6,
                background: i === index ? '#c9a84c' : 'rgba(201,168,76,0.25)',
              }}
            />
          ))}
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto px-5 pb-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={index}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {/* Arabic text */}
              <div
                className="text-center font-arabic leading-loose py-2"
                dir="rtl"
                style={{
                  fontSize: 26,
                  color: '#f0ede0',
                  fontFamily: 'Noto Naskh Arabic, serif',
                  textShadow: '0 0 20px rgba(201,168,76,0.2)',
                }}
              >
                {item.arabic}
              </div>

              {/* Transliteration */}
              <p className="text-center text-sm font-body italic text-muted leading-relaxed">
                {item.transliteration}
              </p>

              {/* Meaning */}
              <div
                className="rounded-xl p-4"
                style={{ background: 'rgba(201,168,76,0.06)', border: '1px solid rgba(201,168,76,0.1)' }}
              >
                <p className="text-xs font-body text-cream-dim leading-relaxed">{item.meaning}</p>
              </div>

              {/* Source */}
              <p className="text-center text-[10px] font-body text-muted">{item.source}</p>

              {/* Tap counter */}
              {item.count > 1 && (
                <div className="flex flex-col items-center gap-2 py-2">
                  <motion.button
                    whileTap={{ scale: 0.92 }}
                    onClick={handleTap}
                    disabled={currentTapCount === 0}
                    className="w-20 h-20 rounded-full flex items-center justify-center focus:outline-none"
                    style={{
                      border: `3px solid ${currentTapCount === 0 ? 'rgba(201,168,76,0.5)' : '#c9a84c'}`,
                      background: currentTapCount === 0 ? 'rgba(201,168,76,0.1)' : 'rgba(201,168,76,0.08)',
                      boxShadow: currentTapCount > 0 ? '0 0 20px rgba(201,168,76,0.25)' : 'none',
                    }}
                  >
                    <span
                      className="font-display font-bold"
                      style={{ fontSize: 28, color: currentTapCount === 0 ? 'rgba(201,168,76,0.5)' : '#c9a84c' }}
                    >
                      {currentTapCount}
                    </span>
                  </motion.button>
                  <p className="text-xs font-body text-muted">Tap to count</p>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Next / Done button */}
        <div className="px-5 pb-8 pt-3">
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={handleNext}
            disabled={currentTapCount > 0 || logging || done}
            className="w-full py-3.5 rounded-2xl font-body font-semibold text-sm focus:outline-none transition-all duration-200"
            style={{
              background: currentTapCount > 0 || done
                ? 'rgba(201,168,76,0.15)'
                : 'linear-gradient(90deg, #c9a84c, #e0bc6a)',
              color: currentTapCount > 0 || done ? 'rgba(201,168,76,0.5)' : '#050e0e',
              boxShadow: currentTapCount === 0 && !done ? '0 0 20px rgba(201,168,76,0.3)' : 'none',
            }}
          >
            {done ? '✓ Completed!' : logging ? 'Saving...' : isLast ? 'Done ✓' : 'Next →'}
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function Adhkar({ userId }) {
  const [openCollection, setOpenCollection] = useState(null);
  const [toast, setToast] = useState({ visible: false, message: '' });

  const handleLogged = useCallback((xp) => {
    setToast({ visible: true, message: `+${xp} XP — Jazak Allah Khayran!` });
    setOpenCollection(null);
  }, []);

  return (
    <div className="min-h-screen bg-bg pb-20 relative z-10">
      <div className="px-4 pt-6 pb-4">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-5"
        >
          <h1 className="font-display text-gold text-2xl font-bold">Adhkar</h1>
          <p className="text-xs font-body text-muted mt-1">
            Daily remembrance of Allah
          </p>
        </motion.div>

        <div className="space-y-3">
          {Object.entries(ADHKAR_COLLECTIONS).map(([key, coll], i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07, duration: 0.4 }}
            >
              <CollectionCard
                collKey={key}
                collection={coll}
                onOpen={setOpenCollection}
              />
            </motion.div>
          ))}
        </div>
      </div>

      <AnimatePresence>
        {openCollection && (
          <BottomSheet
            collKey={openCollection}
            collection={ADHKAR_COLLECTIONS[openCollection]}
            userId={userId}
            onClose={() => setOpenCollection(null)}
            onLogged={handleLogged}
          />
        )}
      </AnimatePresence>

      <Toast
        message={toast.message}
        visible={toast.visible}
        onDismiss={() => setToast({ visible: false, message: '' })}
      />
    </div>
  );
}

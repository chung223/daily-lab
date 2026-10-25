import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// 偈語數據庫
const quotes = [
  { text: "一切有為法，如夢幻泡影，如露亦如電，應作如是觀", source: "金剛經 · 應化非真分" },
  { text: "過去心不可得，現在心不可得，未來心不可得", source: "金剛經 · 究竟無我分" },
  { text: "凡所有相，皆是虛妄。若見諸相非相，即見如來", source: "金剛經 · 如理實見分" },
  { text: "應無所住而生其心", source: "金剛經 · 莊嚴淨土分" },
  { text: "法尚應舍，何況非法", source: "金剛經 · 正信希有分" },
  { text: "無我相、無人相、無眾生相、無壽者相", source: "金剛經 · 離相寂滅分" },
  { text: "若以色見我，以音聲求我，是人行邪道，不能見如來", source: "金剛經 · 知見不生分" },
  { text: "一切賢聖，皆以無為法而有差別", source: "金剛經 · 無為福勝分" },
  { text: "是法平等，無有高下", source: "金剛經 · 淨心行善分" },
  { text: "云何為人演說？不取於相，如如不動", source: "金剛經 · 離相寂滅分" },
  { text: "身相無相，不可以身相得見如來", source: "金剛經 · 如理實見分" },
  { text: "如來說諸相具足，即非諸相具足，是名諸相具足", source: "金剛經 · 離相寂滅分" },
  { text: "菩提本無樹，明鏡亦非台，本來無一物，何處惹塵埃", source: "六祖壇經" },
  { text: "不是風動，不是幡動，仁者心動", source: "六祖壇經" },
  { text: "迷時師度，悟了自度", source: "六祖壇經" },
  { text: "日日是好日，時時是好時", source: "雲門匡禪師" },
  { text: "吃茶去", source: "趙州從諗禪師" },
  { text: "平常心是道", source: "南泉普願禪師" },
  { text: "春有百花秋有月，夏有涼風冬有雪，若無閒事掛心頭，便是人間好時節", source: "無門慧開禪師" },
  { text: "虛空無邊際，功德亦如是", source: "華嚴經" },
  { text: "一花一世界，一葉一如來", source: "華嚴經" },
  { text: "心無罣礙，無罣礙故，無有恐怖，遠離顛倒夢想", source: "心經" },
  { text: "色即是空，空即是色", source: "心經" },
  { text: "萬法皆空，因果不空", source: "因果經" },
  { text: "諸行無常，是生滅法；生滅滅已，寂滅為樂", source: "涅槃經" },
]

// 命理小語
const baziQuotes = [
  { text: "命由己造，相由心生", source: "命理格言" },
  { text: "陰陽順逆妙無窮，二至歸鄉一路宮", source: "命理基礎" },
  { text: "君子知命不懼，日日自新", source: "論語" },
  { text: "積善之家必有餘慶", source: "易經" },
  { text: "天行健君子以自強不息", source: "易經" },
  { text: "地勢坤君子以厚德載物", source: "易經" },
  { text: "知命者不怨天，知己者不怨人", source: "孔子" },
  { text: "富貴不能淫，貧賤不能移，威武不能屈", source: "孟子" },
  { text: "命裡有時終須有，命裡無時莫強求", source: "俗諺" },
  { text: "五行流轉，生生不息", source: "五行學說" },
]

const allQuotes = [...quotes, ...baziQuotes]

function App() {
  const [currentQuote, setCurrentQuote] = useState(allQuotes[0])
  const [isAnimating, setIsAnimating] = useState(false)
  const [count, setCount] = useState(() => {
    const saved = localStorage.getItem('gatha-count')
    return saved ? parseInt(saved) : 0
  })

  useEffect(() => {
    localStorage.setItem('gatha-count', count.toString())
  }, [count])

  const shuffleQuote = () => {
    if (isAnimating) return
    
    setIsAnimating(true)
    let newQuote = currentQuote
    while (newQuote.text === currentQuote.text) {
      newQuote = allQuotes[Math.floor(Math.random() * allQuotes.length)]
    }
    
    setTimeout(() => {
      setCurrentQuote(newQuote)
      setCount(c => c + 1)
      setIsAnimating(false)
    }, 300)
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f5f0] overflow-hidden relative">
      {/* 背景氛圍 */}
      <div className="fixed inset-0 grain" />
      <div className="fixed inset-0 bg-gradient-to-b from-[#0a0a0a] via-[#0f0f0f] to-[#0a0a0a]" />
      
      {/* 浮動光暈 */}
      <div className="fixed top-1/4 -left-32 w-96 h-96 bg-[#b87333]/5 rounded-full blur-3xl" />
      <div className="fixed bottom-1/4 -right-32 w-96 h-96 bg-[#b87333]/3 rounded-full blur-3xl" />

      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-6">
        {/* 標題 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h1 className="text-3xl md:text-5xl font-light tracking-[0.2em] text-[#b87333] mb-4" style={{ fontFamily: 'Noto Serif TC, serif' }}>
            今日偈語
          </h1>
          <p className="text-sm text-[#666] tracking-widest uppercase">
            Gatha of the Day
          </p>
        </motion.div>

        {/* 卡片區域 */}
        <motion.div
          className="w-full max-w-xl"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.6 }}
        >
          <div className="relative bg-[#141414] border border-[#2a2a2a] rounded-sm p-8 md:p-12 shadow-2xl">
            {/* 卡片裝飾 */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2">
              <div className="w-3 h-3 bg-[#b87333]" />
            </div>
            <div className="absolute top-4 left-4 w-8 h-8 border-t border-l border-[#b87333]/30" />
            <div className="absolute bottom-4 right-4 w-8 h-8 border-b border-r border-[#b87333]/30" />

            {/* 偈語內容 */}
            <AnimatePresence mode="wait">
              <motion.div
                key={currentQuote.text}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="text-center"
              >
                <p 
                  className="text-xl md:text-2xl leading-relaxed mb-8 text-[#e8e8e0]"
                  style={{ fontFamily: 'Noto Serif TC, serif' }}
                >
                  「{currentQuote.text}」
                </p>
                <p className="text-sm text-[#666] tracking-wider">
                  — {currentQuote.source}
                </p>
              </motion.div>
            </AnimatePresence>
          </div>
        </motion.div>

        {/* 按钮 */}
        <motion.button
          onClick={shuffleQuote}
          disabled={isAnimating}
          className="mt-12 group relative px-8 py-3 bg-transparent border border-[#b87333]/50 text-[#b87333] tracking-widest uppercase text-sm hover:border-[#b87333] transition-all duration-300 disabled:opacity-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <span className="relative z-10">抽取偈語</span>
          <div className="absolute inset-0 bg-[#b87333]/0 group-hover:bg-[#b87333]/10 transition-colors duration-300" />
        </motion.button>

        {/* 計數器 */}
        <motion.div
          className="mt-8 text-xs text-[#444] tracking-widest"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
        >
          累計抽取 {count} 次
        </motion.div>

        {/* 底部裝飾 */}
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 text-[#333] text-xs tracking-[0.3em]">
          ◆
        </div>
      </div>

      <style>{`
        .grain::before {
          content: '';
          position: fixed;
          inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
          opacity: 0.03;
          pointer-events: none;
          z-index: 100;
        }
      `}</style>
    </div>
  )
}

export default App

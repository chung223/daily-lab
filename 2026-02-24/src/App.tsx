import { useState, useEffect } from 'react'
import './App.css'

// 躺平語錄庫
const lyingFlatQuotes = [
  "今天的努力，就是明天的廢物",
  "別問我為什麼不努力，問就是不想",
  "睡覺是對躺平最基本的尊重",
  "能躺著絕不坐著，能坐著絕不站著",
  "廢話不多說，躺平是王道",
  "努力不一定成功，但不努力一定很輕鬆",
  "我最大的成就，就是什麼都沒做",
  "人生不如意十之八九，剩下的十之一二是躺平",
  "老闆畫的餅，不如我躺平的床",
  "我不是懶，我只是對世界無欲無求",
  "今天的我，已經是未來最努力的一天",
  "與其努力後失敗，不如直接躺平",
  "躺平不是放棄，是對這個世界的溫柔",
  "我的座右銘：能怪別人就不怪自己",
  "日出而作，日落而躺",
  "努力是別人的故事，躺平是我的日常",
  "當你覺得累的時候，恭喜你，你正在走上坡路...的下坡",
  "不是說好要好好努力嗎？好啊，我躺著努力",
  "我的未來不是夢，是做不完的白日夢",
  "別人成功的故事聽多了，不如躺下來想想自己的故事",
  "人生就像打遊戲，我選擇簡單模式",
  "今天的事情留到明天，明天的事情留到後天",
  "努力不一定有回報，但不努力一定很舒服",
  "我已經很努力在省力氣了",
  "躺平是對這個內卷世界的小小反抗",
  "別人跑步前進，我躺著前進",
  "真正的勇士，敢于直面慘淡的躺平",
  "平平淡淡才是真，躺躺平平才是福",
  "我的字典裡沒有「努力」兩個字...因為我沒有字典",
  "只要我躺得夠快，焦慮就追不上我"
]

// 風格變化庫
const styleVariations = [
  { prefix: "🛏️", suffix: "" },
  { prefix: "💤", suffix: " Zzz..." },
  { prefix: "🌙", suffix: "" },
  { prefix: "😴", suffix: "" },
  { prefix: "🫠", suffix: "" },
  { prefix: "🦥", suffix: " 樹懶同路人" },
  { prefix: "🧘", suffix: " 躺平也是一種修煉" },
  { prefix: "🏖️", suffix: " 人生海海，躺著最快" },
  { prefix: "🌊", suffix: " 隨波逐流，躺著漂流" },
  { prefix: "☁️", suffix: " 雲淡風輕，躺平最輕" }
]

function App() {
  const [currentQuote, setCurrentQuote] = useState("")
  const [currentStyle, setCurrentStyle] = useState(styleVariations[0])
  const [isGenerating, setIsGenerating] = useState(false)
  const [totalCount, setTotalCount] = useState(0)
  const [showCopied, setShowCopied] = useState(false)

  useEffect(() => {
    // 載入歷史計數
    const saved = localStorage.getItem('lyingFlatCount')
    if (saved) setTotalCount(parseInt(saved, 10))
    
    // 初始顯示一句
    generateQuote()
  }, [])

  const generateQuote = () => {
    setIsGenerating(true)
    
    // 隨機選語錄
    const randomQuote = lyingFlatQuotes[Math.floor(Math.random() * lyingFlatQuotes.length)]
    // 隨機選風格
    const randomStyle = styleVariations[Math.floor(Math.random() * styleVariations.length)]
    
    setTimeout(() => {
      setCurrentQuote(randomQuote)
      setCurrentStyle(randomStyle)
      setIsGenerating(false)
      
      // 更新計數
      const newCount = totalCount + 1
      setTotalCount(newCount)
      localStorage.setItem('lyingFlatCount', newCount.toString())
    }, 300)
  }

  const copyToClipboard = async () => {
    const fullText = `${currentStyle.prefix} ${currentQuote}${currentStyle.suffix}`
    await navigator.clipboard.writeText(fullText)
    setShowCopied(true)
    setTimeout(() => setShowCopied(false), 2000)
  }

  return (
    <div className="app-container">
      {/* 顆粒感背景 */}
      <div className="grain-overlay"></div>
      
      {/* 頂部裝飾 */}
      <div className="floating-shapes">
        <div className="shape shape-1">💤</div>
        <div className="shape shape-2">🛏️</div>
        <div className="shape shape-3">😴</div>
      </div>

      <main className="main-content">
        {/* 標題區 */}
        <header className="header">
          <h1 className="title">
            <span className="title-main">廢文產生器</span>
            <span className="title-sub">躺平語錄 · 全球首發</span>
          </h1>
          <p className="subtitle">當這個世界太卷，就讓自己成為最淡定的存在</p>
        </header>

        {/* 顯示區 */}
        <div className="quote-display">
          <div className={`quote-card ${isGenerating ? 'generating' : ''}`}>
            <span className="quote-emoji">{currentStyle.prefix}</span>
            <p className="quote-text">{currentQuote}</p>
            <span className="quote-suffix">{currentStyle.suffix}</span>
          </div>
        </div>

        {/* 按鈕區 */}
        <div className="actions">
          <button 
            className="generate-btn"
            onClick={generateQuote}
            disabled={isGenerating}
          >
            <span className="btn-icon">{isGenerating ? '🤔' : '🎲'}</span>
            <span className="btn-text">{isGenerating ? '思考中...' : '再來一句'}</span>
          </button>
          
          <button 
            className="copy-btn"
            onClick={copyToClipboard}
          >
            <span className="btn-icon">{showCopied ? '✅' : '📋'}</span>
            <span className="btn-text">{showCopied ? '複製成功！' : '複製語錄'}</span>
          </button>
        </div>

        {/* 計數器 */}
        <div className="stats">
          <div className="stat-item">
            <span className="stat-number">{totalCount}</span>
            <span className="stat-label">躺平次數</span>
          </div>
        </div>

        {/* 底部提示 */}
        <footer className="footer">
          <p>🤫 偷偷告訴你：躺平是對這個時代溫柔的反叛</p>
        </footer>
      </main>
    </div>
  )
}

export default App

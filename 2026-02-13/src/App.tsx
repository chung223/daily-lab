import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Terminal, AlertTriangle, RefreshCw, X, Check, HelpCircle } from 'lucide-react'
import { cn } from './lib/utils'

// Possible answers
const ANSWERS = [
  { text: "YES", type: "positive", icon: Check },
  { text: "NO", type: "negative", icon: X },
  { text: "MAYBE", type: "neutral", icon: HelpCircle },
  { text: "ASK AGAIN", type: "neutral", icon: RefreshCw },
  { text: "DOOM IMMINENT", type: "negative", icon: AlertTriangle },
  { text: "THE VOID STARES BACK", type: "neutral", icon: Terminal },
  { text: "UNLIKELY", type: "negative", icon: X },
  { text: "CERTAINLY", type: "positive", icon: Check },
  { text: "CHAOS REIGNS", type: "neutral", icon: Sparkles },
  { text: "SILENCE", type: "neutral", icon: Terminal },
]

interface HistoryItem {
  id: number
  question: string
  answer: typeof ANSWERS[0]
  timestamp: string
}

function App() {
  const [question, setQuestion] = useState('')
  const [isConsulting, setIsConsulting] = useState(false)
  const [currentAnswer, setCurrentAnswer] = useState<typeof ANSWERS[0] | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [glitchIntensity, setGlitchIntensity] = useState(0)

  const handleConsult = (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return

    setIsConsulting(true)
    setGlitchIntensity(1) // Max glitch
    setCurrentAnswer(null)

    // Simulate processing time with chaotic glitching
    setTimeout(() => {
      const randomAnswer = ANSWERS[Math.floor(Math.random() * ANSWERS.length)]
      setCurrentAnswer(randomAnswer)
      setIsConsulting(false)
      setGlitchIntensity(0)
      
      const newItem: HistoryItem = {
        id: Date.now(),
        question: question,
        answer: randomAnswer,
        timestamp: new Date().toLocaleTimeString(),
      }
      setHistory(prev => [newItem, ...prev])
      setQuestion('')
    }, 1500)
  }

  return (
    <div className="min-h-screen bg-[var(--color-oracle-bg)] text-[var(--color-oracle-text)] flex flex-col items-center justify-center p-4 font-mono overflow-hidden relative">
      
      {/* Background Noise / Grid */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03] z-0" 
           style={{ backgroundImage: `linear-gradient(#333 1px, transparent 1px), linear-gradient(90deg, #333 1px, transparent 1px)`, backgroundSize: '20px 20px' }}>
      </div>

      <main className="z-10 w-full max-w-md flex flex-col gap-8">
        
        {/* Header */}
        <header className="border-b border-[var(--color-oracle-border)] pb-4 mb-4">
          <h1 className="text-4xl font-bold tracking-tighter uppercase flex items-center justify-between">
            <span className="text-[var(--color-oracle-accent)]">ORACLE</span>
            <span className="text-sm opacity-50 tracking-widest">v13.0.0</span>
          </h1>
          <p className="text-xs text-neutral-500 mt-1 uppercase tracking-widest">
            Friday the 13th Edition
          </p>
        </header>

        {/* Output Display */}
        <div className="min-h-[200px] flex items-center justify-center border border-[var(--color-oracle-border)] bg-[var(--color-oracle-surface)] relative overflow-hidden group">
          <AnimatePresence mode="wait">
            {isConsulting ? (
              <motion.div 
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[var(--color-oracle-accent)] text-center animate-pulse"
              >
                <div className="text-6xl font-bold mb-2">...</div>
                <div className="text-xs uppercase tracking-[0.3em]">COMMUNING WITH VOID</div>
              </motion.div>
            ) : currentAnswer ? (
              <motion.div 
                key="result"
                initial={{ scale: 0.8, opacity: 0, filter: 'blur(10px)' }}
                animate={{ scale: 1, opacity: 1, filter: 'blur(0px)' }}
                transition={{ type: "spring", bounce: 0.5 }}
                className="text-center p-6 w-full"
              >
                <currentAnswer.icon 
                  className={cn("w-16 h-16 mx-auto mb-4", 
                    currentAnswer.type === 'positive' ? 'text-green-500' : 
                    currentAnswer.type === 'negative' ? 'text-[var(--color-oracle-accent)]' : 'text-yellow-500'
                  )} 
                />
                <h2 className="text-4xl font-bold uppercase tracking-tight break-words leading-tight glitch-text" data-text={currentAnswer.text}>
                  {currentAnswer.text}
                </h2>
              </motion.div>
            ) : (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.3 }}
                className="text-center p-8"
              >
                <Terminal className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm uppercase tracking-widest">AWAITING INPUT</p>
              </motion.div>
            )}
          </AnimatePresence>
          
          {/* Scanline effect */}
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[rgba(255,255,255,0.02)] to-transparent h-[4px] w-full animate-[scan_2s_linear_infinite] pointer-events-none" />
        </div>

        {/* Input Form */}
        <form onSubmit={handleConsult} className="flex flex-col gap-2 relative">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="ASK THE ORACLE..."
            className="w-full bg-transparent border-b border-[var(--color-oracle-border)] p-4 text-lg outline-none focus:border-[var(--color-oracle-accent)] transition-colors placeholder:text-neutral-700 uppercase"
            autoFocus
          />
          <button 
            type="submit" 
            disabled={!question.trim() || isConsulting}
            className="mt-4 bg-[var(--color-oracle-surface)] border border-[var(--color-oracle-border)] py-4 text-sm uppercase tracking-[0.2em] hover:bg-[var(--color-oracle-accent)] hover:text-black hover:border-[var(--color-oracle-accent)] transition-all disabled:opacity-50 disabled:cursor-not-allowed group relative overflow-hidden"
          >
            <span className="relative z-10 group-hover:hidden">CONSULT</span>
            <span className="relative z-10 hidden group-hover:inline font-bold">REVEAL FATE</span>
          </button>
        </form>

        {/* History */}
        {history.length > 0 && (
          <div className="mt-8 border-t border-[var(--color-oracle-border)] pt-4">
            <h3 className="text-xs uppercase tracking-widest text-neutral-500 mb-4">Past Prophecies</h3>
            <ul className="space-y-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
              {history.map((item) => (
                <li key={item.id} className="text-sm flex justify-between items-start border-l-2 border-[var(--color-oracle-border)] pl-3 py-1 hover:border-[var(--color-oracle-accent)] hover:bg-[var(--color-oracle-surface)] transition-colors cursor-default group">
                  <div className="flex flex-col">
                    <span className="opacity-60 text-xs">{item.question}</span>
                    <span className={cn("font-bold", 
                      item.answer.type === 'positive' ? 'text-green-500' : 
                      item.answer.type === 'negative' ? 'text-[var(--color-oracle-accent)]' : 'text-yellow-500'
                    )}>{item.answer.text}</span>
                  </div>
                  <span className="text-[10px] opacity-30 whitespace-nowrap">{item.timestamp}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="fixed bottom-4 text-[10px] text-neutral-600 uppercase tracking-widest">
        SYSTEM: ONLINE // LATENCY: 13ms // DATE: 2026-02-13
      </footer>

    </div>
  )
}

export default App

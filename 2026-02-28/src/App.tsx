import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// 六十四卦數據
const hexagrams = [
  { id: 1, name: '乾為天', symbol: '☰', chinese: '乾', meaning: '元亨利貞', desc: '象徵天，龍騰飛躍，諸事大吉。君子自強不息。' },
  { id: 2, name: '坤為地', symbol: '☷', chinese: '坤', meaning: '元亨，利牝馬之貞', desc: '象徵地，柔順寬厚。君子厚德載物。' },
  { id: 3, name: '水雷屯', symbol: '☵☳', chinese: '屯', meaning: '元亨利貞，勿用有攸往', desc: '萬物始生，困難重重。宜靜待機。' },
  { id: 4, name: '山水蒙', symbol: '☶☵', chinese: '蒙', meaning: '亨，匪我求童蒙，童蒙求我', desc: '蒙昧初期，教育啟發。虛心求教。' },
  { id: 5, name: '水天需', symbol: '☵☰', chinese: '需', meaning: '有孚，光亨，貞吉', desc: '等待時機，有信則通。耐心守候。' },
  { id: 6, name: '天水讼', symbol: '☰☵', chinese: '讼', meaning: '有孚窒惕，中吉，終凶', desc: "爭論訴訟，宜於和解。切勿興獄。" },
  { id: 7, name: '地水師', symbol: '☷☵', chinese: '師', meaning: '貞丈人吉，無咎', desc: '軍隊出征，帥領眾人。以正治國。' },
  { id: 8, name: '水地比', symbol: '☵☷', chinese: '比', meaning: '吉，原筮元永貞，無咎', desc: '親密比附，輔佐大臣。誠信親近。' },
  { id: 9, name: '風天小畜', symbol: '☴☰', chinese: '小畜', meaning: '亨，密雲不雨，自我西郊', desc: '小有積蓄，力量不足。繼續積累。' },
  { id: 10, name: '天澤履', symbol: '☰☱', chinese: '履', meaning: '亨，履虎尾，不咥人，亨', desc: '踩虎尾而不被咬。謹慎行事。' },
  { id: 11, name: '地天泰', symbol: '☷☰', chinese: '泰', meaning: '小往大來，吉亨', desc: '天地交泰，陰陽和暢。萬事亨通。' },
  { id: 12, name: '天地否', symbol: '☰☷', chinese: '否', meaning: '否之匪人，不利君子貞', desc: '天地不交，閉塞不通。宜守不宜進。' },
  { id: 13, name: '天火同人', symbol: '☰☲', chinese: '同人', meaning: '同人於野，亨，利涉大川', desc: '同人於野，志同道合。合作共贏。' },
  { id: 14, name: '火天大有', symbol: '☲☰', chinese: '大有', meaning: '元亨', desc: '大獲所有，富有萬物。誠信則吉。' },
  { id: 15, name: '地山謙', symbol: '☷☶', chinese: '謙', meaning: '亨，君子有終', desc: '山在地中，謙遜不驕。君子有終。' },
  { id: 16, name: '雷地豫', symbol: '☳☷', chinese: '豫', meaning: '利建侯行師', desc: '雷出地上，歡悅和樂。宜於行事。' },
  { id: 17, name: '澤雷隨', symbol: '☱☳', chinese: '隨', meaning: '元亨利貞，無咎', desc: '澤中雷聲，隨時而動。順勢而為。' },
  { id: 18, name: '山風蠱', symbol: '☶☴', chinese: '蠱', meaning: '元亨，利涉大川', desc: '風在山下，腐敗之物。革新整飭。' },
  { id: 19, name: '地澤臨', symbol: '☷☱', chinese: '臨', meaning: '元亨利貞，至於八月有凶', desc: '澤在地上，君臨天下。監臨之時。' },
  { id: 20, name: '風觀', symbol: '☴☷', chinese: '觀', meaning: '盥而不荐，有孚颙若', desc: '風行地上，觀仰莊嚴。誠信示人。' },
  { id: 21, name: '火雷噬嗑', symbol: '☲☳', chinese: '噬嗑', meaning: '亨，利用獄', desc: '噬嗑而亨，剛柔分明。斷案公平。' },
  { id: 22, name: '山火賁', symbol: '☶☲', chinese: '賁', meaning: '亨，小利有攸往', desc: '山火相映，文明裝飾。適度美化。' },
  { id: 23, name: '山地剝', symbol: '☶☷', chinese: '剝', meaning: '不利有攸往', desc: '山地剝落，小人道长。宜靜不宜動。' },
  { id: 24, name: '地復', symbol: '☷☳', chinese: '復', meaning: '亨，出入無疾，朋來無咎', desc: '大地回春，陽氣復生。萬物復甦。' },
  { id: 25, name: '天雷無妄', symbol: '☰☳', chinese: '無妄', meaning: '元亨利貞，其匪正有眚', desc: '天雷無妄，不妄為則吉。順其自然。' },
  { id: 26, name: '山天大畜', symbol: '☶☰', chinese: '大畜', meaning: '利貞，不家食吉，利涉大川', desc: '山中畜天，大有積蓄。蓄德待時。' },
  { id: 27, name: '山雷頤', symbol: '☶☳', chinese: '頤', meaning: '貞吉，觀頤，自求口實', desc: '山雷頤腮，養生之道。自食其力。' },
  { id: 28, name: '澤風大過', symbol: '☱☴', chinese: '大過', meaning: '棟橈，利有攸往，亨', desc: '澤風大過，異常過度。須防傾覆。' },
  { id: 29, name: '坎為水', symbol: '☵', chinese: '坎', meaning: '習坎，有孚，維心亨，行有尚', desc: '象徵水，險阻重重。心亨則通。' },
  { id: 30, name: '離為火', symbol: '☲', chinese: '離', meaning: '利貞，亨，畜牝牛吉', desc: '象徵火，光明美麗。依附則吉。' },
  { id: 31, name: '澤山咸', symbol: '☱☶', chinese: '咸', meaning: '亨利貞，取女吉', desc: '澤山相咸，感應之心。虛心接受。' },
  { id: 32, name: '雷風恆', symbol: '☳☴', chinese: '恆', meaning: '亨無咎，利貞，利有攸往', desc: '雷風相與，持之以恆。恆久之道。' },
  { id: 33, name: '天山遯', symbol: '☰☶', chinese: '遯', meaning: '亨，小利貞', desc: '天山遯藏，退隱待機。小心謹慎。' },
  { id: 34, name: '雷天大壯', symbol: '☳☰', chinese: '大壯', meaning: '利貞', desc: '雷在天上，強盛壯大。不可妄動。' },
  { id: 35, name: '火地晉', symbol: '☲☷', chinese: '晉', meaning: '康侯用錫馬蕃庶，晝日三接', desc: '火地晉升，日益精進。受賞晉升。' },
  { id: 36, name: '地火明夷', symbol: '☷☲', chinese: '明夷', meaning: '利艱貞', desc: '明入地中，光明受傷。晦而守正。' },
  { id: 37, name: '風火家人', symbol: '☴☲', chinese: '家人', meaning: '利女貞', desc: '風火家人，家庭和樂。女主內事。' },
  { id: 38, name: '火澤睽', symbol: '☲☱', chinese: '睽', meaning: '小事吉', desc: '火澤相睽，乖離分散。求同存異。' },
  { id: 39, name: '水山蹇', symbol: '☵☶', chinese: '蹇', meaning: '利西南，不利東北，利見大人，貞吉', desc: '水山蹇滯，前路艱難。西南有利。' },
  { id: 40, name: '雷水解', symbol: '☳☵', chinese: '解', meaning: '利西南，無所往，其來復吉', desc: '雷水解散，困難解除。宜靜待機。' },
  { id: 41, name: '山澤損', symbol: '☶☱', chinese: '損', meaning: '有孚，元吉，無咎可貞，利有攸往', desc: '山澤相損，減損之道。誠信則吉。' },
  { id: 42, name: '風雷益', symbol: '☴☳', chinese: '益', meaning: '利有攸往，利涉大川', desc: '風雷益增，受益匪淺。增益之道。' },
  { id: 43, name: '澤天夬', symbol: '☱☰', chinese: '夬', meaning: '揚於王庭，孚號有厲，告自邑，不利即戎', desc: '澤天夬決，果斷除惡。防備小人。' },
  { id: 44, name: '天風姤', symbol: '☰☴', chinese: '姤', meaning: '女壯，勿用取女', desc: '天下有風，機遇將至。防備過度。' },
  { id: 45, name: '澤地萃', symbol: '☱☷', chinese: '萃', meaning: '亨，王假有廟，利見大人，亨利貞', desc: '澤地萃聚，薈萃一堂。誠信聚集。' },
  { id: 46, name: '地風升', symbol: '☷☴', chinese: '升', meaning: '元亨，用見大人，勿恤，南征吉', desc: '地風升進，步步高升。南方吉祥。' },
  { id: 47, name: '澤水困', symbol: '☱☵', chinese: '困', meaning: '亨，貞大人吉，無咎，有言不信', desc: '澤水困乏，處困境中。守正待時。' },
  { id: 48, name: '水風井', symbol: '☵☴', chinese: '井', meaning: '改邑不改井，無喪無得，往來井井', desc: '水風井泉，取之不盡。堅守正道。' },
  { id: 49, name: '澤火革', symbol: '☱☲', chinese: '革', meaning: '己日乃孚，元亨利貞，悔亡', desc: '澤火革變，改革創新。順時而變。' },
  { id: 50, name: '火風鼎', symbol: '☲☴', chinese: '鼎', meaning: '元吉，亨', desc: '火風鼎立，權位穩固。鼎新立異。' },
  { id: 51, name: '震為雷', symbol: '☳', chinese: '震', meaning: '亨，震來虩虩，笑言啞啞', desc: '象徵雷，震動驚懼。化險為夷。' },
  { id: 52, name: '艮為山', symbol: '☶', chinese: '艮', meaning: '艮其背，不獲其身，行其庭，不見其人，無咎', desc: '象徵山，靜止不動。止於其所。' },
  { id: 53, name: '風山漸', symbol: '☴☶', chinese: '漸', meaning: '女歸吉，利貞', desc: '風山漸進，循序漸進。女子歸吉。' },
  { id: 54, name: '雷澤歸妹', symbol: '☳☱', chinese: '歸妹', meaning: '征凶，無攸利', desc: '雷澤歸妹，出嫁之象。不宜妄動。' },
  { id: 55, name: '雷火豐', symbol: '☳☲', chinese: '豐', meaning: '亨，王假之，勿憂，宜日中', desc: '雷火豐盛，盛大豐滿。日中則昃。' },
  { id: 56, name: '火山旅', symbol: '☶☲', chinese: '旅', meaning: '小亨，旅貞吉', desc: '火山旅居，漂泊在外。小心守正。' },
  { id: 57, name: '巽為風', symbol: '☴', chinese: '巽', meaning: '小亨，利有攸往，利見大人', desc: '象徵風，順從謙遜。宜於行事。' },
  { id: 58, name: '兌為澤', symbol: '☱', chinese: '兌', meaning: '亨，利貞', desc: '象徵澤，愉悅和樂。堅守正道。' },
  { id: 59, name: '風水渙', symbol: '☴☵', chinese: '渙', meaning: '亨，王假有廟，勿憂，宜日中', desc: '風水渙散，離散聚合。亨通之道。' },
  { id: 60, name: '水澤節', symbol: '☵☱', chinese: '節', meaning: '亨，苦節不可貞', desc: '水澤節制，適度節省。勿過嚴苛。' },
  { id: 61, name: '風澤中孚', symbol: '☴☱', chinese: '中孚', meaning: '豚魚吉，利涉大川，利貞', desc: '風澤中孚，誠信相孚。堅守正道。' },
  { id: 62, name: '雷山小過', symbol: '☳☶', chinese: '小過', meaning: '亨利貞，可小事，不可大事', desc: '雷山小過，小有過失。宜行小事。' },
  { id: 63, name: '水火既濟', symbol: '☵☲', chinese: '既濟', meaning: '亨小利貞，初吉終亂', desc: '水火既濟，功成圓滿。慎終如始。' },
  { id: 64, name: '火水未濟', symbol: '☲☵', chinese: '未濟', meaning: '亨，小狐汔濟，濡其尾，無攸利', desc: '火水未濟，功未完成。繼續努力。' },
];

function App() {
  const [selectedHexagram, setSelectedHexagram] = useState<typeof hexagrams[0] | null>(null);
  const [isShuffling, setIsShuffling] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [drawCount, setDrawCount] = useState(0);

  useEffect(() => {
    const saved = localStorage.getItem('iching-draw-count');
    if (saved) setDrawCount(parseInt(saved, 10));
  }, []);

  const handleDraw = async () => {
    setIsShuffling(true);
    setShowResult(false);
    setSelectedHexagram(null);

    // Shuffle animation
    for (let i = 0; i < 20; i++) {
      await new Promise(r => setTimeout(r, 80));
      const random = hexagrams[Math.floor(Math.random() * hexagrams.length)];
      setSelectedHexagram(random);
    }

    // Final selection
    await new Promise(r => setTimeout(r, 200));
    const final = hexagrams[Math.floor(Math.random() * hexagrams.length)];
    setSelectedHexagram(final);
    setIsShuffling(false);
    setShowResult(true);

    // Update count
    const newCount = drawCount + 1;
    setDrawCount(newCount);
    localStorage.setItem('iching-draw-count', newCount.toString());
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f5f0] font-sans overflow-x-hidden">
      {/* Grain overlay */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] z-50 mix-blend-overlay"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`
        }}
      />

      {/* Header */}
      <header className="py-8 px-4 text-center relative">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <h1 className="text-4xl md:text-5xl font-serif tracking-wide text-[#d4af37] mb-2">
            易經六十四卦
          </h1>
          <p className="text-[#8a8a8a] text-sm tracking-widest uppercase">
            I Ching Hexagram Oracle
          </p>
        </motion.div>
      </header>

      {/* Main area */}
      <main className="max-w-2xl mx-auto px-4 py-8">
        <AnimatePresence mode="wait">
          {showResult && selectedHexagram ? (
            <motion.div
              key="result"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="text-center"
            >
              {/* Result card */}
              <div className="relative mb-8">
                <div className="absolute inset-0 bg-gradient-to-b from-[#d4af37]/20 to-transparent rounded-3xl blur-3xl" />
                <div className="relative bg-[#141414] border border-[#d4af37]/30 rounded-3xl p-8 md:p-12">
                  <motion.div
                    initial={{ scale: 0, rotate: -180 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: "spring", damping: 15 }}
                    className="text-8xl md:text-9xl mb-4"
                  >
                    {selectedHexagram.symbol}
                  </motion.div>
                  <h2 className="text-3xl md:text-4xl font-serif text-[#d4af37] mb-2">
                    {selectedHexagram.name}
                  </h2>
                  <p className="text-lg text-[#c0a062] mb-4">
                    {selectedHexagram.meaning}
                  </p>
                  <p className="text-[#a0a0a0] leading-relaxed max-w-md mx-auto">
                    {selectedHexagram.desc}
                  </p>
                </div>
              </div>

              {/* Draw again button */}
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                onClick={handleDraw}
                className="px-8 py-3 bg-[#d4af37] text-[#0a0a0a] font-semibold rounded-full hover:bg-[#c9a227] transition-colors duration-300"
              >
                再次抽卦
              </motion.button>
            </motion.div>
          ) : (
            <motion.div
              key="picker"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center"
            >
              {/* Display */}
              <div className="relative mb-12">
                {isShuffling ? (
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ repeat: Infinity, duration: 0.3 }}
                  >
                    <div className="text-8xl md:text-9xl">
                      {selectedHexagram?.symbol || '☰'}
                    </div>
                    <p className="text-xl text-[#d4af37] mt-4">
                      {selectedHexagram?.name || ''}
                    </p>
                  </motion.div>
                ) : (
                  <div className="text-8xl md:text-9xl text-[#2a2a2a]">
                    ☰
                  </div>
                )}
              </div>

              {/* Draw button */}
              <button
                onClick={handleDraw}
                disabled={isShuffling}
                className={`px-12 py-4 bg-gradient-to-r from-[#d4af37] to-[#b8962e] text-[#0a0a0a] text-xl font-bold rounded-full 
                  hover:shadow-[0_0_40px_rgba(212,175,55,0.4)] transition-all duration-300 transform hover:scale-105
                  disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none`}
              >
                {isShuffling ? '占卜中...' : '抽一卦'}
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-16 text-center"
        >
          <p className="text-[#4a4a4a] text-sm">
            累計抽卦次數：<span className="text-[#d4af37] font-mono">{drawCount}</span>
          </p>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="py-8 text-center text-[#3a3a3a] text-xs">
        <p>誠則靈，心誠則應</p>
      </footer>
    </div>
  );
}

export default App;

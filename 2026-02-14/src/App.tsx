import './App.css'

function App() {
  return (
    <div className="page">
      <div className="grain" />
      <header className="nav">
        <div className="logo">NIGHTSHIFT</div>
        <nav className="links">
          <a href="#features">功能</a>
          <a href="#flow">流程</a>
          <a href="#cta">加入</a>
        </nav>
        <button className="ghost">取得範本</button>
      </header>

      <main className="hero">
        <div className="hero-text">
          <span className="badge">凌晨實驗室 03:10 作品</span>
          <h1>
            你的夜班腦袋，
            也能有秩序
          </h1>
          <p>
            NightShift Planner 是一張超濃縮、超有儀式感的夜間工作節奏板：
            讓你把雜亂的念頭關進盒子裡，清楚知道下一步該做什麼。
          </p>
          <div className="actions">
            <button className="primary">立即下載模板</button>
            <button className="secondary">看範例排程</button>
          </div>
          <div className="stats">
            <div>
              <strong>45 分鐘</strong>
              <span>最短有效番茄</span>
            </div>
            <div>
              <strong>3</strong>
              <span>段式夜班節奏</span>
            </div>
            <div>
              <strong>1</strong>
              <span>分鐘冷卻儀式</span>
            </div>
          </div>
        </div>
        <div className="hero-card">
          <div className="orb" />
          <div className="card-title">夜班節奏板</div>
          <div className="card-block">
            <span>01 深度專注</span>
            <strong>40 分鐘</strong>
            <em>只做一件事</em>
          </div>
          <div className="card-block">
            <span>02 短休息</span>
            <strong>8 分鐘</strong>
            <em>放鬆眼睛</em>
          </div>
          <div className="card-block">
            <span>03 冷卻收尾</span>
            <strong>1 分鐘</strong>
            <em>寫下下一步</em>
          </div>
          <div className="card-note">把「想太多」切成可以做的節奏。</div>
        </div>
      </main>

      <section id="features" className="features">
        <article>
          <h3>夜間專注模式</h3>
          <p>一頁三區塊，把晚上最重要的事情鎖在視線中央。</p>
        </article>
        <article>
          <h3>冷卻儀式</h3>
          <p>結束前 1 分鐘寫下「明天的第一步」，降低隔日啟動成本。</p>
        </article>
        <article>
          <h3>疲勞計量</h3>
          <p>用簡單符號標記精神狀態，幫你知道何時該收工。</p>
        </article>
      </section>

      <section id="flow" className="flow">
        <div className="flow-title">
          <h2>最短流程，保留夜裡的乾淨感</h2>
          <p>不是更努力，而是更有節奏。</p>
        </div>
        <div className="flow-steps">
          <div>
            <span>步驟 01</span>
            <h4>寫下今晚唯一任務</h4>
            <p>避免無限開分頁，讓注意力保持在一條線上。</p>
          </div>
          <div>
            <span>步驟 02</span>
            <h4>切成 40-8-1</h4>
            <p>用三段節奏把腦袋收進一個可控盒子。</p>
          </div>
          <div>
            <span>步驟 03</span>
            <h4>留下明天的起點</h4>
            <p>把未完成的東西變成可接續的句子。</p>
          </div>
        </div>
      </section>

      <section id="cta" className="cta">
        <h2>今晚就用一次，明天你會感謝你自己</h2>
        <p>模板下載後可直接列印或放進筆記 App。</p>
        <button className="primary">下載 NightShift Planner</button>
      </section>

      <footer className="footer">Crafted at 03:10 · Lab Project 20260214</footer>
    </div>
  )
}

export default App

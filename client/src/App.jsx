import React, { useState, useRef, useEffect } from 'react';
import { getPage, uploadImage } from './api';
import './index.css';

function App() {
  const [topic, setTopic] = useState('');
  const [pages, setPages] = useState([]); // Array of {id, imageUrl, x, y}
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [isLoading, setIsLoading] = useState(false);
  const [ripple, setRipple] = useState(null);
  const [visionModel, setVisionModel] = useState('gemini');
  const [groundingMode, setGroundingMode] = useState('red_ring'); // Default to red_ring for Magazine layout
  const [activeTab, setActiveTab] = useState('detected'); // 'detected', 'prompt', 'raw'
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleInitialGenerate = async (e) => {
    e.preventDefault();
    if (!topic) return;
    
    setIsLoading(true);
    try {
      const data = await getPage({ query: topic, visionModel });
      setPages([data]);
      setCurrentIndex(0);
    } catch (err) {
      console.error(err);
      alert("Error generating page");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsLoading(true);
    try {
      const data = await uploadImage(file);
      setPages([data]);
      setCurrentIndex(0);
    } catch (err) {
      console.error(err);
      alert("Error uploading image");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCanvasClick = async (e) => {
    if (isLoading || currentIndex === -1) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;

    // Show ripple
    setRipple({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setTimeout(() => setRipple(null), 600);

    const parentPage = pages[currentIndex];
    setIsLoading(true);
    
    try {
      const data = await getPage({
        parentId: parentPage.id,
        x,
        y,
        visionModel,
        groundingMode
      });
      
      // Update the current page with click coordinates for history/red ring
      const updatedPages = [...pages.slice(0, currentIndex + 1)];
      updatedPages[currentIndex] = { ...updatedPages[currentIndex], lastClick: { x, y } };
      
      // Add the new page
      const newPages = [...updatedPages, data];
      setPages(newPages);
      setCurrentIndex(newPages.length - 1);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const currentPage = pages[currentIndex];

  return (
    <div className="app-container">
      <nav className="mag-nav">
        <div className="mag-logo">DRILL<span>DOWN</span></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <select 
            value={visionModel} 
            onChange={(e) => setVisionModel(e.target.value)}
            style={{
              background: 'var(--navy-light)',
              color: 'var(--white)',
              border: '1px solid rgba(237,106,44,0.4)',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="all">Compare ALL Models</option>
            <option value="gemini">Vision: Gemini 2.5 Pro (Best)</option>
            <option value="qwen">Vision: Qwen2-VL (Grounding)</option>
            <option value="internvl">Vision: InternVL-2 (SOTA)</option>
            <option value="pixtral">Vision: Pixtral (Mistral)</option>
            <option value="llava_next">Vision: LLaVA-NeXT (8B)</option>
            <option value="minicpm">Vision: MiniCPM-V (Efficient)</option>
            <option value="moondream">Vision: Moondream2 (Fast)</option>
            <option value="llava">Vision: Llava 1.5</option>
          </select>

          <select 
            value={groundingMode} 
            onChange={(e) => setGroundingMode(e.target.value)}
            style={{
              background: 'var(--navy-light)',
              color: 'var(--white)',
              border: '1px solid rgba(237,106,44,0.4)',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="sam2">Grounding: SAM2 (Segment)</option>
            <option value="red_ring">Grounding: Red Ring (Visual)</option>
          </select>

          {currentIndex !== -1 && (
            <div style={{ color: 'var(--orange)', fontSize: '14px', fontWeight: '700' }}>
              PAGE {currentIndex + 1} / {pages.length}
            </div>
          )}
        </div>
      </nav>

      <main className="main-layout">
        {currentIndex === -1 ? (
          <div className="topic-input-container">
            <h1><span>Drill</span>Down</h1>
            <p style={{ color: 'var(--gray-400)', marginBottom: '32px' }}>
              Type a topic. Click anywhere. Drill infinitely deep.
            </p>
            <form onSubmit={handleInitialGenerate} className="search-box">
              <input 
                type="text" 
                placeholder="How volcanoes work..." 
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                autoFocus
              />
              <button type="submit">Generate</button>
            </form>
            <div style={{ marginTop: '20px' }}>
              <p style={{ color: 'var(--gray-600)', margin: '10px 0' }}>or</p>
              <input 
                type="file" 
                ref={fileInputRef} 
                style={{ display: 'none' }} 
                onChange={handleFileUpload}
                accept="image/*"
              />
              <button 
                onClick={() => fileInputRef.current.click()}
                style={{ 
                  background: 'var(--navy-light)', 
                  color: 'var(--white)', 
                  border: '1px solid var(--orange)', 
                  padding: '12px 32px', 
                  borderRadius: '8px', 
                  cursor: 'pointer' 
                }}
              >
                Upload Image
              </button>
            </div>
          </div>
        ) : (
          <div className="canvas-wrapper" ref={canvasRef} onClick={handleCanvasClick}>
            {currentPage && (
              <img 
                src={currentPage.imageUrl} 
                className="canvas-image" 
                alt="Drill down visualization" 
              />
            )}
            
            {/* Show red ring for previous page click if available */}
            {currentPage?.lastClick && (
              <div 
                className="red-ring" 
                style={{ 
                  left: `${currentPage.lastClick.x * 100}%`, 
                  top: `${currentPage.lastClick.y * 100}%` 
                }} 
              />
            )}

            {ripple && (
              <div 
                className="ripple" 
                style={{ left: ripple.x, top: ripple.y }} 
              />
            )}

            {isLoading && (
              <div className="loading-overlay">
                <div className="spinner"></div>
                <p>Analyzing with {visionModel.toUpperCase()}...</p>
              </div>
            )}
          </div>
        )}
        {currentPage?.isComparison && (
          <div style={{ marginTop: '20px', width: '100%', maxWidth: '1200px', background: 'rgba(20,34,96,0.3)', borderRadius: '12px', border: '1px solid rgba(237,106,44,0.2)', overflow: 'hidden', padding: '24px' }}>
            <h2 style={{ fontSize: '24px', fontFamily: 'Playfair Display', marginBottom: '16px', color: 'var(--orange)', textAlign: 'center' }}>Vision Model Comparison</h2>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: 'rgba(10,22,40,0.8)' }}>
                    <th style={{ padding: '12px', textAlign: 'left', color: 'var(--gray-400)', borderBottom: '1px solid rgba(237,106,44,0.3)' }}>Model</th>
                    <th style={{ padding: '12px', textAlign: 'left', color: 'var(--gray-400)', borderBottom: '1px solid rgba(237,106,44,0.3)' }}>Object Detected</th>
                    <th style={{ padding: '12px', textAlign: 'left', color: 'var(--gray-400)', borderBottom: '1px solid rgba(237,106,44,0.3)' }}>Editorial Headline</th>
                    <th style={{ padding: '12px', textAlign: 'left', color: 'var(--gray-400)', borderBottom: '1px solid rgba(237,106,44,0.3)' }}>Drill Topic (Next Generation)</th>
                  </tr>
                </thead>
                <tbody>
                  {currentPage.results?.map(res => (
                    <tr key={res.model} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '12px', fontWeight: 'bold', color: 'var(--white)' }}>{res.model.toUpperCase()}</td>
                      <td style={{ padding: '12px', color: 'var(--gray-200)' }}>{res.metadata?.object || res.metadata?.error || 'N/A'}</td>
                      <td style={{ padding: '12px', color: 'var(--orange)' }}>{res.metadata?.editorial_headline || 'N/A'}</td>
                      <td style={{ padding: '12px', color: 'var(--gray-200)', fontStyle: 'italic' }}>{res.metadata?.drill_topic || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!currentPage?.isComparison && currentPage?.metadata && Object.keys(currentPage.metadata).length > 0 && (
          <div style={{ marginTop: '20px', width: '100%', maxWidth: '1000px', background: 'rgba(20,34,96,0.3)', borderRadius: '12px', border: '1px solid rgba(237,106,44,0.2)', overflow: 'hidden' }}>
            <div style={{ display: 'flex', background: 'rgba(10,22,40,0.5)', borderBottom: '1px solid rgba(237,106,44,0.2)' }}>
              {['detected', 'prompt', 'raw'].map(tab => (
                <button 
                  key={tab} 
                  onClick={() => setActiveTab(tab)}
                  style={{
                    padding: '12px 24px',
                    background: activeTab === tab ? 'rgba(237,106,44,0.1)' : 'transparent',
                    color: activeTab === tab ? 'var(--orange)' : 'var(--gray-400)',
                    border: 'none',
                    borderBottom: activeTab === tab ? '2px solid var(--orange)' : '2px solid transparent',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    letterSpacing: '1px'
                  }}
                >
                  {tab === 'detected' ? 'Detected Context' : tab === 'prompt' ? 'Vision Prompt' : 'Raw JSON Output'}
                </button>
              ))}
            </div>

            <div style={{ padding: '24px' }}>
              {activeTab === 'detected' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '24px' }}>
                  <div>
                    <div style={{ fontSize: '10px', color: 'var(--orange)', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '8px' }}>Analysis ({currentPage.groundingMode === 'sam2' ? 'SAM2 Cutout' : 'Red Marker'})</div>
                    <h2 style={{ fontSize: '24px', fontFamily: 'Playfair Display', marginBottom: '12px', color: 'var(--white)' }}>
                      {currentPage.metadata.editorial_headline || currentPage.metadata.object}
                    </h2>
                    <div style={{ fontSize: '14px', color: 'var(--gray-400)', fontStyle: 'italic', marginBottom: '16px' }}>{currentPage.metadata.style}</div>
                    
                    <p style={{ fontSize: '14px', color: 'var(--gray-200)', lineHeight: '1.6', marginBottom: '16px' }}>
                      {currentPage.metadata.explainer_paragraph}
                    </p>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                      <div style={{ fontSize: '10px', color: 'var(--gray-400)', fontWeight: '700', marginBottom: '4px' }}>MATERIALS</div>
                      <ul style={{ listStyle: 'none', fontSize: '13px' }}>
                        {currentPage.metadata.materials?.map(m => <li key={m} style={{ marginBottom: '2px' }}>• {m}</li>)}
                      </ul>
                    </div>
                    <div style={{ gridColumn: 'span 2' }}>
                      <div style={{ fontSize: '10px', color: 'var(--gray-400)', fontWeight: '700', marginBottom: '4px' }}>NEXT GENERATION TOPIC</div>
                      <div style={{ fontSize: '15px', color: 'var(--orange)', fontWeight: '700' }}>{currentPage.metadata.drill_topic}</div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'prompt' && (
                <div style={{ background: 'var(--navy)', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
                  <div style={{ fontSize: '10px', color: 'var(--gray-600)', marginBottom: '12px' }}>SYSTEM PROMPT FOR VISUAL GROUNDING</div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '13px', color: 'var(--gray-200)', lineHeight: '1.6', fontFamily: 'monospace' }}>
                    {currentPage.inputPrompt}
                  </pre>
                </div>
              )}

              {activeTab === 'raw' && (
                <div style={{ background: 'var(--navy)', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
                  <div style={{ fontSize: '10px', color: 'var(--gray-600)', marginBottom: '12px' }}>STRUCTURED JSON RESPONSE STORED IN CACHE</div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '13px', color: '#4ADE80', lineHeight: '1.6', fontFamily: 'monospace' }}>
                    {currentPage.rawJson}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {pages.length > 0 && (
        <div className="thumb-strip">
          {pages.map((page, idx) => (
            <div 
              key={page.id} 
              className={`thumb-item ${idx === currentIndex ? 'active' : ''}`}
              onClick={() => setCurrentIndex(idx)}
            >
              <img src={page.imageUrl} alt={`Page ${idx + 1}`} />
              <div style={{ position: 'absolute', bottom: 2, right: 4, background: 'rgba(0,0,0,0.5)', padding: '0 4px', borderRadius: '2px' }}>
                {idx + 1}
              </div>
            </div>
          ))}
          <div 
            className="thumb-item" 
            style={{ color: 'var(--orange)', fontSize: '20px' }}
            onClick={() => {
              setPages([]);
              setCurrentIndex(-1);
              setTopic('');
            }}
          >
            &times;
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

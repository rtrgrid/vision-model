import React, { useState, useRef, useEffect } from 'react';
import { getPage, uploadImage, streamPage, analyzePage } from './api';
import './index.css';

function App() {
  const [topic, setTopic] = useState('');
  const [pages, setPages] = useState([]); // Array of {id, imageUrl, x, y}
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [isLoading, setIsLoading] = useState(false);
  const [analyzingId, setAnalyzingId] = useState(null);
  const [ripple, setRipple] = useState(null);
  const [visionModel, setVisionModel] = useState('qwen3.5');
  const [groundingMode, setGroundingMode] = useState('red_ring');
  const [compareMode, setCompareMode] = useState(false); // New state for side-by-side comparison
  const [activeTab, setActiveTab] = useState('detected');
  const [layoutMode, setLayoutMode] = useState('diagram');
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const updateDimensions = () => {
      if (canvasRef.current) {
        setDimensions({
          width: canvasRef.current.clientWidth,
          height: canvasRef.current.clientHeight
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, [currentIndex, layoutMode, pages]);

  const handleInitialGenerate = async (e) => {
    e.preventDefault();
    if (!topic) return;
    
    setIsLoading(true);
    try {
      const streamingPage = {
          id: 'streaming_temp_initial',
          isStreaming: true,
          streamStatus: 'Starting generation...',
          imageUrl: null, 
          metadata: {}, rawJson: '', inputPrompt: '', samConfidence: null
      };
      setPages([streamingPage]);
      setCurrentIndex(0);

      await streamPage({ query: topic, visionModel }, (eventType, eventData) => {
          setPages(prevPages => {
              const current = [...prevPages];
              const lastIdx = current.length - 1;
              const page = current[lastIdx];
              
              console.log('SSE EVENT:', eventType, eventData); console.log('SSE EVENT 2:', eventType, eventData); if (eventType === 'complete') {
                  let finalImageUrl = eventData.imageUrl;
                  if (finalImageUrl && finalImageUrl.startsWith('/static')) {
                      finalImageUrl = `http://localhost:8000${finalImageUrl}`;
                  }
                  current[lastIdx] = { ...eventData, imageUrl: finalImageUrl, isStreaming: false };
                  setIsLoading(false); 
                  
                  // Trigger auto-analysis on new generation
                  if (eventData.id) {
                    handleAutoAnalyze({ id: eventData.id });
                  }
              } else if (eventType === 'error') {
                  alert(eventData.message);
                  current[lastIdx] = { ...page, isStreaming: false, streamStatus: 'Error' };
                  setIsLoading(false);
              } else {
                  current[lastIdx] = { 
                      ...page, 
                      streamStatus: eventData.message 
                  };
              }
              return current;
          });
      });
    } catch (err) {
      console.error(err);
      alert("Error generating page");
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsLoading(true);
    try {
      const data = await uploadImage(file); console.log("UPLOAD DATA:", data);
      setPages([data]);
      setCurrentIndex(0);
      setLayoutMode("diagram"); // Switch to diagram for analysis
      
      if (data.id) {
        handleAutoAnalyze(data);
      }
    } catch (err) {
      console.error(err);
      alert("Error uploading image");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAutoAnalyze = async (specificPage = null) => {
    const targetPage = specificPage || pages[currentIndex];
    if (!targetPage || !targetPage.id || targetPage.isStreaming) return;
    
    // Safety: ignore virtual comparison IDs or temp IDs
    if (targetPage.id.startsWith('streaming_') || targetPage.id.startsWith('compare_')) return;
    if (analyzingId === targetPage.id) return; // Already analyzing this one
    
    setAnalyzingId(targetPage.id);
    
    try {
      const analysis = await analyzePage(targetPage.id, visionModel);
      setPages(prev => {
        return prev.map(p => {
          if (p.id === targetPage.id) {
            return {
              ...p,
              metadata: { ...p.metadata, ...analysis }
            };
          }
          return p;
        });
      });
      setLayoutMode('diagram');
    } catch (err) {
      console.error("Auto-analysis error:", err);
    } finally {
      setAnalyzingId(null);
    }
  };

  const getColumnData = (details, detailIndex) => {
    const currentDetail = details[detailIndex];
    const isLeft = currentDetail.point[0] < 0.5;
    
    const column = details
      .map((d, i) => ({ ...d, originalIndex: i }))
      .filter(d => (d.point[0] < 0.5) === isLeft)
      .sort((a, b) => {
        if (a.point[1] !== b.point[1]) return a.point[1] - b.point[1];
        return a.originalIndex - b.originalIndex;
      });
      
    const indexInCol = column.findIndex(d => d.originalIndex === detailIndex);
    return { isLeft, column, indexInCol };
  };

  const getDistributedY = (details, detailIndex) => {
    if (!details || details.length === 0) return 0.5;
    const { column, indexInCol } = getColumnData(details, detailIndex);
    
    if (indexInCol === -1) return details[detailIndex].point[1];

    const total = column.length;
    if (total === 1) return Math.max(0.1, Math.min(0.9, details[detailIndex].point[1]));

    const startY = 0.1;
    const endY = 0.9;
    return startY + (indexInCol * (endY - startY) / (total - 1));
  };

  const triggerDrillDown = async (x, y, customTopic = null) => {
    console.log(`DRILL DOWN INITIATED: x=${x}, y=${y}, custom=${customTopic}`);
    if (isLoading || currentIndex === -1 || pages[currentIndex]?.isStreaming) return;

    const parentPage = pages[currentIndex];
    setIsLoading(true);
    
    try {
      let newData;
      if (compareMode && visionModel !== 'all' && visionModel !== 'none') {
        const noVisionResult = await getPage({ parentId: parentPage.id, x, y, visionModel: 'none', groundingMode });
        
        newData = {
          id: `compare_${noVisionResult.id}_partial`,
          isSideBySide: true,
          visionLoading: true,
          visionData: null,
          noVisionData: noVisionResult
        };
        
        const partialPages = [...pages.slice(0, currentIndex + 1)];
        partialPages[currentIndex] = { ...partialPages[currentIndex], lastClick: { x, y } };
        const updatedPartialPages = [...partialPages, newData];
        setPages(updatedPartialPages);
        setCurrentIndex(updatedPartialPages.length - 1);

        const visionResult = await getPage({ parentId: parentPage.id, x, y, visionModel, groundingMode });
        
        const finalData = {
          id: `compare_${visionResult.id}_complete`,
          isSideBySide: true,
          visionLoading: false,
          visionData: visionResult,
          noVisionData: noVisionResult
        };

        setPages((prevPages) => {
            const newFinalPages = [...prevPages];
            newFinalPages[newFinalPages.length - 1] = finalData;
            return newFinalPages;
        });

      } else {
        const updatedPages = [...pages.slice(0, currentIndex + 1)];
        updatedPages[currentIndex] = { ...updatedPages[currentIndex], lastClick: { x, y } };
        
        const streamingPage = {
          id: 'streaming_temp',
          isStreaming: true,
          streamStatus: 'Starting analysis...',
          imageUrl: parentPage.imageUrl, 
          metadata: {}, rawJson: '', inputPrompt: '', samConfidence: null
        };
        
        const newPages = [...updatedPages, streamingPage];
        setPages(newPages);
        setCurrentIndex(newPages.length - 1);
        
        await streamPage({
            parentId: parentPage.id,
            x,
            y,
            customTopic,
            visionModel,
            groundingMode
        }, (eventType, eventData) => {
            setPages(prevPages => {
                const current = [...prevPages];
                const lastIdx = current.length - 1;
                const page = current[lastIdx];
                
                if (eventType === 'complete') {
                    let finalImageUrl = eventData.imageUrl;
                    if (finalImageUrl && finalImageUrl.startsWith('/static')) {
                        finalImageUrl = `http://localhost:8000${finalImageUrl}`;
                    }
                    current[lastIdx] = { ...eventData, imageUrl: finalImageUrl, isStreaming: false };
                    if (eventData.id) {
                      handleAutoAnalyze({ id: eventData.id });
                    }
                } else if (eventType === 'generating') {
                    current[lastIdx] = { 
                        ...page, 
                        streamStatus: eventData.message, 
                        metadata: eventData.metadata || page.metadata,
                        samConfidence: eventData.samConfidence || page.samConfidence,
                        rawJson: eventData.rawJson || page.rawJson,
                        inputPrompt: eventData.inputPrompt || page.inputPrompt
                    };
                } else if (eventType === 'error') {
                    alert(eventData.message);
                    current[lastIdx] = { ...page, isStreaming: false, streamStatus: 'Error' };
                } else {
                    current[lastIdx] = { 
                        ...page, 
                        streamStatus: eventData.message, 
                        samConfidence: eventData.samConfidence || page.samConfidence 
                    };
                }
                return current;
            });
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCanvasClick = async (e) => {
    if (isLoading || currentIndex === -1 || pages[currentIndex]?.isStreaming) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    
    // Immediate visual feedback
    setRipple({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setTimeout(() => setRipple(null), 600);
    
    triggerDrillDown(x, y);
  };

  const handleLabelClick = (e, detail) => {
    e.stopPropagation(); // PREVENT CANVAS CLICK FROM FIRING
    if (detail.point && detail.point.length === 2) {
      const [x, y] = detail.point;
      
      // Immediate visual feedback at the point the label is describing
      const rect = canvasRef.current.getBoundingClientRect();
      setRipple({ x: x * rect.width, y: y * rect.height });
      setTimeout(() => setRipple(null), 600);
      
      triggerDrillDown(x, y, detail.label);
    }
  };

  const currentPage = pages[currentIndex];

  const renderMetadataPanel = (data) => (
    <div style={{ marginTop: '20px', width: '100%', background: 'rgba(20,34,96,0.3)', borderRadius: '12px', border: '1px solid rgba(237,106,44,0.2)', overflow: 'hidden' }}>
      <div style={{ padding: '24px' }}>
        <div style={{ fontSize: '10px', color: 'var(--orange)', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '8px' }}>
          Forensic Analysis ({data.groundingMode === 'sam2' ? 'SAM2 Cutout' : 'Red Marker'})
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '32px' }}>
          <div>
            <h2 style={{ fontSize: '28px', fontFamily: 'Playfair Display', marginBottom: '8px', color: 'var(--white)' }}>
              {data.metadata?.editorial_headline || data.metadata?.object || "Undefined Component"}
            </h2>
            <div style={{ fontSize: '14px', color: 'var(--orange)', fontWeight: '600', marginBottom: '16px' }}>{data.metadata?.object} • {data.metadata?.style}</div>
            
            <p style={{ fontSize: '15px', color: 'var(--gray-200)', lineHeight: '1.6', marginBottom: '20px', borderLeft: '3px solid var(--orange)', paddingLeft: '16px' }}>
              {data.metadata?.explainer_paragraph}
            </p>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '10px', color: 'var(--gray-400)', fontWeight: '700', marginBottom: '8px', textTransform: 'uppercase' }}>Spatial Position</div>
              <div style={{ fontSize: '13px', color: 'var(--white)', opacity: 0.8 }}>{data.metadata?.spatial_context || "N/A"}</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <div style={{ fontSize: '10px', color: 'var(--gray-400)', fontWeight: '700', marginBottom: '8px', textTransform: 'uppercase' }}>Materials & Colors</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {data.metadata?.materials?.map(m => (
                  <span key={m} style={{ padding: '4px 10px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', fontSize: '12px', color: 'var(--gray-200)', border: '1px solid rgba(255,255,255,0.1)' }}>{m}</span>
                ))}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '10px', color: 'var(--gray-400)', fontWeight: '700', marginBottom: '8px', textTransform: 'uppercase' }}>Granular Observations</div>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {data.metadata?.granular_details?.map(detail => (
                  <li key={detail.label || detail} style={{ fontSize: '13px', color: 'var(--gray-300)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '4px', height: '4px', background: 'var(--orange)', borderRadius: '50%' }}></span>
                    {typeof detail === 'string' ? detail : detail.label}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ fontSize: '10px', color: 'var(--gray-400)', fontWeight: '700', marginBottom: '4px' }}>NEXT GENERATION TOPIC</div>
          <div style={{ fontSize: '14px', color: 'var(--orange)', fontWeight: '700', fontStyle: 'italic' }}>
            {data.context || data.metadata?.drill_topic || "Direct Visual Zoom"}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="app-container">
      <nav className="mag-nav">
        <div className="mag-logo">DRILL<span>DOWN</span></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          
          
          <select 
            value={layoutMode} 
            onChange={(e) => setLayoutMode(e.target.value)}
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
            <option value='diagram'>Layout: Technical Diagram</option>
            <option value='standard'>Layout: Standard (Bottom Tabs)</option>
          </select>
          
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--white)', fontSize: '12px', cursor: 'pointer' }}>
            <input 
              type="checkbox" 
              checked={compareMode}
              onChange={(e) => setCompareMode(e.target.checked)}
              disabled={visionModel === 'all' || visionModel === 'none'}
            />
            Compare: Vision vs. No-Vision
          </label>

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
            <option value="qwen3.5">Vision: Qwen 3.5 VL (9B - New)</option>
            <option value="gemini">Vision: Gemini 2.5 Pro (Best)</option>
            <option value="none">Skip Vision (Direct Zoom)</option>
            <option value="llava_nv">Vision: NVIDIA Llava v1.6</option>
            <option value="kosmos_nv">Vision: NVIDIA Kosmos-2</option>
            <option value="qwen">Vision: Qwen2-VL (Grounding)</option>
            <option value="internvl">Vision: InternVL-2 (SOTA)</option>
            <option value="pixtral">Vision: Pixtral (Mistral)</option>
            <option value="llava_next">Vision: LLaVA-NeXT (8B)</option>
            <option value="minicpm">Vision: MiniCPM-V (Efficient)</option>
            <option value="moondream">Vision: Moondream2 (Fast)</option>
            <option value="llava">Vision: Llava 1.5</option>
            <option value="phi4">Vision: Phi-4 Multimodal</option>
            <option value="llama_vision">Vision: Llama 3.2 (11B)</option>
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
            <button
              onClick={() => handleAutoAnalyze()}
              disabled={!!analyzingId || pages[currentIndex]?.isStreaming}
              style={{
                background: analyzingId === pages[currentIndex]?.id ? 'var(--gray-600)' : 'var(--orange)',
                color: 'var(--navy)',
                border: 'none',
                padding: '6px 16px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: '700',
                cursor: analyzingId ? 'wait' : 'pointer',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {analyzingId === pages[currentIndex]?.id ? (
                <>
                  <div className="spinner" style={{ width: '12px', height: '12px', borderWidth: '2px', borderTopColor: 'transparent' }}></div>
                  Analyzing...
                </>
              ) : 'Auto-Analyze Scene'}
            </button>
          )}

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
              <button type="submit" disabled={isLoading}>{isLoading ? "Loading..." : "Generate"}</button>
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
                {isLoading ? "Uploading..." : "Upload Image"}
              </button>
            </div>
          </div>
        ) : (
          <div style={{ width: '100%', maxWidth: '1400px', margin: '0 auto' }}>
            {currentPage?.isSideBySide ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', width: '100%' }}>
                
                {/* No Vision Results (Always renders first now) */}
                <div>
                  <h3 style={{ color: 'var(--gray-400)', textAlign: 'center', marginBottom: '16px', fontFamily: 'Playfair Display', fontSize: '24px' }}>Without Vision (Blind Zoom)</h3>
                  <div className="canvas-wrapper" style={{ margin: 0, height: '400px' }}>
                    <img src={currentPage.noVisionData.imageUrl} className="canvas-image" alt="Blind generated" />
                  </div>
                  {renderMetadataPanel(currentPage.noVisionData)}
                </div>

                {/* Vision Results (Might be loading) */}
                <div>
                  <h3 style={{ color: 'var(--orange)', textAlign: 'center', marginBottom: '16px', fontFamily: 'Playfair Display', fontSize: '24px' }}>With {visionModel.toUpperCase()} Vision</h3>
                  
                  {currentPage.visionLoading ? (
                    <div style={{ height: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(20,34,96,0.2)', borderRadius: '12px', border: '1px solid rgba(237,106,44,0.2)' }}>
                      <div className="spinner" style={{ marginBottom: '16px' }}></div>
                      <p style={{ color: 'var(--orange)', fontWeight: 'bold' }}>Now analyzing with Vision AI...</p>
                    </div>
                  ) : (
                    <>
                      <div className="canvas-wrapper" style={{ margin: 0, height: '400px' }}>
                        <img src={currentPage.visionData.imageUrl} className="canvas-image" alt="Vision generated" />
                      </div>
                      {renderMetadataPanel(currentPage.visionData)}
                    </>
                  )}
                </div>

              </div>
            ) : layoutMode === 'diagram' ? (

              <div style={{ display: 'flex', justifyContent: 'center', width: '100%', padding: '0 260px' }}>
                <div className="canvas-wrapper" style={{ margin: 0, position: 'relative', width: '100%', maxWidth: '700px' }} ref={canvasRef} onClick={handleCanvasClick}>
                  {currentPage.imageUrl ? <img src={currentPage.imageUrl} className="canvas-image" alt="Drill down visualization" style={{ display: 'block', width: '100%', aspectRatio: '16/9', borderRadius: '12px', zIndex: 1, position: 'relative', opacity: currentPage.isStreaming ? 0.6 : 1 }} /> : <div style={{ width: "100%", aspectRatio: "16/9", background: "transparent" }} />}
                  
                  {/* SVG Layer for Arrows - Hide during analysis */}
                  {currentPage && !currentPage.isStreaming && analyzingId !== currentPage.id && Array.isArray(currentPage.metadata?.granular_details) && currentPage.metadata.granular_details.length > 0 && (
                    <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 10, overflow: 'visible' }}>
                      <defs>
                        <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto">
                          <polygon points="0 0, 8 4, 0 8" fill="var(--orange)" />
                        </marker>
                      </defs>
                      {currentPage.metadata.granular_details.map((detail, idx) => {
                        if (!detail.point || detail.point.length !== 2) return null;
                        const { isLeft, indexInCol } = getColumnData(currentPage.metadata.granular_details, idx);
                        const labelY = getDistributedY(currentPage.metadata.granular_details, idx);
                        const [x, y] = detail.point;
                        
                        // Use consistent staggering levels
                        const staggerX = [12, 60, 110][indexInCol % 3];

                        return (
                          <g key={idx} className="svg-reveal">
                            <circle cx={x * dimensions.width} cy={y * dimensions.height} r="5" fill="var(--orange)" />
                            <circle cx={x * dimensions.width} cy={y * dimensions.height} r="12" fill="none" stroke="var(--orange)" strokeWidth="1" opacity="0.5">
                              <animate attributeName="r" from="5" to="16" dur="1.5s" repeatCount="indefinite" />
                              <animate attributeName="opacity" from="0.8" to="0" dur="1.5s" repeatCount="indefinite" />
                            </circle>
                            
                            <line 
                              className="technical-line"
                              x1={isLeft ? -staggerX : dimensions.width + staggerX}
                              y1={labelY * dimensions.height}
                              x2={x * dimensions.width}
                              y2={y * dimensions.height}
                              style={{ 
                                transition: 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)'
                              }}
                              fill="none"
                              stroke="var(--orange)"
                              strokeWidth="2"
                              opacity="0.9"
                              markerEnd="url(#arrowhead)"
                              strokeDasharray="4 4"
                            />
                          </g>
                        );
                      })}
                    </svg>
                  )}

                  {/* Floating Labels Outside Image - Hide during analysis */}
                  {currentPage && !currentPage.isStreaming && analyzingId !== currentPage.id && Array.isArray(currentPage.metadata?.granular_details) && currentPage.metadata.granular_details.length > 0 && (
                    <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 11 }}>
                      {currentPage.metadata.granular_details.map((detail, idx) => {
                        if (!detail.point || detail.point.length !== 2) return null;
                        const { isLeft, indexInCol } = getColumnData(currentPage.metadata.granular_details, idx);
                        const labelY = getDistributedY(currentPage.metadata.granular_details, idx);
                        
                        // Use same consistent levels as SVG
                        const staggerX = [12, 60, 110][indexInCol % 3];

                        return (
                          <div key={idx} 
                            className="label-card" 
                            onClick={(e) => handleLabelClick(e, detail)}
                            style={{ 
                              position: 'absolute', 
                              left: isLeft ? 'auto' : `calc(100% + ${staggerX}px)`, 
                              right: isLeft ? `calc(100% + ${staggerX}px)` : 'auto',
                              top: `${labelY * 100}%`, 
                              transform: `translateY(-50%)`,
                              background: 'rgba(10, 22, 40, 0.95)',
                              border: '1px solid rgba(237,106,44,0.6)',
                              padding: '8px 12px',
                              borderRadius: '6px',
                              width: '200px',
                              maxHeight: '100px',
                              overflow: 'hidden',
                              backdropFilter: 'blur(10px)',
                              boxShadow: '0 8px 24px rgba(0,0,0,0.8)',
                              pointerEvents: 'auto',
                              display: 'flex',
                              flexDirection: 'column',
                              cursor: 'pointer'
                          }}>
                             <div style={{ fontSize: '10px', color: 'var(--orange)', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '2px', lineHeight: '1.2' }}>{detail.label}</div>
                             <div style={{ fontSize: '11px', color: 'var(--gray-100)', lineHeight: '1.3', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden', textOverflow: 'ellipsis' }}>{detail.description}</div>
                             
                             {/* Connector Node */}
                             <div className="connector-node" style={{ 
                               left: isLeft ? 'auto' : '-3px', 
                               right: isLeft ? '-3px' : 'auto' 
                             }} />
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Existing Overlays */}
                  {analyzingId === currentPage?.id && (
                    <>
                      <div className="scan-overlay" />
                      <div className="scan-line" />
                    </>
                  )}
                  {currentPage?.isStreaming && currentPage?.lastClick && (
                    <>
                      <div className="target-pulse" style={{ left: `${currentPage.lastClick.x * 100}%`, top: `${currentPage.lastClick.y * 100}%`, zIndex: 18 }} />
                      <div className="target-crosshair" style={{ left: `${currentPage.lastClick.x * 100}%`, top: `${currentPage.lastClick.y * 100}%`, zIndex: 19 }} />
                    </>
                  )}
                  {currentPage?.lastClick && !currentPage?.isStreaming && (
                    <div className="red-ring" style={{ left: `${currentPage.lastClick.x * 100}%`, top: `${currentPage.lastClick.y * 100}%`, zIndex: 2 }} />
                  )}
                  {ripple && <div className="ripple" style={{ left: ripple.x, top: ripple.y, zIndex: 3 }} />}
                  {currentPage?.isStreaming && (
                    <div className="loading-overlay" style={{ background: 'rgba(10, 22, 40, 0.5)', zIndex: 25 }}>
                      <div className="spinner"></div>
                      <p style={{ color: 'var(--orange)', fontWeight: 'bold', marginTop: '16px' }}>{currentPage.streamStatus}</p>
                    </div>
                  )}
                  {isLoading && !currentPage?.isStreaming && (
                    <div className="loading-overlay" style={{ zIndex: 0 }}>
                      <div className="spinner"></div><p>Generating Layer...</p>
                    </div>
                  )}
                </div>
              </div>
            ) : layoutMode === 'standard' ? (
              <div style={{ width: '100%', maxWidth: '1000px', margin: '0 auto' }}>
                <div className="canvas-wrapper" ref={canvasRef} onClick={handleCanvasClick}>
                  {currentPage.imageUrl ? <img src={currentPage.imageUrl} className="canvas-image" alt="Drill down visualization" /> : <div style={{ width: "100%", aspectRatio: "16/9", background: "transparent" }} /> }
                  {currentPage?.lastClick && <div className="red-ring" style={{ left: `${currentPage.lastClick.x * 100}%`, top: `${currentPage.lastClick.y * 100}%` }} />}
                  {ripple && <div className="ripple" style={{ left: ripple.x, top: ripple.y }} />}
                  {currentPage?.isStreaming && (
                    <div className="loading-overlay" style={{ background: 'rgba(10, 22, 40, 0.7)' }}>
                      <div className="spinner"></div>
                      <p style={{ color: 'var(--orange)', fontWeight: 'bold', marginTop: '16px' }}>{currentPage.streamStatus}</p>
                      {currentPage.samConfidence && <div style={{ fontSize: '12px', marginTop: '8px', color: 'var(--gray-300)' }}>Grounding Confidence: {(currentPage.samConfidence * 100).toFixed(1)}%</div>}
                    </div>
                  )}
                  {isLoading && !currentPage?.isStreaming && (
                    <div className="loading-overlay">
                      <div className="spinner"></div><p>Generating Layer...</p>
                    </div>
                  )}
                </div>

                {!currentPage?.isSideBySide && !currentPage?.isComparison && currentPage?.metadata && Object.keys(currentPage.metadata).length > 0 && (
                  <div style={{ margin: '20px auto 0', width: '100%', background: 'rgba(20,34,96,0.3)', borderRadius: '12px', border: '1px solid rgba(237,106,44,0.2)', overflow: 'hidden' }}>
                    <div style={{ display: 'flex', background: 'rgba(10,22,40,0.5)', borderBottom: '1px solid rgba(237,106,44,0.2)' }}>
                      {['detected', 'prompt', 'raw'].map(tab => (
                        <button key={tab} onClick={() => setActiveTab(tab)} style={{ padding: '12px 24px', background: activeTab === tab ? 'rgba(237,106,44,0.1)' : 'transparent', color: activeTab === tab ? 'var(--orange)' : 'var(--gray-400)', border: 'none', borderBottom: activeTab === tab ? '2px solid var(--orange)' : '2px solid transparent', cursor: 'pointer', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '1px' }}>
                          {tab === 'detected' ? 'Detected Context' : 'Raw JSON Output'}
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
                            <p style={{ fontSize: '14px', color: 'var(--gray-200)', lineHeight: '1.6', marginBottom: '16px' }}>{currentPage.metadata.explainer_paragraph}</p>
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
                      {activeTab === 'raw' && (
                        <div style={{ background: 'var(--navy)', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
                          <div style={{ fontSize: '10px', color: 'var(--gray-600)', marginBottom: '12px' }}>STRUCTURED JSON RESPONSE</div>
                          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '13px', color: '#4ADE80', lineHeight: '1.6', fontFamily: 'monospace' }}>{currentPage.rawJson}</pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        )}
      </main>

      {pages.length > 0 && (
        <div className="thumb-strip">
          {pages.map((page, idx) => (
            <div 
              key={page.id || idx} 
              className={`thumb-item ${idx === currentIndex ? 'active' : ''}`}
              onClick={() => setCurrentIndex(idx)}
            >
              {/* Safely handle partial loading state where visionData might be null */}
              <img 
                src={page.isSideBySide ? (page.visionData?.imageUrl || page.noVisionData?.imageUrl) : page.imageUrl} 
                alt={`Page ${idx + 1}`} 
              />
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

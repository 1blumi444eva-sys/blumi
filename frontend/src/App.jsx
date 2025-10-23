import React, { useEffect, useRef, useState } from "react";

// Consider several common local hostnames so the dev frontend (served from
// either "localhost" or "127.0.0.1") correctly points at the local backend.
const isLocalHost = (() => {
  const h = window.location.hostname;
  return (
    h === "localhost" ||
    h === "127.0.0.1" ||
    h === "::1" ||
    // allow machines using .local hostnames (e.g. my-machine.local)
    h.endsWith(".local")
  );
})();

const DEFAULT_BACKEND = isLocalHost ? "http://127.0.0.1:8000" : "https://your-render-service.onrender.com";

export default function App() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_BACKEND);
  const [voices, setVoices] = useState([]);
  const [fontsShort, setFontsShort] = useState([]);
  const [selectedFont, setSelectedFont] = useState("Orbitron");
  const [showFontsModal, setShowFontsModal] = useState(false);
  const [allFonts, setAllFonts] = useState([]);
  const [customFontName, setCustomFontName] = useState("");
  const [installStatus, setInstallStatus] = useState("");
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [captionPlacement, setCaptionPlacement] = useState("auto");
  const [captionHue, setCaptionHue] = useState(200);
  const [captionFontSize, setCaptionFontSize] = useState(48);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [previewUrl, setPreviewUrl] = useState(null);
  const rafRef = useRef(null);
  const canvasRef = useRef(null);

  // Interactive visual controls
  const [starCount, setStarCount] = useState(80);
  const [animSpeed, setAnimSpeed] = useState(1.0);
  const [glow, setGlow] = useState(0.6);
  const [showButterfly, setShowButterfly] = useState(true);
  const [showTrail, setShowTrail] = useState(true);

  useEffect(() => {
    setApiUrl(DEFAULT_BACKEND);
    initBackground();
    // fetch available voices from backend
    (async () => {
      try {
        const r = await fetch(`${DEFAULT_BACKEND}/voices`);
        if (r.ok) {
          const j = await r.json();
          if (j.ok && Array.isArray(j.voices)) setVoices(j.voices);
        }
        // fetch short font list
        try {
          const fr = await fetch(`${DEFAULT_BACKEND}/fonts`);
          if (fr.ok) {
            const fj = await fr.json();
            if (fj.ok && Array.isArray(fj.fonts)) setFontsShort(fj.fonts);
          }
        } catch (e) {
          // ignore
        }
      } catch (e) {
        // ignore
      }
    })();
    return () => {
      cancelAnimationFrame(rafRef.current);
      const canvas = canvasRef.current || document.getElementById("bg-canvas");
      if (canvas) {
        window.removeEventListener("resize", canvas._resizeHandler);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-init background when visual settings change
  useEffect(() => {
    // set css variable for glow used by CSS
    document.documentElement.style.setProperty("--blumi-glow", String(glow));
    initBackground();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [starCount, animSpeed, glow]);

  // load full font list when modal opens
  useEffect(()=>{
    if (!showFontsModal) return;
    (async ()=>{
      try{
        const r = await fetch(`${apiUrl}/fonts/all`);
        if (r.ok){
          const j = await r.json();
          if (j.ok && Array.isArray(j.fonts)) setAllFonts(j.fonts);
        }
      }catch(e){
        setAllFonts([]);
      }
    })();
  }, [showFontsModal, apiUrl]);

  function initBackground() {
    const canvas = canvasRef.current || document.getElementById("bg-canvas");
    if (!canvas) return;
    canvasRef.current = canvas;
    const ctx = canvas.getContext("2d");

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    // keep reference to handler for cleanup
    const _resizeHandler = resize;
    canvas._resizeHandler = _resizeHandler;
    window.addEventListener("resize", _resizeHandler);

    // build stars based on starCount
    const stars = Array.from({ length: Math.max(10, Math.min(400, starCount)) }).map(() => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.8 + 0.2,
      v: (Math.random() * 0.8 + 0.02) * animSpeed,
      tw: Math.random() * Math.PI * 2,
    }));

    function step() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // soft neon gradient background
      const g = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
      g.addColorStop(0, "#04021a");
      g.addColorStop(0.35, "rgba(8,6,28,0.6)");
      g.addColorStop(0.7, "rgba(10,20,50,0.45)");
      g.addColorStop(1, "#071029");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // subtle floating nebula blobs
      for (let i = 0; i < 3; i++) {
        const cx = (i / 3) * canvas.width + (Math.sin(Date.now() / (7000 + i * 3000)) * 120);
        const cy = canvas.height * 0.15 + Math.cos(Date.now() / (9000 + i * 2000)) * 40;
        const rad = canvas.width * 0.18;
        const blob = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
        blob.addColorStop(0, `rgba(6,180,255,${0.02 * (i + 1)})`);
        blob.addColorStop(1, 'rgba(6,180,255,0)');
        ctx.fillStyle = blob;
        ctx.beginPath();
        ctx.ellipse(cx, cy, rad, rad * 0.6, 0, 0, Math.PI * 2);
        ctx.fill();
      }

      // stars
      for (const s of stars) {
        s.tw += 0.01 * animSpeed;
        s.x += Math.cos(s.tw + s.y * 0.0005) * s.v * 0.6;
        s.y += s.v * 0.5;
        if (s.y > canvas.height + 20) s.y = -10;
        ctx.beginPath();
        // star glow using shadowBlur for neon pop
        ctx.save();
        ctx.shadowBlur = 6 + 18 * glow;
        ctx.shadowColor = `rgba(0,200,255,${0.6 * glow})`;
        ctx.fillStyle = `rgba(255,255,255,${0.9 - Math.min(0.7, glow)})`;
        ctx.arc(s.x, s.y, s.r + glow * 1.8, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      rafRef.current = requestAnimationFrame(step);
    }

    // cancel previous frame if present
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    step();
  }

  async function generateVideo() {
    setMessage("Queuing job...");
    try {
      const url = `${apiUrl}/run`;
      const payload = {
        topic: "futuristic galaxy",
        style: "post",
        theme: "galaxy",
        font: selectedFont || "Arial",
        voice_id: selectedVoice || null,
        save_preview: true,
        caption: {
          placement: captionPlacement,
          hue: captionHue,
          font: selectedFont,
          font_size: captionFontSize,
        },
      };
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Request failed ${res.status} ${res.statusText}`);
      const data = await res.json();
      setJobId(data.job_id);
      setMessage("Job queued: " + data.job_id);
      pollStatus(data.job_id);
    } catch (e) {
      setMessage("Error creating job: " + (e.message || e) + ` (url: ${apiUrl}/run)`);
    }
  }

  async function pollStatus(id) {
    setMessage("Polling status...");
    const interval = setInterval(async () => {
      try {
        const url = `${apiUrl}/status/${id}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`status error ${res.status} ${res.statusText}`);
        const j = await res.json();
        setJobStatus(j);
        setProgress(j.progress ?? 0);
        setMessage(j.message ?? "");
        if (j.status === "done") {
          clearInterval(interval);
          setPreviewUrl(`${apiUrl}/download/${id}`);
          setMessage("Done — preview ready");
        }
        if (j.status === "failed") {
          clearInterval(interval);
          setMessage("Run failed: " + (j.message || "unknown"));
        }
      } catch (e) {
        clearInterval(interval);
        setMessage("Failed to poll status: " + (e.message || e) + ` (url: ${apiUrl}/status/${id})`);
      }
    }, 2000);
  }

  async function previewResult() {
    if (!jobId) return setMessage("No job to preview");
    setMessage("Preparing preview...");
    setPreviewUrl(`${apiUrl}/download/${jobId}`);
  }

  async function postToTiktok() {
    if (!jobId) return setMessage("No job to post");
    setMessage("Posting to TikTok (simulated)...");
    try {
      const url = `${apiUrl}/upload_tiktok`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, video_url: `${apiUrl}/download/${jobId}` }),
      });
      if (!res.ok) throw new Error(`upload failed ${res.status} ${res.statusText}`);
      const data = await res.json();
      setMessage("TikTok response: " + (data.message || JSON.stringify(data)));
    } catch (e) {
      setMessage("TikTok post failed: " + (e.message || e) + ` (url: ${apiUrl}/upload_tiktok)`);
    }
  }

  return (
    <div className="app-root">
      <canvas id="bg-canvas" aria-hidden="true"></canvas>

      <header className="app-header neon-header">
        <div className="header-left">
          <div className="logo-badge">🦋</div>
          <div>
            <h1 className="title">Blumi Creator Hub</h1>
            <p className="subtitle">Future Creator CEO dashboard</p>
          </div>
        </div>

        <div className="header-controls">
          <div className="status-dot" title="Backend status" />
          <small className="api-url">{apiUrl}</small>
        </div>
      </header>

      {/* Animated butterfly + trail */}
      {showTrail && <div className="trail" aria-hidden="true" />}
      {showButterfly && (
        <div className="butterfly" aria-hidden="true">
          <svg viewBox="0 0 100 100" className="butterfly-svg">
            <path d="M50 50 C20 10, 0 30, 10 50 C0 70, 20 90, 50 50 Z" />
            <path d="M50 50 C80 10, 100 30, 90 50 C100 70, 80 90, 50 50 Z" />
          </svg>
        </div>
      )}

      <main className="hub">
        <div className="modules">
          <button className="module generate" onClick={generateVideo}>
            Generate Video
          </button>
          <button className="module preview" onClick={previewResult}>
            Preview Result
          </button>
          <button className="module tiktok" onClick={postToTiktok}>
            Post to TikTok
          </button>

          <div className="visual-controls card">
            <h4>Visuals</h4>
            <label>Stars: {starCount}</label>
            <input type="range" min="20" max="300" value={starCount} onChange={(e) => setStarCount(Number(e.target.value))} />
            <label>Speed: {animSpeed.toFixed(2)}</label>
            <input type="range" min="0.2" max="3" step="0.05" value={animSpeed} onChange={(e) => setAnimSpeed(Number(e.target.value))} />
            <label>Glow: {glow.toFixed(2)}</label>
            <input type="range" min="0" max="1" step="0.01" value={glow} onChange={(e) => setGlow(Number(e.target.value))} />
            <hr />
            <h4>Captions & Voice</h4>
            <label>Voice</label>
            <select value={selectedVoice || ""} onChange={(e) => setSelectedVoice(e.target.value || null)}>
              <option value="">(default)</option>
              {voices.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>

            <label>Caption placement</label>
            <select value={captionPlacement} onChange={(e) => setCaptionPlacement(e.target.value)}>
              <option value="auto">Smart</option>
              <option value="bottom">Bottom-center</option>
              <option value="grid-0">Top-left</option>
              <option value="grid-1">Top-center</option>
              <option value="grid-2">Top-right</option>
              <option value="grid-3">Mid-left</option>
              <option value="grid-4">Center</option>
              <option value="grid-5">Mid-right</option>
              <option value="grid-6">Bottom-left</option>
              <option value="grid-7">Bottom-center</option>
              <option value="grid-8">Bottom-right</option>
            </select>

            <label>Caption font</label>
            <div style={{display: 'flex', gap: '8px', alignItems: 'center'}}>
              <select value={selectedFont} onChange={(e) => setSelectedFont(e.target.value)}>
                {fontsShort.length ? (
                  fontsShort.map((f) => <option key={f} value={f}>{f}</option>)
                ) : (
                  // fallback
                  ["Orbitron","Montserrat","Poppins","Roboto","Inter","Lato","Open Sans","Oswald"].map((f) => <option key={f} value={f}>{f}</option>)
                )}
              </select>
              <button onClick={() => setShowFontsModal(true)} className="small">See all</button>
            </div>

            <label>Caption hue: {captionHue}</label>
            <input type="range" min="0" max="360" value={captionHue} onChange={(e) => setCaptionHue(Number(e.target.value))} />
            <label>Caption font size: {captionFontSize}px</label>
            <input type="range" min="12" max="96" value={captionFontSize} onChange={(e) => setCaptionFontSize(Number(e.target.value))} />
            <div className="toggles">
              <label><input type="checkbox" checked={showButterfly} onChange={(e) => setShowButterfly(e.target.checked)} /> Butterfly</label>
              <label><input type="checkbox" checked={showTrail} onChange={(e) => setShowTrail(e.target.checked)} /> Trail</label>
            </div>
          </div>
        </div>

        <section className="status-panel">
          <div className="status-row">
            <div className="status-card">
              <div className="label">Job</div>
              <div className="value">{jobId ?? "—"}</div>
            </div>
            <div className="status-card">
              <div className="label">Progress</div>
              <div className="value">{progress}%</div>
            </div>
            <div className="status-card">
              <div className="label">Message</div>
              <div className="value">{message}</div>
            </div>
          </div>

          {previewUrl && (
            <div className="preview">
              <video src={previewUrl} controls width={640} />
            </div>
          )}
        </section>
      </main>

      {/* Fonts modal */}
      {showFontsModal && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>Fonts</h3>
            <div style={{maxHeight: '40vh', overflow: 'auto'}}>
              {allFonts.length ? (
                allFonts.map((f) => (
                  <div key={f} style={{display:'flex', justifyContent:'space-between', alignItems:'center', padding: '6px 0'}}>
                    <div>{f}</div>
                    <button onClick={async ()=>{
                      setInstallStatus('Installing...');
                      try {
                        const r = await fetch(`${apiUrl}/fonts/install`, {method:'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: f})});
                        const j = await r.json();
                        if (j.ok) setInstallStatus(`Installed ${f}`);
                        else setInstallStatus(`Failed: ${j.message}`);
                      } catch (e) { setInstallStatus('Install failed'); }
                    }} className="small">Install</button>
                  </div>
                ))
              ) : (
                <div>Loading fonts...</div>
              )}
            </div>
            <hr />
            <div>
              <label>Install custom font</label>
              <div style={{display:'flex', gap:8}}>
                <input value={customFontName} onChange={(e)=>setCustomFontName(e.target.value)} placeholder="Font name (e.g. Merriweather)" />
                <button onClick={async ()=>{
                  if (!customFontName) return setInstallStatus('Enter a font name');
                  setInstallStatus('Installing...');
                  try {
                    const r = await fetch(`${apiUrl}/fonts/install`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name: customFontName})});
                    const j = await r.json();
                    if (j.ok) setInstallStatus(`Installed ${customFontName}`);
                    else setInstallStatus(`Failed: ${j.message}`);
                  } catch (e) { setInstallStatus('Install failed'); }
                }} className="small">Install</button>
              </div>
              <div style={{marginTop:8}}>{installStatus}</div>
            </div>
            <div style={{textAlign:'right', marginTop:12}}>
              <button onClick={()=>setShowFontsModal(false)} className="small">Close</button>
            </div>
          </div>
        </div>
      )}

      <footer className="footer">Connected to {apiUrl}</footer>
    </div>
  );
}

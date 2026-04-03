/**
 * ScamShield AI — Animated Particle Network Background
 * Professional live background with floating nodes and connecting lines
 */
(function () {
  'use strict';

  const canvas = document.createElement('canvas');
  canvas.id = 'bg-canvas';
  canvas.style.cssText = [
    'position:fixed', 'top:0', 'left:0', 'width:100%', 'height:100%',
    'z-index:0', 'pointer-events:none', 'opacity:1',
  ].join(';');
  document.body.insertBefore(canvas, document.body.firstChild);

  const ctx = canvas.getContext('2d');
  let W, H, nodes, animId;
  const NODE_COUNT = 55;
  const MAX_DIST   = 160;
  const SPEED      = 0.35;

  // Color palette — adapts to theme
  function palette() {
    const dark = document.documentElement.getAttribute('data-theme') !== 'light';
    return {
      bg:       dark ? '#0a0e1a' : '#f0f4ff',
      node:     dark ? 'rgba(59,130,246,0.55)'  : 'rgba(59,130,246,0.35)',
      nodePulse:dark ? 'rgba(99,102,241,0.7)'   : 'rgba(99,102,241,0.5)',
      line:     dark ? 'rgba(59,130,246,0.12)'  : 'rgba(59,130,246,0.1)',
      lineHot:  dark ? 'rgba(139,92,246,0.25)'  : 'rgba(139,92,246,0.18)',
      glow:     dark ? 'rgba(59,130,246,0.08)'  : 'rgba(59,130,246,0.05)',
    };
  }

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function createNodes() {
    nodes = Array.from({ length: NODE_COUNT }, (_, i) => ({
      x:    Math.random() * W,
      y:    Math.random() * H,
      vx:   (Math.random() - 0.5) * SPEED,
      vy:   (Math.random() - 0.5) * SPEED,
      r:    Math.random() * 2.5 + 1.2,
      pulse: Math.random() * Math.PI * 2,
      pulseSpeed: 0.02 + Math.random() * 0.02,
      // Special "scam alert" nodes — red/orange
      hot:  i < 6,
    }));
  }

  // Floating shield icons
  const ICONS = ['🛡️', '🔍', '⚠️', '🔒', '📱', '🌐'];
  const floaters = ICONS.map((icon, i) => ({
    icon,
    x: (i + 0.5) * (window.innerWidth / ICONS.length),
    y: Math.random() * window.innerHeight,
    vy: -0.18 - Math.random() * 0.12,
    opacity: 0.06 + Math.random() * 0.06,
    size: 18 + Math.random() * 14,
  }));

  function drawFrame() {
    const p = palette();
    ctx.clearRect(0, 0, W, H);

    // Background gradient
    const grad = ctx.createRadialGradient(W * 0.3, H * 0.2, 0, W * 0.5, H * 0.5, Math.max(W, H) * 0.8);
    grad.addColorStop(0, p.glow);
    grad.addColorStop(1, 'transparent');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Draw connections
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < MAX_DIST) {
          const alpha = 1 - dist / MAX_DIST;
          const isHot = nodes[i].hot || nodes[j].hot;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.strokeStyle = isHot ? p.lineHot : p.line;
          ctx.globalAlpha = alpha * (isHot ? 0.6 : 0.4);
          ctx.lineWidth = isHot ? 1.2 : 0.7;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }
    }

    // Draw nodes
    nodes.forEach(n => {
      n.pulse += n.pulseSpeed;
      const pulseR = n.r + Math.sin(n.pulse) * 0.8;

      // Outer glow
      const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, pulseR * 5);
      grd.addColorStop(0, n.hot ? 'rgba(239,68,68,0.15)' : 'rgba(59,130,246,0.12)');
      grd.addColorStop(1, 'transparent');
      ctx.beginPath();
      ctx.arc(n.x, n.y, pulseR * 5, 0, Math.PI * 2);
      ctx.fillStyle = grd;
      ctx.fill();

      // Core dot
      ctx.beginPath();
      ctx.arc(n.x, n.y, pulseR, 0, Math.PI * 2);
      ctx.fillStyle = n.hot ? 'rgba(239,68,68,0.7)' : p.node;
      ctx.fill();

      // Move
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < -20) n.x = W + 20;
      if (n.x > W + 20) n.x = -20;
      if (n.y < -20) n.y = H + 20;
      if (n.y > H + 20) n.y = -20;
    });

    // Floating icons
    ctx.font = '20px serif';
    floaters.forEach(f => {
      ctx.globalAlpha = f.opacity;
      ctx.font = `${f.size}px serif`;
      ctx.fillText(f.icon, f.x, f.y);
      f.y += f.vy;
      if (f.y < -40) f.y = H + 40;
      ctx.globalAlpha = 1;
    });

    animId = requestAnimationFrame(drawFrame);
  }

  function init() {
    resize();
    createNodes();
    if (animId) cancelAnimationFrame(animId);
    drawFrame();
  }

  window.addEventListener('resize', () => { resize(); createNodes(); });

  // Re-init on theme change
  const observer = new MutationObserver(init);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for external control
  window.ScamShieldBG = { pause: () => cancelAnimationFrame(animId), resume: drawFrame };
})();

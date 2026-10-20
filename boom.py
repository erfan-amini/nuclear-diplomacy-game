"""Full-screen explosion shown once when a nuclear terrorist attack hits a country.

Rendered with st.html(..., unsafe_allow_javascript=True). The script draws on a
canvas laid over the whole page, then removes itself. Viewers who ask their system
for reduced motion get a short static card instead.
"""

_JS = r"""
<div style="display:none" data-nd-boom="1"></div>
<script>
(function () {
  if (window.__ndBoomAt && performance.now() - window.__ndBoomAt < 4000) return;
  window.__ndBoomAt = performance.now();

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var wrap = document.createElement('div');
  wrap.id = 'nd-boom';
  wrap.style.cssText = 'position:fixed;inset:0;z-index:2147483000;pointer-events:none;opacity:1;' +
    'transition:opacity .9s ease, backdrop-filter .7s ease, -webkit-backdrop-filter .7s ease;backdrop-filter:blur(0px)';
  var cv = document.createElement('canvas');
  cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%';
  wrap.appendChild(cv);

  var card = document.createElement('div');
  card.style.cssText = 'position:absolute;left:0;right:0;top:8%;text-align:center;color:#fff;opacity:0;' +
    'transform:translateY(10px);transition:opacity .5s ease, transform .5s ease;' +
    'font-family:"Barlow Condensed","Barlow",Arial,sans-serif;text-shadow:0 3px 22px rgba(0,0,0,.65)';
  function el(tag, css, text) {
    var n = document.createElement(tag);
    n.style.cssText = css;
    if (text) n.textContent = text;
    return n;
  }
  card.appendChild(el('div', 'font-size:clamp(20px,2.3vw,34px);font-weight:600;opacity:.92', 'Nuclear terrorist attack'));
  var row = el('div', 'display:flex;align-items:center;justify-content:center;gap:clamp(10px,1.4vw,22px);margin-top:4px');
  var img = el('img', 'height:clamp(36px,4.4vw,70px);border-radius:5px;box-shadow:0 3px 14px rgba(0,0,0,.45)');
  img.src = '__FLAG__';
  row.appendChild(img);
  row.appendChild(el('span', 'font-size:clamp(46px,7vw,112px);font-weight:700;line-height:1', '__NAME__'));
  card.appendChild(row);
  card.appendChild(el('div', 'font-size:clamp(22px,2.6vw,40px);font-weight:600;margin-top:6px;color:#FFD9C7', '__SUB__'));
  wrap.appendChild(card);
  document.body.appendChild(wrap);
  setTimeout(function () { wrap.style.backdropFilter = 'blur(8px)'; wrap.style.webkitBackdropFilter = 'blur(8px)'; }, 60);

  function finish(delay) {
    setTimeout(function () { wrap.style.opacity = '0'; }, delay);
    setTimeout(function () { if (wrap.parentNode) wrap.parentNode.removeChild(wrap); }, delay + 1000);
  }

  if (reduce) {
    wrap.style.background = 'rgba(40,6,6,.88)';
    card.style.opacity = '1'; card.style.transform = 'none';
    finish(2600);
    return;
  }

  // a short shake of the page
  var css = document.createElement('style');
  css.textContent = '@keyframes ndShake{0%,100%{transform:translate(0,0)}10%{transform:translate(-10px,5px)}' +
    '20%{transform:translate(9px,-6px)}30%{transform:translate(-8px,-3px)}40%{transform:translate(6px,6px)}' +
    '50%{transform:translate(-5px,2px)}60%{transform:translate(4px,-3px)}70%{transform:translate(-2px,2px)}' +
    '80%{transform:translate(1px,-1px)}}.nd-shake{animation:ndShake .8s cubic-bezier(.36,.07,.19,.97) both}';
  document.head.appendChild(css);
  var app = document.querySelector('[data-testid="stAppViewContainer"]') || document.querySelector('.stApp');
  setTimeout(function () { if (app) app.classList.add('nd-shake'); }, 90);
  setTimeout(function () { if (app) app.classList.remove('nd-shake'); }, 1000);

  var ctx = cv.getContext('2d');
  var dpr = Math.min(2, window.devicePixelRatio || 1);
  var W = 0, H = 0;
  function fit() {
    W = window.innerWidth; H = window.innerHeight;
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  fit();
  window.addEventListener('resize', fit);

  var R = Math.min(W, H) * 0.13;
  var cx = W * 0.5, gy = H * 0.88;

  function clamp(x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }
  function ease(x) { x = clamp(x); return 1 - Math.pow(1 - x, 3); }
  function mix(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
  function rgba(c, a) { return 'rgba(' + (c[0] | 0) + ',' + (c[1] | 0) + ',' + (c[2] | 0) + ',' + a.toFixed(3) + ')'; }
  function puff(x, y, r, c, a) {
    if (r <= 0 || a <= 0) return;
    var g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(c, a));
    g.addColorStop(0.62, rgba(c, a * 0.88));
    g.addColorStop(1, rgba(c, 0));
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  }

  var FIRE = [255, 160, 60], HOT = [255, 236, 170], SMOKE = [158, 138, 122], DARK = [104, 90, 82], DUST = [150, 132, 116], LIT = [236, 214, 188];

  // cloud cap: a rolling ring plus a dome on top
  var cap = [];
  for (var i = 0; i < 34; i++) {
    cap.push({ ring: true, a: (i / 34) * Math.PI * 2, s: 0.34 + Math.random() * 0.2, j: Math.random() * 6.28 });
  }
  for (var k = 0; k < 26; k++) {
    var ux = (Math.random() * 2 - 1) * 0.95;
    cap.push({ ring: false, x: ux, y: -0.25 - Math.sqrt(1 - ux * ux) * (0.35 + Math.random() * 0.35),
               s: 0.36 + Math.random() * 0.22, j: Math.random() * 6.28 });
  }
  var embers = [];
  for (var m = 0; m < 240; m++) {
    var ang = -Math.PI * (0.05 + Math.random() * 0.9);
    var sp = 2.5 + Math.random() * 12;
    embers.push({ x: cx, y: gy - R * 0.6, vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp,
                  life: 900 + Math.random() * 1700, r: 1 + Math.random() * 2.8 });
  }

  var t0 = performance.now(), last = t0;
  setTimeout(function () { card.style.opacity = '1'; card.style.transform = 'none'; }, 1500);
  setTimeout(function () { card.style.opacity = '0'; }, 4700);
  finish(5000);

  function frame(now) {
    var e = now - t0, dt = Math.min(3, (now - last) / 16.7); last = now;
    ctx.clearRect(0, 0, W, H);

    // darken the page, with a warm glow behind the blast
    var dark = 0.9 * clamp((e - 120) / 600);
    ctx.fillStyle = 'rgba(20,10,8,' + dark.toFixed(3) + ')';
    ctx.fillRect(0, 0, W, H);

    var p = clamp((e - 350) / 3400), ep = ease(p);
    var capY = gy - R * 0.75 - ep * H * 0.36;
    var capR = R * (0.75 + 1.05 * ep);

    var glow = ctx.createRadialGradient(cx, capY, 0, cx, capY, Math.max(W, H) * 0.6);
    glow.addColorStop(0, 'rgba(255,120,40,' + (0.45 * (1 - p * 0.6)).toFixed(3) + ')');
    glow.addColorStop(1, 'rgba(255,80,20,0)');
    ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);

    // ground dust spreading out
    var spread = R * (0.6 + 3.6 * ease((e - 150) / 2600));
    for (var d = -26; d <= 26; d++) {
      var f = Math.abs(d) / 26, jj = Math.sin(d * 12.9898) * 0.5;
      puff(cx + (d / 26) * spread, gy + R * (0.05 + 0.06 * jj) - (1 - f) * R * 0.2, R * (0.6 - 0.28 * f) * (0.9 + 0.2 * jj),
           DUST, 0.42 * clamp(e / 500) * (1 - 0.45 * f));
    }

    // stem
    var stemTop = capY + capR * 0.3, n = 18;
    for (var s = 0; s < n; s++) {
      var t = s / (n - 1);
      var y = gy - R * 0.4 + (stemTop - (gy - R * 0.4)) * t;
      var x = cx + Math.sin(s * 1.7 + e * 0.003) * capR * 0.05;
      var heat = clamp(1 - p * 1.5 + (1 - t) * 0.2);
      puff(x, y, capR * (0.2 + 0.12 * t), mix(SMOKE, FIRE, heat * 0.85), 0.9 * clamp(p * 4));
    }

    // cap: back half of the ring, dome, then front half of the ring
    var roll = e * 0.0007;
    function drawCap(front) {
      for (var q = 0; q < cap.length; q++) {
        var c = cap[q], px, py, warm;
        if (c.ring) {
          var a = c.a + roll, sy = Math.sin(a);
          if ((sy > 0) !== front) continue;
          px = cx + Math.cos(a) * capR * 1.3;
          py = capY + capR * 0.28 + sy * capR * 0.32;
          warm = clamp(1 - p * 1.1 + (sy > 0 ? 0.35 : 0));
        } else {
          if (front) continue;
          px = cx + c.x * capR * 1.05 + Math.sin(e * 0.002 + c.j) * capR * 0.04;
          py = capY + c.y * capR;
          warm = clamp(1 - p * 1.5);
        }
        var base = c.ring ? mix(DARK, SMOKE, 0.55 + 0.45 * Math.sin(c.j)) : mix(SMOKE, LIT, clamp(-c.y - 0.45));
        var col = mix(base, mix(FIRE, HOT, warm * 0.5), warm);
        puff(px, py, capR * c.s * (0.85 + 0.15 * Math.sin(e * 0.003 + c.j)), col, 0.92 * clamp(p * 5));
      }
    }
    drawCap(false);
    drawCap(true);

    // fireball
    var fb = ease(e / 650);
    var fbA = 1 - clamp((e - 1300) / 1300);
    if (fbA > 0) {
      var fy = gy - R * 0.6 - ep * H * 0.3;
      var fr = R * (0.2 + 0.95 * fb) * (1 + 0.04 * Math.sin(e * 0.05));
      var g2 = ctx.createRadialGradient(cx, fy, 0, cx, fy, fr);
      g2.addColorStop(0, 'rgba(255,253,240,' + fbA + ')');
      g2.addColorStop(0.3, 'rgba(255,238,150,' + fbA + ')');
      g2.addColorStop(0.6, 'rgba(255,150,50,' + (fbA * 0.95) + ')');
      g2.addColorStop(0.85, 'rgba(225,70,25,' + (fbA * 0.7) + ')');
      g2.addColorStop(1, 'rgba(150,30,10,0)');
      ctx.fillStyle = g2;
      ctx.beginPath(); ctx.arc(cx, fy, fr, 0, Math.PI * 2); ctx.fill();
    }

    // shock wave
    if (e > 60 && e < 1800) {
      var k2 = (e - 60) / 1740, rr = R * 0.8 + k2 * Math.max(W, H) * 0.95;
      ctx.lineWidth = 2 + 12 * (1 - k2);
      ctx.strokeStyle = 'rgba(255,240,225,' + (0.8 * (1 - k2)).toFixed(3) + ')';
      ctx.beginPath(); ctx.ellipse(cx, gy - R * 0.2, rr, rr * 0.28, 0, 0, Math.PI * 2); ctx.stroke();
      ctx.lineWidth = 1 + 6 * (1 - k2);
      ctx.strokeStyle = 'rgba(255,255,255,' + (0.45 * (1 - k2)).toFixed(3) + ')';
      ctx.beginPath(); ctx.arc(cx, gy - R * 0.6, rr * 0.7, 0, Math.PI * 2); ctx.stroke();
    }

    // embers
    for (var b = 0; b < embers.length; b++) {
      var em = embers[b];
      if (e > em.life) continue;
      em.vy += 0.13 * dt; em.vx *= Math.pow(0.986, dt);
      em.x += em.vx * dt; em.y += em.vy * dt;
      var lf = e / em.life;
      ctx.fillStyle = rgba(mix(HOT, [200, 60, 30], clamp(lf * 1.3)), 0.95 * (1 - lf));
      ctx.beginPath(); ctx.arc(em.x, em.y, em.r * (1 - lf * 0.5), 0, Math.PI * 2); ctx.fill();
    }

    // the flash
    var fl = e < 90 ? e / 90 : Math.max(0, 1 - (e - 90) / 650);
    if (fl > 0) { ctx.fillStyle = 'rgba(255,252,240,' + fl.toFixed(3) + ')'; ctx.fillRect(0, 0, W, H); }

    if (e < 6200 && wrap.parentNode) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
</script>
"""


def _js_text(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("<", "").replace(">", "")


def explosion_html(country: str, flag_uri: str, sub: str) -> str:
    return (_JS.replace("__NAME__", _js_text(country))
               .replace("__FLAG__", flag_uri)
               .replace("__SUB__", _js_text(sub)))

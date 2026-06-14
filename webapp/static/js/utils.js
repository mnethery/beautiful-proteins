// ==========================================================================
// UI Utilities — small helpers used across the app
// ==========================================================================

function status(msg) { document.getElementById('status').textContent = msg; }

/** Toggle a collapsible sidebar section. Each H2 header controls the
 *  section-body div immediately after it via display:none. */
function toggleSection(h2) {
  const body = h2.nextElementSibling;
  if (!body || !body.classList.contains('section-body')) return;
  h2.classList.toggle('collapsed');
  body.classList.toggle('hidden');
}

/** Convert hex color "#rrggbb" to Illustrate-style [r, g, b] floats (0.0-1.0) */
function hexToRgb(hex) {
  return [parseInt(hex.slice(1,3),16)/255, parseInt(hex.slice(3,5),16)/255, parseInt(hex.slice(5,7),16)/255].map(v=>Math.round(v*100)/100);
}

/** Convert Illustrate-style [r, g, b] floats to hex color "#rrggbb" */
function rgbToHex(r,g,b) {
  const h=v=>Math.round(v*255).toString(16).padStart(2,'0');
  return '#'+h(r)+h(g)+h(b);
}

function switchTab(e,tabId) {
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-bar button').forEach(b=>b.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  e.target.classList.add('active');
}

function toggleRenderPane() {
  const pane = document.getElementById('render-pane');
  const btn = document.getElementById('render-toggle');
  pane.classList.toggle('open');
  btn.textContent = pane.classList.contains('open') ? 'Hide Render' : 'Show Render';
}

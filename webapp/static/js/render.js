// ==========================================================================
// PDB Loading — Fetch from RCSB or upload from disk
// ==========================================================================

async function fetchPDB() {
  const id = document.getElementById('pdb-id').value.trim();
  if (!id) return;
  status('Fetching ' + id + '...');
  const form = new FormData();
  form.append('pdb_id', id);
  try {
    const resp = await fetch('/upload', {method:'POST', body:form});
    const data = await resp.json();
    if (data.error) { status('Error: '+data.error); return; }
    onStructureLoaded(data);
  } catch(e) { status('Error: '+e.message); }
}

async function uploadFile() {
  const file = document.getElementById('pdb-file').files[0];
  if (!file) return;
  status('Uploading...');
  const form = new FormData();
  form.append('pdb_file', file);
  try {
    const resp = await fetch('/upload', {method:'POST', body:form});
    const data = await resp.json();
    if (data.error) { status('Error: '+data.error); return; }
    onStructureLoaded(data);
  } catch(e) { status('Error: '+e.message); }
}

/**
 * Called after /upload returns. Sets up state, regenerates descriptors
 * if a non-default style is selected, loads the PDB into 3Dmol, and
 * kicks off an automatic preview render.
 */
async function onStructureLoaded(data) {
  pdbPath = data.pdb_path;
  pdbFilename = data.pdb_filename;
  chains = data.chains;
  chainTypes = data.chain_types || {};
  hiddenChains = new Set();
  chainColorOverrides = {};
  descriptors = data.descriptors;
  document.getElementById('render-btn').disabled = false;
  document.getElementById('preview-btn').disabled = false;
  status('Loaded: ' + chains.length + ' chains (' + chains.join(', ') + ')');

  // /upload always returns entity_chain descriptors. If user has a different
  // style selected, regenerate descriptors before building the chain UI.
  const style = document.getElementById('style-select').value;
  if (style !== 'entity_chain') {
    await refreshDescriptors();
  }
  buildChainUI();

  // Load PDB data into the 3Dmol viewer for interactive preview
  const resp = await fetch('/pdb/' + pdbFilename);
  const pdbData = await resp.text();
  loadStructureInViewer(pdbData);

  doRender(true);
}


// ==========================================================================
// Rendering
// ==========================================================================

/**
 * Collect all rendering parameters from the sidebar into a single object
 * for the /render API call. If preview=true, halves the scale for faster rendering.
 */
function getParams(preview) {
  const p = {
    xrot: parseFloat(document.getElementById('xrot').value),
    yrot: parseFloat(document.getElementById('yrot').value),
    zrot: parseFloat(document.getElementById('zrot').value),
    scale: parseFloat(document.getElementById('scale').value),
    tx: parseFloat(document.getElementById('tx').value),
    ty: parseFloat(document.getElementById('ty').value),
    tz: parseFloat(document.getElementById('tz').value),
    bg: hexToRgb(document.getElementById('bg-color').value),
    fog: hexToRgb(document.getElementById('fog-color').value),
    fog_front: parseFloat(document.getElementById('fog-front').value),
    fog_back: parseFloat(document.getElementById('fog-back').value),
    img_size: parseInt(document.getElementById('img-size').value),
    shadow_on: parseInt(document.getElementById('shadow-on').value),
    shadow_strength: parseFloat(document.getElementById('shadow-strength').value),
    shadow_cone: parseFloat(document.getElementById('shadow-cone').value),
    shadow_zdiff: parseFloat(document.getElementById('shadow-zdiff').value),
    shadow_max: parseFloat(document.getElementById('shadow-max').value),
    l_low: parseFloat(document.getElementById('l-low').value),
    l_high: parseFloat(document.getElementById('l-high').value),
    kernel: parseInt(document.getElementById('kernel').value),
    l_diff_min: parseFloat(document.getElementById('l-diff-min').value),
    l_diff_max: parseFloat(document.getElementById('l-diff-max').value),
    r_low: parseFloat(document.getElementById('r-low').value),
    r_high: parseFloat(document.getElementById('r-high').value),
    g_low: parseFloat(document.getElementById('g-low').value),
    g_high: parseFloat(document.getElementById('g-high').value),
    resdiff: parseFloat(document.getElementById('resdiff').value),
    descriptors: descriptors,
  };
  p.scale = Math.max(1, Math.min(100, p.scale));
  if (preview) p.scale = Math.max(p.scale * 0.5, 2);
  for (const k of ['xrot','yrot','zrot','tx','ty','tz','scale']) {
    if (isNaN(p[k])) p[k] = 0;
  }
  return p;
}

/**
 * Trigger a render via the backend. Syncs the current viewer rotation
 * to the sidebar fields first, then sends all parameters to /render.
 * On success, displays the rendered image in the bottom pane.
 */
async function doRender(preview) {
  if (!pdbPath || rendering) return;
  rendering = true;
  document.getElementById('render-btn').disabled = true;
  document.getElementById('preview-btn').disabled = true;
  document.getElementById('loading').style.display = 'block';
  status(preview ? 'Generating preview...' : 'Rendering full resolution...');

  // Sync rotation from the 3Dmol viewer so the render matches what the user sees
  updateRotationDisplay();

  try {
    const resp = await fetch('/render', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({pdb_path: pdbPath, params: getParams(preview)}),
    });
    const data = await resp.json();
    if (data.error) {
      status('Error: '+data.error);
    } else {
      const img = document.getElementById('render-img');
      img.src = data.image_url + '?t=' + Date.now();  // Cache bust
      lastImageUrl = data.image_url;
      lastJobId = data.job_id;
      if (!document.getElementById('render-pane').classList.contains('open')) toggleRenderPane();
      status(preview ? 'Preview ready.' : 'Render complete.');
    }
  } catch(e) { status('Error: '+e.message); }

  document.getElementById('loading').style.display = 'none';
  rendering = false;
  document.getElementById('render-btn').disabled = false;
  document.getElementById('preview-btn').disabled = false;
}

function exportAs(fmt) {
  if (!lastJobId) { status('Render an image first'); return; }
  if (fmt === 'svg') status('Converting to SVG (vector trace)...');
  const a = document.createElement('a');
  a.href = `/export/${lastJobId}/${fmt}`;
  a.download = `illustrate_${lastJobId}.${fmt}`;
  a.click();
  if (fmt !== 'svg') status(`${fmt.toUpperCase()} download started.`);
}

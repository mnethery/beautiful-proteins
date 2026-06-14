// ==========================================================================
// 3Dmol.js Viewer — Initialization, structure loading, and color application
// ==========================================================================

function initViewer() {
  const el = document.getElementById('mol-viewer');
  viewer = $3Dmol.createViewer(el, {
    backgroundColor: 'black',
    antialias: true,
  });
}

function loadStructureInViewer(pdbData) {
  viewer.removeAllModels();
  viewer.addModel(pdbData, 'pdb');
  applyViewerColors();
  viewer.zoomTo();
  viewer.render();
  // Save this initial view as the "base" for translation/scale calculations.
  // applyTransform() applies translation as an offset from this baseline.
  baseView = viewer.getView().slice();
  drawAxes();
}

/** Apply the current style's colors to all chains in the 3Dmol viewer. */
function applyViewerColors() {
  if (!viewer) return;
  const style = document.getElementById('style-select').value;
  chains.forEach((ch, i) => {
    if (hiddenChains.has(ch)) {
      viewer.setStyle({chain: ch}, {});
      return;
    }
    if (style === 'cpk') {
      viewer.setStyle({chain: ch}, {sphere: {radius: 1.2, colorscheme: 'Jmol'}});
    } else {
      const color = getChainColor(ch, i, style);
      viewer.setStyle({chain: ch}, {sphere: {radius: 1.2, color: rgbToHex(color[0], color[1], color[2])}});
    }
  });
  viewer.render();
}

// ==========================================================================
// Bootstrap — wire up event listeners and start the 3Dmol viewer.
// All function definitions live in the other module files (loaded earlier
// in index.html): state.js, utils.js, viewer.js, transform.js, chains.js,
// render.js.
// ==========================================================================

// Enter key in PDB ID field triggers fetch
document.getElementById('pdb-id').addEventListener('keydown', e => { if (e.key==='Enter') fetchPDB(); });

// Track 3Dmol viewer rotation changes from mouse interaction.
// We debounce the rotation display update to avoid excessive recomputation
// during drag operations (quaternion -> Euler extraction on every frame).
let rotTimer = null;
const molEl = document.getElementById('mol-viewer');
molEl.addEventListener('mousemove', (e) => {
  if (e.buttons) { clearTimeout(rotTimer); rotTimer = setTimeout(updateRotationDisplay, 30); }
});
molEl.addEventListener('mouseup', () => {
  clearTimeout(rotTimer);
  rotTimer = setTimeout(updateRotationDisplay, 50);
});
molEl.addEventListener('wheel', () => {
  clearTimeout(rotTimer);
  rotTimer = setTimeout(updateRotationDisplay, 100);
});

initViewer();

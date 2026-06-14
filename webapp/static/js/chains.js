// ==========================================================================
// Chain UI — Per-chain color pickers and visibility checkboxes
// ==========================================================================

/** Rebuild the chain list in the sidebar based on current chains and style. */
function buildChainUI() {
  const list = document.getElementById('chain-list');
  if (!list) return;
  list.innerHTML = '';
  if (!chains || chains.length === 0) {
    list.innerHTML = '<span class="hint">No chains detected</span>';
    return;
  }
  const style = document.getElementById('style-select').value;
  chains.forEach((ch, i) => {
    const color = getChainColor(ch, i, style);
    const row = document.createElement('div');
    row.className = 'chain-row';

    // Visibility checkbox
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.id = 'chain-vis-' + i;
    cb.checked = !hiddenChains.has(ch);
    cb.addEventListener('change', () => toggleChainVisibility(i));
    row.appendChild(cb);

    // Color picker (not shown for CPK since it colors by element, not chain)
    if (style !== 'cpk') {
      const colorInput = document.createElement('input');
      colorInput.type = 'color';
      colorInput.id = 'chain-color-' + i;
      colorInput.value = rgbToHex(color[0], color[1], color[2]);
      colorInput.addEventListener('change', () => updateChainColor(i));
      row.appendChild(colorInput);
    }

    // Label with chain type annotation
    const label = document.createElement('span');
    const ct = chainTypes[ch];
    const typeTag = ct === 'nucleic' ? ' (DNA/RNA)' : ct === 'protein' ? '' : ct ? ' (' + ct + ')' : '';
    label.textContent = 'Chain ' + ch + typeTag;
    row.appendChild(label);
    list.appendChild(row);
  });
}

/**
 * Handle a chain color change from the color picker.
 * Stores the override, regenerates descriptors on the backend (important
 * for nucleic acid chains where color affects backbone shading), and
 * updates the 3Dmol preview.
 */
async function updateChainColor(ci) {
  const hex = document.getElementById('chain-color-'+ci).value;
  const [r,g,b] = hexToRgb(hex);
  const ch = chains[ci];
  const style = document.getElementById('style-select').value;
  chainColorOverrides[style + ':' + ch] = [r, g, b];
  // Regenerate descriptors server-side (needed for nucleic backbone shading)
  await refreshDescriptors();
  viewer.setStyle({chain: ch}, {sphere: {radius: 1.2, color: hex}});
  viewer.render();
}

/** Toggle a chain's visibility in both the 3Dmol preview and Illustrate render. */
function toggleChainVisibility(ci) {
  const ch = chains[ci];
  const vis = document.getElementById('chain-vis-'+ci).checked;
  if (vis) {
    hiddenChains.delete(ch);
  } else {
    hiddenChains.add(ch);
  }
  const style = document.getElementById('style-select').value;
  if (vis) {
    if (style === 'cpk') {
      viewer.setStyle({chain: ch}, {sphere: {radius: 1.2, colorscheme: 'Jmol'}});
    } else {
      const color = getChainColor(ch, ci, style);
      viewer.setStyle({chain: ch}, {sphere: {radius: 1.2, color: rgbToHex(color[0], color[1], color[2])}});
    }
  } else {
    viewer.setStyle({chain: ch}, {});  // Empty style = invisible
  }
  viewer.render();
  refreshDescriptors();
}


// ==========================================================================
// Style Management
// ==========================================================================

/** Handle style dropdown change: regenerate descriptors and update UI. */
async function changeStyle() {
  const style = document.getElementById('style-select').value;
  document.getElementById('one-color-field').style.display = style === 'one_color' ? '' : 'none';
  if (style === 'one_color') {
    const [r,g,b] = hexToRgb(document.getElementById('one-color-picker').value);
    chainColorOverrides['one_color:__one'] = [r, g, b];
  }
  if (!pdbPath) return;
  await refreshDescriptors();
  buildChainUI();
  applyViewerColors();
}

/**
 * Ask the backend to regenerate the Illustrate descriptor list.
 * Called when style, colors, or chain visibility changes. The backend
 * re-parses the PDB and builds fresh descriptors with the correct
 * ATOM/HETATM patterns for the current settings.
 */
async function refreshDescriptors() {
  if (!pdbPath) return;
  const style = document.getElementById('style-select').value;
  const colors = {};
  if (style === 'one_color') {
    const oneOverride = chainColorOverrides['one_color:__one'];
    if (oneOverride) {
      colors['__one'] = oneOverride;
    } else {
      const [r,g,b] = hexToRgb(document.getElementById('one-color-picker').value);
      colors['__one'] = [r, g, b];
    }
  } else if (style !== 'cpk') {
    // Send current effective colors so backend can derive nucleic shades etc.
    chains.forEach((ch, i) => {
      const color = getChainColor(ch, i, style);
      colors[ch] = color;
    });
  }
  const resp = await fetch('/descriptors', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pdb_path: pdbPath, style, colors, hidden: [...hiddenChains]}),
  });
  const data = await resp.json();
  if (data.descriptors) descriptors = data.descriptors;
  if (data.chain_types) chainTypes = data.chain_types;
}

// ==========================================================================
// Application State and Palette Constants
// ==========================================================================
//
// All globals attached to window scope so the other module files can read
// and mutate them. Loaded first in index.html so every later file sees them.
// ==========================================================================

let pdbPath = null;       // Server-side path to the loaded PDB file
let pdbFilename = null;   // Filename for fetching via /pdb/<filename>
let descriptors = [];     // Current Illustrate atom descriptor list (sent to /render)
let chains = [];          // Ordered chain IDs from the PDB
let chainTypes = {};      // Chain ID -> "protein" | "nucleic" | "other"
let hiddenChains = new Set();       // Chains toggled off by the user
let chainColorOverrides = {};       // User color overrides, keyed as "style:chainId"
let rendering = false;    // Mutex to prevent concurrent renders
let lastImageUrl = null;  // URL of the most recent rendered image
let lastJobId = null;     // Job ID for export (maps to server-side output files)
let viewer = null;        // 3Dmol.js GLViewer instance
let baseView = null;      // Snapshot of getView() at load time, used as reference
                          // for translation/scale offsets in applyTransform()
const DEFAULT_SCALE = 12.0;  // Default Illustrate scale (pixels per Angstrom)

// Default per-chain colors matching the backend's CHAIN_COLORS palette
const CHAIN_COLORS = [
  [0.65,0.65,0.95],[0.95,0.65,0.65],[0.65,0.95,0.65],
  [0.95,0.95,0.65],[0.95,0.65,0.95],[0.65,0.95,0.95],
  [0.85,0.75,0.65],[0.75,0.85,0.75],
];
const PROTEIN_COLOR = [0.30, 0.53, 0.84];
const DNA_COLOR = [0.92, 0.72, 0.90];

/**
 * Return the default color for a chain given the current style.
 * Protein/DNA style assigns biologically meaningful defaults; Entity Chain
 * cycles through the palette; One Color uses the picker value.
 */
function defaultChainColor(ch, i, style) {
  if (style === 'protein_dna') return (chainTypes[ch] === 'nucleic') ? DNA_COLOR : PROTEIN_COLOR;
  if (style === 'one_color') return hexToRgb(document.getElementById('one-color-picker').value);
  return CHAIN_COLORS[i % CHAIN_COLORS.length];
}

/**
 * Return the effective color for a chain, checking user overrides first.
 * Overrides are stored per-style so switching styles doesn't lose custom colors.
 */
function getChainColor(ch, i, style) {
  const key = style + ':' + ch;
  if (chainColorOverrides[key]) return chainColorOverrides[key];
  return defaultChainColor(ch, i, style);
}

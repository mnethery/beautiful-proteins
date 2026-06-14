// ==========================================================================
// Coordinate System Mapping — 3Dmol.js <-> Illustrate
// ==========================================================================
//
// 3Dmol.js and Illustrate use different coordinate conventions:
//
//   3Dmol.js:   X = right,  Y = up,      Z = toward viewer
//   Illustrate: X = down,   Y = right,   Z = toward viewer
//
// The coordinate transform matrix C maps from 3Dmol to Illustrate:
//
//   C = [ [ 0, -1,  0 ],      C^-1 = [ [ 0,  1,  0 ],
//         [ 1,  0,  0 ],               [ -1,  0,  0 ],
//         [ 0,  0,  1 ] ]              [  0,  0,  1 ] ]
//
// To convert a 3Dmol rotation Q to Illustrate angles: R = C * Q
// To convert Illustrate angles back to 3Dmol rotation: Q = C^-1 * R
//
// Illustrate applies rotations as intrinsic XYZ Euler angles:
//   R = Rx(a) * Ry(b) * Rz(c)
// where a = xrot, b = yrot, c = zrot (in degrees).
//
// The default Z rotation of 90 degrees accounts for the coordinate swap:
// with no user rotation, Illustrate's Y-axis (right) aligns with 3Dmol's
// X-axis (right), so molecules appear in the same orientation in both views.
// ==========================================================================

/**
 * Extract Illustrate XYZ Euler angles from the 3Dmol viewer's current quaternion.
 *
 * 3Dmol getView() returns [pos.x, pos.y, pos.z, rotZ, q.x, q.y, q.z, q.w]
 * where q is the orientation quaternion.
 *
 * Steps:
 *   1. Convert quaternion to 3x3 rotation matrix Q
 *   2. Apply coordinate transform: R = C * Q (3Dmol -> Illustrate)
 *   3. Decompose R as Rx(a) * Ry(b) * Rz(c) using XYZ intrinsic Euler extraction
 */
function getViewerRotation() {
  if (!viewer) return {xrot:0, yrot:0, zrot:90};
  const view = viewer.getView();
  if (!view || view.length < 8) return {xrot:0, yrot:0, zrot:90};

  const qx=view[4], qy=view[5], qz=view[6], qw=view[7];

  // Quaternion -> rotation matrix Q
  const Q00 = 1-2*(qy*qy+qz*qz), Q01 = 2*(qx*qy-qz*qw), Q02 = 2*(qx*qz+qy*qw);
  const Q10 = 2*(qx*qy+qz*qw), Q11 = 1-2*(qx*qx+qz*qz), Q12 = 2*(qy*qz-qx*qw);
  const Q20 = 2*(qx*qz-qy*qw), Q21 = 2*(qy*qz+qx*qw), Q22 = 1-2*(qx*qx+qy*qy);

  // Apply coordinate transform C: R = C * Q
  // C = [[0,-1,0],[1,0,0],[0,0,1]]  =>  R row0 = -Q row1, R row1 = Q row0, R row2 = Q row2
  const R00=-Q10, R01=-Q11, R02=-Q12;
  const R10= Q00, R11= Q01, R12= Q02;
  const R20= Q20, R21= Q21, R22= Q22;

  // Decompose R = Rx(a) * Ry(b) * Rz(c) — XYZ intrinsic Euler angles
  // From the rotation matrix: R[0][2] = sin(b)
  let b = Math.asin(Math.max(-1, Math.min(1, R02)));
  let a, c;
  const cb = Math.cos(b);
  if (Math.abs(cb) > 1e-6) {
    a = Math.atan2(-R12, R22);   // atan2(-R[1][2], R[2][2])
    c = Math.atan2(-R01, R00);   // atan2(-R[0][1], R[0][0])
  } else {
    // Gimbal lock: Y rotation is +-90 degrees, X and Z are coupled
    a = Math.atan2(R10, R11);
    c = 0;
  }

  let xrot = a * 180/Math.PI;
  let yrot = b * 180/Math.PI;
  let zrot = c * 180/Math.PI;

  if (isNaN(xrot)) xrot = 0;
  if (isNaN(yrot)) yrot = 0;
  if (isNaN(zrot)) zrot = 90;

  return {
    xrot: Math.round(xrot * 10)/10,
    yrot: Math.round(yrot * 10)/10,
    zrot: Math.round(zrot * 10)/10,
  };
}

/** Sync the sidebar rotation fields and HUD overlay from the current 3Dmol view. */
function updateRotationDisplay() {
  const r = getViewerRotation();
  document.getElementById('xrot').value = r.xrot;
  document.getElementById('yrot').value = r.yrot;
  document.getElementById('zrot').value = r.zrot;

  if (viewer && baseView) {
    const view = viewer.getView();
    const raw = DEFAULT_SCALE * baseView[3] / view[3];
    const scale = Math.round(Math.max(1, Math.min(100, raw > 0 ? raw : 100)) * 10) / 10;
    document.getElementById('scale').value = scale;
  }

  document.getElementById('rot-info').textContent =
    `X: ${r.xrot}°  Y: ${r.yrot}°  Z: ${r.zrot}°  •  Drag to rotate • Scroll to zoom`;
  drawAxes();
}


// ==========================================================================
// 3D Axis Legend
// ==========================================================================

/**
 * Draw an axis indicator in the bottom-left corner showing Illustrate's
 * X/Y/Z axes in their current orientation within the 3Dmol viewport.
 *
 * Each Illustrate axis unit vector is mapped to 3Dmol screen space via C^-1,
 * then rotated by the current viewer quaternion to get screen-space directions.
 *
 * Mapping (Illustrate -> 3Dmol via C^-1):
 *   Ill X (1,0,0) -> 3Dmol (0,-1,0) -> rotated: (-Q01, -Q11, -Q21)
 *   Ill Y (0,1,0) -> 3Dmol (1, 0,0) -> rotated: ( Q00,  Q10,  Q20)
 *   Ill Z (0,0,1) -> 3Dmol (0, 0,1) -> rotated: ( Q02,  Q12,  Q22)
 *
 * The Z component (sz) controls opacity: axes pointing toward the viewer
 * (sz > 0) are drawn at full opacity, axes pointing away are dimmed.
 */
function drawAxes() {
  if (!viewer) return;
  const canvas = document.getElementById('axis-canvas');
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const view = viewer.getView();
  if (!view || view.length < 8) return;
  const qx=view[4], qy=view[5], qz=view[6], qw=view[7];

  // Quaternion -> rotation matrix (3Dmol screen space)
  const Q00=1-2*(qy*qy+qz*qz), Q01=2*(qx*qy-qz*qw), Q02=2*(qx*qz+qy*qw);
  const Q10=2*(qx*qy+qz*qw), Q11=1-2*(qx*qx+qz*qz), Q12=2*(qy*qz-qx*qw);
  const Q20=2*(qx*qz-qy*qw), Q21=2*(qy*qz+qx*qw), Q22=1-2*(qx*qx+qy*qy);

  // Illustrate axes in 3Dmol screen space (see derivation above)
  const axes = [
    {label:'X', color:'#ff4444', sx: -Q01, sy: -Q11, sz: -Q21},
    {label:'Y', color:'#44ff44', sx: Q00, sy: Q10, sz: Q20},
    {label:'Z', color:'#4488ff', sx: Q02, sy: Q12, sz: Q22},
  ];

  const cx = w/2, cy = h/2, len = 30;

  // Background circle
  ctx.beginPath();
  ctx.arc(cx, cy, len + 8, 0, 2*Math.PI);
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.fill();

  // Sort by depth so closer axes draw on top (painter's algorithm)
  axes.sort((a, b) => a.sz - b.sz);

  axes.forEach(ax => {
    const ex = cx + ax.sx * len;
    const ey = cy - ax.sy * len;  // Negate Y: canvas Y increases downward
    const opacity = ax.sz > 0 ? 1.0 : 0.35;

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(ex, ey);
    ctx.strokeStyle = ax.color;
    ctx.globalAlpha = opacity;
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.font = 'bold 11px sans-serif';
    ctx.fillStyle = ax.color;
    const lx = cx + ax.sx * (len + 10);
    const ly = cy - ax.sy * (len + 10);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(ax.label, lx, ly);
    ctx.globalAlpha = 1.0;
  });
}


// ==========================================================================
// Apply Transform — Sidebar values -> 3Dmol viewer
// ==========================================================================

/**
 * Set the 3Dmol viewer's orientation from the sidebar rotation/translation/scale
 * fields. This is the inverse of getViewerRotation(): given Illustrate Euler
 * angles, build the 3Dmol quaternion.
 *
 * Steps:
 *   1. Build rotation matrix R = Rx(a) * Ry(b) * Rz(c) from sidebar angles
 *   2. Undo coordinate transform: Q = C^-1 * R (Illustrate -> 3Dmol)
 *   3. Convert Q to quaternion and apply to the viewer
 *   4. Apply translation/scale as offsets from the initial baseView
 *
 * Translation coordinate mapping (Illustrate -> 3Dmol):
 *   Ill X (down)    -> 3Dmol Y (up) with sign flip:  view[1] = baseView[1] + tx
 *   Ill Y (right)   -> 3Dmol X (right) with sign flip: view[0] = baseView[0] - ty
 *   Ill Z (toward)  -> 3Dmol Z (toward) with sign flip: view[2] = baseView[2] - tz
 *
 * Scale: 3Dmol's view[3] is a zoom factor (larger = more zoomed out), which is
 * inversely proportional to Illustrate's scale (pixels per Angstrom).
 */
function applyTransform() {
  if (!viewer) return;
  const a = parseFloat(document.getElementById('xrot').value) * Math.PI/180;
  const b = parseFloat(document.getElementById('yrot').value) * Math.PI/180;
  const c = parseFloat(document.getElementById('zrot').value) * Math.PI/180;
  const ca=Math.cos(a), sa=Math.sin(a), cb=Math.cos(b), sb=Math.sin(b), cc=Math.cos(c), sc=Math.sin(c);

  // R = Rx(a) * Ry(b) * Rz(c)
  const R00=cb*cc, R01=-cb*sc, R02=sb;
  const R10=sa*sb*cc+ca*sc, R11=-sa*sb*sc+ca*cc, R12=-sa*cb;
  const R20=-ca*sb*cc+sa*sc, R21=ca*sb*sc+sa*cc, R22=ca*cb;

  // Q = C^-1 * R, where C^-1 = [[0,1,0],[-1,0,0],[0,0,1]]
  // Q row0 = R row1, Q row1 = -R row0, Q row2 = R row2
  const Q00=R10, Q01=R11, Q02=R12;
  const Q10=-R00, Q11=-R01, Q12=-R02;
  const Q20=R20, Q21=R21, Q22=R22;

  // Rotation matrix -> quaternion (Shepperd's method)
  let qx, qy, qz, qw;
  const tr = Q00 + Q11 + Q22;
  if (tr > 0) {
    const s = 0.5 / Math.sqrt(tr + 1);
    qw = 0.25 / s;
    qx = (Q21 - Q12) * s;
    qy = (Q02 - Q20) * s;
    qz = (Q10 - Q01) * s;
  } else if (Q00 > Q11 && Q00 > Q22) {
    const s = 2 * Math.sqrt(1 + Q00 - Q11 - Q22);
    qw = (Q21 - Q12) / s;
    qx = 0.25 * s;
    qy = (Q01 + Q10) / s;
    qz = (Q02 + Q20) / s;
  } else if (Q11 > Q22) {
    const s = 2 * Math.sqrt(1 + Q11 - Q00 - Q22);
    qw = (Q02 - Q20) / s;
    qx = (Q01 + Q10) / s;
    qy = 0.25 * s;
    qz = (Q12 + Q21) / s;
  } else {
    const s = 2 * Math.sqrt(1 + Q22 - Q00 - Q11);
    qw = (Q10 - Q01) / s;
    qx = (Q02 + Q20) / s;
    qy = (Q12 + Q21) / s;
    qz = 0.25 * s;
  }

  const tx = parseFloat(document.getElementById('tx').value) || 0;
  const ty = parseFloat(document.getElementById('ty').value) || 0;
  const tz = parseFloat(document.getElementById('tz').value) || 0;
  const scale = Math.max(1, Math.min(100, parseFloat(document.getElementById('scale').value) || DEFAULT_SCALE));

  const view = viewer.getView();
  if (baseView) {
    // Translation: offset from baseline position with coordinate swap
    view[0] = baseView[0] - ty;
    view[1] = baseView[1] + tx;
    view[2] = baseView[2] - tz;
    // Scale: inversely proportional (higher Illustrate scale = more zoomed in)
    view[3] = baseView[3] * (DEFAULT_SCALE / scale);
  }
  view[4] = qx; view[5] = qy; view[6] = qz; view[7] = qw;
  viewer.setView(view);
  updateRotationDisplay();
}

"""Illustrate command file (stdin script) generation for the Fortran binary."""


def _safe_float(val, default=0.0):
    """Convert a value to float, returning default on failure or NaN."""
    try:
        v = float(val)
        if v != v:  # NaN check
            return default
        return v
    except (TypeError, ValueError):
        return default


def build_command_file(pdb_path, params, output_path):
    """Generate the Illustrate command file (stdin input for the Fortran binary).

    Illustrate reads commands sequentially from stdin. The command file format:

      read           — Begin reading a PDB file
      <pdb_path>     — Path to the PDB file
      <descriptors>  — One line per descriptor (pattern + residue range + color + radius)
      END            — End of descriptor list
      center / auto  — Auto-center the molecule
      trans / x,y,z  — Translation offset in Angstroms
      scale / N      — Pixels per Angstrom
      xro / angle    — X rotation in degrees (applied as intrinsic XYZ Euler rotation)
      yro / angle    — Y rotation in degrees
      zro / angle    — Z rotation in degrees
      wor            — World parameters (background, fog, shadows, image size)
      ill            — Illustration parameters (outline detection thresholds)
      cal            — Calculate (render) and write output
      <output_path>  — Path for the output PNM image

    Each descriptor line has the format:
      PATTERN RES_START,RES_END, R,G,B, RADIUS
    where PATTERN is exactly 16 characters (padded with "-" wildcards if shorter).
    """
    p = params
    descriptors = p.get("descriptors", [])

    lines = ["read", str(pdb_path)]
    for d in descriptors:
        # Pad pattern to exactly 16 chars (Illustrate's fixed-width format)
        pat = d["pattern"]
        while len(pat) < 16:
            pat += "-"
        pat = pat[:16]
        lines.append(f"{pat} {d['res_start']},{d['res_end']}, {d['r']:.1f},{d['g']:.1f},{d['b']:.1f}, {d['radius']:.1f}")
    lines.append("END")

    lines.extend(["center", "auto"])
    lines.extend(["trans", f"{p.get('tx', 0.0)},{p.get('ty', 0.0)},{p.get('tz', 0.0)}"])
    lines.extend(["scale", str(p.get("scale", 12.0))])

    # Rotations — Illustrate applies these as intrinsic XYZ Euler rotations.
    # Internally, Illustrate builds rm = Rz * Ry * Rx (in Fortran "catenate" order)
    # and applies as rm^T * v, which is equivalent to Rx(a) * Ry(b) * Rz(c) * v.
    xrot = _safe_float(p.get("xrot"), 0.0)
    yrot = _safe_float(p.get("yrot"), 0.0)
    zrot = _safe_float(p.get("zrot"), 0.0)
    if xrot != 0:
        lines.extend(["xro", str(xrot)])
    if yrot != 0:
        lines.extend(["yro", str(yrot)])
    if zrot != 0:
        lines.extend(["zro", str(zrot)])

    # World parameters: background color, fog color/distance, shadow settings
    bg = p.get("bg", [1.0, 1.0, 1.0])
    fog = p.get("fog", [1.0, 1.0, 1.0])
    fog_front = p.get("fog_front", 1.0)
    fog_back = p.get("fog_back", 1.0)
    shadow_on = p.get("shadow_on", 1)
    shadow_strength = p.get("shadow_strength", 0.0023)
    shadow_cone = p.get("shadow_cone", 2.0)
    shadow_zdiff = p.get("shadow_zdiff", 1.0)
    shadow_max = p.get("shadow_max", 0.2)
    img_size = p.get("img_size", -30)  # Negative = padding in pixels around molecule

    lines.append("wor")
    lines.append(f"{bg[0]},{bg[1]},{bg[2]},{fog[0]},{fog[1]},{fog[2]},{fog_front},{fog_back}")
    lines.append(f"{shadow_on},{shadow_strength},{shadow_cone},{shadow_zdiff},{shadow_max}")
    lines.append(f"{img_size},{img_size}")

    # Illustration parameters: outline/contour detection thresholds
    # l_low/l_high: depth-based contour line intensity range
    # kernel: outline detection kernel size (1-4)
    # l_diff_min/max: Z-depth difference thresholds for contour detection
    # r_low/r_high: subunit boundary outline intensity
    # g_low/g_high: residue boundary outline intensity
    # resdiff: residue number difference threshold for inter-residue outlines
    l_low = p.get("l_low", 3.0)
    l_high = p.get("l_high", 10.0)
    kernel = p.get("kernel", 4)
    l_diff_min = p.get("l_diff_min", 0.0)
    l_diff_max = p.get("l_diff_max", 5.0)
    r_low = p.get("r_low", 3.0)
    r_high = p.get("r_high", 10.0)
    g_low = p.get("g_low", 3.0)
    g_high = p.get("g_high", 8.0)
    resdiff = p.get("resdiff", 6000.0)

    lines.append("ill")
    lines.append(f"{l_low},{l_high},{kernel},{l_diff_min},{l_diff_max}")
    lines.append(f"{r_low},{r_high}")
    lines.append(f"{g_low},{g_high},{resdiff}")

    lines.append("cal")
    lines.append(str(output_path))

    return "\n".join(lines) + "\n"

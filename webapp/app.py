"""
Flask backend for the Illustrate web interface.

Handles PDB file loading, atom descriptor generation, and rendering via
the Illustrate Fortran binary. The frontend (index.html) communicates
with this server through a small JSON API:

  POST /upload       — Load a PDB by ID (fetched from RCSB) or file upload
  POST /descriptors  — Regenerate atom descriptors for a given style/color set
  POST /render       — Run the Illustrate binary and return the rendered image
  GET  /export/<id>  — Download rendered output as PNG, PNM, or SVG

Domain logic lives in the supporting modules:
  palettes.py        — Color constants and shade derivation
  pdb_parser.py      — PDB chain/residue extraction
  descriptors.py     — Illustrate descriptor card generation per style
  illustrate_cmd.py  — Command file (stdin) generation for the Fortran binary
"""

import os
import shutil
import subprocess
import tempfile
import uuid
import urllib.request
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image
import vtracer

from pdb_parser import get_chains_from_pdb
from descriptors import build_descriptors
from illustrate_cmd import build_command_file

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
ILLUSTRATE_BIN = BASE_DIR.parent / "Illustrate" / "illustrate"
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Load a PDB structure by RCSB ID or file upload.

    Returns chain info and default (entity_chain) descriptors. The frontend
    may immediately call /descriptors to switch to a different style.
    """
    pdb_id = request.form.get("pdb_id", "").strip()
    file = request.files.get("pdb_file")

    if pdb_id:
        pdb_path = UPLOAD_DIR / f"{pdb_id.upper()}.pdb"
        if not pdb_path.exists():
            url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
            try:
                urllib.request.urlretrieve(url, str(pdb_path))
            except Exception as e:
                return jsonify({"error": f"Could not fetch PDB {pdb_id}: {e}"}), 400
    elif file and file.filename:
        fname = f"{uuid.uuid4().hex}_{file.filename}"
        pdb_path = UPLOAD_DIR / fname
        file.save(str(pdb_path))
    else:
        return jsonify({"error": "No PDB file or ID provided"}), 400

    chains, chain_types, chain_nuc_residues, chain_has_hetatm, chain_hetatm_residues = get_chains_from_pdb(str(pdb_path))
    descriptors = build_descriptors(chains, chain_types, style="entity_chain", chain_has_hetatm=chain_has_hetatm, chain_hetatm_residues=chain_hetatm_residues)

    return jsonify({
        "pdb_path": str(pdb_path),
        "pdb_filename": pdb_path.name,
        "chains": chains,
        "chain_types": chain_types,
        "descriptors": descriptors,
    })


@app.route("/descriptors", methods=["POST"])
def get_descriptors():
    """Regenerate descriptors for the current PDB with a new style, colors, or visibility."""
    data = request.get_json()
    pdb_path = data.get("pdb_path")
    if not pdb_path or not os.path.exists(pdb_path):
        return jsonify({"error": "PDB file not found"}), 400
    chains, chain_types, chain_nuc_residues, chain_has_hetatm, chain_hetatm_residues = get_chains_from_pdb(pdb_path)
    style = data.get("style", "entity_chain")
    colors = data.get("colors")
    hidden = data.get("hidden", [])
    descriptors = build_descriptors(chains, chain_types, style=style, colors=colors, hidden=hidden, chain_nuc_residues=chain_nuc_residues, chain_has_hetatm=chain_has_hetatm, chain_hetatm_residues=chain_hetatm_residues)
    return jsonify({"descriptors": descriptors, "chain_types": chain_types})


@app.route("/pdb/<filename>")
def serve_pdb(filename):
    """Serve a PDB file for the 3Dmol.js viewer to load."""
    return send_file(str(UPLOAD_DIR / filename), mimetype="chemical/x-pdb")


@app.route("/render", methods=["POST"])
def render():
    """Run the Illustrate Fortran binary and return the rendered image.

    Workflow:
      1. Create a temp working directory (Illustrate writes intermediate files)
      2. Copy the PDB into it, stripping REMARK 350 biological assembly records
         so Illustrate renders ALL chains — without this, it would only render
         chains listed in BIOMOLECULE 1 (e.g. 1TTT: only chains A,D of 6)
      3. Generate the Illustrate command file from the frontend's parameters
      4. Run the Fortran binary with the command file piped to stdin
      5. Convert the output PNM to PNG and return the image URL
    """
    data = request.get_json()
    pdb_path = data.get("pdb_path")
    if not pdb_path or not os.path.exists(pdb_path):
        return jsonify({"error": "PDB file not found"}), 400

    params = data.get("params", {})
    job_id = uuid.uuid4().hex[:12]
    output_png = OUTPUT_DIR / f"{job_id}.png"
    output_pnm = OUTPUT_DIR / f"{job_id}.pnm"

    work_dir = Path(tempfile.mkdtemp(prefix="ill_", dir="/tmp"))
    try:
        short_pdb = work_dir / "in.pdb"
        # Strip REMARK 350 lines to prevent Illustrate's biological assembly
        # filter from hiding chains. Illustrate parses BIOMOLECULE 1's chain
        # list and silently skips all atoms not in that list.
        with open(pdb_path) as src, open(str(short_pdb), "w") as dst:
            for line in src:
                if line.startswith("REMARK 350"):
                    continue
                dst.write(line)
        short_out = "out.pnm"

        cmd_content = build_command_file("in.pdb", params, short_out)
        (work_dir / "cmd.inp").write_text(cmd_content)

        try:
            result = subprocess.run(
                [str(ILLUSTRATE_BIN)],
                input=cmd_content,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(work_dir),
            )
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Render timed out (>120s)"}), 500

        out_pnm = work_dir / short_out
        if not out_pnm.exists():
            return jsonify({
                "error": "Render failed - no output file produced",
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
            }), 500

        try:
            img = Image.open(str(out_pnm))
            img.save(str(output_png), "PNG")
        except Exception as e:
            return jsonify({"error": f"Image conversion failed: {e}"}), 500

        # Keep the PNM for lossless export
        shutil.copy2(str(out_pnm), str(output_pnm))

        return jsonify({
            "image_url": f"/output/{job_id}.png",
            "job_id": job_id,
            "stdout": result.stdout[-2000:] if result.stdout else "",
        })
    finally:
        shutil.rmtree(str(work_dir), ignore_errors=True)


@app.route("/export/<job_id>/<fmt>")
def export(job_id, fmt):
    """Download a rendered image in the requested format.

    PNG and PNM are served directly from cached render output. SVG is generated
    on-demand using vtracer (raster-to-vector tracing) and cached for reuse.
    """
    if fmt == "png":
        path = OUTPUT_DIR / f"{job_id}.png"
        if not path.exists():
            return jsonify({"error": "File not found"}), 404
        return send_file(str(path), as_attachment=True, download_name=f"illustrate_{job_id}.png")

    if fmt == "pnm":
        path = OUTPUT_DIR / f"{job_id}.pnm"
        if not path.exists():
            return jsonify({"error": "PNM file not found — re-render first"}), 404
        return send_file(str(path), as_attachment=True, download_name=f"illustrate_{job_id}.pnm")

    if fmt == "svg":
        png_path = OUTPUT_DIR / f"{job_id}.png"
        svg_path = OUTPUT_DIR / f"{job_id}.svg"
        if not png_path.exists():
            return jsonify({"error": "File not found — render first"}), 404
        if not svg_path.exists():
            try:
                vtracer.convert_image_to_svg_py(
                    image_path=str(png_path),
                    out_path=str(svg_path),
                    colormode="color",
                    hierarchical="stacked",
                    mode="spline",
                    filter_speckle=4,
                    color_precision=6,
                    layer_difference=16,
                    corner_threshold=60,
                    length_threshold=4.0,
                    max_iterations=10,
                    splice_threshold=45,
                    path_precision=3,
                )
            except Exception as e:
                return jsonify({"error": f"SVG conversion failed: {e}"}), 500
        return send_file(str(svg_path), as_attachment=True, download_name=f"illustrate_{job_id}.svg")

    return jsonify({"error": f"Unknown format: {fmt}"}), 400


@app.route("/output/<filename>")
def serve_output(filename):
    """Serve rendered images for inline display in the frontend."""
    return send_file(str(OUTPUT_DIR / filename))


if __name__ == "__main__":
    app.run(debug=False, port=5001)

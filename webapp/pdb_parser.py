"""PDB file parsing — extract chain information needed for descriptor generation."""

from palettes import NUCLEIC_RESIDUES


def get_chains_from_pdb(pdb_path):
    """Parse a PDB file to extract chain information needed for descriptor generation.

    Scans every ATOM/HETATM record and returns:
      - chains:              Ordered list of chain IDs (first-seen order)
      - chain_types:         Dict mapping chain ID → "protein", "nucleic", or "other"
      - chain_nuc_residues:  Dict mapping nucleic chain ID → set of raw 3-char
                             residue names from ATOM records (e.g. {"  C", " DG"}).
                             These are the *unstripped* PDB columns 18-20, preserved
                             exactly so descriptor patterns align with the PDB file.
      - chain_has_hetatm:    Set of chain IDs that contain non-water HETATM records
      - chain_hetatm_residues: Dict mapping chain ID → set of raw 3-char residue
                             names from HETATM records (modified bases like "2MG",
                             ligands like "GNP", etc.)

    The HETATM tracking is essential because many PDB structures store modified
    nucleotides (PSU, H2U, 7MG, 5MC, YYG, etc.) as HETATM rather than ATOM.
    Without HETATM descriptors, these atoms would be invisible to Illustrate
    even though 3Dmol.js displays them in the preview.
    """
    chains = []
    seen = set()
    chain_types = {}
    chain_nuc_residues = {}
    chain_has_hetatm = set()
    chain_hetatm_residues = {}
    with open(pdb_path) as f:
        for line in f:
            if line.startswith("ATOM") or line.startswith("HETATM"):
                chain = line[21:22].strip()
                if not chain:
                    continue
                resname = line[17:20].strip()
                raw_resname = line[17:20]
                if chain not in seen:
                    seen.add(chain)
                    chains.append(chain)
                is_nuc = resname in NUCLEIC_RESIDUES
                if line.startswith("ATOM"):
                    # Classify chain type from the first ATOM record we see
                    if chain not in chain_types:
                        chain_types[chain] = "nucleic" if is_nuc else "protein"
                    if is_nuc:
                        chain_nuc_residues.setdefault(chain, set()).add(raw_resname)
                elif line.startswith("HETATM"):
                    # Track non-water HETATM residues per chain
                    if resname != "HOH":
                        chain_has_hetatm.add(chain)
                        chain_hetatm_residues.setdefault(chain, set()).add(raw_resname)
    for ch in chains:
        if ch not in chain_types:
            chain_types[ch] = "other"
    return chains, chain_types, chain_nuc_residues, chain_has_hetatm, chain_hetatm_residues

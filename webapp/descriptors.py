"""
Illustrate atom descriptor generation.

Illustrate Descriptor Format
-----------------------------
Illustrate classifies each PDB atom using "descriptor cards" — 16-character
pattern strings that are matched against each ATOM/HETATM record:

    Positions 1-6:   Record type — must match "ATOM  " or "HETATM" exactly
    Positions 7-16:  Matched against PDB columns 13-22 (atom name, residue
                     name, chain ID). The character "-" acts as a wildcard.

Illustrate processes descriptors top-to-bottom and uses the FIRST match.
A radius of 0.0 hides the atom. This first-match behavior means specific
patterns (e.g. carbon on chain A) must appear before generic catch-alls
(e.g. any atom on chain A).

PDB column reference for the 10-char descriptor field:
    Col 13-16: Atom name    (e.g. " CA ", " P  ", " O3'")
    Col 17:    Alt location  (usually " ")
    Col 18-20: Residue name  (e.g. "ALA", " DG", "2MG")
    Col 21:    Unused        (usually " ")
    Col 22:    Chain ID      (e.g. "A", "D")
"""

from palettes import (
    CHAIN_COLORS,
    PROTEIN_COLOR,
    DNA_COLOR,
    CPK_COLORS,
    CPK_DEFAULT,
    CPK_RADII,
    CPK_DEFAULT_RADIUS,
    nuc_shades,
)


def _hide_descriptors():
    """Descriptors that hide unwanted atoms.

    These are placed at the TOP of the descriptor list so they match first:
      - Water molecules (HOH) — hidden in both ATOM and HETATM forms
      - Hydrogen atoms — hidden to match Illustrate's heavy-atom-only convention

    A radius of 0.0 tells Illustrate to skip the atom entirely.
    """
    return [
        {"pattern": "HETATM-----HOH--", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0},
        {"pattern": "ATOM  -H--------", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0},
        {"pattern": "ATOM  H---------", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0},
        {"pattern": "HETATM-H--------", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0},
        {"pattern": "HETATMH---------", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0},
    ]


def _hetatm_descriptors():
    """Special-case descriptors for well-known ligands, appended at the END.

    These provide distinctive coloring for heme groups (HEM). Because they
    use specific residue name patterns, they override the generic chain
    catch-alls that precede them — but only if the generic patterns haven't
    already matched. In practice, the chain-specific HETATM wildcards will
    match first for chains that have them, so these serve as fallback
    coloring for HEM on chains without explicit HETATM descriptors.
    """
    return [
        {"pattern": "HETATMFE---HEM--", "res_start": 0, "res_end": 9999, "r": 1.0, "g": 0.8, "b": 0.0, "radius": 1.8},
        {"pattern": "HETATM-C---HEM--", "res_start": 0, "res_end": 9999, "r": 1.0, "g": 0.3, "b": 0.3, "radius": 1.6},
        {"pattern": "HETATM-----HEM--", "res_start": 0, "res_end": 9999, "r": 1.0, "g": 0.1, "b": 0.1, "radius": 1.5},
    ]


def build_descriptors(chains, chain_types, style="entity_chain", colors=None, hidden=None, chain_nuc_residues=None, chain_has_hetatm=None, chain_hetatm_residues=None):
    """Build the ordered list of Illustrate atom descriptors for a given style.

    The descriptor list structure is always:
      1. Hide descriptors (water, hydrogens)         — matched first
      2. Per-chain style descriptors (ATOM + HETATM) — the main coloring rules
      3. Special ligand descriptors (HEM, etc.)       — matched last as fallback

    Within each chain's block, descriptors go from most-specific to least-specific.
    For example, in entity_chain style:
      - Carbon atoms (-C-------)  at radius 1.6  (slightly larger for visual weight)
      - Sulfur atoms (-S-------)  at radius 1.8  (larger van der Waals radius)
      - All other    (----------) at radius 1.5  (catch-all for N, O, P, etc.)

    Each ATOM pattern is mirrored by a HETATM pattern for chains that have
    heteroatoms, ensuring modified residues render with the same colors.

    Hidden chains get radius=0.0 descriptors so Illustrate skips their atoms.

    Args:
        chains:               Ordered chain ID list from get_chains_from_pdb()
        chain_types:          Dict of chain ID → "protein"/"nucleic"/"other"
        style:                One of "entity_chain", "protein_dna", "cpk", "one_color"
        colors:               Optional dict of chain ID → [r, g, b] overrides
        hidden:               List of chain IDs to hide (radius 0)
        chain_nuc_residues:   Dict of chain → set of raw 3-char ATOM nucleic residue names
        chain_has_hetatm:     Set of chain IDs with non-water HETATM records
        chain_hetatm_residues: Dict of chain → set of raw 3-char HETATM residue names
    """
    descriptors = _hide_descriptors()
    hidden = set(hidden or [])
    chain_has_hetatm = chain_has_hetatm or set()
    chain_hetatm_residues = chain_hetatm_residues or {}

    if style == "entity_chain":
        # Each chain gets a distinct color from CHAIN_COLORS, cycled if > 8 chains
        for i, chain in enumerate(chains):
            c = chain if chain != " " else "-"
            if chain in hidden:
                descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0})
                if chain in chain_has_hetatm:
                    descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0})
                continue
            if colors and chain in colors:
                color = tuple(colors[chain])
            else:
                color = CHAIN_COLORS[i % len(CHAIN_COLORS)]
            # Carbon gets the full color; other atoms get slightly darkened
            descriptors.append({"pattern": f"ATOM  -C-------{c}", "res_start": 0, "res_end": 9999, "r": color[0], "g": color[1], "b": color[2], "radius": 1.6})
            descriptors.append({"pattern": f"ATOM  -S-------{c}", "res_start": 0, "res_end": 9999, "r": max(color[0] - 0.1, 0), "g": max(color[1] - 0.1, 0), "b": max(color[2] - 0.1, 0), "radius": 1.8})
            descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": max(color[0] - 0.1, 0), "g": max(color[1] - 0.1, 0), "b": max(color[2] - 0.1, 0), "radius": 1.5})
            # Mirror for HETATM (modified residues, ligands on this chain)
            if chain in chain_has_hetatm:
                descriptors.append({"pattern": f"HETATM-C-------{c}", "res_start": 0, "res_end": 9999, "r": color[0], "g": color[1], "b": color[2], "radius": 1.6})
                descriptors.append({"pattern": f"HETATM-S-------{c}", "res_start": 0, "res_end": 9999, "r": max(color[0] - 0.1, 0), "g": max(color[1] - 0.1, 0), "b": max(color[2] - 0.1, 0), "radius": 1.8})
                descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": max(color[0] - 0.1, 0), "g": max(color[1] - 0.1, 0), "b": max(color[2] - 0.1, 0), "radius": 1.5})

    elif style == "protein_dna":
        # Protein chains: uniform color. Nucleic chains: per-atom-role shading.
        # Nucleic acid descriptors are generated per-residue-name so that each
        # specific residue (e.g. " DG", "  C") gets backbone highlighting.
        nuc_residues = chain_nuc_residues or {}
        for i, chain in enumerate(chains):
            c = chain if chain != " " else "-"
            if chain in hidden:
                descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0})
                if chain in chain_has_hetatm:
                    descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0})
                continue
            ct = chain_types.get(chain, "protein")
            if ct == "nucleic":
                base = DNA_COLOR
                if colors and chain in colors:
                    base = tuple(colors[chain])
                phos, bkbn, bases = nuc_shades(base)

                # --- ATOM residues (standard nucleotides) ---
                # For each residue name, emit specific patterns for backbone atoms
                # before the generic catch-all, so backbone gets distinct shading.
                # Pattern anatomy for "ATOM  -P---  C-D":
                #   "ATOM  " = record type (6 chars)
                #   "-P---"  = match P in atom name col 14, wildcards elsewhere (5 chars)
                #   "  C"    = residue name exactly as in PDB cols 18-20 (3 chars)
                #   "-"      = wildcard for col 21 (1 char)
                #   "D"      = chain ID (1 char)
                found_residues = nuc_residues.get(chain, set())
                for raw_res in sorted(found_residues):
                    r = raw_res
                    descriptors.append({"pattern": f"ATOM  -P---{r}-{c}", "res_start": 0, "res_end": 9999, "r": phos[0], "g": phos[1], "b": phos[2], "radius": 1.8})
                    descriptors.append({"pattern": f"ATOM  -O3'-{r}-{c}", "res_start": 0, "res_end": 9999, "r": bkbn[0], "g": bkbn[1], "b": bkbn[2], "radius": 1.5})
                    descriptors.append({"pattern": f"ATOM  -O5'-{r}-{c}", "res_start": 0, "res_end": 9999, "r": bkbn[0], "g": bkbn[1], "b": bkbn[2], "radius": 1.5})
                    descriptors.append({"pattern": f"ATOM  -OP--{r}-{c}", "res_start": 0, "res_end": 9999, "r": bkbn[0], "g": bkbn[1], "b": bkbn[2], "radius": 1.5})
                    # ---' matches any atom with a prime in position 16 (sugar carbons: C1', C2', C3', C4', C5', O2', O4')
                    descriptors.append({"pattern": f"ATOM  ---'-{r}-{c}", "res_start": 0, "res_end": 9999, "r": bkbn[0], "g": bkbn[1], "b": bkbn[2], "radius": 1.6})
                    # Catch-all for remaining atoms in this residue (the nucleobase)
                    descriptors.append({"pattern": f"ATOM  -----{r}-{c}", "res_start": 0, "res_end": 9999, "r": bases[0], "g": bases[1], "b": bases[2], "radius": 1.6})
                # Final catch-all for any ATOM on this chain not matched above
                descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": bases[0], "g": bases[1], "b": bases[2], "radius": 1.5})

                # --- HETATM residues (modified nucleotides: PSU, H2U, 7MG, etc.) ---
                # Many tRNA structures store modified bases as HETATM rather than ATOM.
                # We generate the same backbone-highlighting patterns for each HETATM
                # residue name so modified nucleotides render identically to standard ones.
                het_residues = chain_hetatm_residues.get(chain, set())
                for raw_res in sorted(het_residues):
                    r = raw_res
                    descriptors.append({"pattern": f"HETATM-P---{r}-{c}", "res_start": 0, "res_end": 9999, "r": phos[0], "g": phos[1], "b": phos[2], "radius": 1.8})
                    descriptors.append({"pattern": f"HETATM-O3'-{r}-{c}", "res_start": 0, "res_end": 9999, "r": bkbn[0], "g": bkbn[1], "b": bkbn[2], "radius": 1.5})
                    descriptors.append({"pattern": f"HETATM-O5'-{r}-{c}", "res_start": 0, "res_end": 9999, "r": bkbn[0], "g": bkbn[1], "b": bkbn[2], "radius": 1.5})
                    descriptors.append({"pattern": f"HETATM-OP--{r}-{c}", "res_start": 0, "res_end": 9999, "r": bkbn[0], "g": bkbn[1], "b": bkbn[2], "radius": 1.5})
                    descriptors.append({"pattern": f"HETATM---'-{r}-{c}", "res_start": 0, "res_end": 9999, "r": bkbn[0], "g": bkbn[1], "b": bkbn[2], "radius": 1.6})
                    descriptors.append({"pattern": f"HETATM-----{r}-{c}", "res_start": 0, "res_end": 9999, "r": bases[0], "g": bases[1], "b": bases[2], "radius": 1.6})
                if chain in chain_has_hetatm:
                    descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": bases[0], "g": bases[1], "b": bases[2], "radius": 1.5})
            else:
                # Protein / other chains — simple uniform coloring
                base = PROTEIN_COLOR
                if colors and chain in colors:
                    base = tuple(colors[chain])
                descriptors.append({"pattern": f"ATOM  -C-------{c}", "res_start": 0, "res_end": 9999, "r": base[0], "g": base[1], "b": base[2], "radius": 1.6})
                descriptors.append({"pattern": f"ATOM  -S-------{c}", "res_start": 0, "res_end": 9999, "r": max(base[0] - 0.1, 0), "g": max(base[1] - 0.1, 0), "b": max(base[2] - 0.1, 0), "radius": 1.8})
                descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": max(base[0] - 0.1, 0), "g": max(base[1] - 0.1, 0), "b": max(base[2] - 0.1, 0), "radius": 1.5})
                if chain in chain_has_hetatm:
                    descriptors.append({"pattern": f"HETATM-C-------{c}", "res_start": 0, "res_end": 9999, "r": base[0], "g": base[1], "b": base[2], "radius": 1.6})
                    descriptors.append({"pattern": f"HETATM-S-------{c}", "res_start": 0, "res_end": 9999, "r": max(base[0] - 0.1, 0), "g": max(base[1] - 0.1, 0), "b": max(base[2] - 0.1, 0), "radius": 1.8})
                    descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": max(base[0] - 0.1, 0), "g": max(base[1] - 0.1, 0), "b": max(base[2] - 0.1, 0), "radius": 1.5})

    elif style == "cpk":
        # Color by element (Corey-Pauling-Koltun scheme)
        for chain in chains:
            c = chain if chain != " " else "-"
            if chain in hidden:
                descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0})
                if chain in chain_has_hetatm:
                    descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0})
                continue
            for elem, color in CPK_COLORS.items():
                if elem == "H":
                    continue
                # Element symbol is left-justified and padded with "-" to 2 chars,
                # matching PDB atom name column 14-15 (e.g. "C-", "FE", "ZN")
                pad = elem.ljust(2, "-")[:2]
                descriptors.append({"pattern": f"ATOM  -{pad}------{c}", "res_start": 0, "res_end": 9999, "r": color[0], "g": color[1], "b": color[2], "radius": CPK_RADII.get(elem, CPK_DEFAULT_RADIUS)})
                if chain in chain_has_hetatm:
                    descriptors.append({"pattern": f"HETATM-{pad}------{c}", "res_start": 0, "res_end": 9999, "r": color[0], "g": color[1], "b": color[2], "radius": CPK_RADII.get(elem, CPK_DEFAULT_RADIUS)})
            descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": CPK_DEFAULT[0], "g": CPK_DEFAULT[1], "b": CPK_DEFAULT[2], "radius": CPK_DEFAULT_RADIUS})
            if chain in chain_has_hetatm:
                descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": CPK_DEFAULT[0], "g": CPK_DEFAULT[1], "b": CPK_DEFAULT[2], "radius": CPK_DEFAULT_RADIUS})

    elif style == "one_color":
        # Uniform color for the entire structure
        base = (0.65, 0.65, 0.95)
        if colors and "__one" in colors:
            base = tuple(colors["__one"])
        for chain in chains:
            c = chain if chain != " " else "-"
            if chain in hidden:
                descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0})
                if chain in chain_has_hetatm:
                    descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": 0.5, "g": 0.5, "b": 0.5, "radius": 0.0})
                continue
            descriptors.append({"pattern": f"ATOM  -C-------{c}", "res_start": 0, "res_end": 9999, "r": base[0], "g": base[1], "b": base[2], "radius": 1.6})
            descriptors.append({"pattern": f"ATOM  -S-------{c}", "res_start": 0, "res_end": 9999, "r": max(base[0] - 0.1, 0), "g": max(base[1] - 0.1, 0), "b": max(base[2] - 0.1, 0), "radius": 1.8})
            descriptors.append({"pattern": f"ATOM  ---------{c}", "res_start": 0, "res_end": 9999, "r": max(base[0] - 0.1, 0), "g": max(base[1] - 0.1, 0), "b": max(base[2] - 0.1, 0), "radius": 1.5})
            if chain in chain_has_hetatm:
                descriptors.append({"pattern": f"HETATM-C-------{c}", "res_start": 0, "res_end": 9999, "r": base[0], "g": base[1], "b": base[2], "radius": 1.6})
                descriptors.append({"pattern": f"HETATM-S-------{c}", "res_start": 0, "res_end": 9999, "r": max(base[0] - 0.1, 0), "g": max(base[1] - 0.1, 0), "b": max(base[2] - 0.1, 0), "radius": 1.8})
                descriptors.append({"pattern": f"HETATM---------{c}", "res_start": 0, "res_end": 9999, "r": max(base[0] - 0.1, 0), "g": max(base[1] - 0.1, 0), "b": max(base[2] - 0.1, 0), "radius": 1.5})

    descriptors.extend(_hetatm_descriptors())
    return descriptors

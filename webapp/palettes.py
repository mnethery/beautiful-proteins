"""
Color palettes and element/residue lookup tables used by descriptor generation.

All RGB values are Illustrate-style floats in the range 0.0-1.0, not 0-255.
"""

# Default per-chain colors for the "Entity Chain" style (cycled by chain index).
CHAIN_COLORS = [
    (0.65, 0.65, 0.95),
    (0.95, 0.65, 0.65),
    (0.65, 0.95, 0.65),
    (0.95, 0.95, 0.65),
    (0.95, 0.65, 0.95),
    (0.65, 0.95, 0.95),
    (0.85, 0.75, 0.65),
    (0.75, 0.85, 0.75),
]

# Standard and modified nucleic acid residue names found in PDB files.
# Used to classify chains as "nucleic" vs "protein" when parsing.
NUCLEIC_RESIDUES = {
    "DA", "DT", "DC", "DG", "DU", "DI",       # DNA
    "A", "T", "C", "G", "U", "I",              # RNA
    "ADE", "THY", "CYT", "GUA", "URA",         # Long-form names
}

# Default colors for the "Protein/DNA" style
PROTEIN_COLOR = (0.30, 0.53, 0.84)   # Steel blue
DNA_COLOR = (0.92, 0.72, 0.90)       # Soft pink


def nuc_shades(base):
    """
    Derive three shades from a single base color for nucleic acid rendering.

    The Protein/DNA style highlights the structural hierarchy within each
    nucleotide by assigning different shades to different chemical roles:

      - Phosphorus atoms:  Darkest/warmest — boosted red, suppressed green/blue
      - Backbone atoms:    Mid-tone — slightly boosted red, moderate suppression
        (O3', O5', OP*, sugar carbons with prime in name)
      - Base atoms:        Lightest/coolest — gently brightened across all channels

    This creates a visual gradient: hot phosphorus → warm backbone → cool bases,
    giving depth and structural readability even in a space-filling representation.

    Returns (phosphorus, backbone, base_atoms) as (r, g, b) tuples, all 0.0-1.0.
    """
    r, g, b = base
    phosphorus = (min(r * 1.2, 1.0), max(g * 0.65, 0.0), max(b * 0.65, 0.0))
    backbone = (min(r * 1.1, 1.0), max(g * 0.75, 0.0), max(b * 0.75, 0.0))
    bases = (min(r * 1.05, 1.0), min(g * 1.1, 1.0), min(b * 1.15, 1.0))
    return phosphorus, backbone, bases


# CPK coloring — standard element-based color scheme
CPK_COLORS = {
    "C": (0.6, 0.6, 0.6),
    "N": (0.3, 0.3, 0.95),
    "O": (0.95, 0.3, 0.3),
    "S": (0.95, 0.85, 0.2),
    "P": (0.95, 0.6, 0.1),
    "H": (0.8, 0.8, 0.8),
    "FE": (0.85, 0.5, 0.0),
    "ZN": (0.5, 0.5, 0.7),
    "MG": (0.0, 0.7, 0.0),
    "CA": (0.3, 0.7, 0.3),
}
CPK_DEFAULT = (0.95, 0.5, 0.95)  # Fallback for unlisted elements

CPK_RADII = {"C": 1.6, "N": 1.5, "O": 1.5, "S": 1.8, "P": 1.8, "H": 1.0, "FE": 1.8, "ZN": 1.5, "MG": 1.5, "CA": 1.5}
CPK_DEFAULT_RADIUS = 1.5

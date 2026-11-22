#!/usr/bin/env python3
"""Deck-only figure assets.

The manuscript's Figure 2 caption says "48-rule inference engine" but the
committed figures/fig2_fis_architecture.png is still drawn with 42. The deck
carries its own copy at the manuscript's count rather than changing a figure
the manuscript embeds.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

import generate_figures as G

if __name__ == '__main__':
    p = G.fig2_fis_architecture(n_rules=48, outdir=HERE, stem='fig2_fis_architecture_48')
    print('wrote', p)

#!/usr/bin/env python3
"""Quick NHANES analysis report generation."""
import sys, os
sys.path.insert(0, '/opt/data/fuzzy-audiogram')
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Load
df = pd.read_sas('/opt/data/P_AUX.xpt', format='xport', encoding='utf-8')
print(f"Loaded {len(df)} participants from NHANES P_AUX (2017-2020)")

# Identify threshold columns
all_cols = list(df.columns)
print(f"Total columns: {len(all_cols)}")
audiometry_cols = [c for c in all_cols if any(x in c.upper() for x in ['AUD', 'AUX', 'EAR', 'THR'])]
print(f"Audiometry-related: {audiometry_cols[:20]}")

# Extract thresholds: find the actual column pattern
left_threshold_cols = sorted([c for c in all_cols if 'RO' in c.upper() and 'C' in c.upper()])
right_threshold_cols = sorted([c for c in all_cols if 'LO' in c.upper() and 'C' in c.upper()])
print(f"Left ear threshold cols: {left_threshold_cols}")
print(f"Right ear threshold cols: {right_threshold_cols}")

if not left_threshold_cols:
    # Try other patterns
    for c in all_cols[:50]:
        print(f"  {c}: {df[c].dtype}, first val={df[c].iloc[0] if len(df) > 0 else 'N/A'}")

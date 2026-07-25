#!/usr/bin/env python3
"""
demo.py — Fuzzy Audiogram Demo
Quick demonstration of all framework features.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fuzzy_audiogram.core import classify_audiogram, compare_fuzzy_vs_crisp, demo_cases
from fuzzy_audiogram import __version__

print("=" * 70)
print(f"  FUZZY AUDIOGRAM FRAMEWORK v{__version__}")
print("=" * 70)

# 1. Single patient classification
print("\n\n📋 CASE 1: Chidi (35-year-old, borderline loss)")
print("-" * 50)
chidi_left = [20, 22, 25, 28, 30, 35, 28, 22]
result = classify_audiogram(chidi_left)
print(f"   PTA-4:          {result['pt4a']} dB (crisp label: Mild)")
print(f"   Fuzzy FAI:      {result['fai_score']}")
print(f"   Fuzzy Label:    {result['fai_label']}")
print(f"   Configuration:  {result['configuration_label']}")
for cat, val in result['threshold_memberships'].items():
    if val > 0:
        print(f"   ╰ {cat.replace('_', ' ').title()}: {val:.0%}")

# 2. Ngozi (noise-induced hearing loss)
print("\n\n📋 CASE 2: Ngozi (factory worker, NIHL)")
print("-" * 50)
ngozi_left = [10, 10, 12, 20, 35, 50, 45, 30]
result2 = classify_audiogram(ngozi_left)
print(f"   PTA-4:          {result2['pt4a']} dB")
print(f"   Fuzzy FAI:      {result2['fai_score']}")
print(f"   Fuzzy Label:    {result2['fai_label']}")
print(f"   Configuration:  {result2['configuration_label']}")
print(f"   Notch Depth:    {result2['features']['notch_depth']:.1f} dB at 4 kHz")

# 3. Emeka (presbycusis)
print("\n\n📋 CASE 3: Emeka (70-year-old, presbycusis)")
print("-" * 50)
emeka_left = [15, 20, 25, 35, 45, 55, 65, 70]
result3 = classify_audiogram(emeka_left)
print(f"   PTA-4:          {result3['pt4a']} dB")
print(f"   Fuzzy FAI:      {result3['fai_score']}")
print(f"   Fuzzy Label:    {result3['fai_label']}")
print(f"   Configuration:  {result3['configuration_label']}")
print(f"   Slope:          {result3['features']['slope']:.1f} dB")

# 4. Fuzzy vs Crisp comparison
print("\n\n📊 FUZZY vs CRISP CLASSIFICATION")
print("-" * 50)
df = compare_fuzzy_vs_crisp([15, 20, 24, 25, 26, 27, 30, 40, 41, 55, 56, 70, 71, 90, 91])
print(df.to_string(index=False))

print("\n\n✅ Demo complete!")

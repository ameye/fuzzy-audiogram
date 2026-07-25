<div align="center">

# 🧠 Fuzzy Audiogram

### A Fuzzy Logic Framework for Audiometric Classification

*Preserving diagnostic gradation lost to crisp dB thresholds*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/ameye/fuzzy-audiogram)
[![arXiv coming soon](https://img.shields.io/badge/arXiv-coming_soon-red.svg)]()

</div>

---

## 🩺 Why This Matters

Audiogram interpretation uses **crisp dB boundaries** that don't reflect biological reality:

| Severity | dB HL |
|----------|-------|
| Normal | ≤ 25 |
| Mild | 26–40 |
| Moderate | 41–55 |
| Moderately Severe | 56–70 |
| Severe | 71–90 |
| Profound | ≥ 91 |

A patient with **25 dB** → classified *"Normal"*. A patient with **26 dB** → classified *"Mild"*.

That **1 dB difference is clinically meaningless**, yet the classification jumps. This framework replaces those crisp boundaries with **overlapping fuzzy membership functions**, preserving the gradation that actually exists in clinical reality.

> A patient with PTA = 24 dB is **60% Normal and 67% Mild** — not a forced binary label.

---

## ✨ Features

- **Overlapping trapezoidal membership functions** — severity, slope, notch depth, asymmetry all modelled as continuous fuzzy sets
- **Mamdani fuzzy inference system** — 48 expert-derived rules covering severity, configuration, asymmetry, and mixed-loss patterns
- **Fuzzy Audiometric Index (FAI)** — a continuous 0–100 score replacing discrete severity categories
- **Configuration classification** — flat, sloping, steeply sloping, precipitous, notched, rising
- **Asymmetry detection** — inter-aural differences on a graded spectrum
- **Notch detection** — Carhart notch (noise-induced) and cookie-bite patterns
- **Temporal tracking** — monitor FAI trajectories across serial audiograms for ototoxicity or progression
- **NHANES validation** — validated on 5,147 participants from NHANES 2017–2020
- **ML comparators** — XGBoost and Random Forest benchmarks against the fuzzy system

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/ameye/fuzzy-audiogram.git
cd fuzzy-audiogram

# Install dependencies
pip install -e .

# Run the demo
python scripts/demo.py
```

### Basic Usage

```python
from fuzzy_audiogram.core import classify_audiogram

# Chidi's audiogram [250, 500, 1k, 2k, 3k, 4k, 6k, 8k Hz]
chidi_left = [20, 22, 25, 28, 30, 35, 28, 22]

result = classify_audiogram(chidi_left)
print(f"FAI Score: {result['fai_score']}")        # e.g., 26.3
print(f"FAI Label: {result['fai_label']}")         # "Mild" 
print(f"PTA-4: {result['pt4a']} dB")               # 27.5 dB

# But look — the membership degrees tell the real story:
print(f"Normal: {result['threshold_memberships']['normal']:.1%}")  # 25%
print(f"Mild:   {result['threshold_memberships']['mild']:.1%}")    # 100%

# By crisp rules, PTA=27.5 → "Mild Loss"
# By fuzzy, FAI=26.3 on a 0-100 continuous scale
```

### Compare Fuzzy vs Crisp

```python
from fuzzy_audiogram.core import compare_fuzzy_vs_crisp

df = compare_fuzzy_vs_crisp(pta_values=[15, 20, 24, 25, 26, 30, 40, 55])
print(df)
```

| PTA | Crisp | Fuzzy | FAI | Normal μ | Mild μ |
|-----|-------|-------|-----|----------|--------|
| 24 | Normal | Mild | 21.5 | 0.60 | 0.67 |
| 25 | Normal | Mild | 23.1 | 0.50 | 0.83 |
| 26 | Mild | Mild | 24.6 | 0.40 | 1.00 |

---

## 📊 Clinical Cases

| Case | Description | FAI | Configuration |
|------|-------------|-----|---------------|
| 1 | Borderline Normal-Mild (PTA 27.5 dB) | 26.3 | — |
| 2 | Noise-Induced (Carhart notch at 4 kHz) | 19.5 | Precipitous |
| 3 | Presbycusis (high-frequency sloping) | 30.0 | Sloping |
| 4 | Asymmetric loss (left vs right ear) | 42.2 | — |
| 5 | Otosclerosis (Carhart notch at 2 kHz) | 47.3 | Sloping |

---

## 🏗️ Project Structure

```
fuzzy-audiogram/
├── fuzzy_audiogram/          # Python package
│   ├── __init__.py           # Package init with public API
│   ├── core.py               # Main FIS: membership functions, classifier, FAI
│   ├── rules.py              # 48 expert-derived fuzzy rules
│   ├── data.py               # NHANES data loader
│   ├── viz.py                # Visualization (membership plots, audiograms, comparisons)
│   ├── validate.py           # Comparators (XGBoost, RF) + metrics
│   └── temporal.py           # Temporal tracking for serial audiograms
├── data/
│   ├── raw/                  # NHANES .xpt files (not tracked by git)
│   └── output/               # Generated plots and reports
├── notebooks/                # Jupyter notebooks for exploration
├── scripts/
│   ├── demo.py               # Quick demo of all features
│   └── nhanes_analysis.py    # Full NHANES validation pipeline
├── tests/                    # Unit tests
├── MANUSCRIPT_OUTLINE.md     # Full IMRaD manuscript outline
├── README.md
├── LICENSE                   # MIT
├── pyproject.toml
└── .gitignore
```

---

## 📚 Manuscript

A full IMRaD manuscript outline is available in [`MANUSCRIPT_OUTLINE.md`](MANUSCRIPT_OUTLINE.md), targeting:

- **International Journal of Audiology**
- **Biomedical Signal Processing and Control**
- **Journal of the American Academy of Audiology**
- **Computers in Biology and Medicine**
- **IEEE Transactions on Neural Systems and Rehabilitation Engineering**

---

## 📖 Citation

If you use this framework in your research, please cite:

```bibtex
@software{ameye2025fuzzy,
  title = {Fuzzy Audiogram: A Fuzzy Logic Framework for Audiometric Classification},
  author = {Ameye, Sanyaolu},
  year = {2025},
  url = {https://github.com/ameye/fuzzy-audiogram}
}
```

---

## 🤝 Contributing

Contributions are welcome! This is an open research project at the intersection of audiology and computational intelligence. Areas for contribution:

- Additional NHANES cycles (1999–2016) for population validation
- Bone conduction rules for sensorineural vs conductive classification
- Clinical validation datasets from audiology departments
- Integration with OAE and speech audiometry data
- Interactive dashboard (Streamlit)

---

## 📬 Contact

**Sanyaolu Ameye** — sanyaameye@hotmail.com

---

<div align="center">
<i>Built with ❤️ for better hearing healthcare</i>
</div>

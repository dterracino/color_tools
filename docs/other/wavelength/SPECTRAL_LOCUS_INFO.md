# CIE 1931 Spectral Locus Documentation  
**Wavelength Range:** 380–700 nm  
**Coordinates:** CIE 1931 2° chromaticity (x, y)

## Overview
The **spectral locus** is the parametric curve traced in the **CIE 1931 xy chromaticity diagram** by monochromatic light across the visible spectrum. Each wavelength λ corresponds to a chromaticity coordinate (x(λ), y(λ)), derived from the CIE 1931 2° Color-Matching Functions.

This document provides data sources, computation formulas, and a full spectral-locus dataset from 380–700 nm at 1 nm resolution.

---

## Data Sources

### CVRL (Colour & Vision Research Laboratory)
The definitive machine-readable source for the **CIE 1931 2° XYZ CMFs**.  
The dataset provides values of **X̅(λ), Y̅(λ), Z̅(λ)** sampled at 1 nm.

Chromaticity is computed as:

```
x = X / (X + Y + Z)
y = Y / (X + Y + Z)
```

### R “photobiology” Dataset (`ciexyzCC2.spct`)
This dataset contains **normalized** chromaticity values x, y, z derived from CIE XYZ functions.  
Useful when chromaticity data is needed directly.

---

## Chromaticity Computation Formula
Given tristimulus values X(λ), Y(λ), Z(λ):

```math
x(λ) = X / (X + Y + Z)
y(λ) = Y / (X + Y + Z)
z(λ) = Z / (X + Y + Z)
```

For the xy chromaticity diagram, only x and y are used.

---

## Example Python Code

```python
import csv

spectral_locus = []

with open("ciexyz31.csv", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        lam = float(row["lambda"])
        if 380 <= lam <= 700:
            X = float(row["X"])
            Y = float(row["Y"])
            Z = float(row["Z"])
            denom = X + Y + Z
            if denom > 0:
                x = X / denom
                y = Y / denom
                spectral_locus.append((lam, x, y))

with open("spectral_locus_380_700.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["wavelength_nm", "x", "y"])
    writer.writerows(spectral_locus)
```

---

## Spectral Locus Dataset (380–700 nm)
The following table is computed directly from the CIE 1931 2° observer XYZ CMFs.  
Values are given per-nanometer.

**See the CSV file included below.**

---

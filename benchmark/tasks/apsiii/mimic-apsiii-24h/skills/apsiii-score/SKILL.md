---
name: apsiii-score
description: Calculate APACHE III (Acute Physiology Score III) for ICU patients. Use for mortality prediction, severity stratification, case-mix adjustment, or risk-adjusted outcome comparisons.
tier: validated
category: clinical
---

# APACHE III (APS III) Score Calculation

The Acute Physiology Score III (APS III) is the physiological component of APACHE III (Knaus 1991). Calculated from the **worst values** in the first 24 hours of ICU stay; "worst" = furthest from a defined normal reference. Total APS-III ranges 0–252 across 16 components.

## M4Bench Use

In M4Bench, target concept tables listed in the task configuration are removed or unavailable in the agent database. Use this skill as procedural guidance and derive the requested output from available source or intermediate tables; do not rely on a precomputed target table or bundled SQL script.

## When to Use This Skill

- Hospital mortality prediction
- Severity stratification and risk adjustment
- Case-mix adjustment for benchmarking
- Comparing outcomes across ICUs or time periods
- Research cohort severity matching

## Scoring Tables

Source: van Valburg MK, et al. *Eur J Anaesthesiol*. 2024;41(2):105–113 (Suppl. 2), reproducing the APACHE III APS calculation.

### Heart Rate (bpm) — value furthest from 75
| Value | Points |
|-------|--------|
| ≤39 | 8 |
| 40–49 | 5 |
| 50–99 | 0 |
| 100–109 | 1 |
| 110–119 | 5 |
| 120–139 | 7 |
| 140–154 | 13 |
| ≥155 | 17 |

### Mean Blood Pressure (mmHg) — value furthest from 90
| Value | Points |
|-------|--------|
| ≤39 | 23 |
| 40–59 | 15 |
| 60–69 | 7 |
| 70–79 | 6 |
| 80–99 | 0 |
| 100–119 | 4 |
| 120–129 | 7 |
| 130–139 | 9 |
| ≥140 | 10 |

### Temperature (°C, core) — value furthest from 38; add 1°C to axillary before scoring
| Value | Points |
|-------|--------|
| ≤32.9 | 20 |
| 33.0–33.4 | 16 |
| 33.5–33.9 | 13 |
| 34.0–34.9 | 8 |
| 35.0–35.9 | 2 |
| 36.0–39.9 | 0 |
| ≥40.0 | 4 |

### Respiratory Rate (breaths/min) — value furthest from 19
| Value | Points |
|-------|--------|
| ≤5 | 17 |
| 6–11 | 8 |
| 12–13 | 7 |
| 14–24 | 0 |
| 25–34 | 6 |
| 35–39 | 9 |
| 40–49 | 11 |
| ≥50 | 18 |

**Ventilation exception**: For ventilated patients, no points are assigned for respiratory rates of **6–12** (override the standard table). The override does NOT apply to RR ≤5 (apnea remains 17) or RR ≥13.

### Oxygenation (one of two paths)

**PaO₂ (mmHg)** — used for non-intubated patients OR intubated patients with FiO₂ <0.5
| Value | Points |
|-------|--------|
| ≤49 | 15 |
| 50–69 | 5 |
| 70–79 | 2 |
| ≥80 | 0 |

**Alveolar–arterial Oxygen Gradient (A-aDO₂)** — used for intubated patients with FiO₂ ≥0.5
| Value | Points |
|-------|--------|
| <100 | 0 |
| 100–249 | 7 |
| 250–349 | 9 |
| 350–499 | 11 |
| ≥500 | 14 |

### Hematocrit (%) — value furthest from 45.5
| Value | Points |
|-------|--------|
| ≤40.9 | 3 |
| 41.0–49.9 | 0 |
| ≥50.0 | 3 |

### White Blood Count (×10⁹/L)
| Value | Points |
|-------|--------|
| <1.0 | 19 |
| 1.0–2.9 | 5 |
| 3.0–19.9 | 0 |
| 20.0–24.9 | 1 |
| ≥25.0 | 5 |

### Creatinine (mg/dL)

**Acute Renal Failure (ARF) definition**: creatinine ≥1.5 mg/dL AND urine output <410 mL/day AND no chronic kidney disease (operationalized in MIMIC as ICD-9 585.4–585.6 / ICD-10 N18.4–N18.6).

**Without ARF**:
| Value | Points |
|-------|--------|
| ≤0.4 | 3 |
| 0.5–1.4 | 0 |
| 1.5–1.94 | 4 |
| ≥1.95 | 7 |

**With ARF**:
| Value | Points |
|-------|--------|
| 0–1.4 | 0 |
| ≥1.5 | 10 |

### Urine Output (mL/day)
| Value | Points |
|-------|--------|
| ≤399 | 15 |
| 400–599 | 8 |
| 600–899 | 7 |
| 900–1499 | 5 |
| 1500–1999 | 4 |
| 2000–3999 | 0 |
| ≥4000 | 1 |

### Blood Urea Nitrogen (mg/dL)
| Value | Points |
|-------|--------|
| ≤16.9 | 0 |
| 17.0–19.9 | 2 |
| 20.0–39.9 | 7 |
| 40.0–79.9 | 11 |
| ≥80.0 | 12 |

### Sodium (mEq/L) — value furthest from 145.5
| Value | Points |
|-------|--------|
| ≤119 | 3 |
| 120–134 | 2 |
| 135–154 | 0 |
| ≥155 | 4 |

### Albumin (g/dL) — value furthest from 3.5
| Value | Points |
|-------|--------|
| ≤1.9 | 11 |
| 2.0–2.4 | 6 |
| 2.5–4.4 | 0 |
| ≥4.5 | 4 |

### Bilirubin (mg/dL)
| Value | Points |
|-------|--------|
| ≤1.9 | 0 |
| 2.0–2.9 | 5 |
| 3.0–4.9 | 6 |
| 5.0–7.9 | 8 |
| ≥8.0 | 16 |

### Glucose (mg/dL) — value furthest from 130
| Value | Points |
|-------|--------|
| ≤39 | 8 |
| 40–59 | 9 |
| 60–199 | 0 |
| 200–349 | 3 |
| ≥350 | 5 |

### Acid–Base Abnormalities (pH × pCO₂ interaction; pCO₂ in mmHg)

| pH \ pCO₂ | <25 | 25–<30 | 30–<35 | 35–<40 | 40–<45 | 45–<50 | ≥50 |
|---|---|---|---|---|---|---|---|
| <7.20 | 12 | 12 | 12 | 12 | 12 | 12 | 4 |
| 7.20–<7.30 | 9 | 9 | 6 | 6 | 3 | 3 | 2 |
| 7.30–<7.35 | 9 | 9 | 0 | 0 | 0 | 1 | 1 |
| 7.35–<7.45 | 5 | 5 | 0 | 0 | 0 | 1 | 1 |
| 7.45–<7.50 | 5 | 5 | 0 | 2 | 2 | 12 | 12 |
| 7.50–<7.60 | 3 | 3 | 3 | 3 | 12 | 12 | 12 |
| ≥7.60 | 0 | 3 | 3 | 3 | 12 | 12 | 12 |

### Glasgow Coma Score (GCS) — interaction matrix

For sedated/anaesthetised patients, use the GCS from the 12 hours pre-ICU when assessable. If no assessable GCS is documented, assign 0 points. If verbal cannot be assessed (e.g., intubation), use clinical judgment to assign verbal score: alert/oriented = 5, confused = 3, nonresponsive = 1.

**Eyes open spontaneously (4) or to stimulation (2,3)**:

| Motor ↓ \ Verbal → | Oriented (5) | Confused (4) | Inappropriate / sounds (3,2) | None (1) |
|---|---|---|---|---|
| Obeys (6) | 0 | 3 | 10 | 15 |
| Localises pain (5) | 3 | 8 | 13 | 15 |
| Flexion (4,3) | 3 | 13 | 24 | 24 |
| Decerebrate / no response (2,1) | 3 | 13 | 29 | 29 |

**Eyes do not open (1)**:

| Motor ↓ \ Verbal → | Oriented (5) | Confused (4) | Inappropriate / sounds (3,2) | None (1) |
|---|---|---|---|---|
| Obeys (6) | — | — | — | 16 |
| Localises pain (5) | — | — | — | 16 |
| Flexion (4,3) | — | — | 24 | 33 |
| Decerebrate / no response (2,1) | — | — | 29 | 48 |

(Cells marked "—" are clinically unlikely combinations per van Valburg 2024 Suppl.; assign no score.)

## Critical Implementation Notes

1. **Worst Value Definition**: For variables with a defined normal reference (HR, MBP, temp, RR, hematocrit, sodium, albumin, glucose), worst = max(|x_min − ref|, |x_max − ref|). For monotonic variables (BUN, bilirubin, urine output), worst = the value yielding the higher score per its table. Ties broken in favor of the higher score.

2. **Oxygenation routing**: Use PaO₂ for non-intubated patients OR intubated patients with FiO₂ <0.5. Use A-aDO₂ for intubated patients with FiO₂ ≥0.5. Arterial specimens only.

3. **Mortality probability** (Johnson 2015 calibration):
   ```
   apsiii_prob = 1 / (1 + exp(-(-4.4360 + 0.04726 · apsiii)))
   ```

## References

- Knaus WA, Wagner DP, Draper EA, et al. "The APACHE III prognostic system: Risk prediction of hospital mortality for critically ill hospitalized adults." Chest. 1991;100(6):1619-1636.
- Johnson AEW. "Mortality prediction and acuity assessment in critical care." University of Oxford. 2015. (Calibration equation source)
- van Valburg MK, et al. "Predicting 30-day mortality in intensive care unit patients with ischaemic stroke and intracerebral haemorrhage." Eur J Anaesthesiol. 2024;41(2):105-113. (Suppl. 2 — APACHE-III APS calculation reference table)

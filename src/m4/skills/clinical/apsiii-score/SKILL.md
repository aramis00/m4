---
name: apsiii-score
description: Calculate APACHE III (Acute Physiology Score III) for ICU patients. Use for mortality prediction, severity stratification, case-mix adjustment, or risk-adjusted outcome comparisons.
tier: validated
category: clinical
---

# APACHE III (APS III) Score Calculation

The Acute Physiology Score III (APS III) is the physiological component of APACHE III (Knaus 1991), scoring 0–252 across 16 physiologic derangements in the first 24 hours of ICU stay. Full APACHE III adds age (0–24) and chronic-health (0–23) points for a maximum of ~299; this skill computes APS-III only and supports hospital-mortality probability estimates.

## When to Use This Skill

- Hospital mortality prediction
- Severity stratification and risk adjustment
- Case-mix adjustment for benchmarking
- Comparing outcomes across ICUs or time periods
- Research cohort severity matching

## Score Components (First 24 Hours)

APS-III uses **worst values** from the first 24 hours of ICU stay, where "worst" = furthest from a predefined normal reference (not simply min or max). Total APS-III is the sum of all 16 component scores.

| Variable | Scoring | Point range |
|----------|---------|--------|
| Heart rate | worst-from-75 bpm | 0–17 |
| Mean BP | worst-from-90 mmHg | 0–23 |
| Temperature | worst-from-38°C | 0–20 |
| Respiratory rate | worst-from-19/min (vented exception: RR 6–12 → 0) | 0–18 |
| Oxygenation | PaO₂ if non-vented or FiO₂ <50%; A-aDO₂ if vented and FiO₂ ≥50% | 0–15 |
| Hematocrit | worst-from-45.5 % | 0–3 |
| WBC | worst-from-11.5 ×10⁹/L | 0–19 |
| Creatinine | worst-from-1.0 mg/dL (modified by ARF flag) | 0–10 |
| BUN | mg/dL, monotonic | 0–12 |
| Sodium | worst-from-145.5 mEq/L | 0–4 |
| Albumin | worst-from-3.5 g/dL | 0–11 |
| Bilirubin | mg/dL, monotonic | 0–16 |
| Glucose | worst-from-130 mg/dL | 0–9 |
| Acid-base | pH × PaCO₂ interaction grid | 0–12 |
| GCS | eye × verbal × motor matrix; 0 if sedated/unable to assess | 0–48 |
| Urine output | mL over first 24h, monotonic | 0–15 |

## Critical Implementation Notes

1. **Worst-from-normal**: For variables with a defined normal reference, worst = max(|x_min − ref|, |x_max − ref|). For monotonic variables (BUN, bilirubin), worst = max value. Ties broken in favor of the higher score.

2. **Acute Renal Failure (ARF) modifier**: ARF = creatinine ≥1.5 mg/dL AND urine output <410 mL/day AND no chronic kidney disease. Triggers the high-creatinine penalty.

3. **Oxygenation routing**: PaO₂ for non-ventilated patients with FiO₂ <50%; A-aDO₂ for invasively ventilated patients with FiO₂ ≥50%. Arterial specimens only.

4. **GCS**: Complex eye × verbal × motor interaction matrix per Knaus. Patients flagged as unable to assess (e.g., sedation/intubation) default to 0.

5. **Mortality probability**: Logistic calibration from Johnson 2015:

   ```
   apsiii_prob = 1 / (1 + exp(-(-4.4360 + 0.04726 · apsiii)))
   ```

## Dataset Availability

### MIMIC-IV

APS-III is available as a pre-computed derived table. Materialize with:

```bash
m4 init-derived mimic-iv          # All derived tables including apsiii
```

The derived table provides the total score, predicted mortality probability, and all 16 component sub-scores (`hr_score`, `mbp_score`, `temp_score`, `resp_rate_score`, `pao2_aado2_score`, `hematocrit_score`, `wbc_score`, `creatinine_score`, `uo_score`, `bun_score`, `sodium_score`, `albumin_score`, `bilirubin_score`, `glucose_score`, `acidbase_score`, `gcs_score`).

BigQuery users already have this table via `physionet-data.mimiciv_derived.apsiii` without running `init-derived`.

**MIMIC-IV implementation details:**
- **Source tables**: Builds from `first_day_vitalsign`, `first_day_lab`, `first_day_urine_output`, `first_day_gcs` (intermediate derived tables) plus `bg` for arterial blood gases.
- **Ventilation classification**: `mimiciv_derived.ventilation` filtered to `ventilation_status = 'InvasiveVent'`.
- **ARF chronic-renal exclusion**: ICD-9 585.4–585.6 / ICD-10 N18.4–N18.6 (CKD stage 4 through ESRD).
- **GCS handling**: Patients flagged in `first_day_gcs.gcs_unable = 1` (e.g., intubated, sedated) default to score 0.

**MIMIC-IV limitations:**
- **Axillary-temperature correction** not implemented; per Knaus, axillary measurements should be increased by 1°C, but specimen site is not consistently recorded in MIMIC.
- **Urine output** is summed over available hours, not extrapolated to 24h. For stays <24h, this may overestimate severity.
- Follows MIT-LCP/mimic-code canonical implementation.

### eICU

APS-III is **not pre-computed** in eICU (only APACHE IV is provided in `apachepatientresult`). It must be calculated from raw tables.

| Component | eICU Source |
|-----------|-------------|
| Heart rate, MBP, Temp, RR | `vitalperiodic` / `vitalaperiodic` |
| PaO₂, A-aDO₂, pH, PaCO₂ | `lab` |
| FiO₂, ventilation status | `respiratorycare` / `respiratorycharting` |
| Hematocrit, WBC, Cr, BUN, Na, albumin, bilirubin, glucose | `lab` (text `labname`, not numeric itemid) |
| Urine output | `intakeoutput` |
| GCS | `nursecharting` |

**eICU limitations:**
- **No precomputed APS-III**; only APACHE IV is provided. APACHE IV uses different cutoffs and components, so the APACHE IV `apachescore` cannot be used as a substitute.
- **ARF chronic-renal exclusion**: `diagnosis` table uses free-text `diagnosisstring` with variably populated `icd9code` across the 208 sites. ICD-based CKD detection may have incomplete capture; consider supplementing with `pasthistory`.
- **Ventilation detection**: Different logic than MIMIC — uses `respiratorycare` and `respiratorycharting` tables rather than procedural events.

See `scripts/apsiii.sql` for the full MIMIC-IV implementation. An eICU script is not yet available.

## References

- Knaus WA, Wagner DP, Draper EA, et al. "The APACHE III prognostic system: Risk prediction of hospital mortality for critically ill hospitalized adults." Chest. 1991;100(6):1619-1636.
- Johnson AEW. "Mortality prediction and acuity assessment in critical care." University of Oxford. 2015. (Calibration equation source)

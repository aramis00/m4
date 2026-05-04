---
name: baseline-creatinine
description: Estimate baseline serum creatinine for AKI assessment. Use for KDIGO staging, AKI research, or renal function baseline establishment.
tier: validated
category: clinical
---

# Baseline Creatinine Estimation

Estimates the patient's baseline (pre-illness) serum creatinine, which is critical for accurate AKI staging. The true baseline is often unknown; when no preadmission outpatient creatinine is available (as in MIMIC), this skill applies the hierarchical fallback approach derived from the ADQI 2004 / KDIGO 2012 RIFLE-era consensus.

## When to Use This Skill

- KDIGO AKI staging (requires baseline comparison)
- AKI research cohorts
- Chronic kidney disease identification
- Renal function trajectory analysis

## Baseline Determination Rules

The baseline creatinine is determined hierarchically:

1. **If lowest admission creatinine ≤ 1.1 mg/dL**: Use the lowest value (assumed normal)
2. **If patient has CKD diagnosis**: Use the lowest admission value (even if elevated)
3. **Otherwise**: Estimate baseline by back-calculating from assumed eGFR = 75 mL/min/1.73m²

## Imputation Equations

Two race-free imputation equations are computed in parallel for step 3. The hierarchy logic (steps 1–3) is identical between the two outputs; only the imputation equation differs.

### Default: race-free MDRD-IV → `mdrd_est`, `scr_baseline`

Implements MDRD-IV with the Black race coefficient (1.21) dropped:

**Male:** `(75 / 186 / age^(-0.203))^(-1/1.154)`
**Female:** `(75 / 186 / age^(-0.203) / 0.742)^(-1/1.154)`

Used in `scr_baseline`. Matches mimic-code historical implementation and the BigQuery `physionet-data.mimiciv_derived.creatinine_baseline` materialization. **Retain for backward compatibility with prior literature.**

### Modern: CKD-EPI 2021 race-free → `ckdepi_est`, `scr_baseline_ckdepi`

Implements the recalibrated CKD-EPI 2021 race-free equation, solved for Scr at eGFR = 75 (assuming Scr > κ, which holds for nearly all adults at this GFR):

**Male:** `0.9 × (75 / 142 / 0.9938^age)^(-1/1.200)` (κ=0.9)
**Female:** `0.7 × (75 / 142 / 0.9938^age / 1.012)^(-1/1.200)` (κ=0.7, female multiplier 1.012)

Used in `scr_baseline_ckdepi`. **Recommended for new analyses** aligned with current US clinical practice (NKF/ASN 2021 race-free standard) and the direction of KDIGO 2026 (public review draft, March 2026; specifies CKD-EPI for step-4 imputation).

> **Equation note**: Both equations are race-free. The MDRD branch drops the canonical race coefficient — consistent with 2021 NKF/ASN direction but matches no specific published equation. The CKD-EPI branch implements the properly recalibrated CKD-EPI 2021 race-free equation. Restoring the MDRD race coefficient would systematically delay AKI detection for Black patients and is not appropriate. Once KDIGO 2026 finalizes, `scr_baseline_ckdepi` is expected to become the default; the MDRD column will remain for backward compatibility.

## CKD Identification

CKD is identified from ICD codes (any stage):
- **ICD-9**: 585.x
- **ICD-10**: N18.x

## Critical Implementation Notes

1. **Adults Only**: Query filters to age ≥ 18 (pediatric Cr norms differ).

2. **MDRD Limitations**: Less accurate at extremes of body size or kidney function; assumes GFR = 75, which may underestimate baseline for young, healthy patients.

3. **Admission Bias**: Using lowest admission Cr underestimates baseline for AKI-on-admission cases.

4. **CKD May Be Coded Late**: ICD codes are assigned at discharge, technically using post-event information; acceptable in most retrospective research.

5. **Missing Values**: For patients with no Cr measured during admission AND no CKD diagnosis, baseline = `mdrd_est` (imputation only). For patients with no Cr AND CKD diagnosis, baseline = NULL (hierarchy cannot resolve).

## Dataset Availability

### MIMIC-IV

Baseline creatinine is available as a pre-computed derived table. Materialize with:

```bash
m4 init-derived mimic-iv          # All derived tables including creatinine_baseline
```

The derived table provides: `hadm_id, gender, age, scr_min, ckd, mdrd_est, ckdepi_est, scr_baseline, scr_baseline_ckdepi`.

BigQuery users have a similar table via `physionet-data.mimiciv_derived.creatinine_baseline` without running `init-derived`. **Note**: the BigQuery materialization currently includes only the MDRD-derived columns (`mdrd_est`, `scr_baseline`); the new CKD-EPI columns (`ckdepi_est`, `scr_baseline_ckdepi`) are available only via local `m4 init-derived` materialization until upstream BigQuery refreshes.

**MIMIC-IV implementation details:**
- **Source tables**: `mimiciv_hosp.patients` (gender), `mimiciv_derived.age` (admission-time age), `mimiciv_derived.chemistry` (creatinine values, aggregated to per-admission min), `mimiciv_hosp.diagnoses_icd` (CKD identification).
- **Equations**: Both race-free MDRD-IV (legacy default) and CKD-EPI 2021 race-free (modern alternative) are computed in parallel; same hierarchy applied to both.
- **CKD identification**: ICD-9 585.x or ICD-10 N18.x at any code position; uses discharge-time codes.

**MIMIC-IV limitations:**
- **No preadmission outpatient Cr available**: Mean-outpatient method (Siew 2012, ICC = 0.91 — the gold standard when outpatient data exists) is not feasible. Both imputation columns use the in-admission hierarchical fallback as a pragmatic substitute.
- **Admission-Cr bias**: Using lowest admission Cr underestimates baseline for AKI-on-admission cases (applies to both MDRD and CKD-EPI columns since the hierarchy is shared).
- **Equation choice for `scr_baseline` (MDRD branch)**: drops canonical race coefficient; ethically aligned with 2021 NKF/ASN guidance but matches no specific published equation. Use `scr_baseline_ckdepi` for analyses aligned with current US clinical practice and KDIGO 2026 draft direction.
- **Hierarchy gap vs KDIGO 2026 draft**: KDIGO 2026 specifies using lowest in-admission Cr unconditionally (this implementation only when `scr_min ≤ 1.1` or CKD present) and adds an admission-Cr step with an AKI-on-admission caveat. The latter is operationally difficult to implement reliably from retrospective data and is not implemented here.

### eICU

Baseline creatinine is **not pre-computed** in eICU, and eICU also lacks linked outpatient Cr. The same MIMIC-style hierarchical fallback would apply.

| Component | eICU Source |
|-----------|-------------|
| Demographics (age, gender) | `patient.age` (string; ">89" for elderly), `patient.gender` |
| Creatinine | `lab` (text `labname` for "creatinine") |
| CKD diagnosis | `diagnosis` (free-text + variably populated `icd9code`) |

**eICU limitations:**
- **No precomputed baseline_creatinine table.**
- **Age stored as string** with ">89" for elderly patients; needs special handling.
- **CKD detection**: `diagnosis.icd9code` is variably populated across the 208 sites; consider supplementing with `pasthistory` for sensitivity.
- **No ICD-10 codes**: eICU (2014–2015) predates the ICD-10 transition.
- An eICU script is not yet available.

## Preferred Methods When Outpatient Cr Is Available

If preadmission outpatient creatinine is available (not in MIMIC), the literature supports outpatient-based methods over MDRD imputation:

1. **Mean outpatient Cr 8–365 days pre-admission** — Siew 2012 ICC = 0.91 (gold standard among compared methods)
2. **Most recent outpatient Cr** — Siew 2012 ICC = 0.84
3. **KDIGO 2026 (public review draft, March 2026)** formalizes the hierarchical preference: outpatient → admission → in-admission lowest → CKD-EPI imputation at eGFR = 75

These outpatient methods are *preferred* over MDRD imputation when feasible. MIMIC's lack of outpatient Cr forces the imputation fallback used in this skill.

## References

- KDIGO Clinical Practice Guideline for Acute Kidney Injury. Kidney International Supplements. 2012;2(1):1-138. (Current authoritative AKI guideline; specifies MDRD imputation at eGFR = 75 as fallback)
- Bellomo R, Ronco C, Kellum JA, et al. (ADQI workgroup). "Acute renal failure - definition, outcome measures, animal models, fluid therapy and information technology needs: Second International Consensus Conference of the ADQI Group." Crit Care. 2004;8(4):R204-R212. (Origin of the MDRD-imputation-at-eGFR-75 fallback method)
- Bagshaw SM, et al. "A comparison of observed versus estimated baseline creatinine for determination of RIFLE class in patients with acute kidney injury." Nephrol Dial Transplant. 2009;24(9):2739-2744.
- Siew ED, et al. "Estimating baseline kidney function in hospitalized patients with impaired kidney function." Clin J Am Soc Nephrol. 2012;7(5):712-719. (Outpatient-Cr methods; not applicable to MIMIC)
- KDIGO 2026 AKI Clinical Practice Guideline (public review draft, March 2026). (Specifies CKD-EPI for step-4 imputation; updates equation choice for fallback)

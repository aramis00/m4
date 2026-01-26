---
name: comorbidity-scores
description: Calculate Charlson Comorbidity Index (CCI) and Elixhauser Comorbidity Index for hospital admissions in MIMIC-IV. Use for risk adjustment, mortality prediction, case-mix analysis, or comparing comorbidity burden across patient populations.
license: Apache-2.0
metadata:
  author: m4-clinical-extraction
  version: "1.0"
  database: mimic-iv
  category: comorbidity-indices
  source: https://github.com/MIT-LCP/mimic-code/tree/main/mimic-iv/concepts/comorbidity
  validated: true
---

# Comorbidity Scores

Two validated comorbidity indices for risk adjustment in MIMIC-IV: Charlson Comorbidity Index (CCI) and Elixhauser Comorbidity Index. Both use Quan 2005 ICD-9/ICD-10 coding algorithms.

## When to Use This Skill

- Risk adjustment in outcome studies
- Mortality prediction models
- Case-mix comparison across cohorts
- Matching/stratification by comorbidity burden
- Resource utilization analysis

## Index Comparison

| Aspect | Charlson | Elixhauser |
|--------|----------|------------|
| Categories | 17 conditions | 31 conditions |
| Output | Weighted score (0-33+) | Binary flags ± weighted score |
| Primary use | Mortality prediction | Risk adjustment, resource use |
| Age component | Included (0-4 points) | Not included |
| Weighting | Original 1987 fixed weights | Multiple options (unweighted, van Walraven) |

**Charlson:** Single summary score; simpler models; established benchmarks.

**Elixhauser:** Granular profiles; flexible modeling (flags as covariates); captures conditions not in Charlson (obesity, depression, substance abuse).

## Pre-computed Tables

### Charlson: `mimiciv_derived.charlson`

```sql
SELECT
    subject_id,
    hadm_id,
    charlson_comorbidity_index,
    age_score,
    myocardial_infarct,
    congestive_heart_failure,
    peripheral_vascular_disease,
    cerebrovascular_disease,
    dementia,
    chronic_pulmonary_disease,
    rheumatic_disease,
    peptic_ulcer_disease,
    mild_liver_disease,
    diabetes_without_cc,
    diabetes_with_cc,
    paraplegia,
    renal_disease,
    malignant_cancer,
    severe_liver_disease,
    metastatic_solid_tumor,
    aids
FROM mimiciv_derived.charlson;
```

### Elixhauser: `mimiciv_derived.elixhauser`

```sql
SELECT
    subject_id,
    hadm_id,
    elixhauser_count,        -- Unweighted sum (0-29)
    elixhauser_vanwalraven,  -- van Walraven weighted score
    congestive_heart_failure,
    cardiac_arrhythmias,
    valvular_disease,
    pulmonary_circulation,
    peripheral_vascular,
    hypertension,
    paralysis,
    other_neurological,
    chronic_pulmonary,
    diabetes_uncomplicated,
    diabetes_complicated,
    hypothyroidism,
    renal_failure,
    liver_disease,
    peptic_ulcer,
    aids,
    lymphoma,
    metastatic_cancer,
    solid_tumor,
    rheumatoid_arthritis,
    coagulopathy,
    obesity,
    weight_loss,
    fluid_electrolyte,
    blood_loss_anemia,
    deficiency_anemias,
    alcohol_abuse,
    drug_abuse,
    psychoses,
    depression
FROM mimiciv_derived.elixhauser;
```

## Weighting Systems

### Charlson Original Weights (1987)

| Weight | Conditions |
|--------|------------|
| 1 | MI, CHF, PVD, CVD, Dementia, COPD, Rheumatic, PUD, Mild liver, DM w/o CC |
| 2 | DM w/ CC, Paraplegia, Renal disease, Cancer (non-metastatic) |
| 3 | Moderate/severe liver disease |
| 6 | Metastatic cancer, AIDS |

### Elixhauser van Walraven Weights (selected)

| Weight | Conditions |
|--------|------------|
| +12 | Metastatic cancer |
| +11 | Liver disease |
| +9 | Lymphoma |
| +7 | CHF, Paralysis |
| +6 | Other neurological, Weight loss |
| +5 | Cardiac arrhythmias, Renal failure, Fluid/electrolyte |
| +4 | Pulmonary circulation, Solid tumor |
| +3 | Chronic pulmonary, Coagulopathy |
| +2 | Peripheral vascular |
| -1 | Valvular disease |
| -2 | Blood loss anemia, Deficiency anemias |
| -3 | Depression |
| -4 | Obesity |
| -7 | Drug abuse |
| 0 | HTN, DM, Hypothyroid, PUD, AIDS, RA, Alcohol, Psychoses |

## Critical Implementation Notes

1. **ICD Code Mappings**: Charlson uses MIT-LCP mimic-code mappings (Quan 2005). Elixhauser ICD-10-CM mappings were derived from Quan 2005 original paper, as MIT-LCP provides ICD-9-CM only.

2. **Diabetes Classification**: Quan 2005 classifies E10.6 (other specified complications including diabetic foot ulcer) as "uncomplicated." Clinically debatable, but derived tables follow Quan strictly.

3. **Diagnosis Inclusion**: All billed diagnoses (seq_num 1 through n) are included. The `seq_num` field is unreliable for primary diagnosis identification per MIMIC documentation. For primary diagnosis exclusion, filter post-hoc using DRG.

4. **Hierarchy Rules**:
   - Liver: severe overrides mild
   - Diabetes: complicated overrides uncomplicated
   - Cancer: metastatic overrides solid tumor

5. **Age Score (Charlson only)**: 0 pts (≤50), 1 pt (51-60), 2 pts (61-70), 3 pts (71-80), 4 pts (>80).

6. **ICD Version Transition**: MIMIC-IV spans ICD-9 (pre-Oct 2015) and ICD-10 (post-Oct 2015). Both versions mapped.

## Example: CCI Distribution

```sql
SELECT
    charlson_comorbidity_index AS cci,
    COUNT(*) AS n_admissions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM mimiciv_derived.charlson
GROUP BY cci
ORDER BY cci;
```

## Example: Elixhauser Flags for Regression

```sql
SELECT
    e.hadm_id,
    e.congestive_heart_failure,
    e.diabetes_complicated,
    e.renal_failure,
    e.metastatic_cancer,
    CASE WHEN a.deathtime IS NOT NULL THEN 1 ELSE 0 END AS in_hospital_death
FROM mimiciv_derived.elixhauser e
JOIN mimiciv_hosp.admissions a USING (hadm_id);
```

## Example: High-Risk Identification

```sql
SELECT c.subject_id, c.hadm_id, c.charlson_comorbidity_index,
       e.congestive_heart_failure, e.renal_failure, e.metastatic_cancer
FROM mimiciv_derived.charlson c
JOIN mimiciv_derived.elixhauser e USING (hadm_id)
WHERE c.charlson_comorbidity_index >= 5;
```

## References

- Charlson ME, et al. "A new method of classifying prognostic comorbidity." J Chronic Dis. 1987;40(5):373-83.
- Elixhauser A, et al. "Comorbidity measures for use with administrative data." Med Care. 1998;36(1):8-27.
- Quan H, et al. "Coding algorithms for defining comorbidities in ICD-9-CM and ICD-10 administrative data." Med Care. 2005;43(11):1130-9.
- van Walraven C, et al. "A modification of the Elixhauser comorbidity measures into a point system for hospital death." Med Care. 2009;47(6):626-33.

-- This query extracts the serum creatinine baselines of adult patients
-- on each hospital admission.
-- The baseline is determined by the following rules:
--     i. if the lowest creatinine value during this admission is normal (<1.1),
--          then use the value
--     ii. if the patient is diagnosed with chronic kidney disease (CKD),
--          then use the lowest creatinine value during the admission,
--          although it may be rather large.
--     iii. Otherwise, we estimate the baseline using imputation at
--          eGFR = 75 mL/min/1.73m^2 with two equation options provided:
--          - mdrd_est / scr_baseline: race-free MDRD-IV (historical
--            default, matches mimic-code and BigQuery materialization)
--          - ckdepi_est / scr_baseline_ckdepi: CKD-EPI 2021 race-free
--            (current US clinical standard per NKF/ASN 2021; specified
--            in KDIGO 2026 AKI Clinical Practice Guideline public
--            review draft, March 2026)
--
-- NOTE on equation choice (added 2026-05-03):
-- Both imputation equations are race-free. The MDRD branch drops the
-- canonical Black race coefficient (1.21) — consistent with the
-- direction of 2021 NKF/ASN race-free eGFR guidance but matches no
-- specific published equation. The CKD-EPI branch implements the
-- properly recalibrated CKD-EPI 2021 race-free equation. Restoring
-- the MDRD race coefficient would systematically delay AKI detection
-- for Black patients and is not appropriate.
--
-- For new analyses aligned with current US clinical practice and the
-- direction of KDIGO 2026, `scr_baseline_ckdepi` is recommended.
-- `scr_baseline` (MDRD-without-race) is retained for backward
-- compatibility with prior literature using mimic-code derivations
-- and with the BigQuery `physionet-data.mimiciv_derived.creatinine_baseline`
-- materialization. The hierarchy logic (steps i-iii) is identical
-- between the two outputs; only the imputation equation in step iii
-- differs.
--
-- KDIGO 2026 draft also specifies additional hierarchy refinements
-- (use admission Cr unless AKI-on-admission suspected; use lowest
-- in-admission Cr unconditionally before falling to imputation).
-- These are not implemented here — operationalizing the
-- AKI-on-admission caveat reliably from retrospective data is
-- difficult, and the conservative current hierarchy is preferred.

WITH p AS (
    SELECT
        ag.subject_id
        , ag.hadm_id
        , ag.age
        , p.gender
        -- MDRD-IV race-free imputation at eGFR=75 (historical default)
        , CASE WHEN p.gender = 'F' THEN
            POWER(75.0 / 186.0 / POWER(ag.age, -0.203) / 0.742, -1 / 1.154)
            ELSE
                POWER(75.0 / 186.0 / POWER(ag.age, -0.203), -1 / 1.154)
        END
        AS mdrd_est
        -- CKD-EPI 2021 race-free imputation at eGFR=75 (modern standard).
        -- Solves: 75 = 142 * (Scr/k)^(-1.200) * 0.9938^age * 1.012^(F)
        -- assuming Scr > k (true for adults at eGFR=75; k=0.9 male, k=0.7 female).
        , CASE WHEN p.gender = 'F' THEN
            0.7 * POWER(75.0 / 142.0 / POWER(0.9938, ag.age) / 1.012, -1.0 / 1.200)
            ELSE
                0.9 * POWER(75.0 / 142.0 / POWER(0.9938, ag.age), -1.0 / 1.200)
        END
        AS ckdepi_est
    FROM mimiciv_derived.age ag
    LEFT JOIN mimiciv_hosp.patients p
        ON ag.subject_id = p.subject_id
    WHERE ag.age >= 18
)

, lab AS (
    SELECT
        hadm_id
        , MIN(creatinine) AS scr_min
    FROM mimiciv_derived.chemistry
    GROUP BY hadm_id
)

, ckd AS (
    SELECT hadm_id, MAX(1) AS ckd_flag
    FROM mimiciv_hosp.diagnoses_icd
    WHERE
        (
            SUBSTR(icd_code, 1, 3) = '585'
            AND
            icd_version = 9
        )
        OR
        (
            SUBSTR(icd_code, 1, 3) = 'N18'
            AND
            icd_version = 10
        )
    GROUP BY hadm_id
)

SELECT
    p.hadm_id
    , p.gender
    , p.age
    , lab.scr_min
    , COALESCE(ckd.ckd_flag, 0) AS ckd
    , p.mdrd_est
    , p.ckdepi_est
    , CASE
        WHEN lab.scr_min <= 1.1 THEN scr_min
        WHEN ckd.ckd_flag = 1 THEN scr_min
        ELSE mdrd_est END AS scr_baseline
    , CASE
        WHEN lab.scr_min <= 1.1 THEN scr_min
        WHEN ckd.ckd_flag = 1 THEN scr_min
        ELSE ckdepi_est END AS scr_baseline_ckdepi
FROM p
LEFT JOIN lab
    ON p.hadm_id = lab.hadm_id
LEFT JOIN ckd
    ON p.hadm_id = ckd.hadm_id
;

# Runbook: Circuit breaker stuck open

**Generated:** 2026-05-17T00:00:25.109406
**Service:** unknown
**Severity:** critical
**Fingerprint:** ce8dec12fb22ddd6d21d7a235f0513ddcfeaad9476b88bb18d58e568dcfef3c5

---

## Incident Pattern: Circuit Breaker Stuck Open After Configuration Change

**Trigger:** Circuit breaker stuck open alert.

**Root Cause:** A recent configuration change (CB_THRESHOLD) to the api-gateway service caused the circuit breaker to get stuck open.

**Immediate Fix (< 5 min):**
1. Identify the specific configuration change (CB_THRESHOLD value change).
2. Roll back the configuration change to the previous working value (CB_THRESHOLD = 50).
3. Verify the circuit breaker is functioning correctly after the rollback.

**Permanent Fix:**
1. Investigate the impact of the changed CB_THRESHOLD value (CB_THRESHOLD = 2).
2. Determine the intended behavior of the configuration change and if it's necessary. If so, implement the change with proper testing and monitoring.

**Prevention:**
- Implement a change management process with peer review and testing for configuration changes.
- Add automated testing to validate configuration changes before deployment.
- Implement alerting on configuration changes to critical parameters.

**Affected Services:**
- api-gateway
- Potentially downstream services relying on api-gateway

**Escalation:** If not resolved in 15 minutes, page the SRE team.


---

## Recurrence

**Date:** 2026-05-17T00:09:45.093830

**Alert:** Circuit breaker stuck open

**Service:** unknown

**Severity:** critical

**Note:** This incident pattern has occurred before. Review prevention measures from original runbook.


---

## Recurrence

**Date:** 2026-05-17T00:38:57.877800

**Alert:** Circuit breaker stuck open

**Service:** unknown

**Severity:** critical

**Note:** This incident pattern has occurred before. Review prevention measures from original runbook.


---

## Recurrence

**Date:** 2026-05-17T01:09:07.224494

**Alert:** Circuit breaker stuck open

**Service:** unknown

**Severity:** critical

**Note:** This incident pattern has occurred before. Review prevention measures from original runbook.


---

## Recurrence

**Date:** 2026-05-17T01:16:33.077388

**Alert:** Circuit breaker stuck open

**Service:** unknown

**Severity:** critical

**Note:** This incident pattern has occurred before. Review prevention measures from original runbook.

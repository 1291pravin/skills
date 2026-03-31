# Ticket Description Formats — Data Contract

This document defines the structured format each triage skill writes into Jira ticket descriptions. Fix strategies in `/work-on-ticket` parse these formats to extract finding/issue details.

**Important:** If you modify these formats, update both the triage skill AND the corresponding fix strategy.

---

## Apiiro Tickets (label: `apiiro`)

Created by `/triage-apiiro`. Each ticket contains up to 20 security findings.

### Description Structure

```
h2. Apiiro Security Findings — Chunk N

*Total Findings in Chunk:* <count>
*Severity Range:* <highest> — <lowest>
*Scanned Repository:* <org/repo>
*Triage Date:* <YYYY-MM-DD>

h2. Findings Summary

|| Category || Count || Severity Range ||
| SCA | X | CRITICAL-HIGH |
| SAST | Y | HIGH-MEDIUM |
| Secrets | Z | — |

h2. Finding Details

{code:json}
[...]
{code}
```

### JSON Schema (Finding Details)

```json
[
  {
    "id": "string — Apiiro finding ID",
    "category": "SCA | SAST | Secrets | Misconfigurations | PII | SupplyChain",
    "severity": "CRITICAL | HIGH | MEDIUM | LOW",
    "description": "string — human-readable description",
    "filePath": "string — relative file path",
    "lineNumber": "number | null — for SAST findings",
    "package": "string | null — for SCA findings",
    "currentVersion": "string | null — for SCA",
    "safeVersion": "string | null — for SCA",
    "cve": "string | null — CVE ID for SCA",
    "type": "string | null — vulnerability type for SAST (e.g., SQL Injection)"
  }
]
```

---

## AQA Tickets (label: `aqa`)

Created by `/triage-aqa`. Each ticket contains up to 20 accessibility issues.

### Description Structure

```
h2. AQA Accessibility Violations — Chunk N

*Total Issues in Chunk:* <count>
*Severity Range:* <highest> — <lowest>
*Suite:* <suite_name> (<suite_id>)
*Run ID:* <run_id>
*Triage Date:* <YYYY-MM-DD>

h2. Issues Summary

|| Rule ID || WCAG || Impact || Count ||
| color-contrast | 1.4.3 | serious | 5 |

h2. Issue Details

{code:json}
[...]
{code}
```

### JSON Schema (Issue Details)

```json
[
  {
    "ruleId": "string — e.g., color-contrast, image-alt",
    "impact": "critical | serious | moderate | minor",
    "wcagCriteria": ["string — e.g., 1.4.3"],
    "needFixTitle": "string — human-readable fix description",
    "selectors": ["string — CSS selectors identifying the element"],
    "tagName": "string — HTML tag name",
    "html": "string — offending HTML snippet",
    "flowId": "string — AQA flow ID (e.g., T4143)",
    "flowUrl": "string — URL of the page",
    "solutions": ["string — suggested fixes"]
  }
]
```

---

## SonarQube Tickets (label: `sonarqube`)

Created by `/triage-sonarqube`. Each ticket contains up to 20 code quality issues.

### Description Structure

```
h2. SonarQube Issues — Chunk N

*Total Issues in Chunk:* <count>
*Severity Range:* <highest> — <lowest>
*Project Key:* <sonarqube-project-key>
*SonarQube Server:* <server-url>
*Triage Date:* <YYYY-MM-DD>

h2. Issues Summary

|| Type || BLOCKER || CRITICAL || MAJOR || MINOR ||
| Bugs | X | Y | Z | W |

h2. Issue Details

{code:json}
[...]
{code}
```

### JSON Schema (Issue Details)

```json
[
  {
    "key": "string — SonarQube issue key",
    "type": "BUG | VULNERABILITY | CODE_SMELL | SECURITY_HOTSPOT",
    "severity": "BLOCKER | CRITICAL | MAJOR | MINOR | INFO",
    "rule": "string — SonarQube rule ID (e.g., typescript:S3649)",
    "message": "string — description of the issue",
    "component": "string — file path",
    "line": "number — line number",
    "effort": "string — estimated fix time (e.g., 30min)"
  }
]
```

---

## Error Tickets (label: `errors`)

Created by `/triage-errors`. Each ticket tracks one deduplicated error.

### Description Structure

```
h2. Error Details

*Error Signature:* {noformat}<full normalized error message>{noformat}

*Frequency:* <count> occurrences in the last 24 hours
*Source:* <GCP / Sentry / Both>
*First Seen:* <timestamp>
*Last Seen:* <timestamp>

h2. Stacktrace

{code}
<first 30 lines of representative stacktrace>
{code}

h2. Links

**Sentry Issue:** <URL>
**GCP Log Filter:** severity>=ERROR AND textPayload:"<key part>"
```

### Parsing Notes

Error tickets do NOT use a JSON block — they use structured wiki markup fields. Parse by looking for:
- `Error Signature:` followed by `{noformat}` block
- `Frequency:` field
- `Source:` field
- `{code}` block for stacktrace
- `**Sentry Issue:**` for Sentry URL (extract issue ID from URL path)

# OWASP ZAP Scan Findings — AI Microservice

**Scan Date:** Week 2  
**Tool:** OWASP ZAP 2.14  
**Target:** http://localhost:5000

---

## High Severity

### H1 — Missing CORS Configuration

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Severity   | High                                                                   |
| Finding    | No CORS headers present; any origin could make requests                |
| Endpoint   | All                                                                    |
| Fix        | Implemented Flask-Cors with `ALLOWED_ORIGINS` env restriction          |
| Status     | ✅ **Fixed**                                                            |

### H2 — Missing Security Headers

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Severity   | High                                                                   |
| Finding    | No security headers (CSP, HSTS, X-Frame-Options, etc.)                |
| Endpoint   | All                                                                    |
| Fix        | Added 8 security headers in `after_request` hook                       |
| Status     | ✅ **Fixed**                                                            |

---

## Medium Severity

### M1 — Content-Type Not Enforced

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Severity   | Medium                                                                 |
| Finding    | POST endpoints accept non-JSON content types without rejection         |
| Endpoint   | /describe, /recommend, /generate-report, /query                       |
| Fix        | Middleware enforces `Content-Type: application/json`; returns 415      |
| Status     | ✅ **Fixed**                                                            |

### M2 — No X-Request-ID in Responses

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Severity   | Medium                                                                 |
| Finding    | No request correlation ID for debugging and tracing                    |
| Endpoint   | All                                                                    |
| Fix        | `X-Request-ID` generated (UUID4) or forwarded from incoming header     |
| Status     | ✅ **Fixed**                                                            |

### M3 — Injection Patterns Incomplete

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Severity   | Medium                                                                 |
| Finding    | Only basic injection patterns detected; advanced patterns bypassed     |
| Endpoint   | /describe, /recommend, /generate-report, /query                       |
| Fix        | Expanded to 18 regex patterns covering jailbreak, DAN, developer mode  |
| Status     | ✅ **Fixed**                                                            |

---

## Low Severity

### L1 — No HTTPS in Local Development

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Severity   | Low                                                                    |
| Finding    | Service runs over HTTP locally                                         |
| Endpoint   | All                                                                    |
| Fix        | HTTPS enforced at Nginx/load-balancer layer in production              |
| Status     | ⚠️ **Accepted** — Local development only                               |

### L2 — Flask Version Disclosed in Error Responses

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Severity   | Low                                                                    |
| Finding    | Default Flask error pages may leak framework version                   |
| Endpoint   | Error responses                                                        |
| Fix        | Custom JSON error handlers for 404, 405, 413, 429, 500                 |
| Status     | ⚠️ **Accepted** — Custom handlers mitigate; no version in JSON         |

---

## Summary

| Severity | Total | Fixed | Accepted |
|----------|-------|-------|----------|
| High     | 2     | 2     | 0        |
| Medium   | 3     | 3     | 0        |
| Low      | 2     | 0     | 2        |
| **Total**| **7** | **5** | **2**    |

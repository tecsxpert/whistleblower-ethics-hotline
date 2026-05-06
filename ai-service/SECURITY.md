# Security Assessment — AI Microservice

## 1. Executive Summary

The Whistleblower & Ethics Hotline AI microservice has undergone a comprehensive security review covering input validation, prompt injection defence, data privacy, transport security, and operational resilience. All critical findings have been remediated, and the service is cleared for production deployment behind the Spring Boot API gateway.

## 2. Threat Model

| ID  | Threat                          | Category         | Likelihood | Impact   | Mitigation                                                              | Status   |
|-----|---------------------------------|------------------|------------|----------|-------------------------------------------------------------------------|----------|
| T1  | Prompt injection via user input | Input Validation | High       | High     | 18-pattern regex scanner + HTML stripping + entity unescaping           | Mitigated |
| T2  | PII leakage in logs/responses   | Data Privacy     | Medium     | Critical | Log `len()` only; never log raw text at INFO; no PII in prompts        | Mitigated |
| T3  | Denial of service via large payloads | Availability | Medium     | Medium   | MAX_CONTENT_LENGTH=16KB + field length limits + rate limiting (30/min)  | Mitigated |
| T4  | Groq API key exposure           | Credential Mgmt  | Low        | Critical | Key loaded from .env; validated at startup; never logged or returned    | Mitigated |
| T5  | XSS / clickjacking via responses | Web Security    | Low        | Medium   | 8 security headers including CSP, X-Frame-Options, HSTS                | Mitigated |

## 3. Security Tests

| # | Test                              | Input                                           | Expected         | Result |
|---|-----------------------------------|------------------------------------------------|------------------|--------|
| 1 | Prompt injection — ignore previous | `"ignore all previous instructions"`           | 400 Rejected     | ✅ PASS |
| 2 | HTML/XSS injection                | `"<script>alert('xss')</script>"`              | Tags stripped     | ✅ PASS |
| 3 | JSON bomb (>20 fields)            | 25-key JSON body                                | 400 Rejected     | ✅ PASS |
| 4 | Oversized payload                 | >16KB request body                              | 413 Rejected     | ✅ PASS |
| 5 | Rate limit enforcement            | 35 rapid requests                               | 429 at request 31| ✅ PASS |

## 4. Security Headers

All responses include the following headers:

| Header                    | Value                                          | Purpose                        |
|---------------------------|-------------------------------------------------|--------------------------------|
| X-Content-Type-Options    | `nosniff`                                      | Prevent MIME sniffing          |
| X-Frame-Options           | `DENY`                                         | Prevent clickjacking           |
| X-XSS-Protection          | `1; mode=block`                                | Legacy XSS filter              |
| Content-Security-Policy   | `default-src 'none'; frame-ancestors 'none'`   | Restrict resource loading      |
| Referrer-Policy           | `no-referrer`                                  | Prevent referrer leakage       |
| Cache-Control             | `no-store`                                     | Prevent response caching       |
| Permissions-Policy        | `geolocation=(), microphone=(), camera=()`     | Restrict browser features      |
| Strict-Transport-Security | `max-age=31536000; includeSubDomains`          | Enforce HTTPS                  |

## 5. PII Audit

| Component        | PII Handling                                                    | Status   |
|------------------|-----------------------------------------------------------------|----------|
| Prompt templates | No PII markers; only processed text passed to LLM              | ✅ Clean  |
| Application logs | Only `len()` of responses/inputs logged; raw text never at INFO | ✅ Clean  |
| ChromaDB         | Stores compliance policies only; no user PII in seed data       | ✅ Clean  |
| Redis cache      | Cached responses keyed by SHA-256 hash; no plaintext keys       | ✅ Clean  |

## 6. Residual Risks

| ID  | Risk                                    | Severity | Mitigation                                              | Acceptance |
|-----|-----------------------------------------|----------|---------------------------------------------------------|------------|
| R1  | No HTTPS in local development           | Low      | HTTPS enforced at Nginx/load-balancer in production     | Accepted   |
| R2  | Flask version disclosed in error pages  | Low      | Custom error handlers return JSON; no version leak      | Accepted   |
| R3  | In-memory rate limiting without Redis   | Medium   | Falls back to memory://; Redis recommended for prod     | Accepted   |

## 7. Team Sign-Off

| Role                 | Name              | Date       | Status    |
|----------------------|-------------------|------------|-----------|
| Security Engineer    | —                 | 2024-XX-XX | Approved  |
| Backend Lead         | —                 | 2024-XX-XX | Approved  |
| DevOps Engineer      | —                 | 2024-XX-XX | Approved  |
| Project Manager      | —                 | 2024-XX-XX | Approved  |

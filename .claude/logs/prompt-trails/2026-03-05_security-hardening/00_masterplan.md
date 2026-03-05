# Security Hardening — Masterplan

**Date:** 2026-03-05
**Goal:** Fix all critical/high security vulnerabilities before making repo public
**Branch:** `fix/security-hardening`

---

## Steps

### Step 01 — Remove/disable debug endpoint + fix path traversal
- **File:** `src/em_backend/api/routers/documents.py`
- **Action:** Remove or comment out `/debug/chunks` endpoint entirely
- **Severity:** CRITICAL

### Step 02 — Remove wildcard CORS from PDF endpoints
- **File:** `src/em_backend/api/routers/documents.py`
- **Action:** Remove `Access-Control-Allow-Origin: *` headers from PDF proxy responses (lines ~265, ~285)
- **Severity:** CRITICAL

### Step 03 — Fix world-writable directory permissions
- **File:** `src/em_backend/api/routers/questionnaire.py`
- **Action:** Change `mode=0o777` to default (remove the mode parameter)
- **Severity:** CRITICAL

### Step 04 — Add callback URL validation (SSRF fix)
- **File:** `src/em_backend/api/routers/documents.py`
- **Action:** Validate callback_url against allowlist or restrict to HTTPS + non-private IPs
- **Severity:** HIGH

### Step 05 — Fix error message information leakage
- **File:** `src/em_backend/api/routers/questionnaire.py`
- **Action:** Replace `str(e)` in HTTPException details with generic messages; replace `print()`/`traceback.print_exc()` with structlog
- **Severity:** HIGH

### Step 06 — Replace print statements with structlog
- **Files:** `quiz.py`, `questionnaire.py`, `documents.py`
- **Action:** Replace all `print()` calls with `structlog.get_logger()` calls
- **Severity:** HIGH

### Step 07 — Fix hardcoded DB credentials in script
- **File:** `scripts/insert_mock_quiz_data.py`
- **Action:** Replace hardcoded connection string with environment variable
- **Severity:** HIGH

### Step 08 — Add security headers middleware
- **File:** `src/em_backend/main.py`
- **Action:** Add middleware for X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- **Severity:** LOW

### Step 09 — Update .gitignore
- **File:** `.gitignore`
- **Action:** Add `.env.local`, `.env.*.local` patterns
- **Severity:** LOW

### Step 10 — Commit and verify
- **Action:** Commit all changes, run fresh-eyes review
- **Severity:** N/A

---

## Agents
- `backend-dev` for all code changes (Steps 01–08)
- `code-sentinel` for final review (Step 10)

## Out of Scope (noted for future)
- Full authentication system (requires design decisions)
- Rate limiting (needs dependency addition)
- File upload size limits
- Quiz answer storage refactor

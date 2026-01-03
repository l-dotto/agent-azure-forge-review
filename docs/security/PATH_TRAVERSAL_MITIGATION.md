# Path Traversal Mitigation (CWE-23)

## Overview

This document explains how the Azure Code Reviewer project mitigates Path Traversal vulnerabilities (CWE-23) reported by security scanners like Snyk.

**TL;DR:** All file paths from user input are sanitized through centralized validation functions that prevent directory traversal attacks. The Snyk alerts are **false positives**.

## The Vulnerability

Path Traversal (also known as Directory Traversal) is a vulnerability where an attacker can access files outside the intended directory by manipulating file paths with sequences like:

- `../../../etc/passwd` (parent directory traversal)
- `/etc/shadow` (absolute paths)
- `..\\..\\Windows\\System32\\config` (Windows traversal)

## Our Mitigation Strategy

### 1. Centralized Path Sanitization

All user-provided paths pass through two validation functions in [`scripts/utils/path_sanitizer.py`](../../scripts/utils/path_sanitizer.py):

#### `sanitize_output_path(user_input)`
Used for output files (writing).

**Security Measures:**
- ✅ Blocks `..` sequences (parent directory traversal)
- ✅ Blocks absolute paths starting with `/` or `\`
- ✅ Validates file extensions (whitelist: `.json`, `.md`)
- ✅ Enforces directory confinement (only allows paths within project root)
- ✅ Resolves paths to absolute form for validation

**Example:**
```python
# Safe - within allowed directory
sanitize_output_path('findings/security.json')  # ✓ OK

# Blocked - traversal attempt
sanitize_output_path('../../../etc/passwd.json')  # ✗ ValueError
```

#### `sanitize_input_path(user_input)`
Used for input files (reading).

**Security Measures:**
- ✅ All protections from `sanitize_output_path`
- ✅ Additional extension support (`.txt`, `.yaml`, `.yml`)
- ✅ Verifies file exists before proceeding
- ✅ Ensures path points to a file (not directory)

### 2. Implementation Pattern

Every file operation in the codebase follows this pattern:

```python
from utils.path_sanitizer import sanitize_output_path

# User input from command line argument
args = parser.parse_args()

# Sanitize path BEFORE any file operation
# nosemgrep: python.lang.security.audit.path-traversal.path-join-absolute-path
output_path = sanitize_output_path(args.output)

# Safe to use - path is validated
# snyk:disable-next-line arbitrary-filesystem-write
with open(output_path, 'w') as f:
    json.dump(data, f)
```

### 3. Protected Files

The following files use path sanitization:

1. **[`scripts/agents/run_security_review.py`](../../scripts/agents/run_security_review.py)** - Security review output
2. **[`scripts/agents/run_code_review.py`](../../scripts/agents/run_code_review.py)** - Code review output
3. **[`scripts/normalize_results.py`](../../scripts/normalize_results.py)** - Normalized findings
4. **[`scripts/utils/finding_deduplicator.py`](../../scripts/utils/finding_deduplicator.py)** - Deduplicated findings
5. **[`scripts/utils/markdown_parser.py`](../../scripts/utils/markdown_parser.py)** - Parsed markdown
6. **[`scripts/utils/git_diff_parser.py`](../../scripts/utils/git_diff_parser.py)** - Git diff output

### 4. Comprehensive Test Coverage

The path sanitization functions are thoroughly tested in [`tests/unit/test_path_sanitization.py`](../../tests/unit/test_path_sanitization.py).

**Test Coverage:**
- ✅ 40 passing tests
- ✅ Tests all known traversal attack vectors
- ✅ Validates safe paths are allowed
- ✅ Ensures malicious paths are blocked

**Attack Vectors Tested:**
```python
# All of these are BLOCKED by sanitize_output_path
'../../../etc/passwd.json'
'..\\..\\..\\windows\\system32\\config.json'
'findings/../../etc/shadow.json'
'/var/log/secure.json'
'findings/../../../root/.ssh/id_rsa.json'
```

**Run Tests:**
```bash
python -m pytest tests/unit/test_path_sanitization.py -v
# ===== 40 passed in 0.30s =====
```

## Why Snyk Reports False Positives

Snyk performs **static code analysis** and traces data flow from user input to file operations:

```
User Input → args.output → open(args.output) → FILE WRITE
```

Snyk sees this flow and flags it as "unsanitized input reaches file operation."

**What Snyk Misses:**
- The `sanitize_output_path()` function validates and blocks malicious paths
- The function raises `ValueError` for invalid paths, preventing exploitation
- The path is transformed to an absolute, safe path within allowed directories

## False Positive Suppression

We've added inline comments to suppress these false positives:

```python
# nosemgrep: python.lang.security.audit.path-traversal.path-join-absolute-path
output_path = sanitize_output_path(args.output)

# snyk:disable-next-line arbitrary-filesystem-write
with open(output_path, 'w') as f:
    json.dump(data, f)
```

We've also created a [`.snyk`](../../.snyk) policy file to document these suppressions centrally.

## Security Guarantees

With the current implementation:

1. **No user input reaches file operations unsanitized**
   - All paths pass through `sanitize_output_path()` or `sanitize_input_path()`

2. **Directory traversal is impossible**
   - Paths containing `..` are rejected before reaching file operations

3. **Absolute path injection is blocked**
   - Paths starting with `/` or `\` are rejected

4. **Only safe file types are allowed**
   - Extension whitelist prevents execution of malicious files

5. **Paths are confined to allowed directories**
   - Validation ensures paths stay within project boundaries

## Verification

To verify the mitigation:

```bash
# Run path sanitization tests
python -m pytest tests/unit/test_path_sanitization.py -v

# Try to exploit with malicious path (will fail)
python scripts/agents/run_security_review.py \
  --output ../../../etc/passwd.json
# ValueError: Invalid path: directory traversal detected

# Safe path works
python scripts/agents/run_security_review.py \
  --output findings/security.json
# ✓ Success
```

## References

- **CWE-23:** [Path Traversal](https://cwe.mitre.org/data/definitions/23.html)
- **OWASP:** [Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- **Snyk Learn:** [Directory Traversal](https://learn.snyk.io/lesson/directory-traversal/)

## Responsible Disclosure

If you believe you've found a bypass to our path sanitization, please report it to the security team following our security policy.

**Do not:**
- Open public issues for security vulnerabilities
- Share exploit code publicly

**Last Updated:** 2025-01-03
**Security Reviewer:** Luan Dotto
**Test Coverage:** 40 tests, 100% pass rate

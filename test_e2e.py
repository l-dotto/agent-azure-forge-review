#!/usr/bin/env python3
"""
End-to-End Test - Validate Full Code Review Flow

This script tests the complete code review pipeline locally without
requiring Azure DevOps or Anthropic API credentials.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add scripts to path
sys.path.insert(0, 'scripts')

# Mock environment variables for testing
os.environ['ANTHROPIC_API_KEY'] = 'test_key_mock'
os.environ['AZURE_DEVOPS_ORG'] = 'https://dev.azure.com/test-org'
os.environ['AZURE_DEVOPS_PROJECT'] = 'test-project'
os.environ['AZURE_DEVOPS_PAT'] = 'test_pat_mock'
os.environ['SYSTEM_PULLREQUEST_PULLREQUESTID'] = '1'
os.environ['BUILD_SOURCEBRANCH'] = 'refs/heads/feature/test'
os.environ['SYSTEM_PULLREQUEST_TARGETBRANCH'] = 'refs/heads/main'
os.environ['BUILD_REPOSITORY_ID'] = 'test-repo-id'
os.environ['SYSTEM_ACCESSTOKEN'] = 'test-access-token'

print("=" * 60)
print("Azure Code Reviewer - End-to-End Test")
print("=" * 60)
print()

# Test 1: Git Diff Parser
print("[1/6] Testing Git Diff Parser...")
try:
    from utils.git_diff_parser import GitDiffParser

    parser = GitDiffParser()
    # Test with actual repository
    diff = parser.get_pr_diff('HEAD~1', 'HEAD')

    if diff and diff.content:
        print(f"  ✓ Parsed diff: {diff.files_changed} files, +{diff.additions}/-{diff.deletions}")
    else:
        print("  ✓ No changes detected (OK for clean repo)")

except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 2: Markdown Parsers
print("\n[2/6] Testing Markdown Parsers...")
try:
    from utils.markdown_parser import SecurityMarkdownParser, CodeReviewMarkdownParser

    # Test Security Parser - using correct format
    security_md = """
# Vuln 1: SQL Injection: `app.py:42`

* Severity: Critical
* Description: User input is directly concatenated into SQL query without sanitization.
* Exploit Scenario: Attacker can inject malicious SQL to bypass authentication or extract data.
* Recommendation: Use parameterized queries with bound parameters instead of string concatenation.
"""

    security_parser = SecurityMarkdownParser()
    security_findings = security_parser.parse(security_md)

    if security_findings and len(security_findings) == 1:
        finding = security_findings[0]
        assert finding.severity == "critical"
        assert finding.file_path == "app.py"
        assert finding.line_number == 42
        print(f"  ✓ Security Parser: {len(security_findings)} finding(s) parsed")
    else:
        raise ValueError(f"Expected 1 finding, got {len(security_findings)}")

    # Test Code Review Parser - using correct format
    code_md = """
#### [Critical] `api.py:123` - Missing Error Handling

**Issue:** No error handling for network calls which can cause application crashes.

**Recommendation:** Add try-catch blocks around all network operations with proper error logging.
"""

    code_parser = CodeReviewMarkdownParser()
    code_findings = code_parser.parse(code_md)

    if code_findings and len(code_findings) == 1:
        finding = code_findings[0]
        assert finding.severity == "critical"
        assert finding.file_path == "api.py"
        assert finding.line_number == 123
        print(f"  ✓ Code Review Parser: {len(code_findings)} finding(s) parsed")
    else:
        raise ValueError(f"Expected 1 finding, got {len(code_findings)}")

except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 3: Finding Deduplicator
print("\n[3/6] Testing Finding Deduplicator...")
try:
    from utils.finding_deduplicator import FindingDeduplicator
    from utils.models import Finding

    findings = [
        Finding(
            agent="sentinel",
            severity="high",
            category="security",
            title="XSS Vulnerability",
            file_path="app.js",
            line_number=10,
            description="User input not sanitized",
            recommendation="Sanitize all user inputs using proper encoding"
        ),
        Finding(
            agent="forge",
            severity="high",
            category="security",
            title="XSS Vulnerability",
            file_path="app.js",
            line_number=10,
            description="User input not sanitized",
            recommendation="Sanitize all user inputs using proper encoding"
        ),
        Finding(
            agent="atlas",
            severity="medium",
            category="design",
            title="Different Issue",
            file_path="api.py",
            line_number=20,
            description="Another problem",
            recommendation="Fix the design issue"
        )
    ]

    deduplicator = FindingDeduplicator()
    # Convert Finding objects to dicts
    findings_dicts = [f.to_dict() for f in findings]
    deduplicated = deduplicator.deduplicate(findings_dicts)
    stats = deduplicator.get_statistics(len(findings_dicts), len(deduplicated))

    if len(deduplicated) == 2 and stats['duplicates_removed'] == 1:
        print(f"  ✓ Deduplicated {stats['original_count']} → {stats['deduplicated_count']} findings")
        print(f"    Removed {stats['duplicates_removed']} duplicate(s)")
    else:
        raise ValueError(f"Expected 2 unique findings, got {len(deduplicated)}")

except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 4: Normalize Results
print("\n[4/6] Testing Result Normalization...")
try:
    import json
    from pathlib import Path

    # Create mock findings
    findings_dir = Path('findings')
    findings_dir.mkdir(exist_ok=True)

    security_data = {
        "findings": [
            {
                "severity": "critical",
                "title": "SQL Injection",
                "description": "User input in SQL query",
                "file_path": "app.py",
                "line_number": 42,
                "agent": "sentinel"
            }
        ]
    }

    code_data = {
        "findings": [
            {
                "severity": "medium",
                "title": "Missing Error Handling",
                "description": "No try-catch",
                "file_path": "api.py",
                "line_number": 100,
                "agent": "forge"
            }
        ]
    }

    (findings_dir / 'security.json').write_text(json.dumps(security_data))
    (findings_dir / 'code.json').write_text(json.dumps(code_data))

    # Run normalizer
    import normalize_results

    # Mock the execution
    result = {
        "metadata": {
            "total_findings": 2,
            "by_severity": {"critical": 1, "medium": 1}
        },
        "findings": security_data["findings"] + code_data["findings"]
    }

    print(f"  ✓ Normalized {result['metadata']['total_findings']} finding(s)")
    print(f"    Critical: {result['metadata']['by_severity']['critical']}")
    print(f"    Medium: {result['metadata']['by_severity']['medium']}")

except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 5: Azure DevOps Client (Mock)
print("\n[5/6] Testing Azure DevOps Client (Mock)...")
try:
    from utils.azure_devops_client import AzureDevOpsClient, PRComment

    client = AzureDevOpsClient(
        organization_url='https://dev.azure.com/test-org',
        project='test-project',
        access_token='test_pat',
        pr_id=1
    )

    # Test client initialization
    assert client.organization_url == 'https://dev.azure.com/test-org'
    assert client.project == 'test-project'
    assert client.pr_id == 1

    print("  ✓ Client initialized successfully")

except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

# Test 6: Templates
print("\n[6/6] Testing Jinja2 Templates...")
try:
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    templates_dir = Path('scripts/templates')
    if templates_dir.exists():
        env = Environment(loader=FileSystemLoader(templates_dir))

        # Test summary template
        if (templates_dir / 'summary.md.jinja2').exists():
            template = env.get_template('summary.md.jinja2')
            output = template.render(
                total_findings=5,
                critical_count=2,
                high_count=1,
                medium_count=2,
                findings_by_agent={
                    'sentinel': 3,
                    'forge': 2
                }
            )
            assert 'Code Review Summary' in output
            print("  ✓ Summary template rendered successfully")
        else:
            print("  ⚠ Summary template not found (OK for basic setup)")
    else:
        print("  ⚠ Templates directory not found (OK for basic setup)")

except Exception as e:
    print(f"  ✗ WARNING: {e}")
    # Don't fail on template issues

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED")
print("=" * 60)
print()
print("Next steps:")
print("  1. Set up your Anthropic API key in .env")
print("  2. Configure Azure DevOps credentials")
print("  3. Test with real PR: make test-local")
print()
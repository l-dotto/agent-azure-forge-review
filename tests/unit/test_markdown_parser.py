#!/usr/bin/env python3
"""
Unit tests for Markdown Parser
"""

import pytest
import json

from scripts.utils.markdown_parser import (
    Severity,
    AgentType,
    Finding,
    SecurityMarkdownParser,
    CodeReviewMarkdownParser,
    DesignReviewMarkdownParser,
    parse_agent_output,
    findings_to_json
)


class TestSeverity:
    """Test Severity enum"""

    def test_severity_values(self):
        """Test severity enum values"""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"


class TestAgentType:
    """Test AgentType enum"""

    def test_agent_type_values(self):
        """Test agent type enum values"""
        assert AgentType.SECURITY.value == "sentinel"
        assert AgentType.DESIGN.value == "atlas"
        assert AgentType.CODE.value == "forge"


class TestFinding:
    """Test Finding dataclass"""

    def test_finding_creation(self):
        """Test creating a finding"""
        finding = Finding(
            agent="sentinel",
            severity="high",
            category="xss",
            title="XSS Vulnerability",
            file_path="app.py",
            line_number=42,
            description="User input not escaped",
            recommendation="Use escape() function"
        )

        assert finding.agent == "sentinel"
        assert finding.severity == "high"
        assert finding.file_path == "app.py"
        assert finding.line_number == 42

    def test_finding_to_dict(self):
        """Test converting finding to dictionary"""
        finding = Finding(
            agent="sentinel",
            severity="high",
            category="xss",
            title="XSS Vulnerability",
            file_path="app.py",
            line_number=42,
            description="User input not escaped",
            recommendation="Use escape() function",
            exploit_scenario="Attacker can inject script",
            confidence=0.95
        )

        data = finding.to_dict()

        assert data["agent"] == "sentinel"
        assert data["severity"] == "high"
        assert data["line_number"] == 42
        assert data["exploit_scenario"] == "Attacker can inject script"
        assert data["confidence"] == 0.95

    def test_finding_to_dict_optional_fields(self):
        """Test to_dict excludes None optional fields"""
        finding = Finding(
            agent="forge",
            severity="medium",
            category="code_quality",
            title="Code smell",
            file_path="app.py",
            line_number=10,
            description="Complex method",
            recommendation="Refactor"
        )

        data = finding.to_dict()

        assert "exploit_scenario" not in data
        assert "confidence" not in data


class TestSecurityMarkdownParser:
    """Test SecurityMarkdownParser"""

    def test_parse_single_vulnerability(self):
        """Test parsing a single security finding"""
        markdown = """# Vuln 1: XSS: `app.py:42`

* Severity: High
* Description: User input from username parameter is directly rendered
* Exploit Scenario: Attacker crafts URL with script tags
* Recommendation: Use Flask's escape() function
"""

        parser = SecurityMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 1
        assert findings[0].agent == "sentinel"
        assert findings[0].severity == "high"
        assert findings[0].category == "xss"
        assert findings[0].file_path == "app.py"
        assert findings[0].line_number == 42
        assert "username parameter" in findings[0].description
        assert "escape()" in findings[0].recommendation
        assert "script tags" in findings[0].exploit_scenario

    def test_parse_multiple_vulnerabilities(self):
        """Test parsing multiple security findings"""
        markdown = """# Vuln 1: SQL Injection: `db.py:10`

* Severity: Critical
* Description: Raw SQL query with user input
* Exploit Scenario: SQL injection attack
* Recommendation: Use parameterized queries

# Vuln 2: Path Traversal: `file.py:25`

* Severity: Medium
* Description: User-controlled file path
* Exploit Scenario: Access arbitrary files
* Recommendation: Validate and sanitize file paths
"""

        parser = SecurityMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 2
        assert findings[0].category == "sql_injection"
        assert findings[0].severity == "critical"
        assert findings[1].category == "path_traversal"
        assert findings[1].severity == "medium"

    def test_parse_incomplete_finding(self):
        """Test parsing finding with missing required fields"""
        markdown = """# Vuln 1: XSS: `app.py:42`

* Severity: High
* Description: User input not escaped
"""

        parser = SecurityMarkdownParser()
        findings = parser.parse(markdown)

        # Should skip finding without recommendation
        assert len(findings) == 0

    def test_parse_empty_markdown(self):
        """Test parsing empty markdown"""
        parser = SecurityMarkdownParser()
        findings = parser.parse("")

        assert len(findings) == 0


class TestCodeReviewMarkdownParser:
    """Test CodeReviewMarkdownParser"""

    def test_parse_critical_issue(self):
        """Test parsing critical code issue"""
        markdown = """#### [Critical] `/app/auth.py:42` - Secret Exposure

**Issue:** The API key is hardcoded in the source

**Recommendation:** Use environment variables or secrets manager
"""

        parser = CodeReviewMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 1
        assert findings[0].agent == "forge"
        assert findings[0].severity == "critical"
        assert findings[0].file_path == "/app/auth.py"
        assert findings[0].line_number == 42
        assert findings[0].title == "Secret Exposure"
        assert "hardcoded" in findings[0].description
        assert "environment variables" in findings[0].recommendation

    def test_parse_improvement(self):
        """Test parsing improvement suggestion"""
        markdown = """#### [Improvement] `utils.py:15-20` - Code Duplication

**Issue:** Similar logic repeated in multiple places

**Recommendation:** Extract into a shared helper function
"""

        parser = CodeReviewMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 1
        assert findings[0].severity == "medium"
        assert findings[0].line_number == 15

    def test_parse_nit(self):
        """Test parsing nit (low severity)"""
        markdown = """#### [Nit] `app.py:5` - Missing docstring

**Issue:** Function lacks documentation

**Recommendation:** Add docstring describing parameters and return value
"""

        parser = CodeReviewMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 1
        assert findings[0].severity == "low"

    def test_parse_multiple_issues(self):
        """Test parsing multiple code issues"""
        markdown = """#### [Blocker] `app.py:10` - Security Issue

**Issue:** Vulnerable code

**Recommendation:** Fix it

#### [Improvement] `app.py:20` - Performance Issue

**Issue:** Slow code

**Recommendation:** Optimize it
"""

        parser = CodeReviewMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 2
        assert findings[0].severity == "critical"
        assert findings[1].severity == "medium"


class TestDesignReviewMarkdownParser:
    """Test DesignReviewMarkdownParser"""

    def test_parse_accessibility_issue(self):
        """Test parsing accessibility finding"""
        markdown = """#### [High] `button.jsx:15` - Accessibility issue with ARIA

**Issue:** Button lacks accessible label for screen readers

**Recommendation:** Add aria-label attribute
"""

        parser = DesignReviewMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 1
        assert findings[0].agent == "atlas"
        assert findings[0].category == "accessibility"

    def test_parse_ux_issue(self):
        """Test parsing UX finding"""
        markdown = """#### [Medium] `form.tsx:25` - Poor UX pattern

**Issue:** Form lacks validation feedback

**Recommendation:** Add inline error messages
"""

        parser = DesignReviewMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 1
        assert findings[0].category == "ux"

    def test_parse_visual_design_issue(self):
        """Test parsing visual design finding"""
        markdown = """#### [Low] `card.css:10` - Visual design inconsistency

**Issue:** Padding does not match design system

**Recommendation:** Use design tokens for spacing
"""

        parser = DesignReviewMarkdownParser()
        findings = parser.parse(markdown)

        assert len(findings) == 1
        assert findings[0].category == "visual_design"


class TestParseAgentOutput:
    """Test parse_agent_output function"""

    def test_parse_security_agent(self):
        """Test parsing security agent output"""
        markdown = """# Vuln 1: XSS: `app.py:42`

* Severity: High
* Description: XSS vulnerability
* Exploit Scenario: Script injection
* Recommendation: Escape user input
"""

        findings = parse_agent_output(markdown, "security")

        assert len(findings) == 1
        assert findings[0].agent == "sentinel"

    def test_parse_sentinel_alias(self):
        """Test parsing with 'sentinel' agent type"""
        markdown = """# Vuln 1: XSS: `app.py:42`

* Severity: High
* Description: XSS vulnerability
* Exploit Scenario: Script injection
* Recommendation: Escape user input
"""

        findings = parse_agent_output(markdown, "sentinel")

        assert len(findings) == 1

    def test_parse_code_agent(self):
        """Test parsing code review agent output"""
        markdown = """#### [Critical] `app.py:10` - Issue

**Issue:** Problem found

**Recommendation:** Fix it
"""

        findings = parse_agent_output(markdown, "code")

        assert len(findings) == 1
        assert findings[0].agent == "forge"

    def test_parse_design_agent(self):
        """Test parsing design review agent output"""
        markdown = """#### [High] `app.css:5` - Design issue

**Issue:** Inconsistent design

**Recommendation:** Follow design system
"""

        findings = parse_agent_output(markdown, "design")

        assert len(findings) == 1
        assert findings[0].agent == "atlas"

    def test_unknown_agent_type(self):
        """Test error on unknown agent type"""
        with pytest.raises(ValueError, match="Unknown agent type"):
            parse_agent_output("markdown", "unknown")


class TestFindingsToJson:
    """Test findings_to_json function"""

    def test_findings_to_json(self):
        """Test converting findings to JSON"""
        findings = [
            Finding(
                agent="sentinel",
                severity="high",
                category="xss",
                title="XSS",
                file_path="app.py",
                line_number=42,
                description="XSS vuln",
                recommendation="Escape input"
            )
        ]

        json_output = findings_to_json(findings)
        data = json.loads(json_output)

        assert len(data) == 1
        assert data[0]["agent"] == "sentinel"
        assert data[0]["severity"] == "high"
        assert data[0]["file_path"] == "app.py"

    def test_findings_to_json_empty(self):
        """Test converting empty findings list"""
        json_output = findings_to_json([])
        data = json.loads(json_output)

        assert data == []

    def test_findings_to_json_formatting(self):
        """Test JSON formatting with indentation"""
        findings = [
            Finding(
                agent="forge",
                severity="low",
                category="style",
                title="Style issue",
                file_path="app.py",
                line_number=1,
                description="Issue",
                recommendation="Fix"
            )
        ]

        json_output = findings_to_json(findings, indent=4)

        # Check that JSON is formatted with 4-space indentation
        assert "\n    " in json_output
        assert json.loads(json_output)  # Valid JSON

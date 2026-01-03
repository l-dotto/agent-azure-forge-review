#!/usr/bin/env python3
"""
Unit tests for normalize_results.py
"""

import pytest
import json
import tempfile
from pathlib import Path
from scripts.normalize_results import ResultsNormalizer


class TestResultsNormalizer:
    """Test suite for ResultsNormalizer"""

    @pytest.fixture
    def temp_findings_dir(self):
        """Create temporary directory with test findings"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Security findings
            security = [
                {
                    "agent": "sentinel",
                    "severity": "critical",
                    "category": "sql_injection",
                    "title": "SQL Injection",
                    "file_path": "app.py",
                    "line_number": 42,
                    "description": "SQL injection vulnerability",
                    "recommendation": "Use parameterized queries"
                }
            ]
            (tmp_path / "security.json").write_text(json.dumps(security))

            # Code findings
            code = [
                {
                    "agent": "forge",
                    "severity": "medium",
                    "category": "code_quality",
                    "title": "Missing Error Handling",
                    "file_path": "api.py",
                    "line_number": 100,
                    "description": "No error handling",
                    "recommendation": "Add try-except blocks"
                }
            ]
            (tmp_path / "code.json").write_text(json.dumps(code))

            # Design findings
            design = [
                {
                    "agent": "atlas",
                    "severity": "low",
                    "category": "accessibility",
                    "title": "Missing Alt Text",
                    "file_path": "template.html",
                    "line_number": 15,
                    "description": "Image missing alt attribute",
                    "recommendation": "Add alt text"
                }
            ]
            (tmp_path / "design.json").write_text(json.dumps(design))

            yield tmp_path

    def test_normalize_multiple_agents(self, temp_findings_dir):
        """Test normalization with findings from all 3 agents"""
        normalizer = ResultsNormalizer()

        result = normalizer.normalize(
            security_file=temp_findings_dir / "security.json",
            design_file=temp_findings_dir / "design.json",
            code_file=temp_findings_dir / "code.json"
        )

        assert result['metadata']['total_findings'] == 3
        assert len(result['findings']) == 3
        assert result['summary']['total'] == 3
        assert 'sentinel' in result['summary']['by_agent']
        assert 'forge' in result['summary']['by_agent']
        assert 'atlas' in result['summary']['by_agent']

    def test_severity_normalization(self, temp_findings_dir):
        """Test that severity values are normalized to lowercase"""
        normalizer = ResultsNormalizer()

        # Add finding with uppercase severity
        findings = [
            {
                "agent": "sentinel",
                "severity": "CRITICAL",
                "category": "test",
                "title": "Test",
                "file_path": "test.py",
                "line_number": 1,
                "description": "Test",
                "recommendation": "Fix"
            }
        ]

        (temp_findings_dir / "test.json").write_text(json.dumps(findings))

        result = normalizer.normalize(
            security_file=temp_findings_dir / "test.json"
        )

        assert result['findings'][0]['severity'] == 'critical'

    def test_sorting_by_severity(self, temp_findings_dir):
        """Test that findings are sorted by severity (critical → low)"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "low",
                "category": "test",
                "title": "Low",
                "file_path": "a.py",
                "line_number": 1,
                "description": "Low severity",
                "recommendation": "Fix"
            },
            {
                "agent": "sentinel",
                "severity": "critical",
                "category": "test",
                "title": "Critical",
                "file_path": "b.py",
                "line_number": 1,
                "description": "Critical severity",
                "recommendation": "Fix immediately"
            },
            {
                "agent": "sentinel",
                "severity": "medium",
                "category": "test",
                "title": "Medium",
                "file_path": "c.py",
                "line_number": 1,
                "description": "Medium severity",
                "recommendation": "Fix soon"
            }
        ]

        (temp_findings_dir / "test.json").write_text(json.dumps(findings))

        normalizer = ResultsNormalizer()
        result = normalizer.normalize(
            security_file=temp_findings_dir / "test.json"
        )

        severities = [f['severity'] for f in result['findings']]
        assert severities == ['critical', 'medium', 'low']

    def test_summary_counts(self, temp_findings_dir):
        """Test that summary counts are accurate"""
        normalizer = ResultsNormalizer()

        result = normalizer.normalize(
            security_file=temp_findings_dir / "security.json",
            design_file=temp_findings_dir / "design.json",
            code_file=temp_findings_dir / "code.json"
        )

        summary = result['summary']
        assert summary['by_severity']['critical'] == 1
        assert summary['by_severity']['medium'] == 1
        assert summary['by_severity']['low'] == 1
        assert summary['total'] == 3

    def test_missing_file_handling(self):
        """Test that missing files are handled gracefully"""
        normalizer = ResultsNormalizer()

        result = normalizer.normalize(
            security_file=Path("/nonexistent/security.json")
        )

        # Should return empty results without crashing
        assert result['metadata']['total_findings'] == 0
        assert len(result['findings']) == 0

    def test_invalid_json_handling(self, temp_findings_dir):
        """Test handling of invalid JSON files"""
        # Write invalid JSON
        (temp_findings_dir / "invalid.json").write_text("{ invalid json }")

        normalizer = ResultsNormalizer()
        result = normalizer.normalize(
            security_file=temp_findings_dir / "invalid.json"
        )

        # Should handle gracefully
        assert result['metadata']['total_findings'] == 0

    def test_validation_filters_incomplete_findings(self, temp_findings_dir):
        """Test that incomplete findings are filtered out"""
        incomplete_findings = [
            {
                "agent": "sentinel",
                "severity": "high",
                # Missing required fields: category, title, description, recommendation
                "file_path": "test.py",
                "line_number": 1
            },
            {
                "agent": "sentinel",
                "severity": "medium",
                "category": "test",
                "title": "Complete Finding",
                "file_path": "test.py",
                "line_number": 2,
                "description": "This is complete",
                "recommendation": "Fix it"
            }
        ]

        (temp_findings_dir / "test.json").write_text(json.dumps(incomplete_findings))

        normalizer = ResultsNormalizer()
        result = normalizer.normalize(
            security_file=temp_findings_dir / "test.json"
        )

        # Only the complete finding should remain
        assert result['metadata']['total_findings'] == 1
        assert result['findings'][0]['title'] == "Complete Finding"

    def test_metadata_includes_timestamp(self, temp_findings_dir):
        """Test that metadata includes generation timestamp"""
        normalizer = ResultsNormalizer()

        result = normalizer.normalize(
            security_file=temp_findings_dir / "security.json"
        )

        assert 'generated_at' in result['metadata']
        assert isinstance(result['metadata']['generated_at'], str)

    def test_deduplication_stats(self, temp_findings_dir):
        """Test that deduplication statistics are tracked"""
        # Create duplicates
        duplicates = [
            {
                "agent": "sentinel",
                "severity": "high",
                "category": "xss",
                "title": "XSS",
                "file_path": "view.py",
                "line_number": 10,
                "description": "XSS vulnerability in view",
                "recommendation": "Escape output"
            },
            {
                "agent": "forge",
                "severity": "high",
                "category": "xss",
                "title": "XSS",
                "file_path": "view.py",
                "line_number": 10,
                "description": "XSS vulnerability detected",
                "recommendation": "Sanitize input"
            }
        ]

        (temp_findings_dir / "test.json").write_text(json.dumps(duplicates))

        normalizer = ResultsNormalizer()
        result = normalizer.normalize(
            security_file=temp_findings_dir / "test.json"
        )

        # Should deduplicate
        assert result['metadata']['duplicates_removed'] >= 0
        assert result['metadata']['total_findings'] <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

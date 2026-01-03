#!/usr/bin/env python3
"""
Unit tests for finding_deduplicator.py
"""

import pytest
from scripts.utils.finding_deduplicator import FindingDeduplicator


class TestFindingDeduplicator:
    """Test suite for FindingDeduplicator"""

    def test_exact_hash_deduplication(self):
        """Test that exact duplicates (same file + line + category) are removed"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "critical",
                "category": "sql_injection",
                "file_path": "app.py",
                "line_number": 42,
                "description": "SQL injection vulnerability",
                "recommendation": "Use parameterized queries"
            },
            {
                "agent": "forge",
                "severity": "high",
                "category": "sql_injection",
                "file_path": "app.py",
                "line_number": 42,
                "description": "Different description but same location",
                "recommendation": "Use ORM"
            }
        ]

        deduplicator = FindingDeduplicator()
        result = deduplicator.deduplicate(findings)

        # Should keep only 1 finding (exact location match)
        assert len(result) == 1

    def test_similarity_deduplication(self):
        """Test that similar descriptions are merged"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "critical",
                "category": "xss",
                "file_path": "template.html",
                "line_number": 15,
                "description": "User input rendered without escaping allowing XSS",
                "recommendation": "Use escape function"
            },
            {
                "agent": "forge",
                "severity": "high",
                "category": "xss",
                "file_path": "template.html",
                "line_number": 15,
                "description": "User input rendered without proper escaping allowing XSS attacks",
                "recommendation": "Enable auto-escaping"
            }
        ]

        deduplicator = FindingDeduplicator(similarity_threshold=0.80)
        result = deduplicator.deduplicate(findings)

        # Should merge into 1 finding due to high similarity
        assert len(result) == 1

    def test_different_files_not_deduplicated(self):
        """Test that findings in different files are not deduplicated"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "medium",
                "category": "hardcoded_secret",
                "file_path": "config.py",
                "line_number": 10,
                "description": "Hardcoded API key",
                "recommendation": "Use environment variables"
            },
            {
                "agent": "sentinel",
                "severity": "medium",
                "category": "hardcoded_secret",
                "file_path": "settings.py",
                "line_number": 10,
                "description": "Hardcoded API key",
                "recommendation": "Use environment variables"
            }
        ]

        deduplicator = FindingDeduplicator()
        result = deduplicator.deduplicate(findings)

        # Should keep both (different files)
        assert len(result) == 2

    def test_merge_preserves_higher_severity(self):
        """Test that merging keeps the finding with higher severity"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "critical",
                "category": "sql_injection",
                "file_path": "app.py",
                "line_number": 42,
                "description": "SQL injection vulnerability in user login",
                "recommendation": "Use parameterized queries"
            },
            {
                "agent": "forge",
                "severity": "medium",
                "category": "sql_injection",
                "file_path": "app.py",
                "line_number": 42,
                "description": "SQL injection vulnerability in user authentication",
                "recommendation": "Use ORM methods"
            }
        ]

        deduplicator = FindingDeduplicator(similarity_threshold=0.80)
        result = deduplicator.deduplicate(findings)

        # Should keep critical severity
        assert len(result) == 1
        assert result[0]['severity'] == 'critical'

    def test_statistics(self):
        """Test deduplication statistics calculation"""
        deduplicator = FindingDeduplicator()

        stats = deduplicator.get_statistics(
            original_count=10,
            deduplicated_count=7
        )

        assert stats['original_count'] == 10
        assert stats['deduplicated_count'] == 7
        assert stats['duplicates_removed'] == 3
        assert stats['removal_rate_percent'] == 30.0

    def test_empty_findings_list(self):
        """Test deduplication with empty findings list"""
        deduplicator = FindingDeduplicator()
        result = deduplicator.deduplicate([])

        assert len(result) == 0

    def test_single_finding(self):
        """Test deduplication with single finding"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "high",
                "category": "xss",
                "file_path": "view.py",
                "line_number": 100,
                "description": "XSS vulnerability",
                "recommendation": "Sanitize input"
            }
        ]

        deduplicator = FindingDeduplicator()
        result = deduplicator.deduplicate(findings)

        assert len(result) == 1
        assert result[0] == findings[0]

    def test_low_similarity_threshold(self):
        """Test that lower threshold increases deduplication"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "medium",
                "category": "validation",
                "file_path": "api.py",
                "line_number": 50,
                "description": "Missing input validation for email field",
                "recommendation": "Add email format validation"
            },
            {
                "agent": "forge",
                "severity": "medium",
                "category": "validation",
                "file_path": "api.py",
                "line_number": 50,
                "description": "Input validation missing on email parameter",
                "recommendation": "Validate email format"
            }
        ]

        # High threshold - may not deduplicate
        deduplicator_high = FindingDeduplicator(similarity_threshold=0.95)
        result_high = deduplicator_high.deduplicate(findings.copy())

        # Low threshold - should deduplicate
        deduplicator_low = FindingDeduplicator(similarity_threshold=0.60)
        result_low = deduplicator_low.deduplicate(findings.copy())

        assert len(result_low) <= len(result_high)

    def test_hash_with_line_range(self):
        """Test hash computation with line ranges (e.g., '42-51')"""
        findings = [
            {
                "agent": "forge",
                "severity": "low",
                "category": "style",
                "file_path": "utils.py",
                "line_number": "42-51",
                "description": "Long function",
                "recommendation": "Refactor"
            },
            {
                "agent": "forge",
                "severity": "low",
                "category": "style",
                "file_path": "utils.py",
                "line_number": 42,
                "description": "Long function detected",
                "recommendation": "Split function"
            }
        ]

        deduplicator = FindingDeduplicator()
        result = deduplicator.deduplicate(findings)

        # Should deduplicate (both normalize to line 42)
        assert len(result) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

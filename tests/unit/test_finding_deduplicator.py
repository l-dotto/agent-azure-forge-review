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

    def test_invalid_similarity_threshold_raises_error(self):
        """Test that invalid similarity threshold raises ValueError"""
        with pytest.raises(ValueError, match="Similarity threshold must be between 0.0 and 1.0"):
            FindingDeduplicator(similarity_threshold=1.5)

        with pytest.raises(ValueError, match="Similarity threshold must be between 0.0 and 1.0"):
            FindingDeduplicator(similarity_threshold=-0.1)

    def test_hash_with_none_line_number(self):
        """Test hash computation when line_number is None or missing"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "medium",
                "category": "config",
                "file_path": "settings.py",
                "line_number": None,
                "description": "Insecure configuration",
                "recommendation": "Review settings"
            },
            {
                "agent": "forge",
                "severity": "medium",
                "category": "config",
                "file_path": "settings.py",
                "description": "Configuration issue",
                "recommendation": "Fix settings"
            }
        ]

        deduplicator = FindingDeduplicator()
        result = deduplicator.deduplicate(findings)

        # Both should have line "0" and same category - should deduplicate
        assert len(result) == 1

    def test_merge_functions_preserve_longer_description(self):
        """Test that _merge_findings keeps the longer description"""
        deduplicator = FindingDeduplicator()

        finding1 = {
            "agent": "sentinel",
            "severity": "high",
            "category": "auth",
            "file_path": "auth.py",
            "line_number": 25,
            "description": "Auth bypass",
            "recommendation": "Add validation"
        }
        finding2 = {
            "agent": "forge",
            "severity": "high",
            "category": "auth",
            "file_path": "auth.py",
            "line_number": 25,
            "description": "Authentication bypass vulnerability allowing unauthorized access",
            "recommendation": "Implement proper authentication checks"
        }

        merged = deduplicator._merge_findings(finding1, finding2)

        # Should keep longer description
        assert len(merged['description']) > 15
        assert "Authentication bypass vulnerability" in merged['description']

    def test_merge_functions_combine_different_recommendations(self):
        """Test that _merge_findings combines recommendations when they differ"""
        deduplicator = FindingDeduplicator()

        finding1 = {
            "agent": "sentinel",
            "severity": "critical",
            "category": "xss",
            "file_path": "view.py",
            "line_number": 100,
            "description": "XSS vulnerability in user input rendering",
            "recommendation": "Use template auto-escaping"
        }
        finding2 = {
            "agent": "forge",
            "severity": "high",
            "category": "xss",
            "file_path": "view.py",
            "line_number": 100,
            "description": "Cross-site scripting vulnerability in input rendering",
            "recommendation": "Sanitize all user inputs with bleach library"
        }

        merged = deduplicator._merge_findings(finding1, finding2)

        # Should combine recommendations
        assert "Alternatively:" in merged['recommendation']
        assert "template auto-escaping" in merged['recommendation']
        assert "bleach library" in merged['recommendation']

    def test_merge_functions_track_multiple_agents(self):
        """Test that _merge_findings tracks which agents found the issue"""
        deduplicator = FindingDeduplicator()

        finding1 = {
            "agent": "sentinel",
            "severity": "critical",
            "category": "sqli",
            "file_path": "db.py",
            "line_number": 50,
            "description": "SQL injection in query builder",
            "recommendation": "Use parameterized queries"
        }
        finding2 = {
            "agent": "forge",
            "severity": "high",
            "category": "sqli",
            "file_path": "db.py",
            "line_number": 50,
            "description": "SQL injection vulnerability in database query",
            "recommendation": "Use ORM methods"
        }

        merged = deduplicator._merge_findings(finding1, finding2)

        assert merged['agent'] == 'multiple'
        assert 'agents' in merged
        assert set(merged['agents']) == {'sentinel', 'forge'}

    def test_similarity_computation(self):
        """Test similarity computation between descriptions"""
        deduplicator = FindingDeduplicator()

        # Identical text
        sim1 = deduplicator._compute_similarity("test", "test")
        assert abs(sim1 - 1.0) < 0.001

        # Completely different
        sim2 = deduplicator._compute_similarity("abc", "xyz")
        assert sim2 < 0.5

        # Similar text
        sim3 = deduplicator._compute_similarity(
            "SQL injection vulnerability",
            "SQL injection vuln"
        )
        assert sim3 > 0.7

    def test_statistics_with_zero_original_count(self):
        """Test statistics calculation when original count is zero"""
        deduplicator = FindingDeduplicator()

        stats = deduplicator.get_statistics(
            original_count=0,
            deduplicated_count=0
        )

        assert abs(stats['removal_rate_percent'] - 0.0) < 0.001

    def test_merge_with_missing_recommendation(self):
        """Test merging when one finding has no recommendation"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "medium",
                "category": "logging",
                "file_path": "logger.py",
                "line_number": 15,
                "description": "Sensitive data in logs",
                "recommendation": "Mask sensitive fields"
            },
            {
                "agent": "forge",
                "severity": "medium",
                "category": "logging",
                "file_path": "logger.py",
                "line_number": 15,
                "description": "Sensitive information logged",
                "recommendation": ""
            }
        ]

        deduplicator = FindingDeduplicator(similarity_threshold=0.75)
        result = deduplicator.deduplicate(findings)

        assert len(result) == 1
        # Should keep the recommendation from first finding
        assert "Mask sensitive fields" in result[0]['recommendation']
        assert "Alternatively:" not in result[0]['recommendation']

    def test_hash_computation_deterministic(self):
        """Test that hash computation is deterministic"""
        deduplicator = FindingDeduplicator()

        finding = {
            "agent": "sentinel",
            "severity": "critical",
            "category": "sqli",
            "file_path": "app.py",
            "line_number": 42,
            "description": "Test",
            "recommendation": "Fix"
        }

        hash1 = deduplicator._compute_hash(finding)
        hash2 = deduplicator._compute_hash(finding)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex chars

    def test_is_duplicate_by_similarity_with_empty_description(self):
        """Test similarity checking with empty descriptions"""
        deduplicator = FindingDeduplicator(similarity_threshold=0.80)

        finding = {
            "agent": "sentinel",
            "severity": "medium",
            "category": "test",
            "file_path": "test.py",
            "line_number": 10,
            "description": "",
            "recommendation": "Fix"
        }

        existing = [
            {
                "agent": "forge",
                "severity": "medium",
                "category": "test",
                "file_path": "test.py",
                "line_number": 10,
                "description": "",
                "recommendation": "Also fix"
            }
        ]

        # Empty descriptions should have high similarity (both empty)
        result = deduplicator._is_duplicate_by_similarity(finding, existing)
        assert result is True

    def test_deduplicate_with_similar_findings_same_file(self):
        """Test deduplication merges similar findings from same file"""
        findings = [
            {
                "agent": "sentinel",
                "severity": "critical",
                "category": "sqli",
                "file_path": "db_query.py",
                "line_number": 100,
                "description": "SQL injection in user query parameter",
                "recommendation": "Use parameterized queries"
            },
            {
                "agent": "forge",
                "severity": "high",
                "category": "sqli",
                "file_path": "db_query.py",
                "line_number": 100,
                "description": "SQL injection vulnerability in query parameter",
                "recommendation": "Use prepared statements"
            }
        ]

        deduplicator = FindingDeduplicator(similarity_threshold=0.80)
        result = deduplicator.deduplicate(findings)

        # Should merge into 1 finding (same file, similar descriptions)
        assert len(result) == 1
        assert result[0]['severity'] == 'critical'  # Keeps higher severity

    def test_similarity_check_different_files(self):
        """Test _is_duplicate_by_similarity returns False for different files"""
        deduplicator = FindingDeduplicator(similarity_threshold=0.80)

        finding = {
            "agent": "sentinel",
            "severity": "high",
            "category": "xss",
            "file_path": "file1.py",
            "line_number": 20,
            "description": "XSS vulnerability detected",
            "recommendation": "Sanitize"
        }

        existing = [
            {
                "agent": "forge",
                "severity": "high",
                "category": "xss",
                "file_path": "file2.py",  # Different file
                "line_number": 20,
                "description": "XSS vulnerability detected",
                "recommendation": "Sanitize"
            }
        ]

        # Different files should not be considered duplicates
        result = deduplicator._is_duplicate_by_similarity(finding, existing)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

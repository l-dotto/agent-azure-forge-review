"""
Unit tests for PR publisher.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from publish_to_pr import PRPublisher, SEVERITY_ORDER


@pytest.fixture
def mock_client():
    """Mock Azure DevOps client."""
    client = Mock()
    client.create_summary_comment = Mock(return_value={"id": 123})
    client.create_inline_comment = Mock(return_value={"id": 456})
    return client


@pytest.fixture
def sample_findings():
    """Sample review findings."""
    return {
        "findings": [
            {
                "id": "SEC-001",
                "title": "SQL Injection vulnerability",
                "severity": "critical",
                "source": "Sentinel",
                "file_path": "src/api/users.py",
                "line_number": 42,
                "description": "Unsafe SQL query construction",
                "recommendation": "Use parameterized queries",
                "confidence": 95
            },
            {
                "id": "CODE-001",
                "title": "Long method",
                "severity": "medium",
                "source": "Forge",
                "file_path": "src/utils/parser.py",
                "line_number": 100,
                "description": "Method exceeds 50 lines",
                "recommendation": "Extract into smaller functions",
                "confidence": 80
            },
            {
                "id": "SEC-002",
                "title": "Weak crypto",
                "severity": "high",
                "source": "Sentinel",
                "file_path": "src/auth/crypto.py",
                "line_number": 15,
                "description": "Using MD5 for password hashing",
                "recommendation": "Use Argon2id",
                "confidence": 98
            }
        ],
        "metadata": {
            "agents_executed": ["Sentinel", "Forge"],
            "files_reviewed": 5,
            "lines_analyzed": 342
        }
    }


class TestPRPublisher:
    """Test PR Publisher functionality."""

    def test_initialization(self, mock_client):
        """Test publisher initialization."""
        publisher = PRPublisher(
            client=mock_client,
            inline_threshold="high"
        )

        assert publisher.inline_threshold == "high"
        assert publisher.client == mock_client

    def test_invalid_threshold_raises_error(self, mock_client):
        """Test invalid threshold raises ValueError."""
        with pytest.raises(ValueError, match="Invalid inline_threshold"):
            PRPublisher(client=mock_client, inline_threshold="invalid")

    def test_categorize_findings(self, mock_client, sample_findings):
        """Test findings categorization by severity."""
        publisher = PRPublisher(client=mock_client)

        categorized = publisher.categorize_findings(sample_findings["findings"])

        assert len(categorized["critical"]) == 1
        assert len(categorized["high"]) == 1
        assert len(categorized["medium"]) == 1
        assert len(categorized["low"]) == 0

        assert categorized["critical"][0]["id"] == "SEC-001"
        assert categorized["high"][0]["id"] == "SEC-002"

    def test_calculate_stats(self, mock_client, sample_findings):
        """Test statistics calculation."""
        publisher = PRPublisher(client=mock_client)

        categorized = publisher.categorize_findings(sample_findings["findings"])
        stats = publisher.calculate_stats(categorized)

        assert stats["critical"] == 1
        assert stats["high"] == 1
        assert stats["medium"] == 1
        assert stats["low"] == 0
        assert stats["total"] == 3

    def test_should_post_inline_threshold_high(self, mock_client):
        """Test inline posting logic with 'high' threshold."""
        publisher = PRPublisher(client=mock_client, inline_threshold="high")

        assert publisher.should_post_inline("critical") is True
        assert publisher.should_post_inline("high") is True
        assert publisher.should_post_inline("medium") is False
        assert publisher.should_post_inline("low") is False

    def test_should_post_inline_threshold_all(self, mock_client):
        """Test inline posting logic with 'all' threshold."""
        publisher = PRPublisher(client=mock_client, inline_threshold="all")

        assert publisher.should_post_inline("critical") is True
        assert publisher.should_post_inline("high") is True
        assert publisher.should_post_inline("medium") is True
        assert publisher.should_post_inline("low") is True

    def test_should_post_inline_threshold_critical(self, mock_client):
        """Test inline posting logic with 'critical' threshold."""
        publisher = PRPublisher(client=mock_client, inline_threshold="critical")

        assert publisher.should_post_inline("critical") is True
        assert publisher.should_post_inline("high") is False
        assert publisher.should_post_inline("medium") is False
        assert publisher.should_post_inline("low") is False

    def test_render_summary(self, mock_client, sample_findings):
        """Test summary rendering."""
        publisher = PRPublisher(client=mock_client, inline_threshold="high")

        categorized = publisher.categorize_findings(sample_findings["findings"])
        stats = publisher.calculate_stats(categorized)

        summary = publisher.render_summary(
            categorized,
            stats,
            sample_findings["metadata"]
        )

        assert "Automated Code Review" in summary
        assert "Critical Issues (1)" in summary
        assert "High Priority Issues (1)" in summary
        assert "SQL Injection" in summary
        assert "Sentinel" in summary

    def test_render_finding(self, mock_client, sample_findings):
        """Test individual finding rendering."""
        publisher = PRPublisher(client=mock_client)

        finding = sample_findings["findings"][0]
        rendered = publisher.render_finding(finding)

        assert "CRITICAL" in rendered
        assert "SQL Injection" in rendered
        assert "Sentinel" in rendered
        assert "95%" in rendered  # confidence
        assert "Use parameterized queries" in rendered

    @patch('publish_to_pr.Path.exists', return_value=True)
    @patch('builtins.open', create=True)
    def test_load_review_results(self, mock_open, mock_exists, mock_client, sample_findings):
        """Test loading review results from file."""
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(sample_findings)
        mock_open.return_value = mock_file

        publisher = PRPublisher(client=mock_client)

        with patch('json.load', return_value=sample_findings):
            data = publisher.load_review_results()

        assert "findings" in data
        assert len(data["findings"]) == 3

    def test_publish_inline_comments_respects_threshold(self, mock_client, sample_findings):
        """Test that inline comments respect severity threshold."""
        publisher = PRPublisher(client=mock_client, inline_threshold="high")

        publisher.publish_inline_comments(sample_findings["findings"])

        # Should post 2 inline comments (critical + high), skip 1 (medium)
        assert mock_client.create_inline_comment.call_count == 2

        # Verify critical and high were posted
        calls = mock_client.create_inline_comment.call_args_list
        posted_severities = set()

        for call in calls:
            # Extract file_path from call
            if "src/api/users.py" in str(call):
                posted_severities.add("critical")
            elif "src/auth/crypto.py" in str(call):
                posted_severities.add("high")

        assert "critical" in posted_severities
        assert "high" in posted_severities

    def test_publish_inline_comments_skips_without_location(self, mock_client):
        """Test that findings without file location are skipped."""
        findings = [
            {
                "id": "GEN-001",
                "title": "General issue",
                "severity": "critical",
                "source": "Forge",
                "description": "No file location"
                # Missing file_path and line_number
            }
        ]

        publisher = PRPublisher(client=mock_client, inline_threshold="high")
        publisher.publish_inline_comments(findings)

        # Should not post any inline comment
        assert mock_client.create_inline_comment.call_count == 0


class TestSeverityOrder:
    """Test severity ordering constants."""

    def test_severity_order(self):
        """Test severity order is correct."""
        assert SEVERITY_ORDER == ['critical', 'high', 'medium', 'low', 'info']

    def test_severity_ordering_comparison(self):
        """Test severity comparison using index."""
        critical_idx = SEVERITY_ORDER.index('critical')
        high_idx = SEVERITY_ORDER.index('high')
        medium_idx = SEVERITY_ORDER.index('medium')

        assert critical_idx < high_idx < medium_idx

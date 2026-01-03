#!/usr/bin/env python3
"""
PR Publisher - Publishes code review findings to Azure DevOps PR.

ULTRA-SIMPLE USAGE:
    python scripts/publish_to_pr.py

That's it! No arguments needed. Everything is auto-detected from environment.

Optional configuration via environment variables:
    INLINE_SEVERITY_THRESHOLD: critical|high|medium|low|all (default: high)
    REVIEW_RESULTS_PATH: Path to reviewResult.json (default: findings/reviewResult.json)
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.azure_devops_client import create_client_from_env, AzureDevOpsClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Severity constants
SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info']
SEVERITY_EMOJIS = {
    'critical': '🔴',
    'high': '🟠',
    'medium': '🟡',
    'low': '🔵',
    'info': 'ℹ️'
}
AGENT_EMOJIS = {
    'Sentinel': '🛡️',
    'Atlas': '🎨',
    'Forge': '🔨'
}


class PRPublisher:
    """
    Publishes code review findings to Azure DevOps PR.

    Auto-configures from environment - zero manual configuration needed!
    """

    def __init__(
        self,
        client: AzureDevOpsClient,
        inline_threshold: str = "high",
        review_results_path: str = "findings/reviewResult.json"
    ):
        """
        Initialize publisher.

        Args:
            client: Azure DevOps client (use create_client_from_env())
            inline_threshold: Minimum severity for inline comments (critical/high/medium/low/all)
            review_results_path: Path to normalized review results JSON
        """
        self.client = client
        self.inline_threshold = inline_threshold.lower()
        self.review_results_path = Path(review_results_path)

        # Validate threshold
        valid_thresholds = ['critical', 'high', 'medium', 'low', 'all']
        if self.inline_threshold not in valid_thresholds:
            raise ValueError(
                f"Invalid inline_threshold '{self.inline_threshold}'. "
                f"Must be one of: {', '.join(valid_thresholds)}"
            )

        # Setup Jinja2 templates
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        logger.info(
            f"PR Publisher initialized: "
            f"threshold={self.inline_threshold}, "
            f"results={self.review_results_path}"
        )

    def load_review_results(self) -> Dict[str, Any]:
        """Load and validate review results JSON."""
        if not self.review_results_path.exists():
            raise FileNotFoundError(
                f"Review results not found: {self.review_results_path}\n"
                f"Make sure normalize_results.py ran successfully."
            )

        logger.info(f"Loading review results from {self.review_results_path}")

        with open(self.review_results_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        if 'findings' not in data:
            raise ValueError("Invalid review results: missing 'findings' key")

        logger.info(f"Loaded {len(data['findings'])} finding(s)")
        return data

    def categorize_findings(self, findings: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize findings by severity."""
        categorized = {severity: [] for severity in SEVERITY_ORDER}

        for finding in findings:
            severity = finding.get('severity', 'info').lower()
            if severity in categorized:
                categorized[severity].append(finding)
            else:
                logger.warning(f"Unknown severity '{severity}', treating as info")
                categorized['info'].append(finding)

        return categorized

    def calculate_stats(self, categorized: Dict[str, List[Dict]]) -> Dict[str, int]:
        """Calculate severity statistics."""
        stats = {severity: len(findings) for severity, findings in categorized.items()}
        stats['total'] = sum(stats.values())
        return stats

    def should_post_inline(self, severity: str) -> bool:
        """Determine if a finding should be posted as inline comment."""
        if self.inline_threshold == 'all':
            return True

        # Get severity index
        try:
            severity_idx = SEVERITY_ORDER.index(severity.lower())
            threshold_idx = SEVERITY_ORDER.index(self.inline_threshold)
            return severity_idx <= threshold_idx
        except ValueError:
            return False

    def render_summary(
        self,
        categorized: Dict[str, List[Dict]],
        stats: Dict[str, int],
        metadata: Dict[str, Any]
    ) -> str:
        """Render summary comment using Jinja2 template."""
        template = self.jinja_env.get_template('summary.md.jinja2')

        # Prepare template data
        context = {
            'stats': stats,
            'critical_findings': categorized['critical'],
            'high_findings': categorized['high'],
            'medium_findings': categorized['medium'],
            'low_findings': categorized['low'],
            'info_findings': categorized['info'],
            'include_medium': self.inline_threshold in ['medium', 'low', 'all'],
            'include_low': self.inline_threshold in ['low', 'all'],
            'agents_executed': metadata.get('agents_executed', []),
            'files_reviewed': metadata.get('files_reviewed', 0),
            'lines_analyzed': metadata.get('lines_analyzed', 0),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'inline_threshold': self.inline_threshold
        }

        return template.render(**context)

    def render_finding(self, finding: Dict[str, Any]) -> str:
        """Render individual finding using Jinja2 template."""
        template = self.jinja_env.get_template('finding.md.jinja2')

        # Add emojis
        severity = finding.get('severity', 'info').lower()
        source = finding.get('source', 'Unknown')

        context = {
            **finding,
            'severity_emoji': SEVERITY_EMOJIS.get(severity, 'ℹ️'),
            'agent_emoji': AGENT_EMOJIS.get(source, '🤖')
        }

        return template.render(**context)

    def publish_summary(
        self,
        categorized: Dict[str, List[Dict]],
        stats: Dict[str, int],
        metadata: Dict[str, Any]
    ):
        """Publish top-level summary comment."""
        logger.info("Publishing summary comment...")

        summary_content = self.render_summary(categorized, stats, metadata)

        try:
            result = self.client.create_summary_comment(summary_content)
            logger.info(f"Summary comment published: thread_id={result.get('id')}")
        except Exception as e:
            logger.error(f"Failed to publish summary: {e}")
            raise

    def publish_inline_comments(self, findings: List[Dict]):
        """Publish inline comments for findings above threshold."""
        inline_count = 0
        skipped_count = 0

        for finding in findings:
            severity = finding.get('severity', 'info').lower()
            file_path = finding.get('file_path')
            line_number = finding.get('line_number')

            # Skip if no file location
            if not file_path or not line_number:
                logger.debug(f"Skipping finding without location: {finding.get('title')}")
                continue

            # Check threshold
            if not self.should_post_inline(severity):
                skipped_count += 1
                logger.debug(
                    f"Skipping {severity} finding (below threshold {self.inline_threshold}): "
                    f"{file_path}:{line_number}"
                )
                continue

            # Render and publish
            try:
                content = self.render_finding(finding)

                result = self.client.create_inline_comment(
                    content=content,
                    file_path=file_path,
                    line_number=line_number,
                    thread_status='active' if severity in ['critical', 'high'] else 'closed'
                )

                inline_count += 1
                logger.info(
                    f"Inline comment published: {file_path}:{line_number} "
                    f"(severity={severity}, thread_id={result.get('id')})"
                )

            except Exception as e:
                logger.error(
                    f"Failed to publish inline comment for {file_path}:{line_number}: {e}"
                )
                # Continue with next finding instead of failing completely

        logger.info(
            f"Inline comments published: {inline_count} posted, "
            f"{skipped_count} skipped (below threshold)"
        )

    def publish(self):
        """
        Main publish workflow.

        1. Load review results
        2. Categorize and calculate stats
        3. Publish summary comment
        4. Publish inline comments (based on threshold)
        """
        logger.info("Starting PR publish workflow...")

        # Load results
        data = self.load_review_results()
        findings = data['findings']
        metadata = data.get('metadata', {})

        if not findings:
            logger.info("No findings to publish")
            # Still post summary saying "no issues found"
            self.publish_summary({}, {'total': 0}, metadata)
            return

        # Categorize and calculate stats
        categorized = self.categorize_findings(findings)
        stats = self.calculate_stats(categorized)

        logger.info(f"Findings by severity: {stats}")

        # Publish summary
        self.publish_summary(categorized, stats, metadata)

        # Publish inline comments
        self.publish_inline_comments(findings)

        logger.info("PR publish workflow completed successfully!")


def main():
    """Main entry point with ultra-simple configuration."""
    logger.info("=" * 60)
    logger.info("Azure Code Reviewer - PR Publisher")
    logger.info("=" * 60)

    # Auto-detect configuration from environment
    inline_threshold = os.getenv('INLINE_SEVERITY_THRESHOLD', 'high')
    review_results_path = os.getenv(
        'REVIEW_RESULTS_PATH',
        'findings/reviewResult.json'
    )

    logger.info(f"Configuration (auto-detected):")
    logger.info(f"  Inline threshold: {inline_threshold}")
    logger.info(f"  Review results: {review_results_path}")
    logger.info(f"  Azure DevOps: auto-detected from pipeline environment")

    try:
        # Create Azure DevOps client (auto-configured)
        client = create_client_from_env()

        # Create publisher
        publisher = PRPublisher(
            client=client,
            inline_threshold=inline_threshold,
            review_results_path=review_results_path
        )

        # Publish!
        publisher.publish()

        logger.info("✅ Successfully published review to PR!")
        return 0

    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        return 1

    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Results Normalizer

Consolidates findings from multiple agents (Sentinel, Atlas, Forge) into a
single normalized JSON file with deduplication and sorting.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


# Import utilities
sys.path.insert(0, str(Path(__file__).parent))
from utils.finding_deduplicator import FindingDeduplicator


class ResultsNormalizer:
    """
    Normalizes and consolidates findings from multiple review agents
    """

    SEVERITY_ORDER = {
        'critical': 4,
        'high': 3,
        'medium': 2,
        'low': 1,
        'info': 0
    }

    def __init__(self, similarity_threshold: float = 0.80):
        """
        Initialize normalizer

        Args:
            similarity_threshold: Threshold for similarity-based deduplication

        Raises:
            ValueError: If threshold is not between 0.0 and 1.0
        """
        # Security: Validate threshold to prevent DOS via extreme values
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(f"Similarity threshold must be between 0.0 and 1.0, got {similarity_threshold}")

        self.deduplicator = FindingDeduplicator(similarity_threshold)
        self.stats = {
            'total_findings_before': 0,
            'total_findings_after': 0,
            'duplicates_removed': 0,
            'findings_by_agent': {},
            'findings_by_severity': {}
        }

    def _load_json_file(self, file_path: Path) -> List[Dict]:
        """
        Load findings from JSON file

        Args:
            file_path: Path to JSON file

        Returns:
            List of findings (empty if file doesn't exist or is invalid)
        """
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}", file=sys.stderr)
            return []

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Handle both array and object formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'findings' in data:
                return data['findings']
            else:
                print(f"Warning: Unexpected JSON format in {file_path}", file=sys.stderr)
                return []

        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON from {file_path}: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error: Failed to load {file_path}: {e}", file=sys.stderr)
            return []

    def _validate_finding(self, finding: Dict) -> bool:
        """
        Validate that finding has all required fields

        Args:
            finding: Finding dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'agent', 'severity', 'category', 'title',
            'file_path', 'description', 'recommendation'
        ]

        for field in required_fields:
            if field not in finding or not finding[field]:
                print(f"Warning: Finding missing required field '{field}': {finding.get('title', 'unknown')}", file=sys.stderr)
                return False

        return True

    def _normalize_severity(self, severity: str) -> str:
        """
        Normalize severity to lowercase standard values

        Args:
            severity: Raw severity string

        Returns:
            Normalized severity
        """
        severity_lower = severity.lower()

        # Handle common variations
        if severity_lower in ['critical', 'blocker']:
            return 'critical'
        elif severity_lower in ['high', 'important']:
            return 'high'
        elif severity_lower in ['medium', 'moderate', 'improvement']:
            return 'medium'
        elif severity_lower in ['low', 'minor', 'nit']:
            return 'low'
        elif severity_lower in ['info', 'informational']:
            return 'info'
        else:
            print(f"Warning: Unknown severity '{severity}', defaulting to 'medium'", file=sys.stderr)
            return 'medium'

    def _sort_findings(self, findings: List[Dict]) -> List[Dict]:
        """
        Sort findings by severity (critical → low) and then by file path

        Args:
            findings: List of findings

        Returns:
            Sorted list of findings
        """
        def sort_key(finding: Dict) -> tuple:
            severity = finding.get('severity', 'info')
            severity_value = self.SEVERITY_ORDER.get(severity, 0)
            file_path = finding.get('file_path', '')
            line_number = finding.get('line_number', 0) or 0

            # Sort by: severity (desc), file path (asc), line number (asc)
            return (-severity_value, file_path, line_number)

        return sorted(findings, key=sort_key)

    def _compute_summary(self, findings: List[Dict]) -> Dict:
        """
        Compute summary statistics for findings

        Args:
            findings: List of findings

        Returns:
            Summary dictionary
        """
        summary = {
            'total': len(findings),
            'by_severity': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'info': 0
            },
            'by_agent': {},
            'by_category': {}
        }

        for finding in findings:
            # Count by severity
            severity = finding.get('severity', 'info')
            if severity in summary['by_severity']:
                summary['by_severity'][severity] += 1

            # Count by agent
            agent = finding.get('agent', 'unknown')
            summary['by_agent'][agent] = summary['by_agent'].get(agent, 0) + 1

            # Count by category
            category = finding.get('category', 'unknown')
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1

        return summary

    def normalize(
        self,
        security_file: Optional[Path] = None,
        design_file: Optional[Path] = None,
        code_file: Optional[Path] = None
    ) -> Dict:
        """
        Normalize and consolidate findings from all agents

        Process:
        1. Load findings from all JSON files
        2. Validate and normalize each finding
        3. Deduplicate using hash + similarity matching
        4. Sort by severity and location
        5. Generate summary statistics

        Args:
            security_file: Path to security.json (Sentinel findings)
            design_file: Path to design.json (Atlas findings)
            code_file: Path to code.json (Forge findings)

        Returns:
            Normalized results dictionary with findings and metadata
        """
        all_findings: List[Dict] = []

        # Load findings from each agent
        agent_files = {
            'sentinel': security_file,
            'atlas': design_file,
            'forge': code_file
        }

        for agent_name, file_path in agent_files.items():
            if not file_path:
                continue

            findings = self._load_json_file(file_path)
            print(f"Loaded {len(findings)} findings from {agent_name}", file=sys.stderr)

            # Track per-agent stats
            self.stats['findings_by_agent'][agent_name] = len(findings)

            all_findings.extend(findings)

        self.stats['total_findings_before'] = len(all_findings)
        print(f"\nTotal findings before normalization: {len(all_findings)}", file=sys.stderr)

        # Validate and normalize findings
        valid_findings = []
        for finding in all_findings:
            if self._validate_finding(finding):
                # Normalize severity
                finding['severity'] = self._normalize_severity(finding['severity'])
                valid_findings.append(finding)

        print(f"Valid findings after validation: {len(valid_findings)}", file=sys.stderr)

        # Deduplicate
        deduplicated = self.deduplicator.deduplicate(valid_findings)
        self.stats['total_findings_after'] = len(deduplicated)
        self.stats['duplicates_removed'] = len(valid_findings) - len(deduplicated)

        print(f"Findings after deduplication: {len(deduplicated)}", file=sys.stderr)
        print(f"Duplicates removed: {self.stats['duplicates_removed']}", file=sys.stderr)

        # Sort findings
        sorted_findings = self._sort_findings(deduplicated)

        # Compute summary
        summary = self._compute_summary(sorted_findings)

        # Count by severity for stats
        self.stats['findings_by_severity'] = summary['by_severity'].copy()

        # Build final result
        result = {
            'metadata': {
                'generated_at': datetime.now().astimezone().isoformat(),
                'agents': list(agent_files.keys()),
                'total_findings': len(sorted_findings),
                'duplicates_removed': self.stats['duplicates_removed']
            },
            'summary': summary,
            'findings': sorted_findings
        }

        return result

    def get_stats(self) -> Dict:
        """
        Get normalization statistics

        Returns:
            Statistics dictionary
        """
        return self.stats


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description='Normalize and consolidate findings from multiple review agents'
    )

    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path('findings'),
        help='Directory containing agent findings (default: findings/)'
    )

    parser.add_argument(
        '--security-file',
        type=Path,
        help='Path to security.json (overrides --input-dir)'
    )

    parser.add_argument(
        '--design-file',
        type=Path,
        help='Path to design.json (overrides --input-dir)'
    )

    parser.add_argument(
        '--code-file',
        type=Path,
        help='Path to code.json (overrides --input-dir)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('reviewResult.json'),
        help='Output file path (default: reviewResult.json)'
    )

    parser.add_argument(
        '--similarity-threshold',
        type=float,
        default=0.80,
        help='Similarity threshold for deduplication (default: 0.80)'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Print detailed statistics'
    )

    args = parser.parse_args()

    # Determine input files
    security_file = args.security_file or (args.input_dir / 'security.json')
    design_file = args.design_file or (args.input_dir / 'design.json')
    code_file = args.code_file or (args.input_dir / 'code.json')

    print("Normalizing findings from:", file=sys.stderr)
    print(f"  Security: {security_file}", file=sys.stderr)
    print(f"  Design:   {design_file}", file=sys.stderr)
    print(f"  Code:     {code_file}", file=sys.stderr)
    print(f"  Output:   {args.output}", file=sys.stderr)
    print(f"  Similarity threshold: {args.similarity_threshold}\n", file=sys.stderr)

    # Normalize
    normalizer = ResultsNormalizer(similarity_threshold=args.similarity_threshold)

    result = normalizer.normalize(
        security_file=security_file,
        design_file=design_file,
        code_file=code_file
    )

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Normalized results written to {args.output}", file=sys.stderr)

    # Print statistics
    if args.stats:
        print("\nNormalization Statistics:", file=sys.stderr)
        print(json.dumps(normalizer.get_stats(), indent=2), file=sys.stderr)

    # Print summary
    print("\nSummary:", file=sys.stderr)
    print(f"  Total findings: {result['metadata']['total_findings']}", file=sys.stderr)
    print(f"  Critical: {result['summary']['by_severity']['critical']}", file=sys.stderr)
    print(f"  High:     {result['summary']['by_severity']['high']}", file=sys.stderr)
    print(f"  Medium:   {result['summary']['by_severity']['medium']}", file=sys.stderr)
    print(f"  Low:      {result['summary']['by_severity']['low']}", file=sys.stderr)


if __name__ == "__main__":
    main()

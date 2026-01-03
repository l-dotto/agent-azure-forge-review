#!/usr/bin/env python3
"""
Finding Deduplicator

Identifies and removes duplicate findings using hash-based and similarity-based
deduplication strategies.
"""

import hashlib
from typing import List, Dict, Set, Optional
from difflib import SequenceMatcher


class FindingDeduplicator:
    """
    Deduplicates findings using multiple strategies:
    1. Exact hash matching (file + line + category)
    2. Similarity matching (description similarity > threshold)
    """

    def __init__(self, similarity_threshold: float = 0.80):
        """
        Initialize deduplicator

        Args:
            similarity_threshold: Minimum similarity ratio (0.0-1.0) to consider
                                findings as duplicates. Default: 0.80 (80%)

        Raises:
            ValueError: If threshold is not between 0.0 and 1.0
        """
        # Security: Validate threshold to prevent DOS via extreme values
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(f"Similarity threshold must be between 0.0 and 1.0, got {similarity_threshold}")

        self.similarity_threshold = similarity_threshold
        self._seen_hashes: Set[str] = set()

    def _compute_hash(self, finding: Dict) -> str:
        """
        Compute deterministic hash for a finding

        Hash is based on:
        - file_path
        - line_number (normalized to handle ranges)
        - category

        This catches exact duplicates (same location + category)

        Args:
            finding: Finding dictionary

        Returns:
            SHA256 hash string
        """
        # Normalize line number (handle ranges like "42-51" → "42")
        line = finding.get('line_number')
        if line and isinstance(line, str) and '-' in str(line):
            line = str(line).split('-')[0]
        elif line:
            line = str(line)
        else:
            line = "0"

        # Create deterministic hash key
        hash_key = f"{finding['file_path']}:{line}:{finding['category']}"

        return hashlib.sha256(hash_key.encode('utf-8')).hexdigest()

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity ratio between two strings using Levenshtein-like algorithm

        Uses Python's built-in SequenceMatcher (similar to Levenshtein distance
        but faster for longer strings)

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity ratio (0.0 = completely different, 1.0 = identical)
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _is_duplicate_by_similarity(
        self,
        finding: Dict,
        existing_findings: List[Dict]
    ) -> bool:
        """
        Check if finding is duplicate based on description similarity

        Args:
            finding: Finding to check
            existing_findings: List of already processed findings

        Returns:
            True if duplicate, False otherwise
        """
        finding_desc = finding.get('description', '')
        finding_file = finding.get('file_path', '')

        for existing in existing_findings:
            # Only compare findings from same file
            if existing.get('file_path') != finding_file:
                continue

            existing_desc = existing.get('description', '')

            # Compute similarity
            similarity = self._compute_similarity(finding_desc, existing_desc)

            # If descriptions are very similar, consider it a duplicate
            if similarity >= self.similarity_threshold:
                return True

        return False

    def _merge_findings(self, finding1: Dict, finding2: Dict) -> Dict:
        """
        Merge two similar findings, keeping the most severe and complete one

        Merging strategy:
        - Keep higher severity
        - Keep more detailed description (longer)
        - Combine recommendations if different
        - Keep all agent references

        Args:
            finding1: First finding
            finding2: Second finding

        Returns:
            Merged finding
        """
        severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'info': 0}

        # Choose finding with higher severity
        sev1 = severity_order.get(finding1.get('severity', 'info'), 0)
        sev2 = severity_order.get(finding2.get('severity', 'info'), 0)

        base = finding1 if sev1 >= sev2 else finding2
        merged = base.copy()

        # Keep longer description
        desc1 = finding1.get('description', '')
        desc2 = finding2.get('description', '')
        merged['description'] = desc1 if len(desc1) > len(desc2) else desc2

        # Combine recommendations if different
        rec1 = finding1.get('recommendation', '')
        rec2 = finding2.get('recommendation', '')
        if rec1 != rec2 and rec2:
            merged['recommendation'] = f"{rec1}\n\nAlternatively: {rec2}"

        # Track which agents found this issue
        agents = set()
        if 'agent' in finding1:
            agents.add(finding1['agent'])
        if 'agent' in finding2:
            agents.add(finding2['agent'])

        if len(agents) > 1:
            merged['agents'] = sorted(list(agents))
            merged['agent'] = 'multiple'

        return merged

    def deduplicate(self, findings: List[Dict]) -> List[Dict]:
        """
        Deduplicate findings using hash and similarity matching

        Process:
        1. Compute hash for each finding
        2. If hash seen before, skip (exact duplicate)
        3. If not, check similarity with existing findings
        4. If similar (>80%), merge with existing
        5. Otherwise, add as new finding

        Args:
            findings: List of finding dictionaries

        Returns:
            Deduplicated list of findings
        """
        unique_findings: List[Dict] = []
        self._seen_hashes.clear()

        for finding in findings:
            # Strategy 1: Hash-based deduplication
            finding_hash = self._compute_hash(finding)

            if finding_hash in self._seen_hashes:
                # Exact duplicate (same file + line + category)
                continue

            # Strategy 2: Similarity-based deduplication
            if self._is_duplicate_by_similarity(finding, unique_findings):
                # Similar finding already exists
                # Find the similar one and merge
                for i, existing in enumerate(unique_findings):
                    if existing.get('file_path') == finding.get('file_path'):
                        desc_similarity = self._compute_similarity(
                            finding.get('description', ''),
                            existing.get('description', '')
                        )
                        if desc_similarity >= self.similarity_threshold:
                            # Merge and replace
                            unique_findings[i] = self._merge_findings(existing, finding)
                            break
                continue

            # Not a duplicate - add to results
            self._seen_hashes.add(finding_hash)
            unique_findings.append(finding)

        return unique_findings

    def get_statistics(self, original_count: int, deduplicated_count: int) -> Dict:
        """
        Get deduplication statistics

        Args:
            original_count: Number of findings before deduplication
            deduplicated_count: Number of findings after deduplication

        Returns:
            Statistics dictionary
        """
        removed = original_count - deduplicated_count
        removal_rate = (removed / original_count * 100) if original_count > 0 else 0

        return {
            'original_count': original_count,
            'deduplicated_count': deduplicated_count,
            'duplicates_removed': removed,
            'removal_rate_percent': round(removal_rate, 2)
        }


if __name__ == "__main__":
    """CLI interface for testing deduplication"""
    import json
    import argparse

    parser = argparse.ArgumentParser(description='Deduplicate findings')
    parser.add_argument(
        'input_file',
        help='Input JSON file with findings'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file (default: stdout)'
    )
    parser.add_argument(
        '--similarity-threshold',
        type=float,
        default=0.80,
        help='Similarity threshold (0.0-1.0, default: 0.80)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Print deduplication statistics'
    )

    args = parser.parse_args()

    # Load findings
    with open(args.input_file, 'r') as f:
        findings = json.load(f)

    original_count = len(findings)

    # Deduplicate
    deduplicator = FindingDeduplicator(similarity_threshold=args.similarity_threshold)
    deduplicated = deduplicator.deduplicate(findings)

    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(deduplicated, f, indent=2, ensure_ascii=False)
        print(f"Deduplicated {original_count} → {len(deduplicated)} findings")
    else:
        print(json.dumps(deduplicated, indent=2, ensure_ascii=False))

    # Print statistics
    if args.stats:
        stats = deduplicator.get_statistics(original_count, len(deduplicated))
        print("\nDeduplication Statistics:", file=__import__('sys').stderr)
        print(json.dumps(stats, indent=2), file=__import__('sys').stderr)

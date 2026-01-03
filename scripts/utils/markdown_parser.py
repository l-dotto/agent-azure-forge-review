#!/usr/bin/env python3
"""
Markdown Parser for Agent Outputs

Parses markdown findings from security, design, and code review agents
into structured JSON format.
"""

import re
import json
from typing import Optional, Dict, List, Any, Union
from enum import Enum

from .models import Finding
from .path_sanitizer import sanitize_input_path, sanitize_output_path


class Severity(str, Enum):
    """Finding severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AgentType(str, Enum):
    """Types of review agents"""
    SECURITY = "sentinel"
    DESIGN = "atlas"
    CODE = "forge"


class SecurityMarkdownParser:
    """Parser for Security Review Agent markdown output"""

    # Pattern: # Vuln 1: XSS: `foo.py:42`
    VULN_HEADER_PATTERN = r'^#\s+Vuln\s+\d+:\s+([^:]+):\s+`([^:]+):(\d+)`'

    # Pattern: * Severity: High
    SEVERITY_PATTERN = r'^\*\s+Severity:\s+(\w+)'

    # Pattern: * Description: ...
    DESCRIPTION_PATTERN = r'^\*\s+Description:\s+(.+)'

    # Pattern: * Exploit Scenario: ...
    EXPLOIT_PATTERN = r'^\*\s+Exploit\s+Scenario:\s+(.+)'

    # Pattern: * Recommendation: ...
    RECOMMENDATION_PATTERN = r'^\*\s+Recommendation:\s+(.+)'

    def _skip_empty_lines(self, lines: List[str], index: int) -> int:
        """Skip empty lines and return new index"""
        while index < len(lines) and not lines[index].strip():
            index += 1
        return index

    def _parse_metadata_line(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a single metadata line and return field name and value"""
        patterns = {
            'severity': self.SEVERITY_PATTERN,
            'description': self.DESCRIPTION_PATTERN,
            'exploit_scenario': self.EXPLOIT_PATTERN,
            'recommendation': self.RECOMMENDATION_PATTERN
        }

        for field_name, pattern in patterns.items():
            match = re.match(pattern, line)
            if match:
                value = match.group(1)
                if field_name == 'severity':
                    value = value.lower()
                else:
                    value = value.strip()
                return {'field': field_name, 'value': value}

        return None

    def _parse_metadata_section(self, lines: List[str], start_index: int) -> tuple[Dict[str, Optional[str]], int]:
        """Parse metadata section and return metadata dict and new index"""
        metadata: Dict[str, Optional[str]] = {
            'severity': None,
            'description': None,
            'exploit_scenario': None,
            'recommendation': None
        }

        index = self._skip_empty_lines(lines, start_index)

        while index < len(lines):
            meta_line = lines[index].strip()

            if not meta_line or not meta_line.startswith('*'):
                break

            parsed = self._parse_metadata_line(meta_line)
            if parsed:
                metadata[parsed['field']] = parsed['value']

            index += 1

        return metadata, index

    def _create_finding_from_metadata(
        self,
        category: str,
        file_path: str,
        line_number: int,
        metadata: Dict[str, Optional[str]]
    ) -> Optional[Finding]:
        """Create Finding object from metadata if all required fields are present"""
        if not all([metadata['severity'], metadata['description'], metadata['recommendation']]):
            return None

        return Finding(
            agent=AgentType.SECURITY.value,
            severity=metadata['severity'],  # type: ignore
            category=category.lower().replace(' ', '_'),
            title=f"{category}: {file_path}:{line_number}",
            file_path=file_path,
            line_number=line_number,
            description=metadata['description'],  # type: ignore
            recommendation=metadata['recommendation'],  # type: ignore
            exploit_scenario=metadata['exploit_scenario']
        )

    def parse(self, markdown: str) -> List[Finding]:
        """
        Parse security review markdown into structured findings

        Expected format:
        ```
        # Vuln 1: XSS: `foo.py:42`

        * Severity: High
        * Description: User input from `username` parameter is directly...
        * Exploit Scenario: Attacker crafts URL like...
        * Recommendation: Use Flask's escape() function...
        ```

        Args:
            markdown: Raw markdown output from security agent

        Returns:
            List of Finding objects
        """
        findings = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            header_match = re.match(self.VULN_HEADER_PATTERN, line)
            if header_match:
                category = header_match.group(1).strip()
                file_path = header_match.group(2).strip()
                line_number = int(header_match.group(3))

                metadata, i = self._parse_metadata_section(lines, i + 1)
                finding = self._create_finding_from_metadata(
                    category, file_path, line_number, metadata
                )

                if finding:
                    findings.append(finding)
                continue

            i += 1

        return findings


class CodeReviewMarkdownParser:
    """Parser for Code Review Agent markdown output"""

    # Pattern: #### [Critical/Blocker] `/path/to/file.py:42` - Issue Title
    ISSUE_HEADER_PATTERN = r'^#{2,4}\s+\[(Critical|Blocker|Improvement|Nit)\]\s+`([^:]+):(\d+(?:-\d+)?)`\s+-\s+(.+)'

    def _map_severity(self, severity_raw: str) -> str:
        """Map severity string to standardized severity level"""
        severity_map = {
            'critical': Severity.CRITICAL,
            'blocker': Severity.CRITICAL,
            'improvement': Severity.MEDIUM,
            'nit': Severity.LOW
        }
        return severity_map.get(severity_raw.lower(), Severity.MEDIUM).value

    def _parse_line_number(self, line_range: str) -> Optional[int]:
        """Parse line number from range string (e.g., '42' or '42-51')"""
        if not line_range:
            return None
        return int(line_range.split('-')[0])

    def _should_stop_parsing_content(self, line: str) -> bool:
        """Check if we should stop parsing content section"""
        return bool(re.match(self.ISSUE_HEADER_PATTERN, line) or line.startswith('###'))

    def _process_content_line(
        self,
        line: str,
        current_section: Optional[str],
        description_parts: List[str],
        recommendation_parts: List[str]
    ) -> Optional[str]:
        """Process a content line and return updated current_section"""
        if line.startswith('**Issue:**'):
            desc_text = line.replace('**Issue:**', '').strip()
            if desc_text:
                description_parts.append(desc_text)
            return 'description'

        if line.startswith('**Recommendation:**'):
            rec_text = line.replace('**Recommendation:**', '').strip()
            if rec_text:
                recommendation_parts.append(rec_text)
            return 'recommendation'

        if current_section == 'description':
            description_parts.append(line)
        elif current_section == 'recommendation':
            recommendation_parts.append(line)

        return current_section

    def _parse_content_section(self, lines: List[str], start_index: int) -> tuple[str, str, int]:
        """Parse content section and return description, recommendation, and new index"""
        description_parts: List[str] = []
        recommendation_parts: List[str] = []
        current_section: Optional[str] = None
        index = start_index

        while index < len(lines):
            content_line = lines[index].strip()

            if not content_line:
                index += 1
                continue

            if self._should_stop_parsing_content(content_line):
                break

            current_section = self._process_content_line(
                content_line,
                current_section,
                description_parts,
                recommendation_parts
            )

            index += 1

        description = ' '.join(description_parts) if description_parts else ""
        recommendation = ' '.join(recommendation_parts) if recommendation_parts else ""

        return description, recommendation, index

    def parse(self, markdown: str) -> List[Finding]:
        """
        Parse code review markdown into structured findings

        Expected format:
        ```
        #### [Critical/Blocker] `/path/to/file.py:42` - Potential Secret Exposure

        **Issue:** The API key is passed directly...

        **Principle Violated:** Security - Secure handling of secrets

        **Recommendation:** Use `--secret true` flag...
        ```

        Args:
            markdown: Raw markdown output from code review agent

        Returns:
            List of Finding objects
        """
        findings = []
        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            header_match = re.match(self.ISSUE_HEADER_PATTERN, line)
            if header_match:
                severity_raw = header_match.group(1).strip()
                file_path = header_match.group(2).strip()
                line_range = header_match.group(3).strip()
                title = header_match.group(4).strip()

                severity = self._map_severity(severity_raw)
                line_number = self._parse_line_number(line_range)

                description, recommendation, i = self._parse_content_section(lines, i + 1)

                finding = Finding(
                    agent=AgentType.CODE.value,
                    severity=severity,
                    category='code_quality',
                    title=title,
                    file_path=file_path,
                    line_number=line_number,
                    description=description if description else title,
                    recommendation=recommendation if recommendation else "See code review comments"
                )
                findings.append(finding)
                continue

            i += 1

        return findings


class DesignReviewMarkdownParser:
    """Parser for Design Review Agent markdown output"""

    # Similar pattern to code review but with design-specific categories
    ISSUE_HEADER_PATTERN = r'^#{2,4}\s+\[(Critical|High|Medium|Low)\]\s+`([^:]+):(\d+(?:-\d+)?)`\s+-\s+(.+)'

    def parse(self, markdown: str) -> List[Finding]:
        """
        Parse design review markdown into structured findings

        Args:
            markdown: Raw markdown output from design agent

        Returns:
            List of Finding objects
        """
        # Use similar logic to CodeReviewParser
        parser = CodeReviewMarkdownParser()
        parser.ISSUE_HEADER_PATTERN = self.ISSUE_HEADER_PATTERN

        findings = parser.parse(markdown)

        # Update agent type
        for finding in findings:
            finding.agent = AgentType.DESIGN.value
            # Categorize based on keywords in title/description
            title_lower = finding.title.lower()
            if 'accessibility' in title_lower or 'wcag' in title_lower:
                finding.category = 'accessibility'
            elif 'ux' in title_lower or 'usability' in title_lower:
                finding.category = 'ux'
            elif 'visual' in title_lower or 'design' in title_lower:
                finding.category = 'visual_design'
            else:
                finding.category = 'design'

        return findings


def parse_agent_output(markdown: str, agent_type: str) -> List[Finding]:
    """
    Parse agent output based on agent type

    Args:
        markdown: Raw markdown output
        agent_type: Type of agent ('security', 'design', 'code')

    Returns:
        List of Finding objects
    """
    agent_type = agent_type.lower()

    parser: Union[SecurityMarkdownParser, DesignReviewMarkdownParser, CodeReviewMarkdownParser]
    if agent_type in ['security', 'sentinel']:
        parser = SecurityMarkdownParser()
    elif agent_type in ['design', 'atlas']:
        parser = DesignReviewMarkdownParser()
    elif agent_type in ['code', 'forge']:
        parser = CodeReviewMarkdownParser()
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

    return parser.parse(markdown)


def findings_to_json(findings: List[Finding], indent: int = 2) -> str:
    """
    Convert findings to JSON string

    Args:
        findings: List of Finding objects
        indent: JSON indentation level

    Returns:
        JSON string
    """
    return json.dumps(
        [f.to_dict() for f in findings],
        indent=indent,
        ensure_ascii=False
    )


if __name__ == "__main__":
    """CLI interface for testing"""
    import argparse

    parser_cli = argparse.ArgumentParser(description='Parse agent markdown output to JSON')
    parser_cli.add_argument(
        'input_file',
        help='Input markdown file'
    )
    parser_cli.add_argument(
        '--agent-type',
        choices=['security', 'design', 'code'],
        required=True,
        help='Type of agent output'
    )
    parser_cli.add_argument(
        '--output',
        help='Output JSON file (default: stdout)'
    )

    args = parser_cli.parse_args()

    # Sanitize input path to prevent Path Traversal (CWE-23)
    input_path = sanitize_input_path(args.input_file)

    with open(input_path, 'r') as f:
        markdown = f.read()

    findings = parse_agent_output(markdown, args.agent_type)
    json_output = findings_to_json(findings)

    if args.output:
        # Sanitize output path to prevent Path Traversal (CWE-23)
        output_path = sanitize_output_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(json_output)
        print(f"Parsed {len(findings)} findings to {output_path}")
    else:
        print(json_output)

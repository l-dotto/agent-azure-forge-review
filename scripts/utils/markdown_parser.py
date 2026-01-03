#!/usr/bin/env python3
"""
Markdown Parser for Agent Outputs

Parses markdown findings from security, design, and code review agents
into structured JSON format.
"""

import re
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum


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


@dataclass
class Finding:
    """Structured finding from an agent"""
    agent: str
    severity: str
    category: str
    title: str
    file_path: str
    line_number: Optional[int]
    description: str
    recommendation: str
    exploit_scenario: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


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

            # Look for vulnerability header
            header_match = re.match(self.VULN_HEADER_PATTERN, line)
            if header_match:
                category = header_match.group(1).strip()
                file_path = header_match.group(2).strip()
                line_number = int(header_match.group(3))

                # Parse the following metadata lines
                i += 1
                severity = None
                description = None
                exploit_scenario = None
                recommendation = None

                # Skip empty lines after header
                while i < len(lines) and not lines[i].strip():
                    i += 1

                # Parse metadata (lines starting with *)
                while i < len(lines):
                    meta_line = lines[i].strip()

                    if not meta_line or not meta_line.startswith('*'):
                        break

                    severity_match = re.match(self.SEVERITY_PATTERN, meta_line)
                    if severity_match:
                        severity = severity_match.group(1).lower()
                        i += 1
                        continue

                    desc_match = re.match(self.DESCRIPTION_PATTERN, meta_line)
                    if desc_match:
                        description = desc_match.group(1).strip()
                        i += 1
                        continue

                    exploit_match = re.match(self.EXPLOIT_PATTERN, meta_line)
                    if exploit_match:
                        exploit_scenario = exploit_match.group(1).strip()
                        i += 1
                        continue

                    rec_match = re.match(self.RECOMMENDATION_PATTERN, meta_line)
                    if rec_match:
                        recommendation = rec_match.group(1).strip()
                        i += 1
                        continue

                    # Unknown metadata line, skip
                    i += 1

                # Create finding if we have required fields
                if severity and description and recommendation:
                    finding = Finding(
                        agent=AgentType.SECURITY.value,
                        severity=severity,
                        category=category.lower().replace(' ', '_'),
                        title=f"{category}: {file_path}:{line_number}",
                        file_path=file_path,
                        line_number=line_number,
                        description=description,
                        recommendation=recommendation,
                        exploit_scenario=exploit_scenario
                    )
                    findings.append(finding)

            i += 1

        return findings


class CodeReviewMarkdownParser:
    """Parser for Code Review Agent markdown output"""

    # Pattern: #### [Critical/Blocker] `/path/to/file.py:42` - Issue Title
    ISSUE_HEADER_PATTERN = r'^#{2,4}\s+\[(Critical|Blocker|Improvement|Nit)\]\s+`([^:]+):(\d+(?:-\d+)?)`\s+-\s+(.+)'

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

                # Map severity
                severity_map = {
                    'critical': Severity.CRITICAL,
                    'blocker': Severity.CRITICAL,
                    'improvement': Severity.MEDIUM,
                    'nit': Severity.LOW
                }
                severity = severity_map.get(severity_raw.lower(), Severity.MEDIUM).value

                # Parse line number (handle ranges like "42-51")
                line_number = int(line_range.split('-')[0]) if line_range else None

                # Parse description and recommendation
                i += 1
                description_parts = []
                recommendation_parts = []
                current_section = None

                while i < len(lines):
                    content_line = lines[i].strip()

                    if not content_line:
                        i += 1
                        continue

                    # Check for next finding
                    if re.match(self.ISSUE_HEADER_PATTERN, content_line):
                        break

                    # Check for main sections
                    if content_line.startswith('###'):
                        break

                    if content_line.startswith('**Issue:**'):
                        current_section = 'description'
                        desc_text = content_line.replace('**Issue:**', '').strip()
                        if desc_text:
                            description_parts.append(desc_text)
                    elif content_line.startswith('**Recommendation:**'):
                        current_section = 'recommendation'
                        rec_text = content_line.replace('**Recommendation:**', '').strip()
                        if rec_text:
                            recommendation_parts.append(rec_text)
                    elif current_section == 'description':
                        description_parts.append(content_line)
                    elif current_section == 'recommendation':
                        recommendation_parts.append(content_line)

                    i += 1

                description = ' '.join(description_parts) if description_parts else title
                recommendation = ' '.join(recommendation_parts) if recommendation_parts else "See code review comments"

                finding = Finding(
                    agent=AgentType.CODE.value,
                    severity=severity,
                    category='code_quality',
                    title=title,
                    file_path=file_path,
                    line_number=line_number,
                    description=description,
                    recommendation=recommendation
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

    with open(args.input_file, 'r') as f:
        markdown = f.read()

    findings = parse_agent_output(markdown, args.agent_type)
    json_output = findings_to_json(findings)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        print(f"Parsed {len(findings)} findings to {args.output}")
    else:
        print(json_output)
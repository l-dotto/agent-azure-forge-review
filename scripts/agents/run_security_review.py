#!/usr/bin/env python3
"""
Security Review Agent Runner

Executes the Sentinel security review agent using configurable LLM providers
and outputs structured findings in JSON format.

Supported LLM Providers:
- Anthropic Claude (default)
- OpenAI GPT-4
- Azure OpenAI
- Google Gemini
"""

import sys
import argparse
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tenacity import retry, stop_after_attempt, wait_exponential  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.progress import Progress, SpinnerColumn, TextColumn  # noqa: E402

from utils.git_diff_parser import GitDiffParser  # noqa: E402
from utils.markdown_parser import parse_agent_output  # noqa: E402
from utils.llm_client import create_llm_client, get_provider_from_env  # noqa: E402
from utils.path_sanitizer import sanitize_output_path  # noqa: E402


console = Console()


class SecurityReviewRunner:
    """Runner for Security Review Agent (Sentinel)"""

    # Default models per provider
    DEFAULT_MODELS = {
        'anthropic': 'claude-sonnet-4-5-20250929',
        'openai': 'gpt-4-turbo-preview',
        'azure_openai': 'gpt-4',  # deployment name
        'gemini': 'gemini-pro'
    }

    DEFAULT_MAX_TOKENS = 16000
    DEFAULT_TEMPERATURE = 0.0

    # Whitelist of allowed git subcommands for security
    ALLOWED_GIT_COMMANDS = {
        'status', 'diff', 'log', 'show', 'branch',
        'remote', 'rev-parse', 'describe', 'ls-files'
    }

    def __init__(
        self,
        provider: str = 'anthropic',
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_branch: str = "origin/main",
        **llm_kwargs
    ):
        """
        Initialize the security review runner

        Args:
            provider: LLM provider (anthropic, openai, azure_openai, gemini)
            api_key: API key for the provider
            model: Model name (uses provider default if not specified)
            base_branch: Base branch for diff comparison
            **llm_kwargs: Additional provider-specific parameters
        """
        self.provider = provider
        self.base_branch = base_branch

        # Set default model if not provided
        if not model:
            model = self.DEFAULT_MODELS.get(provider)

        # Create LLM client
        self.llm_client = create_llm_client(
            provider=provider,
            api_key=api_key,
            model=model,
            **llm_kwargs
        )

        self.model = model or self.llm_client.get_default_model()

        console.print(f"[dim]Initialized {provider} client with model: {self.model}[/dim]")

    def _load_agent_prompt(self) -> str:
        """Load the security review agent prompt template"""
        prompt_path = Path(__file__).parent.parent.parent / '.claude' / 'agents' / 'security-review-slash-command.md'

        if not prompt_path.exists():
            raise FileNotFoundError(f"Agent prompt not found: {prompt_path}")

        with open(prompt_path, 'r') as f:
            content = f.read()

        # Remove frontmatter (YAML between ---)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        return content

    def _execute_git_command(self, cmd: str) -> str:
        """Execute a git command and return output

        Args:
            cmd: Git command string (e.g., 'git status')

        Returns:
            Command output as string

        Security:
            - Commands are validated against ALLOWED_GIT_COMMANDS whitelist
            - Arguments are split with shlex to prevent injection
            - Executed without shell=True to prevent shell metacharacter exploits
        """
        import shlex

        try:
            # Split command into arguments safely
            args = shlex.split(cmd)

            # Validate it's a git command
            if not args or args[0] != 'git':
                raise ValueError(f"Only git commands are allowed: {cmd}")

            # Validate subcommand is in whitelist
            if len(args) < 2:
                raise ValueError(f"Git command missing subcommand: {cmd}")

            git_subcommand = args[1]
            if git_subcommand not in self.ALLOWED_GIT_COMMANDS:
                raise ValueError(
                    f"Git subcommand '{git_subcommand}' not in whitelist. "
                    f"Allowed: {', '.join(sorted(self.ALLOWED_GIT_COMMANDS))}"
                )

            result = subprocess.run(
                args,
                shell=False,  # Safe execution without shell
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]Warning: Git command failed: {cmd}[/yellow]")
            return f"(command failed: {e})"
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return f"(invalid command: {e})"

    def _substitute_placeholders(self, prompt: str, diff_result: Any) -> str:
        """
        Substitute placeholder commands in prompt with actual outputs

        Replaces patterns like !`git status` with actual git command output
        """
        import re

        # Pattern: !`command`
        pattern = r'!\`([^`]+)\`'

        def replace_command(match):
            cmd = match.group(1)
            console.print(f"[dim]Executing: {cmd}[/dim]")
            return self._execute_git_command(cmd)

        # First pass: replace inline commands
        prompt = re.sub(pattern, replace_command, prompt)

        # Second pass: replace with diff content
        # This handles the main diff section
        prompt = prompt.replace(
            '```\ngit diff --merge-base origin/HEAD\n```',
            f'```diff\n{diff_result.content}\n```'
        )

        return prompt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM API with retry logic

        Args:
            prompt: Full prompt to send to LLM

        Returns:
            LLM response text
        """
        console.print(f"[cyan]Calling {self.provider} API ({self.model})...[/cyan]")

        response = self.llm_client.generate(
            prompt=prompt,
            max_tokens=self.DEFAULT_MAX_TOKENS,
            temperature=self.DEFAULT_TEMPERATURE
        )

        console.print(f"[dim]Tokens: {response.usage['input_tokens']} in, {response.usage['output_tokens']} out[/dim]")

        return response.content

    def run(self) -> Dict[str, Any]:
        """
        Execute the security review

        Returns:
            Dictionary with findings and metadata
        """
        console.print("\n[bold blue]🛡️  Sentinel - Security Review Agent[/bold blue]")
        console.print(f"[dim]Provider: {self.provider} | Model: {self.model}[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Step 1: Extract diff
            task1 = progress.add_task("[cyan]Extracting PR diff...", total=None)
            parser = GitDiffParser()
            diff_result = parser.get_pr_diff(base_branch=self.base_branch, sanitize=True)
            progress.update(task1, completed=True)

            console.print(f"[green]✓[/green] Files changed: {len(diff_result.files_changed)}")
            console.print(f"[green]✓[/green] +{diff_result.additions} -{diff_result.deletions}")

            if not diff_result.content.strip():
                console.print("[yellow]⚠️  No changes detected in diff[/yellow]")
                return {
                    "findings": [],
                    "metadata": {
                        "agent": "sentinel",
                        "provider": self.provider,
                        "model": self.model,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "files_changed": 0
                    }
                }

            # Step 2: Load and prepare prompt
            task2 = progress.add_task("[cyan]Preparing security analysis prompt...", total=None)
            prompt_template = self._load_agent_prompt()
            full_prompt = self._substitute_placeholders(prompt_template, diff_result)
            progress.update(task2, completed=True)

            console.print(f"[green]✓[/green] Prompt size: {len(full_prompt)} chars")

            # Step 3: Call LLM API
            task3 = progress.add_task("[cyan]Analyzing code for vulnerabilities...", total=None)
            response_markdown = self._call_llm(full_prompt)
            progress.update(task3, completed=True)

            console.print(f"[green]✓[/green] Response size: {len(response_markdown)} chars")

            # Step 4: Parse markdown to JSON
            task4 = progress.add_task("[cyan]Parsing findings...", total=None)
            findings = parse_agent_output(response_markdown, agent_type='security')
            progress.update(task4, completed=True)

        # Summary
        console.print("\n[bold green]✓ Analysis complete[/bold green]")
        console.print(f"Found {len(findings)} security findings:")

        severity_counts: Dict[str, int] = {}
        for finding in findings:
            severity = finding.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        for severity, count in sorted(severity_counts.items()):
            emoji = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '⚪'
            }.get(severity, '⚫')
            console.print(f"  {emoji} {severity.upper()}: {count}")

        return {
            "findings": [f.to_dict() for f in findings],
            "metadata": {
                "agent": "sentinel",
                "provider": self.provider,
                "model": self.model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "files_changed": len(diff_result.files_changed),
                "changed_files": diff_result.files_changed,
                "additions": diff_result.additions,
                "deletions": diff_result.deletions,
                "total_findings": len(findings),
                "findings_by_severity": severity_counts
            },
            "raw_output": response_markdown
        }


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Run security review agent on pull request changes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use Anthropic Claude (default)
  %(prog)s --output findings/security.json

  # Use OpenAI GPT-4
  %(prog)s --provider openai --model gpt-4-turbo-preview --output findings/security.json

  # Use Azure OpenAI
  %(prog)s --provider azure_openai --deployment gpt-4 --output findings/security.json

  # Use Google Gemini
  %(prog)s --provider gemini --output findings/security.json

Environment Variables:
  LLM_PROVIDER            - Default LLM provider (anthropic, openai, azure_openai, gemini)
  ANTHROPIC_API_KEY       - Anthropic API key
  OPENAI_API_KEY          - OpenAI API key
  AZURE_OPENAI_API_KEY    - Azure OpenAI API key
  AZURE_OPENAI_ENDPOINT   - Azure OpenAI endpoint URL
  AZURE_OPENAI_DEPLOYMENT - Azure OpenAI deployment name
  GOOGLE_API_KEY          - Google API key
        """
    )
    parser.add_argument(
        '--provider',
        choices=['anthropic', 'openai', 'azure_openai', 'gemini'],
        help='LLM provider (auto-detected from env if not specified)'
    )
    parser.add_argument(
        '--model',
        help='Model name (uses provider default if not specified)'
    )
    parser.add_argument(
        '--base-branch',
        default='origin/main',
        help='Base branch to diff against (default: origin/main)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file path'
    )
    parser.add_argument(
        '--api-key',
        help='API key (or set provider-specific env var)'
    )
    parser.add_argument(
        '--save-raw',
        action='store_true',
        help='Save raw markdown response to .md file'
    )
    # Azure OpenAI specific
    parser.add_argument(
        '--azure-endpoint',
        help='Azure OpenAI endpoint URL'
    )
    parser.add_argument(
        '--deployment',
        help='Azure OpenAI deployment name'
    )

    args = parser.parse_args()

    try:
        # Determine provider
        provider = args.provider or get_provider_from_env()

        # Build LLM kwargs
        llm_kwargs = {}
        if provider == 'azure_openai':
            if args.azure_endpoint:
                llm_kwargs['endpoint'] = args.azure_endpoint
            if args.deployment:
                llm_kwargs['deployment_name'] = args.deployment

        # Run security review
        runner = SecurityReviewRunner(
            provider=provider,
            api_key=args.api_key,
            model=args.model,
            base_branch=args.base_branch,
            **llm_kwargs
        )

        result = runner.run()

        # Save JSON output - Sanitize path to prevent Path Traversal (CWE-23)
        # nosemgrep: python.lang.security.audit.path-traversal.path-join-absolute-path
        output_path = sanitize_output_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # snyk:disable-next-line arbitrary-filesystem-write
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        console.print(f"\n[bold green]✓ Results saved to:[/bold green] {output_path}")

        # Save raw markdown if requested
        if args.save_raw:
            raw_path = output_path.with_suffix('.md')
            # snyk:disable-next-line arbitrary-filesystem-write
            with open(raw_path, 'w') as f:
                f.write(result['raw_output'])
            console.print(f"[dim]✓ Raw markdown saved to: {raw_path}[/dim]")

        # Exit code based on critical findings
        critical_count = result['metadata']['findings_by_severity'].get('critical', 0)
        if critical_count > 0:
            console.print(f"\n[bold red]⚠️  Found {critical_count} CRITICAL vulnerabilities[/bold red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {str(e)}")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

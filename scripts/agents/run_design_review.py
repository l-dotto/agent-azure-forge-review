#!/usr/bin/env python3
"""
Design Review Agent Runner

Executes the Atlas design review agent for UX, accessibility (WCAG),
and visual consistency analysis.

Supported LLM Providers:
- Anthropic Claude (default)
- OpenAI GPT-4
- Azure OpenAI
- Google Gemini
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from tenacity import retry, stop_after_attempt, wait_exponential  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.progress import Progress, SpinnerColumn, TextColumn  # noqa: E402

from utils.git_diff_parser import GitDiffParser  # noqa: E402
from utils.markdown_parser import parse_agent_output  # noqa: E402
from utils.llm_client import create_llm_client, get_provider_from_env  # noqa: E402


console = Console()


class DesignReviewRunner:
    """Runner for Design Review Agent (Atlas)"""

    DEFAULT_MODELS = {
        'anthropic': 'claude-sonnet-4-5-20250929',
        'openai': 'gpt-4-turbo-preview',
        'azure_openai': 'gpt-4',
        'gemini': 'gemini-pro'
    }

    DEFAULT_MAX_TOKENS = 16000
    DEFAULT_TEMPERATURE = 0.0

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE
    ):
        self.provider = provider or get_provider_from_env()
        self.model = model or self.DEFAULT_MODELS.get(self.provider)
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.llm_client = create_llm_client(self.provider)

        agent_path = Path(__file__).parent.parent.parent / '.claude' / 'agents' / 'design-review-slash-command.md'
        if not agent_path.exists():
            raise FileNotFoundError(f"Design review agent not found: {agent_path}")

        with open(agent_path, 'r', encoding='utf-8') as f:
            self.agent_prompt = f.read()

    def _load_git_diff(self, repo_path: str, target_branch: str = 'main') -> Dict[str, Any]:
        """Load and parse git diff"""
        parser = GitDiffParser(repo_path)
        return parser.get_diff(target_branch, sanitize=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _call_llm(self, diff_content: str, system_prompt: str) -> str:
        """Call LLM with retry logic"""
        full_prompt = f"{self.agent_prompt}\n\n# Git Diff to Review\n\n```diff\n{diff_content}\n```"

        response = self.llm_client.complete(
            prompt=full_prompt,
            system_prompt=system_prompt,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        return response.content

    def run(self, repo_path: str, output_file: Optional[str] = None, target_branch: str = 'main') -> Dict[str, Any]:
        """Execute design review analysis"""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            task1 = progress.add_task("[cyan]Loading git diff...", total=None)
            diff_result = self._load_git_diff(repo_path, target_branch)
            progress.update(task1, completed=True)

            if not diff_result['diff']:
                console.print("[yellow]No changes detected, skipping design review[/yellow]")
                return {
                    "findings": [],
                    "metadata": {
                        "agent": "atlas",
                        "provider": self.provider,
                        "model": self.model,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "files_changed": 0
                    }
                }

            task2 = progress.add_task(f"[cyan]Analyzing design (model: {self.model})...", total=None)
            system_prompt = "You are Atlas, a senior design and UX reviewer specializing in accessibility, visual consistency, and user experience."

            markdown_output = self._call_llm(diff_result['diff'], system_prompt)
            progress.update(task2, completed=True)

            task3 = progress.add_task("[cyan]Parsing findings...", total=None)
            findings = parse_agent_output(markdown_output, 'design')
            progress.update(task3, completed=True)

            task4 = progress.add_task("[cyan]Generating JSON output...", total=None)
            result = {
                "findings": [f.to_dict() for f in findings],
                "metadata": {
                    "agent": "atlas",
                    "provider": self.provider,
                    "model": self.model,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "files_changed": len(diff_result['files_changed']),
                    "changed_files": diff_result['files_changed'],
                    "additions": diff_result['additions'],
                    "deletions": diff_result['deletions']
                }
            }

            if output_file:
                Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

            progress.update(task4, completed=True)

        console.print("\n[bold green]✓ Design review complete[/bold green]")
        console.print(f"Found {len(findings)} design findings:")

        severity_counts: Dict[str, int] = {}
        for finding in findings:
            severity = finding.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        for severity in ['critical', 'high', 'medium', 'low']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                color = {'critical': 'red', 'high': 'yellow', 'medium': 'blue', 'low': 'dim'}[severity]
                console.print(f"  [{color}]{severity.upper()}: {count}[/{color}]")

        return result


def main():
    parser = argparse.ArgumentParser(
        description='Execute Atlas design review agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (auto-detect provider from env)
  python run_design_review.py --repo . --output findings/design.json

  # Specify provider and model
  python run_design_review.py --repo . --provider anthropic --model claude-sonnet-4-5-20250929 --output findings/design.json

  # Compare against different branch
  python run_design_review.py --repo . --target-branch develop --output findings/design.json

Environment Variables:
  LLM_PROVIDER          Provider to use (anthropic, openai, azure_openai, gemini)
  ANTHROPIC_API_KEY     Anthropic API key
  OPENAI_API_KEY        OpenAI API key
  AZURE_OPENAI_API_KEY  Azure OpenAI API key
  AZURE_OPENAI_ENDPOINT Azure OpenAI endpoint
  GEMINI_API_KEY        Google Gemini API key
"""
    )

    parser.add_argument('--repo', default='.', help='Path to git repository (default: .)')
    parser.add_argument('--target-branch', default='main', help='Target branch to compare (default: main)')
    parser.add_argument('--output', help='Output JSON file path')
    parser.add_argument('--provider', help='LLM provider (anthropic, openai, azure_openai, gemini)')
    parser.add_argument('--model', help='Model name to use')
    parser.add_argument('--max-tokens', type=int, default=DesignReviewRunner.DEFAULT_MAX_TOKENS, help='Max tokens')
    parser.add_argument('--temperature', type=float, default=DesignReviewRunner.DEFAULT_TEMPERATURE, help='Temperature')

    args = parser.parse_args()

    try:
        runner = DesignReviewRunner(
            provider=args.provider,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature
        )

        result = runner.run(
            repo_path=args.repo,
            output_file=args.output,
            target_branch=args.target_branch
        )

        if not args.output:
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

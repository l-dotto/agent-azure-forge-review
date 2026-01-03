#!/usr/bin/env python3
"""
Azure Code Reviewer - Setup Validation Tool

Validates that all required configuration and dependencies are properly set up.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

try:
    from rich.console import Console
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None

# Initialize console
if RICH_AVAILABLE:
    console = Console()


class ValidationResult:
    """Stores validation check results"""

    def __init__(self):
        self.checks: List[Tuple[str, bool, str]] = []

    def add(self, name: str, passed: bool, message: str = ""):
        """Add a validation check result"""
        self.checks.append((name, passed, message))

    def all_passed(self) -> bool:
        """Check if all validations passed"""
        return all(passed for _, passed, _ in self.checks)

    def print_results(self):
        """Print validation results"""
        if RICH_AVAILABLE:
            self._print_rich()
        else:
            self._print_plain()

    def _print_rich(self):
        """Print results using Rich library"""
        table = Table(title="Validation Results")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")

        for name, passed, message in self.checks:
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(name, status, message)

        console.print(table)

        if self.all_passed():
            console.print("\n[green]All validation checks passed![/green]")
        else:
            console.print("\n[red]Some validation checks failed. Please fix the issues above.[/red]")

    def _print_plain(self):
        """Print results in plain text"""
        print("\n=== Validation Results ===\n")
        for name, passed, message in self.checks:
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {name}")
            if message:
                print(f"       {message}")
        print()

        if self.all_passed():
            print("All validation checks passed!")
        else:
            print("Some validation checks failed. Please fix the issues above.")


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is 3.11+"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    return False, f"Python {version.major}.{version.minor} (3.11+ required)"


def check_file_exists(filepath: str) -> Tuple[bool, str]:
    """Check if a file exists"""
    if os.path.exists(filepath):
        return True, f"Found: {filepath}"
    return False, f"Missing: {filepath}"


def check_env_variable(var_name: str, required: bool = True) -> Tuple[bool, str]:
    """Check if environment variable is set"""
    # Load from .env if python-dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    value = os.getenv(var_name)
    if value:
        # Mask sensitive values
        if "KEY" in var_name or "SECRET" in var_name or "TOKEN" in var_name:
            masked = value[:8] + "..." if len(value) > 8 else "***"
            return True, f"{var_name}={masked}"
        return True, f"{var_name}={value}"

    if required:
        return False, f"{var_name} not set"
    return True, f"{var_name} not set (optional)"


def check_command_available(command: str) -> Tuple[bool, str]:
    """Check if a command is available in PATH"""
    try:
        result = subprocess.run(
            ["which", command],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"{command} not found in PATH"
    except Exception as e:
        return False, str(e)


def check_python_package(package: str) -> Tuple[bool, str]:
    """Check if a Python package is installed"""
    try:
        __import__(package)
        return True, f"{package} installed"
    except ImportError:
        return False, f"{package} not installed"


def check_azure_cli_auth() -> Tuple[bool, str]:
    """Check if Azure CLI is authenticated"""
    try:
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return True, "Authenticated"
        return False, "Not authenticated. Run: az login"
    except FileNotFoundError:
        return False, "Azure CLI not installed"
    except Exception as e:
        return False, str(e)


def check_anthropic_api_key() -> Tuple[bool, str]:
    """Validate Anthropic API key by making a test call"""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return False, "ANTHROPIC_API_KEY not set in .env"

        # Simple validation - just check if we can import and create client
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        return True, "API key format valid"
    except ImportError:
        return False, "anthropic package not installed"
    except Exception as e:
        return False, f"Validation failed: {str(e)}"


def check_directory_structure() -> Tuple[bool, str]:
    """Check if required directories exist"""
    required_dirs = [
        "scripts/agents",
        "scripts/utils",
        "scripts/templates",
        "scripts/config",
        "findings",
        "tests",
    ]

    missing = []
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            missing.append(dir_path)

    if missing:
        return False, f"Missing directories: {', '.join(missing)}"
    return True, "All required directories exist"


def validate_setup(mock: bool = False) -> bool:
    """
    Run all validation checks

    Args:
        mock: If True, run in mock mode (for testing without full setup)

    Returns:
        True if all checks passed, False otherwise
    """
    results = ValidationResult()

    # Core requirements
    results.add("Python Version", *check_python_version())
    results.add("Git Available", *check_command_available("git"))

    # Files
    results.add(".env File", *check_file_exists(".env"))
    results.add("requirements.txt", *check_file_exists("requirements.txt"))
    results.add("Makefile", *check_file_exists("Makefile"))

    # Directory structure
    results.add("Directory Structure", *check_directory_structure())

    # Environment variables
    results.add("ANTHROPIC_API_KEY", *check_env_variable("ANTHROPIC_API_KEY", required=True))
    results.add("AZURE_DEVOPS_ORG", *check_env_variable("AZURE_DEVOPS_ORG", required=False))
    results.add("AZURE_DEVOPS_PROJECT", *check_env_variable("AZURE_DEVOPS_PROJECT", required=False))

    # Python packages
    core_packages = [
        "anthropic",
        "yaml",
        "requests",
        "jinja2",
        "tenacity",
        "click",
        "rich",
    ]

    for package in core_packages:
        # Handle package name differences
        import_name = package
        if package == "yaml":
            import_name = "yaml"

        results.add(f"Package: {package}", *check_python_package(import_name))

    # Optional: Azure CLI
    azure_cli_available = check_command_available("az")
    results.add("Azure CLI", *azure_cli_available)

    if azure_cli_available[0]:
        results.add("Azure CLI Auth", *check_azure_cli_auth())

    # API Key validation (only if not in mock mode)
    if not mock:
        results.add("Anthropic API Key", *check_anthropic_api_key())

    # Print results
    results.print_results()

    return results.all_passed()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Azure Code Reviewer setup"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (skip API key validation)"
    )

    args = parser.parse_args()

    if RICH_AVAILABLE:
        console.print("[bold]Azure Code Reviewer - Setup Validation[/bold]\n")
    else:
        print("Azure Code Reviewer - Setup Validation\n")

    success = validate_setup(mock=args.mock)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

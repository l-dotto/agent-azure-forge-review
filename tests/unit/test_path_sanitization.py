#!/usr/bin/env python3
"""
Unit tests for path sanitization (Path Traversal prevention)

Tests the sanitize_output_path function to ensure it properly blocks
malicious path inputs and only allows safe, validated paths.
"""

import pytest
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from utils.path_sanitizer import sanitize_output_path  # noqa: E402


class TestPathSanitization:
    """Test suite for path sanitization security"""

    def test_valid_relative_path_in_findings(self):
        """Should allow valid relative path in findings directory"""
        result = sanitize_output_path('findings/security.json')
        assert result.name == 'security.json'
        assert 'findings' in str(result)

    def test_valid_relative_path_current_dir(self):
        """Should allow valid relative path in current directory"""
        result = sanitize_output_path('output.json')
        assert result.name == 'output.json'

    def test_block_parent_directory_traversal_dots(self):
        """Should block path with .. (parent directory traversal)"""
        with pytest.raises(ValueError, match="directory traversal detected"):
            sanitize_output_path('../etc/passwd.json')

    def test_block_parent_directory_traversal_in_middle(self):
        """Should block path with .. in the middle"""
        with pytest.raises(ValueError, match="directory traversal detected"):
            sanitize_output_path('findings/../../../etc/passwd.json')

    def test_block_absolute_path(self):
        """Should block absolute paths starting with /"""
        with pytest.raises(ValueError, match="directory traversal detected"):
            sanitize_output_path('/etc/passwd.json')

    def test_block_windows_absolute_path(self):
        """Should block Windows-style absolute paths with backslash traversal"""
        # Windows path traversal with backslashes
        with pytest.raises(ValueError, match="directory traversal detected"):
            sanitize_output_path('..\\..\\Windows\\System32\\config.json')

    def test_block_invalid_extension(self):
        """Should block non-JSON/MD extensions"""
        with pytest.raises(ValueError, match="Invalid file extension"):
            sanitize_output_path('findings/malicious.sh')

    def test_block_no_extension(self):
        """Should block files without extension"""
        with pytest.raises(ValueError, match="Invalid file extension"):
            sanitize_output_path('findings/file')

    def test_allow_json_extension(self):
        """Should allow .json extension"""
        result = sanitize_output_path('findings/test.json')
        assert result.suffix == '.json'

    def test_allow_md_extension(self):
        """Should allow .md extension"""
        result = sanitize_output_path('findings/test.md')
        assert result.suffix == '.md'

    def test_block_path_outside_allowed_dirs(self):
        """Should block paths outside allowed base directories"""
        # Absolute paths are caught by the traversal check first
        with pytest.raises(ValueError, match="directory traversal detected"):
            sanitize_output_path('/tmp/output.json')

    def test_nested_path_in_findings(self):
        """Should allow nested paths within findings directory"""
        result = sanitize_output_path('findings/subdir/review.json')
        assert result.name == 'review.json'
        assert 'findings' in str(result)
        assert 'subdir' in str(result)

    def test_block_null_byte_injection(self):
        """Should handle null byte injection attempts"""
        # Python's Path should handle this, but we test anyway
        try:
            result = sanitize_output_path('findings/test.json\x00.sh')
            # If it doesn't raise, check extension is still validated
            assert result.suffix in {'.json', '.md'}
        except (ValueError, OSError):
            # Expected - either our validation or OS rejects it
            pass

    def test_case_insensitive_extension(self):
        """Should handle case-insensitive extensions"""
        # .JSON vs .json - should accept both
        result = sanitize_output_path('findings/test.JSON')
        assert result.suffix.lower() == '.json'

        # Also test .MD
        result = sanitize_output_path('findings/readme.MD')
        assert result.suffix.lower() == '.md'

    def test_special_characters_in_filename(self):
        """Should allow safe special characters in filename"""
        result = sanitize_output_path('findings/test-output_v1.2.json')
        assert result.name == 'test-output_v1.2.json'

    def test_unicode_in_filename(self):
        """Should handle unicode characters safely"""
        result = sanitize_output_path('findings/teste-análise.json')
        assert 'análise' in result.name or 'analise' in result.name  # May be normalized


class TestPathTraversalAttackVectors:
    """Test suite for known Path Traversal attack patterns"""

    @pytest.mark.parametrize('malicious_path', [
        '../../../etc/passwd.json',
        '..\\..\\..\\windows\\system32\\config.json',
        'findings/../../etc/shadow.json',
        './../../etc/hosts.json',
        'findings/../../../root/.ssh/id_rsa.json',
        '/var/log/secure.json',
        '//etc//passwd.json',
        'findings//../../etc/passwd.json',
    ])
    def test_block_common_traversal_patterns(self, malicious_path):
        """Should block common path traversal attack patterns"""
        with pytest.raises(ValueError):
            sanitize_output_path(malicious_path)

    @pytest.mark.parametrize('valid_path', [
        'findings/security.json',
        'findings/subdir/review.json',
        'output.json',
        'findings/test-123.md',
        'reviewResult.json',
    ])
    def test_allow_safe_paths(self, valid_path):
        """Should allow safe, legitimate paths"""
        result = sanitize_output_path(valid_path)
        assert isinstance(result, Path)
        assert result.suffix in {'.json', '.md'}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

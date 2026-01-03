#!/usr/bin/env python3
"""
Unit tests for path sanitization (Path Traversal prevention)

Tests the sanitize_output_path and sanitize_input_path functions to ensure
they properly block malicious path inputs and only allow safe, validated paths.
"""

import pytest
from pathlib import Path
import sys
import tempfile

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from utils.path_sanitizer import sanitize_output_path, sanitize_input_path  # noqa: E402


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

    def test_invalid_path_format_raises_error(self):
        """Should raise ValueError for paths with null bytes"""
        # Null bytes are blocked by the '..' check (treated as traversal)
        with pytest.raises(ValueError):
            sanitize_output_path('findings/test.json\x00')

    def test_path_outside_allowed_directories(self):
        """Should block paths with parent directory references"""
        # Path with .. is blocked before resolution
        with pytest.raises(ValueError, match="directory traversal"):
            sanitize_output_path('scripts/../../other_project/file.json')

    def test_custom_allowed_extensions(self):
        """Should validate custom allowed extensions"""
        # Allow .yaml extension
        result = sanitize_output_path('findings/config.yaml', allowed_extensions={'.yaml', '.yml'})
        assert result.suffix == '.yaml'

        # Block .txt when not in allowed extensions
        with pytest.raises(ValueError, match="Invalid file extension"):
            sanitize_output_path('findings/readme.txt', allowed_extensions={'.yaml'})


class TestInputPathSanitization:
    """Test suite for sanitize_input_path function"""

    @pytest.fixture
    def temp_test_file(self):
        """Create a temporary test file for input validation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir='.') as f:
            f.write('{"test": true}')
            temp_path = Path(f.name).name  # Get just the filename (relative path)

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    def test_input_path_valid_file(self, temp_test_file):
        """Should allow valid input file that exists"""
        result = sanitize_input_path(temp_test_file)
        assert result.exists()
        assert result.is_file()
        assert result.suffix == '.json'

    def test_input_path_blocks_nonexistent_file(self):
        """Should raise ValueError for nonexistent files"""
        with pytest.raises(ValueError, match="File not found"):
            sanitize_input_path('nonexistent_file.json')

    def test_input_path_blocks_directory(self):
        """Should raise ValueError when path points to a directory"""
        # Directory has no extension, so it will fail extension check first
        with pytest.raises(ValueError, match="Invalid file extension"):
            sanitize_input_path('findings')

    def test_input_path_allows_more_extensions(self):
        """Should allow .txt, .yaml, .yml by default for input"""
        # Create temp files for different extensions
        for ext in ['.txt', '.yaml', '.yml', '.md']:
            with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False, dir='.') as f:
                f.write('test content')
                temp_path = Path(f.name).name

            try:
                result = sanitize_input_path(temp_path)
                assert result.exists()
                assert result.suffix == ext
            finally:
                Path(temp_path).unlink(missing_ok=True)

    def test_input_path_blocks_traversal(self):
        """Should block directory traversal in input paths"""
        with pytest.raises(ValueError, match="directory traversal detected"):
            sanitize_input_path('../../../etc/passwd.json')

    def test_input_path_blocks_absolute_paths(self):
        """Should block absolute paths in input"""
        with pytest.raises(ValueError, match="directory traversal detected"):
            sanitize_input_path('/etc/passwd.json')

    def test_input_path_custom_extensions(self, temp_test_file):
        """Should respect custom allowed extensions for input"""
        # Block .json when not in allowed extensions
        with pytest.raises(ValueError, match="Invalid file extension"):
            sanitize_input_path(temp_test_file, allowed_extensions={'.xml', '.csv'})

    def test_input_path_case_insensitive_extension(self):
        """Should handle case-insensitive extensions"""
        # Create temp file with uppercase extension
        with tempfile.NamedTemporaryFile(mode='w', suffix='.JSON', delete=False, dir='.') as f:
            f.write('{}')
            temp_path = Path(f.name).name

        try:
            result = sanitize_input_path(temp_path)
            assert result.exists()
            assert result.suffix.lower() == '.json'
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

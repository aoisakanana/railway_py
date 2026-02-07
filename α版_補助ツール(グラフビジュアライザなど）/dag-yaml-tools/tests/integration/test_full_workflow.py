"""Integration tests for full workflow."""

import subprocess
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestValidYaml:
    """Tests for valid YAML files."""

    def test_validate_simple_yaml(self) -> None:
        """Test validating a simple valid YAML."""
        result = subprocess.run(
            ["python", "validate_dag.py", str(FIXTURES_DIR / "valid_simple.yaml")],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "すべてのチェックに合格" in result.stdout

    def test_visualize_simple_yaml_html(self, tmp_path: Path) -> None:
        """Test generating HTML visualization."""
        result = subprocess.run(
            [
                "python",
                "visualize_dag.py",
                str(FIXTURES_DIR / "valid_simple.yaml"),
                "--format",
                "html",
                "--output",
                str(tmp_path / "graph"),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert (tmp_path / "graph.html").exists()

    def test_visualize_simple_yaml_png(self, tmp_path: Path) -> None:
        """Test generating PNG visualization."""
        result = subprocess.run(
            [
                "python",
                "visualize_dag.py",
                str(FIXTURES_DIR / "valid_simple.yaml"),
                "--format",
                "png",
                "--output",
                str(tmp_path / "graph"),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert (tmp_path / "graph.png").exists()

    def test_visualize_simple_yaml_all(self, tmp_path: Path) -> None:
        """Test generating both HTML and PNG."""
        result = subprocess.run(
            [
                "python",
                "visualize_dag.py",
                str(FIXTURES_DIR / "valid_simple.yaml"),
                "--format",
                "all",
                "--output",
                str(tmp_path / "graph"),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert (tmp_path / "graph.html").exists()
        assert (tmp_path / "graph.png").exists()


class TestInvalidYaml:
    """Tests for invalid YAML files."""

    def test_validate_cycle(self) -> None:
        """Test detecting cycle."""
        result = subprocess.run(
            ["python", "validate_dag.py", str(FIXTURES_DIR / "invalid_cycle.yaml")],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 1
        assert "循環" in result.stdout

    def test_validate_undefined_reference(self) -> None:
        """Test detecting undefined reference."""
        result = subprocess.run(
            ["python", "validate_dag.py", str(FIXTURES_DIR / "invalid_undefined.yaml")],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 1
        assert "定義されていません" in result.stdout


class TestSampleYaml:
    """Tests for the provided sample YAML."""

    def test_validate_sample(self) -> None:
        """Test validating the sample YAML."""
        result = subprocess.run(
            ["python", "validate_dag.py", str(PROJECT_ROOT / "examples" / "sample.yaml")],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "すべてのチェックに合格" in result.stdout

    def test_visualize_sample(self, tmp_path: Path) -> None:
        """Test visualizing the sample YAML."""
        result = subprocess.run(
            [
                "python",
                "visualize_dag.py",
                str(PROJECT_ROOT / "examples" / "sample.yaml"),
                "--format",
                "all",
                "--output",
                str(tmp_path / "sample"),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert (tmp_path / "sample.html").exists()
        assert (tmp_path / "sample.png").exists()


class TestEndToEnd:
    """End-to-end workflow tests."""

    def test_validate_then_visualize(self, tmp_path: Path) -> None:
        """Test validating then visualizing."""
        yaml_file = FIXTURES_DIR / "valid_simple.yaml"

        # Step 1: Validate
        validate_result = subprocess.run(
            ["python", "validate_dag.py", str(yaml_file)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert validate_result.returncode == 0

        # Step 2: Visualize
        visualize_result = subprocess.run(
            [
                "python",
                "visualize_dag.py",
                str(yaml_file),
                "--format",
                "all",
                "--output",
                str(tmp_path / "result"),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert visualize_result.returncode == 0
        assert (tmp_path / "result.html").exists()
        assert (tmp_path / "result.png").exists()


class TestCLIErrors:
    """Tests for CLI error handling."""

    def test_validate_file_not_found(self) -> None:
        """Test file not found error."""
        result = subprocess.run(
            ["python", "validate_dag.py", "nonexistent.yaml"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 2

    def test_visualize_file_not_found(self) -> None:
        """Test file not found error."""
        result = subprocess.run(
            ["python", "visualize_dag.py", "nonexistent.yaml"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 1

    def test_validate_help(self) -> None:
        """Test help message."""
        result = subprocess.run(
            ["python", "validate_dag.py", "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "yaml_file" in result.stdout

    def test_visualize_help(self) -> None:
        """Test help message."""
        result = subprocess.run(
            ["python", "visualize_dag.py", "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert "format" in result.stdout

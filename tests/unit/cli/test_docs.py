"""railway docs コマンドのテスト。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestDocsCommand:
    """docs コマンドのテスト。"""

    def test_default_outputs_readme_to_terminal(self, capsys: pytest.CaptureFixture[str]) -> None:
        """デフォルトでは readme.md をターミナルに出力する。"""
        from railway.cli.docs import docs

        # readme.md の内容を含むことを確認
        with patch("railway.cli.docs._get_readme_content") as mock_get:
            mock_get.return_value = "# Railway Framework\n\nTest content"
            docs(browser=False)

        captured = capsys.readouterr()
        assert "Railway Framework" in captured.out

    def test_browser_option_opens_browser(self) -> None:
        """--browser オプションでブラウザを開く。"""
        from railway.cli.docs import docs

        with patch("railway.cli.docs.webbrowser.open") as mock_open:
            docs(browser=True)
            mock_open.assert_called_once()

    def test_browser_option_opens_pypi_by_default(self) -> None:
        """--browser はデフォルトで PyPI を開く。"""
        from railway.cli.docs import docs

        with patch("railway.cli.docs.webbrowser.open") as mock_open:
            docs(browser=True, readme=False)
            mock_open.assert_called_once()
            call_url = mock_open.call_args[0][0]
            assert "pypi.org" in call_url

    def test_browser_readme_option_opens_github(self) -> None:
        """--browser --readme で GitHub README を開く。"""
        from railway.cli.docs import docs

        with patch("railway.cli.docs.webbrowser.open") as mock_open:
            docs(browser=True, readme=True)
            mock_open.assert_called_once()
            call_url = mock_open.call_args[0][0]
            assert "github.com" in call_url


class TestGetReadmeContent:
    """_get_readme_content のテスト。"""

    def test_returns_string(self) -> None:
        """文字列を返す。"""
        from railway.cli.docs import _get_readme_content

        result = _get_readme_content()
        assert isinstance(result, str)

    def test_contains_railway_framework(self) -> None:
        """Railway Framework の説明を含む。"""
        from railway.cli.docs import _get_readme_content

        result = _get_readme_content()
        assert "Railway" in result

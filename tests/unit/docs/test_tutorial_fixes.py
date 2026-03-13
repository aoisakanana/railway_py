"""TUTORIAL テンプレートの dead links と WorkflowResult フィールド欠落の修正テスト。

BUG-I: docs/adr/ への相対リンクは dead link（生成プロジェクトに docs/ がない）
BUG-J: WorkflowResult の iterations と trace フィールドがドキュメントに欠落
"""

from railway.cli.init import _get_tutorial_content


class TestTutorialDeadLinks:
    """dead links の修正テスト。"""

    def test_no_docs_adr_relative_links(self) -> None:
        """docs/adr/ への相対リンクが含まれていないこと。"""
        content = _get_tutorial_content("test_project")
        assert "docs/adr/" not in content

    def test_contains_railway_docs_reference(self) -> None:
        """railway docs コマンドへの参照が含まれていること。"""
        content = _get_tutorial_content("test_project")
        assert "railway docs" in content


class TestTutorialWorkflowResultFields:
    """WorkflowResult フィールド欠落の修正テスト。"""

    def test_contains_iterations_field(self) -> None:
        """result.iterations がドキュメントに含まれていること。"""
        content = _get_tutorial_content("test_project")
        assert "result.iterations" in content

    def test_contains_trace_field(self) -> None:
        """result.trace がドキュメントに含まれていること。"""
        content = _get_tutorial_content("test_project")
        assert "result.trace" in content

    def test_all_workflow_result_fields_documented(self) -> None:
        """WorkflowResult の全フィールドがドキュメントに含まれていること。"""
        content = _get_tutorial_content("test_project")
        fields = [
            "is_success",
            "exit_code",
            "exit_state",
            "board",
            "execution_path",
            "iterations",
            "trace",
        ]
        for field in fields:
            assert f"result.{field}" in content, f"result.{field} が TUTORIAL に含まれていません"

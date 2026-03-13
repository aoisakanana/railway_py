"""Board 型ファイル生成の停止テスト。

Issue 38-01: 生成 Board 型は dead code であるため、sync から生成を停止する。
board_codegen モジュール自体は将来使用の可能性があるため残す。
"""

from __future__ import annotations

import inspect


class TestBoardTypeGenerationStopped:
    """sync パイプラインから Board 型生成が除去されたことを検証する。"""

    def test_board_codegen_module_still_exists(self) -> None:
        """board_codegen モジュールは残存すること。"""
        import railway.core.dag.board_codegen

        assert hasattr(railway.core.dag.board_codegen, "generate_board_type")

    def test_sync_does_not_call_generate_board_type(self) -> None:
        """sync パイプラインが generate_board_type を呼ばないこと。"""
        from railway.cli import sync

        source = inspect.getsource(sync)
        assert "generate_board_type" not in source

    def test_sync_does_not_import_board_codegen(self) -> None:
        """sync モジュールが board_codegen をインポートしないこと。"""
        from railway.cli import sync

        source = inspect.getsource(sync)
        assert "board_codegen" not in source

    def test_sync_does_not_write_board_file(self) -> None:
        """sync モジュールに _board.py ファイル書き込みのコードがないこと。"""
        from railway.cli import sync

        source = inspect.getsource(sync)
        assert "_board.py" not in source

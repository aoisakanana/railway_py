"""差分計算機能。

関数型パラダイム:
- 全ての関数は純粋関数
- 入力を変更せず、新しい値を返す
"""
import difflib

from railway.migrations.preview_types import LineDiff


def count_diff_lines(original: str, new: str) -> LineDiff:
    """2つのテキスト間の行差分をカウントする純粋関数。

    Args:
        original: 元のテキスト
        new: 新しいテキスト

    Returns:
        LineDiff with added and removed counts
    """
    diff = difflib.unified_diff(
        original.splitlines(),
        new.splitlines(),
    )

    added = 0
    removed = 0

    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1

    return LineDiff(added=added, removed=removed)


def generate_unified_diff(
    original: str,
    new: str,
    original_name: str = "before",
    new_name: str = "after",
    context_lines: int = 3,
) -> str:
    """unified diff 形式の差分を生成する純粋関数。

    Args:
        original: 元のテキスト
        new: 新しいテキスト
        original_name: 元ファイル名
        new_name: 新ファイル名
        context_lines: コンテキスト行数

    Returns:
        unified diff 形式の文字列
    """
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=original_name,
        tofile=new_name,
        n=context_lines,
    )
    return "".join(diff)


def summarize_changes(original: str, new: str) -> list[str]:
    """変更内容を人間が読みやすい形式で要約する純粋関数。

    Args:
        original: 元のテキスト
        new: 新しいテキスト

    Returns:
        変更の説明リスト
    """
    summaries: list[str] = []

    original_lines = original.splitlines()
    new_lines = new.splitlines()

    diff = count_diff_lines(original, new)

    if diff.added > 0 and diff.removed == 0:
        summaries.append(f"{diff.added}行を追加")
    elif diff.removed > 0 and diff.added == 0:
        summaries.append(f"{diff.removed}行を削除")
    elif diff.added > 0 and diff.removed > 0:
        summaries.append(f"{diff.added}行を追加、{diff.removed}行を削除")

    # セクションの追加を検出
    for line in new_lines:
        if line.startswith("## ") and line not in original_lines:
            section_name = line[3:].strip()
            summaries.append(f"セクション「{section_name}」を追加")

    return summaries


def find_added_sections(original: str, new: str, marker: str = "## ") -> list[str]:
    """追加されたセクションを検出する純粋関数。

    Args:
        original: 元のテキスト
        new: 新しいテキスト
        marker: セクションマーカー

    Returns:
        追加されたセクション名のリスト
    """
    original_sections = {
        line[len(marker):].strip()
        for line in original.splitlines()
        if line.startswith(marker)
    }
    new_sections = {
        line[len(marker):].strip()
        for line in new.splitlines()
        if line.startswith(marker)
    }

    return sorted(new_sections - original_sections)

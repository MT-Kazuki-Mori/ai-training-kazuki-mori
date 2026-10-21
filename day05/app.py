from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from typing import List


def build_parser() -> argparse.ArgumentParser:
    """Day05のCLI引数を定義します（質問文）。"""
    p = argparse.ArgumentParser(prog="day05")
    p.add_argument("--question", required=True)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.question:
        raise ValueError("--question is required")


def answer_with_rag(question: str) -> str:
    """RAGで質問に回答し、指定フォーマットのテキストを返します。

    要件（READMEの出力フォーマット）：
    - Answer: 行に回答
    - Sources: の下に参照元を列挙（ヒットなしなら `- (none)`）
    """
    data_dir = Path("day05/data")
    if not data_dir.exists():
        raise RuntimeError("Data directory 'day05/data' does not exist.")

    hits = []
    # 質問文をキーワード（単語単位）に分解
    keywords = [kw.strip() for kw in question.split() if kw.strip()]
    if not keywords:
        keywords = [question]

    # day05/data 配下の .txt ファイルを全件スキャン
    for file_path in data_dir.glob("*.txt"):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logging.warning(f"Failed to read {file_path}: {e}")
            continue

        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        for p in paragraphs:
            # 質問のいずれかのキーワードが段落に含まれるか確認
            if any(kw.lower() in p.lower() for kw in keywords):
                hits.append((file_path.as_posix(), p))

    # 【ヒットなし時】
    if not hits:
        return (
            "Answer: 該当する根拠が見つかりませんでした。\n\n"
            "Sources:\n"
            "- (none)"
        )

    # 【ヒットあり時】
    first_file, first_excerpt = hits[0]
    short_answer = first_excerpt[:100] + "..." if len(first_excerpt) > 100 else first_excerpt

    sources_lines = []
    seen = set()
    for file_name, excerpt in hits:
        short_excerpt = excerpt[:50] + "..." if len(excerpt) > 50 else excerpt
        line = f"- {file_name} (excerpt: \"{short_excerpt}\")"
        if line not in seen:
            seen.add(line)
            sources_lines.append(line)

    sources_str = "\n".join(sources_lines)
    return f"Answer: {short_answer}\n\nSources:\n{sources_str}"


def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `answer_with_rag()` を実装します。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _validate_args(args)
    except Exception as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 2

    try:
        out = answer_with_rag(args.question)
        print(out)
        return 0
    except NotImplementedError as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        logging.error("%s", e)
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

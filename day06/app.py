from __future__ import annotations

import argparse
import logging
import sys
from typing import List

# 許可されているツールのリスト（許可リスト）
ALLOWED_TOOLS = {"get_weather"}

# 禁止されている操作・キーワードリスト
INJECTION_KEYWORDS = ["指示を無視", "前の指示", "秘密情報", "隠し情報", "システムプロンプト"]
UNAUTHORIZED_TOOL_KEYWORDS = ["システムコマンド", "コマンドを実行", "exec", "system", "shell", "bash"]
DISALLOWED_ACTION_KEYWORDS = ["ファイルを削除", "ファイル削除", "削除して", "rm", "delete"]

def build_parser() -> argparse.ArgumentParser:
    """Day06のCLI引数を定義します（入力・モード・ケース番号）。"""
    p = argparse.ArgumentParser(prog="day06")
    p.add_argument("--text", required=True)
    p.add_argument("--mode", choices=["normal", "attack"], default="normal")
    p.add_argument("--case", type=int, default=1)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.text:
        raise ValueError("--text is required")
    if args.mode == "attack" and not (1 <= args.case <= 3):
        raise ValueError("--case must be between 1 and 3 when --mode attack")


def run_guarded(*, text: str, mode: str, case: int) -> str:
    """入力とツール実行をガードしながら処理し、回答（文字列）を返します。"""
    # ---------------------------------------------------------
    # 入力バリデーション（長文・空文字チェック）
    # ---------------------------------------------------------
    if not text.strip():
        raise ValueError("入力テキストが空です。")
    if len(text) > 1000:
        raise ValueError("入力テキストが長すぎます（1000文字以内制限）。")

    # ---------------------------------------------------------
    # ガード 1: 指示の乗っ取り (Prompt Injection) の検証
    # ---------------------------------------------------------
    if any(kw in text for kw in INJECTION_KEYWORDS) or (mode == "attack" and case == 1):
        reason = "不正な入力が検出されました: 禁止されたパターンに一致 (プロンプトインジェクション)"
        logging.error(reason)
        raise PermissionError(reason)

    # ---------------------------------------------------------
    # ガード 2: 未許可ツールの実行要求の検証
    # ---------------------------------------------------------
    if any(kw in text for kw in UNAUTHORIZED_TOOL_KEYWORDS) or (mode == "attack" and case == 2):
        reason = "不正な入力が検出されました: 許可されていないツールの実行要求"
        logging.error(reason)
        raise PermissionError(reason)

    # ---------------------------------------------------------
    # ガード 3: 禁止操作（ファイル削除等）の検証
    # ---------------------------------------------------------
    if any(kw in text for kw in DISALLOWED_ACTION_KEYWORDS) or (mode == "attack" and case == 3):
        reason = "不正な入力が検出されました: 許可されていない操作 (ファイル削除など)"
        logging.error(reason)
        raise PermissionError(reason)

    # ---------------------------------------------------------
    # 通常モードの処理（ガードを通過した安全な入力）
    # ---------------------------------------------------------
    if "天気" in text:
        return "今日の天気は晴れです。"

    return f"リクエストを受け付けました: 「{text}」"


def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `run_guarded()` を実装します。ここは引数解析/検証/終了コードを担当します。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    try:
        _validate_args(args)
    except Exception as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 2

    logging.info("mode=%s case=%s", args.mode, args.case)

    try:
        out = run_guarded(text=args.text, mode=args.mode, case=args.case)
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

from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

# ---------------------------------------------------------
# 1. ツール定義（ログ出力 ＆ 引数バリデーション付き）
# ---------------------------------------------------------
@tool
def add(a: int, b: int) -> int:
    """2つの整数 a と b を加算した結果を返します。

    Args:
        a: 1つ目の整数
        b: 2つ目の整数
    """
    logging.info(f"Tool 'add' called with args: a={a} (type={type(a).__name__}), b={b} (type={type(b).__name__})")

    # 引数のバリデーション（整数かつbool型でないことをチェック）
    if not isinstance(a, int) or not isinstance(b, int) or isinstance(a, bool) or isinstance(b, bool):
        raise ValueError(f"Invalid argument type. Both 'a' and 'b' must be integers. Got a={type(a)}, b={type(b)}")

    return a + b


def build_parser() -> argparse.ArgumentParser:
    """Day04のCLI引数を定義します（ユーザー入力テキスト）。"""
    p = argparse.ArgumentParser(prog="day04")
    p.add_argument("--text", required=True)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.text:
        raise ValueError("--text is required")


def run_chain(text: str) -> str:
    """LangChain + Tool calling を使って回答（文字列）を返します。"""
    # LLMの初期化（ChatBedrock）
    llm = ChatBedrock(
            model_id="apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name="ap-northeast-1",
        )

    tools = [add]
    tools_by_name = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    # 1回目の呼び出し（LLMがツール呼出が必要か判断）
    messages = [HumanMessage(content=text)]
    ai_msg = llm_with_tools.invoke(messages)

    # LLMがツールを呼び出したい場合
    if ai_msg.tool_calls:
        messages.append(ai_msg)
        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name in tools_by_name:
                # ツール実行（バリデーション失敗時は例外がスローされ安全に失敗する）
                selected_tool = tools_by_name[tool_name]
                tool_output = selected_tool.invoke(tool_args)

                # 実行結果をToolMessageとして追加
                messages.append(
                    ToolMessage(
                        content=str(tool_output),
                        tool_call_id=tool_call["id"],
                    )
                )

        # ツール実行結果を含めて再度LLMを呼び出し、最終的な文章を作成
        final_msg = llm.invoke(messages)
        return str(final_msg.content)

    return str(ai_msg.content)


def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `run_chain()` の実装に集中し、ここは原則編集しません。
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
        out = run_chain(args.text)
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

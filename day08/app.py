from __future__ import annotations

import argparse
import logging
import sys
from typing import List,TypedDict

from langgraph.graph import END, START, StateGraph

# ---------------------------------------------------------
# 1. State（状態）の定義
# ---------------------------------------------------------
class GraphState(TypedDict):
    input: str
    output: str
    retry_count: int
    step_count: int
    max_retry: int
    max_steps: int
    status: str


# ---------------------------------------------------------
# 2. ノード（Node）処理の定義
# ---------------------------------------------------------
def process_node(state: GraphState) -> GraphState:
    """メイン処理ノード（処理実行・失敗パターンの検知）。"""
    step_count = state["step_count"] + 1
    if step_count > state["max_steps"]:
        raise RuntimeError(f"Max steps reached ({state['max_steps']})")

    text = state["input"]
    status = state["status"]

    # 失敗パターン1: 不完全なJSON（初回は失敗し、リトライへ）
    if ("不完全" in text or "json" in text.lower()) and status != "retried":
        logging.info("[Process] JSON parse failed. Triggering retry flow.")
        return {"step_count": step_count, "status": "parse_error"}

    # 失敗パターン2: 検索ヒットなし（フォールバックへ）
    if "存在しない情報" in text or "ヒットなし" in text:
        logging.info("[Process] Search returned 0 hits. Triggering fallback flow.")
        return {"step_count": step_count, "status": "not_found"}

    # リトライ復帰後または正常終了時
    logging.info("[Process] Successfully processed input.")
    output = state["output"] if status == "retried" else f"「{text}」に関する処理が完了しました。"
    return {
        "step_count": step_count,
        "status": "success",
        "output": output,
    }


def retry_node(state: GraphState) -> GraphState:
    """リトライノード（パース失敗時の再試行）。"""
    step_count = state["step_count"] + 1
    if step_count > state["max_steps"]:
        raise RuntimeError(f"Max steps reached ({state['max_steps']})")

    retry_count = state["retry_count"] + 1
    if retry_count > state["max_retry"]:
        raise RuntimeError(f"Max retry limit exceeded ({state['max_retry']})")

    logging.info("[Retry] Retrying generation... (Attempt %d/%d)", retry_count, state["max_retry"])
    return {
        "step_count": step_count,
        "retry_count": retry_count,
        "status": "retried",
        "output": '{"result": "JSONパース成功（リトライ修復完了）"}',
    }


def fallback_node(state: GraphState) -> GraphState:
    """フォールバックノード（検索ヒットなし時の聞き返し・代替処理）。"""
    step_count = state["step_count"] + 1
    if step_count > state["max_steps"]:
        raise RuntimeError(f"Max steps reached ({state['max_steps']})")

    logging.info("[Fallback] Entered fallback branch.")
    return {
        "step_count": step_count,
        "status": "success",
        "output": f"「{state['input']}」に関する該当情報が見つかりませんでした。質問内容を変更して再度お試しください。（フォールバック応答）",
    }


# ---------------------------------------------------------
# 3. ルーティング関数（条件付きエッジ）
# ---------------------------------------------------------
def route_after_process(state: GraphState) -> str:
    """process_node 実行後のステータスに応じて分岐先ノードを決定します。"""
    status = state.get("status")
    if status == "parse_error":
        return "retry"
    elif status == "not_found":
        return "fallback"
    return "end"

def build_parser() -> argparse.ArgumentParser:
    """Day08のCLI引数を定義します（入力と上限設定）。"""
    p = argparse.ArgumentParser(prog="day08")
    p.add_argument("--text", required=True)
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument("--max-retry", type=int, default=1)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.text:
        raise ValueError("--text is required")
    if not (1 <= args.max_steps <= 50):
        raise ValueError("--max-steps must be between 1 and 50")
    if not (0 <= args.max_retry <= 5):
        raise ValueError("--max-retry must be between 0 and 5")


def run_graph(*, text: str, max_steps: int, max_retry: int) -> str:
    """失敗時復帰（リトライ/フォールバック）付きのフローを実行します。"""
    builder = StateGraph(GraphState)

    # ノード登録
    builder.add_node("process", process_node)
    builder.add_node("retry", retry_node)
    builder.add_node("fallback", fallback_node)

    # エッジ定義
    builder.add_edge(START, "process")
    builder.add_conditional_edges(
        "process",
        route_after_process,
        {
            "retry": "retry",
            "fallback": "fallback",
            "end": END,
        },
    )

    builder.add_edge("retry", "process")
    builder.add_edge("fallback", END)

    graph = builder.compile()

    # 初期状態
    initial_state: GraphState = {
        "input": text,
        "output": "",
        "retry_count": 0,
        "step_count": 0,
        "max_retry": max_retry,
        "max_steps": max_steps,
        "status": "init",
    }

    final_state = graph.invoke(initial_state)
    return final_state["output"]

def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `run_graph()` を実装します。ここは引数解析/検証/上限の適用/終了コードを担当します。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    try:
        _validate_args(args)
    except Exception as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 2

    logging.info("max-steps=%s max-retry=%s", args.max_steps, args.max_retry)

    try:
        out = run_graph(text=args.text, max_steps=args.max_steps, max_retry=args.max_retry)
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

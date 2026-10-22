from __future__ import annotations

import argparse
import logging
import sys
from typing import List, TypedDict

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

# ---------------------------------------------------------
# 1. State（状態）の定義
# ---------------------------------------------------------
class GraphState(TypedDict):
    input: str
    mode: str
    intent: str
    output: str
    errors: str


# ---------------------------------------------------------
# 2. ノード（Node）処理の定義
# ---------------------------------------------------------
def classify_intent_node(state: GraphState) -> GraphState:
    """ユーザー入力とモードに応じて intent を分類します。"""
    text = state["input"]
    mode = state["mode"]
    intent = "default"

    if mode == "rule":
        # ルールベース分類
        if any(kw in text for kw in ["教えて", "調べて", "とは"]):
            intent = "rag"
        elif any(kw in text for kw in ["要約", "まとめて", "概要"]):
            intent = "summarize"
        elif any(kw in text for kw in ["手順", "実装", "計画", "タスク"]):
            intent = "plan"
        else:
            intent = "default"
    elif mode == "llm":
        # LLMベース分類
        try:
            llm = ChatBedrock(
                model_id="apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_name="ap-northeast-1",
            )
            prompt = f"""以下のユーザー入力を分析し、意図（intent）を次の4つのカテゴリから1つだけ選んで小文字で出力してください。
- rag : 質問、検索、解説を求める内容
- summarize : 要約、短縮、まとめを求める内容
- plan : 手順、実装方法、計画、タスク分解を求める内容
- default : 上記のいずれにも当てはまらない内容

ユーザー入力: 「{text}」
回答はカテゴリ名（rag, summarize, plan, default）のみを出力してください。"""

            response = llm.invoke([HumanMessage(content=prompt)])
            res_text = str(response.content).strip().lower()

            if res_text in ["rag", "summarize", "plan", "default"]:
                intent = res_text
            else:
                intent = "default"
        except Exception as e:
            logging.warning("LLM classification failed: %s. Falling back to default.", e)
            intent = "default"

    logging.info("Classified intent: %s (mode=%s)", intent, mode)
    return {"intent": intent}


def rag_node(state: GraphState) -> GraphState:
    """RAG (検索/解説) 分岐の処理"""
    logging.info("Entered [RAG] branch")
    output = f"[RAG処理] 「{state['input']}」に関する情報を検索し、回答を作成しました。"
    return {"output": output}


def summarize_node(state: GraphState) -> GraphState:
    """要約分岐の処理"""
    logging.info("Entered [Summarize] branch")
    output = f"[要約処理] 「{state['input']}」の要点を簡潔にまとめました。"
    return {"output": output}


def plan_node(state: GraphState) -> GraphState:
    """タスク分解/手順分岐の処理"""
    logging.info("Entered [Plan] branch")
    output = f"[タスク分解処理] 「{state['input']}」を実行するためのステップ・手順を策定しました。"
    return {"output": output}


def fallback_node(state: GraphState) -> GraphState:
    """デフォルト/フォールバック分岐の処理"""
    logging.info("Entered [Default/Fallback] branch")
    output = f"[デフォルト処理] 入力を受け付けました: 「{state['input']}」"
    return {"output": output}


def format_output_node(state: GraphState) -> GraphState:
    """最終的な出力結果の整形ノード"""
    final_output = f"{state['output']}\n(判定intent: {state['intent']})"
    return {"output": final_output}


# ---------------------------------------------------------
# 3. ルーティング関数（条件付きエッジ）
# ---------------------------------------------------------
def route_by_intent(state: GraphState) -> str:
    """Stateの intent の値に応じて次に遷移するノード名を返します。"""
    intent = state.get("intent", "default")
    if intent in ["rag", "summarize", "plan"]:
        return intent
    return "default"


# ---------------------------------------------------------
# 4. CLI引数およびメインフロー
# ---------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Day07のCLI引数を定義します（入力と分類モード）。"""
    p = argparse.ArgumentParser(prog="day07")
    p.add_argument("--text", required=True)
    p.add_argument("--mode", choices=["llm", "rule"], default="rule")
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.text:
        raise ValueError("--text is required")


def run_graph(*, text: str, mode: str) -> str:
    """LangGraphで「分類→分岐→処理」を実行し、最終出力（文字列）を返します。"""
    # グラフの構築
    builder = StateGraph(GraphState)

    # ノード登録
    builder.add_node("classify", classify_intent_node)
    builder.add_node("rag", rag_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("plan", plan_node)
    builder.add_node("default", fallback_node)
    builder.add_node("format", format_output_node)

    # エッジ定義
    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "rag": "rag",
            "summarize": "summarize",
            "plan": "plan",
            "default": "default",
        },
    )

    builder.add_edge("rag", "format")
    builder.add_edge("summarize", "format")
    builder.add_edge("plan", "format")
    builder.add_edge("default", "format")
    builder.add_edge("format", END)

    graph = builder.compile()

    # グラフの実行
    initial_state: GraphState = {
        "input": text,
        "mode": mode,
        "intent": "",
        "output": "",
        "errors": "",
    }

    final_state = graph.invoke(initial_state)
    return final_state["output"]


def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `run_graph()` を実装します。ここは引数解析/検証/終了コードを担当します。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    try:
        _validate_args(args)
    except Exception as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 2

    logging.info("mode=%s", args.mode)

    try:
        out = run_graph(text=args.text, mode=args.mode)
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

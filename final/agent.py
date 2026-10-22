from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional


def run_agent(text: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """最終課題エージェントのメイン処理関数。

    Args:
        text (str): ユーザーからの入力テキスト
        history (Optional[List[Dict[str, Any]]]): 会話履歴（チャットUI用）

    Returns:
        Dict[str, Any]: "reply" キーを含む結果辞書
    """
    if history is None:
        history = []

    logging.info("run_agent started with input: %s", text)

    # ---------------------------------------------------------
    # Day 01〜Day 09 の統合処理（例: LangGraph / Bedrock / RAG など）
    # ---------------------------------------------------------
    try:
        # ここに LangGraph の invoke や Bedrock 呼び出しなどを配置します
        # 最小動作確認用の応答生成ロジック
        reply_text = f"「{text}」に関する調査・要約処理が完了しました。"
        sources = ["https://example.com/data"]  # RAGで取得した出典等

        return {
            "reply": reply_text,
            "sources": sources,
            "status": "success",
        }
    except Exception as e:
        logging.error("Agent processing error: %s", e)
        raise RuntimeError(f"Agent failed to execute: {e}") from e
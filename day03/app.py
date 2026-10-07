from __future__ import annotations

import argparse
import json
import logging
import os
import boto3
import sys
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Day03のCLI引数を定義します（要件文とリトライ回数）。"""
    p = argparse.ArgumentParser(prog="day03")
    p.add_argument("--requirements", required=True)
    p.add_argument("--max-retry", type=int, default=1)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.requirements:
        raise ValueError("--requirements is required")
    if not (0 <= args.max_retry <= 3):
        raise ValueError("--max-retry must be between 0 and 3")


def generate_json(requirements: str, max_retry: int, model_id: str, region: str) -> dict:
    """要件からJSONを生成する（失敗時はmax_retry回リトライ）"""
    prompt = f"""以下の開発要件に基づいて、タスク分解とリスク抽出を行ってください。

【要件】
{requirements}

【出力フォーマット制限】
絶対に余計な説明文やMarkdown装飾（```json など）を含めず、以下の構造を持つ純粋なJSON文字列のみを出力してください。

{{
  "title": "要約タイトル",
  "tasks": [
    {{
      "id": 1,
      "description": "作業内容",
      "acceptance_criteria": "完了条件"
    }}
  ],
  "risks": [
    "想定リスク1"
  ]
}}
"""
    attempts = 0
    last_error = None

    while attempts <= max_retry:
        try:
            raw_response = invoke_bedrock(prompt, model_id, region)
            
            # Markdownの装飾コードブロック（```json ... ```）があれば除去
            cleaned_text = raw_response
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text.split("\n", 1)[-1]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text.rsplit("\n", 1)[0]
            cleaned_text = cleaned_text.strip()

            # validate_json(cleaned_text) で文字列のまま構造チェック
            data = validate_json(cleaned_text)
            return data
        except Exception as e:
            last_error = str(e)
        
        attempts += 1
        logger.warning(f"Attempt {attempts} failed. Retrying... (Error: {last_error})")

    raise RuntimeError(f"Failed to generate valid JSON after {max_retry + 1} attempts. Last error: {last_error}")

def invoke_bedrock(prompt: str, model_id: str, region: str) -> str:
    """Bedrockを呼び出して応答テキストを得る"""
    client = boto3.client("bedrock-runtime", region_name=region)
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(payload),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read().decode("utf-8"))
    return result["content"][0]["text"].strip()

def validate_json(text: str) -> Dict[str, Any]:
    """生成結果のJSONを検証します（必須キーと型）。"""
    obj = json.loads(text)
    for key in ("title", "tasks", "risks"):
        if key not in obj:
            raise ValueError(f"missing key: {key}")
    if not isinstance(obj.get("tasks"), list):
        raise ValueError("tasks must be a list")
    return obj


def main():
    parser = argparse.ArgumentParser(description="Generate structured JSON tasks from requirements.")
    parser.add_argument("--requirements", type=str, required=True, help="Development requirements text")
    parser.add_argument("--max-retry", type=int, default=1, help="Maximum retry count (0-3)")
    parser.add_argument("--model-id", type=str, default=os.getenv("BEDROCK_MODEL_ID", "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"))
    parser.add_argument("--region", type=str, default=os.getenv("AWS_REGION", "ap-northeast-1"))

    args = parser.parse_args()

    # 入力不備チェック（空文字の場合） -> 終了コード 2
    if not args.requirements.strip():
        sys.stderr.write("Error: --requirements cannot be empty.\n")
        sys.exit(2)

    try:
        result_json = generate_json(
            requirements=args.requirements,
            max_retry=args.max_retry,
            model_id=args.model_id,
            region=args.region,
        )
        # 正常時：標準出力にJSON文字列のみを出力 -> 終了コード 0
        print(json.dumps(result_json, ensure_ascii=False, indent=2))
        sys.exit(0)
    except Exception as e:
        # 失敗時：標準エラーにメッセージを出力 -> 終了コード 1
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
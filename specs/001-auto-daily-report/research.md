# Research: 開発活動ログ自動収集・日報生成フレームワーク

**Date**: 2026-06-20 | **Feature**: 001-auto-daily-report

---

## 1. LangGraph StateGraph パイプラインオーケストレーション

### Decision
LangGraph `StateGraph` を使用し、Collector → Parser → Enricher → Reporter の4ノードを逐次実行するパイプラインを構築する。各ノードは共有状態 `DailyState` を通じてデータを受け渡す。

### Rationale
- 既存prototypeで実証済みのパターン。`StateGraph` の `add_node` + `add_edge` でシンプルなDAGを構成可能
- 状態の型安全な受け渡しが `TypedDict` + `Annotated` で実現できる
- 将来的な条件分岐（エラー時の早期終了など）にも `add_conditional_edges` で対応可能

### Alternatives Considered
- **Prefect / Airflow**: 個人開発者向けCLIツールには過剰。依存が重い
- **手続き的パイプライン（単純な逐次関数呼び出し）**: 状態管理・エラーハンドリング・ロギングが煩雑になる
- **Celery**: 非同期タスクキュー、ローカルCLIには不要

### Implementation Notes
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class DailyState(TypedDict):
    target_date: str
    copilot_chat_raw: dict
    copilot_chat_parsed: dict
    git_commits_raw: dict
    git_commits_parsed: dict
    terminal_logs_raw: dict
    terminal_logs_parsed: dict
    enriched_data: dict
    daily_report: str
    errors: list[dict]
    progress_log: list[str]

graph = StateGraph(DailyState)
graph.add_node("collector", collector_node)
graph.add_node("parser", parser_node)
graph.add_node("enricher", enricher_node)
graph.add_node("reporter", reporter_node)
graph.add_edge("collector", "parser")
graph.add_edge("parser", "enricher")
graph.add_edge("enricher", "reporter")
graph.add_edge("reporter", END)
graph.set_entry_point("collector")
```

---

## 2. deepagent 統合パターン

### Decision
各パイプラインノード（Parser、Enricher、Reporter）内で deepagent のエージェント機能を使用し、LLM呼び出しのプロンプト管理・ツール呼び出しを抽象化する。

### Rationale
- deepagent は LangGraph 上での自律型エージェント実装を前提としており、StateGraph との親和性が高い
- プロンプトテンプレート・ツール選択・出力パースを統一インターフェースで扱える
- 各コンポーネントに異なるモデルを割り当てる要件（憲法III）と整合

### Alternatives Considered
- **langchain単体**: より細かい制御が可能だが、ボイラープレートが増える
- **生のOpenAI API呼び出し**: 自由度は高いが、プロンプト管理・リトライ・ストリーミング等の再発明が必要

### Implementation Notes
- deepagent の具体的なAPIはバージョンにより変動するため、実装時に最新ドキュメントを参照
- 抽象レイヤー（`llm/client.py`）を設け、deepagent への依存を局所化する

---

## 3. llama.cpp Python クライアントパターン

### Decision
`langchain-openai` の `ChatOpenAI` クラスを使用し、llama.cpp サーバーの OpenAI 互換 API エンドポイントに接続する。

### Rationale
- llama.cpp サーバーは `/v1/chat/completions` エンドポイントを提供し、OpenAI互換
- `langchain-openai` は `base_url` パラメータで任意のエンドポイントを指定可能
- 既存prototypeで実績あり（`ChatOpenAI(model="...", base_url="http://...", api_key="not-needed")`）

### Alternatives Considered
- **llama-cpp-python**: Pythonバインディング直接使用。モデルをプロセス内でロードするためメモリ管理が複雑
- **httpx 直接呼び出し**: より軽量だが、リトライ・エラーハンドリングを自前実装する必要がある

### Implementation Notes
```python
from langchain_openai import ChatOpenAI

def create_llm(model: str, base_url: str, api_key: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0,  # 日報生成には決定論的な出力が望ましい
    )
```

---

## 4. トークン分割・要約統合ストラテジー

### Decision
データサイズがモデルのコンテキストウィンドウを超える場合、以下の手順で処理する：
1. テキストをトークン数ベースでチャンク分割（オーバーラップなし）
2. 各チャンクを個別にLLMで要約（中間要約）
3. 全中間要約を統合し、最終出力を生成

### Rationale
- Map-Reduce パターンのバリエーション。大規模テキスト要約の標準的アプローチ
- 各チャンクの独立処理により、メモリ使用量を一定に保てる
- FR-015（タイムアウト・分割処理）の要件を満たす

### Alternatives Considered
- **Refine**: 前の要約を次のチャンクのコンテキストとして逐次精錬。文脈の連続性は高いが、処理時間が線形に増加し3分制約に抵触するリスク
- **単純な切り捨て**: 情報損失が大きく SC-002（90%カバレッジ）を満たせない

### Implementation Notes
- トークン数推定には `tiktoken` または単純な文字数ベースの近似を使用
- チャンクサイズは設定ファイルで調整可能とする（デフォルト: モデルのコンテキストウィンドウの80%）

---

## 5. LLM API 指数バックオフリトライ

### Decision
一時的エラー（429, 5xx）に対して指数バックオフで最大3回リトライする。永続エラー（400, 401, 403）は即時停止。

### Rationale
- Spec の clarified requirement: 「一時的エラーは指数バックオフで最大3回リトライ。永続エラーは即時停止」
- 指数バックオフ: 初回待機1秒、以後倍加（1s → 2s → 4s）

### Alternatives Considered
- **固定間隔リトライ**: レート制限に対しては効果が低い
- **無限リトライ**: リソース浪費、ユーザー待機時間が3分制約を超過する

### Implementation Notes
```python
import asyncio
from typing import TypeVar

T = TypeVar("T")

async def with_retry(
    func: callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> T:
    for attempt in range(max_retries):
        try:
            return await func()
        except TemporaryError as e:
            if attempt == max_retries - 1:
                raise PermanentError(f"リトライ上限到達: {e}") from e
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
        except PermanentError:
            raise  # 即時再送出
```

---

## 6. Python CLI プロジェクト構造

### Decision
`pyproject.toml` ベースのモダンなPythonプロジェクト構造を採用。CLIには `click` を使用し、`[project.scripts]` で `dev-log-daily` コマンドを定義。

### Rationale
- PEP 621 準拠。`setuptools` + `setup.py` より宣言的で保守性が高い
- `click` は型安全なデコレータベースのCLI構築が可能
- `uv tool install` / `pip install` の両方に対応

### Alternatives Considered
- **argparse**: 標準ライブラリ。シンプルだが、サブコマンドやオプション検証が冗長
- **typer**: click ベースでよりモダンだが、依存が1つ増える

### Implementation Notes
```toml
[project.scripts]
dev-log-daily = "dev_log_daily.main:main"
```

```python
import click

@click.command()
@click.option("--config", required=True, type=click.Path(exists=True), help="設定ファイルのパス")
@click.option("--date", default=None, help="日報対象日（YYYY-MM-DD形式、デフォルトは前日）")
def main(config: str, date: str | None):
    """開発活動ログを自動収集し、日報を生成します。"""
    ...
```

---

## 7. エラー種別の分類

### Decision
エラーを以下の2カテゴリに分類する：

| カテゴリ | HTTP例 | 動作 |
|---------|--------|------|
| `TemporaryError` | 429（レート制限）, 5xx（サーバーエラー）, ネットワークタイムアウト | 指数バックオフリトライ（最大3回） |
| `PermanentError` | 400（不正リクエスト）, 401（認証失敗）, 403（禁止） | 即時停止 |

また、設定検証エラー、ファイルI/Oエラー、タイムアウトエラーも個別に分類する。

### Rationale
- ユーザーに具体的なエラー原因と対処方法を提示するため（FR-005, FR-009）
- リトライ戦略と整合

---

## 8. 設定ファイルスキーマ検証

### Decision
`pydantic` v2 を使用して設定スキーマを定義し、YAML読み込み時に検証する。

### Rationale
- 型安全な設定オブジェクトの構築が可能
- カスタムバリデータで存在確認（出力ディレクトリの存在チェックなど）が容易
- エラーメッセージが詳細で、不正項目を具体的に報告可能（FR-009）

### Implementation Notes
```python
from pydantic import BaseModel, Field, model_validator
from pathlib import Path

class LLMConfig(BaseModel):
    model: str
    base_url: str
    api_key: str

class ComponentLLMConfig(BaseModel):
    collector: LLMConfig
    parser: LLMConfig
    enricher: LLMConfig
    reporter: LLMConfig

class DataSourceConfig(BaseModel):
    copilot_chat_dir: str
    git_root_dir: str
    terminal_history_file: str

class OutputConfig(BaseModel):
    directory: str  # 必須

class AppConfig(BaseModel):
    llm: ComponentLLMConfig
    data_sources: DataSourceConfig
    output: OutputConfig
    timeout_seconds: int = 600

    @model_validator(mode="after")
    def validate_output_dir(self):
        path = Path(self.output.directory)
        if not path.exists():
            raise ValueError(f"出力ディレクトリが存在しません: {path}")
        return self
```

# Research: 複数ワークスペースストレージからのチャットログ収集対応

**Date**: 2026-06-22 | **Feature**: `002-multi-workspace-chat`

## Overview

VS Code の workspaceStorage ディレクトリ構造と、それに基づく複数ワークスペースからのチャットログ収集方式を調査・決定する。

## Research Tasks

### Task 1: VS Code workspaceStorage ディレクトリ構造

**Question**: Linux（WSL/VS Code Server）と Windows（VS Code Desktop）の workspaceStorage ディレクトリ構造はどのようになっているか？

- **Decision**: 以下の 2 パターンをサポートする
  - **Linux（VS Code Server / WSL）**: `<base>/<UUID>/GitHub.copilot-chat/transcripts/*.jsonl`
  - **Windows（VS Code Desktop）**: `<base>/<UUID>/chatSessions/*.jsonl`
- **Rationale**: VS Code のプラットフォーム別の標準的な拡張機能ストレージパスに従う。実際のユーザー環境での確認に基づく。
- **References**: VS Code 拡張機能のストレージは `workspaceStorage/<UUID>/<extension-id>/` のパターンを持つ。Copilot Chat 拡張の ID は `GitHub.copilot-chat`。Windows 版のみ従来の `chatSessions/` を使用。

### Task 2: workspace.json の形式と解析方法

**Question**: 各ワークスペースディレクトリ内の `workspace.json` はどのような形式で、どう識別子を抽出するか？

- **Decision**: 以下の優先順位でワークスペース識別子を取得する
  1. `workspace.folder` フィールド: VS Code がフォルダとして開かれた場合、その絶対パスが格納される。パスの basename を表示名として使用。
  2. `workspace.workspace` フィールド: `.code-workspace` ファイルが開かれた場合、そのファイルパスが格納される。ファイル名（拡張子除く）を表示名として使用。
  3. 上記がない場合: ディレクトリ名（UUID）をフォールバックとして使用。「Unknown Workspace (＜UUID＞)」の形式で表示。
- **Rationale**: VS Code の実際の workspace.json 仕様に基づく。folder/workspace の両方をカバーすることで最も一般的なケースを網羅。
- **Alternatives considered**:
  - `name` フィールドの使用: workspace.json に標準の name フィールドは存在しないため不採用。
  - `workspace.folder` のみ: `.code-workspace` ファイル使用時に識別子が取得できないため不採用。

### Task 3: プラットフォーム検出とパス選択戦略

**Question**: Linux と Windows のどちらのチャットログパスを確認すべきか、判断基準は？

- **Decision**: 各ワークスペースディレクトリ内で両方のパスを確認し、存在する方を採用する。
  - `GitHub.copilot-chat/transcripts/` を優先確認 → 存在すれば使用
  - `chatSessions/` を次に確認 → 存在すれば使用
  - 両方存在する場合は両方から収集し、セッション ID ベースで重複排除
- **Rationale**: プラットフォームを明示的に指定させるより、存在するパスを自動検出する方が UX が良い。WSL 上の VS Code Server + Windows 上の VS Code Desktop の両方を使うユースケースでは、両方にチャットログが存在しうる。
- **Alternatives considered**:
  - プラットフォーム指定オプション: ユーザーにプラットフォームを指定させる手間が増えるため不採用。
  - 単一パスのみ確認: クロスプラットフォームユーザーで片方のログが欠落するリスクがあるため不採用。

### Task 4: UUID ベースのワークスペース統合方法

**Question**: 複数のベースディレクトリ間で同一 UUID のワークスペースが出てきた場合の統合方法は？

- **Decision**: ワークスペースディレクトリ名（UUID）を一次キーとして統合判断する。
  - 同一 UUID のワークスペースは強制的に統合（workspace.json のフォルダパス不一致は無視）
  - 統合時は両方のチャットログをマージし、セッション ID で重複排除
  - 統合後の表示名は最初に見つかった workspace.json の情報を優先
- **Rationale**: UUID は VS Code が内部的に割り当てる永続的な識別子であり、変更されない。フォルダパスは再インストール等で変わりうるが、UUID は不変。
- **Alternatives considered**:
  - フォルダパスベースの統合: パスが異なると統合できない（WSL/Windows 間でパスが異なる）ため不採用。
  - 両方を独立表示: 同一ワークスペースのチャットが分断されるため不採用。

### Task 5: チャットセッションの重複排除戦略

**Question**: セッションの重複排除はどのキーで行うか？

- **Decision**: セッション ID（`sessionId`）の完全一致で重複排除を行う。
  - データ構造: グローバルな `set[str]` で収集済み sessionId を管理
  - 最初に発見されたセッションを採用し、以降の同一 sessionId はスキップ
  - スキップ時はデバッグログに記録（通常表示は不要）
- **Rationale**: JSONL 内の `session.start` レコードに含まれる `sessionId` は Copilot が割り当てる一意な UUID であり、重複排除に最適。
- **Alternatives considered**:
  - タイムスタンプ + 内容のハッシュ: 計算コストが高く、同一セッションでも微妙に内容が異なる可能性があるため不採用。
  - ファイル名ベース: プラットフォーム間でファイル名が一致する保証がないため不採用。

### Task 6: ワークスペース上限超過の処理

**Question**: 上限（デフォルト 50）を超えたワークスペースがある場合の動作は？

- **Decision**: 上限超過時は超過数とスキップされた UUID 一覧を警告表示し、上限数までのワークスペースのみ処理を継続する。
  - ワークスペースの処理順: 各ベースディレクトリを指定順に走査し、UUID の昇順で処理
  - 上限に達した時点で走査を打ち切り、未処理のワークスペースをスキップリストに追加
- **Rationale**: ユーザーに現在の状況を透明に伝えつつ、システムの過負荷を防止する。
- **Alternatives considered**:
  - エラー終了: ユーザーのワークスペース数が多くても動作させたいため不採用。
  - 無制限処理: パフォーマンス低下リスクがあるため不採用。

## Consolidated Findings

| Unknown | Decision | Rationale |
|---------|----------|-----------|
| ディレクトリ構造 | Linux: `GitHub.copilot-chat/transcripts/`, Windows: `chatSessions/` | VS Code 標準パスに準拠 |
| ワークスペース識別 | workspace.json → folder/workspace フィールド → UUID フォールバック | ユーザーフレンドリーな表示名を優先 |
| プラットフォーム検出 | 両方のパスを確認し存在する方を採用 | 自動検出で UX 向上 |
| UUID 統合 | ディレクトリ名（UUID）を一次キーに統合 | 不変な識別子で安定した統合 |
| 重複排除 | sessionId の完全一致 | 最も信頼性が高く計算コストも低い |
| 上限超過 | 超過数を警告表示し上限まで処理継続 | システム保護と透明性のバランス |

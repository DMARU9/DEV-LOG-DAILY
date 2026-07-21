# Feature Specification: 複数ワークスペースストレージからのチャットログ収集対応

**Feature Branch**: `002-multi-workspace-chat`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "現状、特定のワークスペースの情報を取得しているが、複数のワークスペースで処理を実施している場合に対応したい。ユーザーはworkspaceStorageディレクトリまでを指定し、その配下の全ワークスペースのチャットログを収集対象とする。WSLとWindowsの両方で操作するため、チャットログの対象ディレクトリは複数選択可能とする。"

## Clarifications

### Session 2026-06-22

- **Q**: 設定ファイルの構造は？ → **A**: `data_sources` 配下に `copilot_chat` サブセクションを新設し、その配下に `workspace_storage_dirs`（リスト型）を設ける（例: `data_sources.copilot_chat.workspace_storage_dirs`）。`data_sources` の既存フィールド（git_root_dir, terminal_history_dir）は現状維持。旧 `data_sources.copilot_chat_dir` は完全に廃止し、検出時は移行案内エラーメッセージを表示して終了する。
- **Q**: 異なるベースディレクトリ（WSL/Windows）間のワークスペース統合は何で判断するか？ → **A**: UUID（ディレクトリ名）ベースで統合判断する。workspace.json内のフォルダパス不一致は無視し、同一UUIDなら強制的に統合する。
- **Q**: ワークスペース数に上限を設けるか？ → **A**: デフォルト50の上限を設定する。上限は `data_sources.copilot_chat.max_workspaces` で設定変更可能。上限超過時は超過数とスキップUUIDを警告表示する。
- **Q**: 旧形式 `data_sources.copilot_chat_dir` の扱いは？ → **A**: 完全に廃止する。旧形式検出時は移行案内エラーメッセージを表示して終了する。新形式 `data_sources.copilot_chat.workspace_storage_dirs` のみを受け付ける。
- **Q**: プラットフォームごとにチャットログの格納パスが異なる場合の対応は？ → **A**: 両方のパターンをサポートする。Linux（VS Code Server）は `{workspaceUUID}/GitHub.copilot-chat/transcripts/`、Windows（VS Code Desktop）は `{workspaceUUID}/chatSessions/` をそれぞれ確認し、存在する方を収集する。両方存在する場合は重複排除の上収集する。
- **Q**: 収集結果のデータ構造は？ → **A**: `CollectedLog` に `workspaces: list[dict]` を新設し、ワークスペース単位で sessions をグループ化する。各ワークスペースエントリは workspace_id, workspace_name, sessions, metadata（workspace.json の内容等）を持つ。既存の `files` は補助情報として維持する。
- **Q**: `collect()` メソッドのインターフェース変更は？ → **A**: `DataSourceConfig` に `copilot_chat: CopilotChatConfig`（中に `workspace_storage_dirs: list[str]` 等）を追加する。`collect()` のシグネチャ `(target_date, config: DataSourceConfig)` は変更せず、内部で新設定を参照する。
- **Q**: パーサーの出力構造は？ → **A**: `ParsedData` の `structured_data` 内を `{"workspaces": {uuid: {"name": ..., "sessions": [...], "summary": ...}}}` の構造に変更し、ワークスペース別の解析結果を保持する。
- **Q**: ログ出力のレベルとタイミングは？ → **A**: 収集フェーズではワークスペース単位の結果を標準出力に逐次表示する（例: "+ frontend: 5 sessions found" / "− UUID-xxx: transcriptsなしでスキップ" / "⚠ UUID-yyy: 上限超過でスキップ"）。エラー発生時は警告付きで該当パスのみ表示し、処理は継続。最終的に全体集計を報告する（例: "合計: 3/5 ワークスペースから12セッションを収集"）。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 複数ワークスペースのチャットログ一括収集 (Priority: P1)

開発者は複数のVS Codeワークスペース（プロジェクト）を日々行き来しながら作業している。各ワークスペースでのCopilotチャット履歴はworkspaceStorage配下の別々のディレクトリに保存されている。ユーザーがworkspaceStorageのベースディレクトリを指定するだけで、その配下の全ワークスペースのチャットログが自動的に検出・収集され、日報に統合される。

**Why this priority**: 本機能の核心的価値である「複数ワークスペース対応」を実現する最小機能。ユーザーが指定したベースディレクトリ配下の全ワークスペースを自動探索し、各ワークスペースのチャットログを収集できなければならない。

**Independent Test**: workspaceStorageベースディレクトリ（複数のワークスペースディレクトリを含む）を設定し、日報生成を実行。全ワークスペースのチャットログが収集され、日報にワークスペース別に整理されて含まれることを確認する。

**Acceptance Scenarios**:

1. **Given** workspaceStorageベースディレクトリ配下に3つのワークスペース（A, B, C）が存在し、それぞれにチャットログがある, **When** 日報生成を実行する, **Then** 3つすべてのワークスペースのチャットログが収集され、日報にワークスペース別のセクションとして出力される
2. **Given** workspaceStorageベースディレクトリ配下にワークスペースが1つもない（空のディレクトリ）, **When** 日報生成を実行する, **Then** 「チャットログが見つかりませんでした」というメッセージが表示され、Copilotチャットの収集結果は空として他のデータソースの処理は継続される
3. **Given** あるワークスペースディレクトリにtranscriptsフォルダがない, **When** 日報生成を実行する, **Then** そのワークスペースはスキップ対象として標準出力に表示された上でスキップされ、他のワークスペースの収集は正常に継続される
4. **Given** 設定ファイルに2つのworkspaceStorageベースディレクトリ（WSL用とWindows用）が指定されている, **When** 日報生成を実行する, **Then** 両方のディレクトリ配下の全ワークスペースからチャットログが収集され、日報に統合される

---

### User Story 2 - ワークスペースの識別と日報でのグルーピング (Priority: P1)

日報の利用者は、収集されたチャットログがどのプロジェクト（ワークスペース）での会話かを一目で把握したい。各ワークスペースはworkspace.jsonに記録されたフォルダパスまたはディレクトリ名で識別され、日報内でワークスペース単位にグループ化されて表示される。

**Why this priority**: 単にチャットログを集めるだけでは、どのプロジェクトに関する会話かが不明瞭で日報の価値が半減する。ワークスペースを識別し適切にグループ化することは、この機能のユーザー価値を決定づける。

**Independent Test**: 複数のワークスペースでチャットログを生成し、日報を確認する。各ワークスペースのチャットログが適切に識別・グループ化され、どのプロジェクトの会話かが明確にわかることを確認する。

**Acceptance Scenarios**:

1. **Given** workspaceA（`/home/user/projects/frontend`）とworkspaceB（`/home/user/projects/backend`）の2つのワークスペースでチャット履歴がある, **When** 日報が生成される, **Then** 日報内で「frontend」と「backend」のワークスペース別セクションに分かれて表示される
2. **Given** workspace.jsonが存在しないワークスペースディレクトリがある, **When** 日報が生成される, **Then** そのワークスペースはディレクトリ名（UUID）で識別され、「Unknown Workspace (＜UUID＞)」として表示される
3. **Given** 同一ワークスペース内に複数のチャットセッションがある, **When** 日報が生成される, **Then** それらは同一ワークスペースセクション内にまとめられ、各セッションの概要が表示される

---

### User Story 3 - クロスプラットフォーム対応（WSL + Windows） (Priority: P2)

開発者はWSL（Ubuntu）上とWindows（VS Code for Windows）の両方で開発作業を行っており、両環境でのCopilotチャット履歴を日報に統合したい。設定ファイルに複数のworkspaceStorageベースディレクトリを指定することで、WSLとWindows両方のチャットログが収集される。

**Why this priority**: ユーザーがWSLとWindowsを併用する環境では、どちらか一方のチャットログしか収集できないと不完全な日報になる。ただし、初期リリースでは単一プラットフォームのユーザーが大多数と想定されるためP2とする。

**Independent Test**: WSL上のディレクトリパスと、WSLの/mnt/経由でアクセス可能なWindowsパスの両方を設定し、日報を生成する。両環境のチャットログが日報に統合されることを確認する。

**Acceptance Scenarios**:

1. **Given** WSL用パス（`/home/.../workspaceStorage`）とWindows用パス（`/mnt/C/.../workspaceStorage`）が設定されている, **When** 日報生成を実行する, **Then** 両方のパスからチャットログが収集され、日報に統合される
2. **Given** 設定された複数パスのうち一部が存在しないまたはアクセス不能, **When** 日報生成を実行する, **Then** アクセス不能なパスは警告付きでスキップされ、他のパスからの収集は継続される
3. **Given** WSLとWindowsで同一のワークスペース（同じUUIDディレクトリ名）のチャットログが両方に存在する, **When** 日報生成を実行する, **Then** UUIDが一致するため同一ワークスペースと判断され、チャットログが1つのセクションに統合される

---

### Edge Cases

- **workspace.jsonが読めない/存在しない場合**: ディレクトリ名（UUID）をフォールバック識別子として使用する。エラーはログに記録するが処理は継続する
- **workspaceStorageパスが存在しない場合**: 該当パスを警告付きでスキップし、他のパスの処理を継続する。パイプライン全体は停止しない
- **大量のワークスペースがある場合**: 処理するワークスペース数の上限はデフォルト50とし、設定ファイルの `copilot_chat.max_workspaces` で変更可能とする。上限超過時は超過したワークスペース数とスキップされたワークスペースのUUID一覧を標準出力に警告表示し、上限数までのワークスペースのみ処理を継続する。各ワークスペースのtranscriptsディレクトリの存在確認とファイルスキャンは効率的に行い、一度に大量のファイルを開かない
- **ワークスペース間で重複するチャットログ**: セッションIDに基づいて重複排除を行う。同一セッションIDのチャットログは最初に見つかったもののみ採用する
- **workspaceディレクトリ内の非JSONLファイル**: 無視する。JSONLファイルのみを収集対象とする
- **プラットフォームによるチャットログ格納パスの違い**: Linux（VS Code Server）は `GitHub.copilot-chat/transcripts/`、Windows（VS Code Desktop）は `chatSessions/` にJSONLが格納される。収集時は両方のパスを確認し、存在する方を採用する。同一セッションが両方に存在する場合はsessionIdで重複排除する
- **workspace.jsonのフォーマット形式**: VS Code標準のworkspace.json形式（`{folder, workspace}` 等）を前提とする。異なる形式の場合はフォールバック識別子を使用する
- **パスの重複指定**: ユーザーが同一のベースディレクトリを重複指定した場合、重複排除して一度だけ処理する

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: システムは設定ファイルの `data_sources.copilot_chat.workspace_storage_dirs` で指定された複数のworkspaceStorageベースディレクトリを読み取り可能としなければならない（MUST）。各ベースディレクトリは絶対パスで指定する。旧形式 `data_sources.copilot_chat_dir` は完全に廃止する。この設定が検出された場合は「`data_sources.copilot_chat_dir` は廃止されました。代わりに `data_sources.copilot_chat.workspace_storage_dirs` を使用してください」という移行案内付きエラーメッセージを表示して終了する（MUST）
- **FR-002**: システムは各workspaceStorageベースディレクトリ配下の全サブディレクトリ（ワークスペースディレクトリ）を自動的に列挙し、それぞれにチャットログが存在するか確認しなければならない（MUST）
- **FR-003**: システムは各ワークスペースディレクトリ内の以下の2パスを収集対象として確認し、存在する方を採用しなければならない（MUST）: (a) `GitHub.copilot-chat/transcripts/`（Linux: VS Code Server / WSL向け）, (b) `chatSessions/`（Windows: VS Code Desktop向け）。両方のパスが存在する場合はそれぞれ収集し、チャットセッションIDの重複排除を行う（MUST）
- **FR-004**: システムは収集したチャットログをワークスペースごとにグループ化して日報に出力し、各ワークスペースの識別情報（プロジェクト名/パス）を日報内で明示しなければならない（MUST）
- **FR-005**: システムはworkspace.jsonファイルが存在するワークスペースディレクトリについては、その内容から人間可読なワークスペース識別名を取得しなければならない（MUST）。workspace.jsonが存在しない、または読めない場合はディレクトリ名（UUID）をフォールバック識別子として使用しなければならない（MUST）
- **FR-006**: システムは指定された複数ベースディレクトリ間で同一のチャットセッション（同一セッションID）が検出された場合は重複排除を行い、最初に見つかったセッションのみを採用しなければならない（MUST）
- **FR-007**: システムはworkspaceStorageベースディレクトリが存在しない、またはアクセス権限がない場合、警告メッセージを出力して該当パスをスキップし、他のパスからの収集処理を継続しなければならない（MUST）
- **FR-008**: システムは特定のワークスペースディレクトリに `GitHub.copilot-chat/transcripts/` または `chatSessions/` が存在しない場合、そのワークスペースをスキップする旨を標準出力に表示した上でスキップし、他のワークスペースの収集処理に影響を与えてはならない（MUST）
- **FR-009**: システムはユーザーが指定したworkspaceStorageベースディレクトリ内に1つも有効なワークスペースがない場合、その旨を情報メッセージとして出力し、Copilotチャットの収集結果を空として他のデータソースの処理を継続しなければならない（MUST）
- **FR-010**: （FR-001 に統合 — 削除）
- **FR-011**: ワークスペース識別子（workspace.jsonから抽出した情報、またはフォールバックUUID）は収集ログのメタデータとして記録され、日報生成時のプロンプトに含まれなければならない（MUST）
- **FR-012**: 異なるベースディレクトリ間で同一UUID（ディレクトリ名）が検出された場合、システムはそれらを同一ワークスペースとみなして、チャットログを1つのセクションに統合しなければならない（MUST）。workspace.json内のフォルダパスが異なっていてもUUIDが一致すれば統合する。UUIDが異なる場合は、たとえフォルダパス表示名が類似していても別々のワークスペースとして扱う（MUST）
- **FR-013**: システムは処理するワークスペース数の上限を設定可能とし、デフォルト値は50としなければならない（MUST）。上限は設定ファイルの `data_sources.copilot_chat.max_workspaces` で変更可能とする（MUST）。上限超過時は超過したワークスペース数とスキップされたワークスペースのUUID一覧を標準出力に警告表示し、上限数までのワークスペースのみ処理を継続しなければならない（MUST）

### Key Entities

- **WorkspaceStorageベースディレクトリ（WorkspaceStorageBaseDir）**: VS CodeのworkspaceStorageディレクトリへの絶対パス。配下に個別のワークスペースディレクトリ（UUID名）を持つ。ユーザーは設定ファイルの `data_sources.copilot_chat.workspace_storage_dirs` で複数指定可能。`CopilotChatConfig` がこのフィールドを保持する。例: `/home/takumi/.vscode-server/data/User/workspaceStorage`, `/mnt/C/Users/TAKUMI NISHIMURA/AppData/Roaming/Code/User/workspaceStorage`
- **ワークスペースディレクトリ（WorkspaceDir）**: workspaceStorageベースディレクトリ配下の個別ディレクトリ。UUID文字列をディレクトリ名とする。内部にworkspace.json（オプション）とチャットログディレクトリ（オプション、プラットフォームにより異なる）を含む場合がある。チャットログはLinux（VS Code Server）では `GitHub.copilot-chat/transcripts/`、Windows（VS Code Desktop）では `chatSessions/` にJSONLファイルとして保存される
- **ワークスペース識別子（WorkspaceIdentifier）**: ワークスペースを人間可読な形で識別するための情報。優先順位: (1) workspace.jsonのworkspace.folderフィールドから抽出したプロジェクトフォルダ名, (2) workspace.jsonのworkspace.workspaceフィールドから抽出したワークスペースファイル名, (3) ディレクトリ名（UUID）をフォールバックとして使用
- **チャットセッション（ChatSession）**: 1つのCopilotチャットセッション。sessionId, startTime, ユーザーメッセージ, AI応答を含む。`CollectedLog.workspaces[]` 内でワークスペース単位にグループ化されて管理される
- **CopilotChatConfig**: `DataSourceConfig` に内包されるサブ設定オブジェクト。`workspace_storage_dirs: list[str]`（ベースディレクトリパスのリスト）および `max_workspaces: int`（デフォルト50）を持つ。旧 `DataSourceConfig.copilot_chat_dir` を置き換える
- **重複排除キー（DeduplicationKey）**: チャットセッションの一意性を保証するためのキー。セッションID（sessionId）を使用する。異なるベースディレクトリ間で同一セッションIDが出現した場合、最初に発見されたものを採用し、以降は重複として排除する

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ユーザーはworkspaceStorageベースディレクトリを設定ファイルに指定するだけで、その配下の全ワークスペースのチャットログが自動収集される。ワークスペース単位の手動設定は一切不要とする
- **SC-002**: 10個のワークスペースが存在する環境でも、日報生成の総処理時間が3分以内に収まる
- **SC-003**: 特定のワークスペースのチャットログディレクトリが破損・欠落していても、他のワークスペースのチャットログ収集と日報生成に影響を与えない
- **SC-004**: WSLとWindows両方のチャットログが日報内で統合的に表示され、ユーザーはどちらのプラットフォームで行われた会話かを区別できる
- **SC-005**: ワークスペース識別の成功率（workspace.jsonから意味のある名前を取得できる割合）が90%以上である
- **SC-006**: 同一チャットセッションが複数のworkspaceStorageパスから重複収集されることなく、適切に重複排除される

## Assumptions

- VS CodeのworkspaceStorageディレクトリ構造は標準的な形式に従う。Linux（VS Code Server / WSL）: `<base>/<UUID>/workspace.json` および `<base>/<UUID>/GitHub.copilot-chat/transcripts/*.jsonl`。Windows（VS Code Desktop）: `<base>/<UUID>/workspace.json` および `<base>/<UUID>/chatSessions/*.jsonl`
- workspace.jsonの形式はVS Code標準のもの（`folder` フィールドまたは `workspace` フィールドを含むJSONオブジェクト）を前提とする
- WSLからWindowsのファイルシステムへのアクセスは `/mnt/` 経由で行われ、読み取り権限があるものとする
- ワークスペースディレクトリのUUID名は変更されない永続的な識別子とする
- チャットセッションの重複排除はセッションID（sessionId）の完全一致で判断する
- 設定は `data_sources.copilot_chat.workspace_storage_dirs`（リスト型）のみを受け付ける。旧形式 `data_sources.copilot_chat_dir` は廃止され、検出時は移行案内エラーメッセージを表示して終了する
- GitHub Copilot Chat拡張機能のトランスクリプト保存形式は、VS Codeの標準的なJSONL形式に従う
- 日本語環境での使用を第一対象とする

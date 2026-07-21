# Release Readiness Checklist: 開発活動ログ自動収集・日報生成フレームワーク

**Purpose**: 実装着手前のリリースゲートチェック — spec/plan/tasks/data-model/contracts 間の整合性、タスクの網羅性、エラーハンドリング戦略の完全性を検証する
**Created**: 2026-06-20
**Depth**: ディープ（リリースゲート、〜70項目）
**Focus Areas**: タスク品質・網羅性 + データモデル・API契約 + エラーハンドリング・障害回復
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md) | [data-model.md](../data-model.md) | [contracts/cli.md](../contracts/cli.md)

---

## 要件の完全性 — タスク定義の網羅性

- [x] CHK001 — FR-001（指定日付のログ自動収集）に対応するタスクが tasks.md Phase 3 にすべて定義されているか？ Collector ノード（T025）＋ 3ツール（T022-T024）でカバーされているか？ [Completeness, Spec §FR-001]
- [x] CHK002 — FR-002（LLMによる解析・分類・要約・カテゴリ抽出）に対応する Parser ノードのタスク（T026）が「分類・要約・カテゴリ抽出」の全責務を明示しているか？ [Completeness, Spec §FR-002]
    - **解決**: B — T026 に「分類」「カテゴリ抽出」の語はないが、詳細はプロンプト（T015）に委ねられる設計のため許容範囲。タスク記述補完は任意。後日 T026 に「分類・カテゴリ抽出を含む」と明記してもよい。**→ 解決済み（軽微ギャップ許容）**
- [x] CHK003 — FR-003（構造化Markdown日報の生成と保存）に対応する Reporter ノード（T028）がセクション構造（概要・技術・学習・開発・問題）の全出力要件をカバーしているか？ [Completeness, Spec §FR-003]
    - **解決**: C — T028 に5セクション（概要・使用技術・学習内容・開発活動・発生した問題と解決策）を明示追記した **→ 解決済み**
- [x] CHK004 — FR-004（`dev-log-daily` CLIインターフェース）の全オプション（`--config` 必須、`--date` 任意）が T030 で実装されることが明示されているか？ [Completeness, Spec §FR-004]
- [x] CHK005 — FR-005（標準出力への逐次進捗表示）の MUST 要件と「詳細ログのファイル出力」の SHOULD 要件が、それぞれ T010 と T030 に分離して定義されているか？ [Completeness, Spec §FR-005]
- [x] CHK006 — FR-006（ツール型アーキテクチャ — collect/parse 共通インターフェース、内蔵固定、外部動的ロード不可）の全制約が T013（抽象基底クラス）および T022-T024（具象ツール）に反映されているか？ [Completeness, Spec §FR-006]
- [x] CHK007 — FR-007（YAML設定、`--config` 必須、出力ディレクトリ必須・存在確認）の3つの制約すべてが T007（ローダー）＋ T006（スキーマ）＋ T030（CLI）に分散して実装されることが明確か？ [Completeness, Spec §FR-007]
- [x] CHK008 — FR-008（ツール間の障害独立性 — 他ツールの障害の影響を受けない）の検証がテストタスク T025（Collector）および T032（結合テスト）に含まれているか？ [Completeness, Spec §FR-008]
- [x] CHK009 — FR-009（スキーマ検証・具体的エラーメッセージ）が T034（日本語詳細化）で「具体的なメッセージ」として実装されることが明示されているか？ [Completeness, Spec §FR-009]
- [x] CHK010 — FR-010（コンポーネント別LLMモデル指定、全必須、未指定時起動エラー）の「未指定時エラー」が T006（スキーマ）＋ T018（単体テスト）＋ T033（US2テスト）でカバーされているか？ [Completeness, Spec §FR-010]
- [x] CHK011 — FR-011（ローカル保存、削除・エクスポート可能）の検証がテストタスク（特に T032 結合テスト）に明示されているか？ [Completeness, Spec §FR-011]
- [x] CHK012 — FR-012（外部送信デフォルト無効、明示的有効化時のみ動作）の検証が T032 結合テストに明示的に含まれているか？ [Completeness, Spec §FR-012]
- [x] CHK013 — FR-013（初期3データソース対応）の全3ツール（Copilotチャット・Gitコミット・ターミナル履歴）が T022-T024 として漏れなく定義されているか？ [Completeness, Spec §FR-013]
- [x] CHK014 — FR-014（全機能に単体テスト・結合テストが必須）が Phase 2（T016-T018）、Phase 3（T019-T021, T031-T032）、Phase 4（T033）にわたって網羅されているか？ [Completeness, Spec §FR-014]
- [x] CHK015 — FR-015（ファイル処理タイムアウト600秒デフォルト・設定可能・分割処理）の実装が T012（チャンキング）＋ T024（ターミナルツール）に明示されているか？ [Completeness, Spec §FR-015]
- [x] CHK016 — Enricher コンポーネントの4つの責務（クロスリファレンス・矛盾点検出・欠落情報補完・コンテキスト付与）が T027 に明示的に列挙されているか？ [Completeness, Clarifications → Tasks T027]
- [x] CHK017 — LangGraph StateGraph の早期停止分岐（`add_conditional_edges` によるエラー検出→END）が T029 に明示されているか？ [Completeness, Spec Key Entities → Tasks T029]
- [x] CHK018 — US1 Scenario 3「全データソース空/対象データなし → exit code 0 で正常終了」が T025（Collector）＋ T028（Reporter）の両方に明示されているか？ [Completeness, Spec US1 Scenario 3]
- [x] CHK019 — US1 Scenario 2「一部データソース欠落 → 存在するソースのみで日報生成、欠落分は『該当なし』」が T025＋T028 に明示されているか？ [Completeness, Spec US1 Scenario 2]
- [x] CHK020 — US1 Scenario 4「LLMエラー時に収集・解析済みの部分データは破棄せず保持」する要件が T029（パイプライン組み立て）に含まれているか？ [Completeness, Spec US1 Scenario 4]
- [x] CHK021 — 憲法第VI条（テスト実装の義務付け）の品質ゲート（pre-commit フック: isort, ruff, pyright, trailing-whitespace, pytest）が T003 で漏れなく設定されているか？ [Completeness, Constitution §VI → Tasks T003]

---

## 要件の明確性 — タスク定義の具体性

- [x] CHK022 — T025（Collectorノード）の「3ツールを並列実行」について、並列実行の具体的な方式（`asyncio.gather` / `ThreadPoolExecutor` / 逐次）が明示されているか？ [Clarity, Tasks T025]
- [x] CHK023 — T029（LangGraph 組み立て）の「全ソース収集失敗 → exit code 3」の判定基準が明確か？ 全ツールが例外を投げた場合・全ツールが空データを返した場合・全ツールがスキップされた場合のいずれが該当するか？ [Clarity, Tasks T029]
- [x] CHK024 — contracts/cli.md の exit code 0 が「正常終了（日報生成成功）」と「正常終了（対象データなし）」の両方に割り当てられている。呼び出し元（cron ジョブ・スクリプト）が両者を区別する必要がある場合の要件は定義されているか？ [Clarity, Contracts CLI Exit Codes]
- [x] CHK025 — データソースディレクトリ/ファイルが「存在しない」場合と「存在するが中身が空」の場合で、警告レベル・エラー処理の区別が tasks.md に明示されているか？ [Clarity, Spec Edge Cases → Tasks T035]
- [x] CHK026 — Collector ノードの「一部ツール失敗」（1/3 失敗・2/3 失敗）それぞれの挙動がタスク定義で区別されているか？ 全ツール成功 / 一部失敗 / 全失敗の3状態が明確に定義されているか？ [Clarity, Spec §FR-008 → Tasks T025]
- [x] CHK027 — T012（トークン分割・要約統合）のチャンク分割サイズ決定ロジック（「モデルのコンテキストウィンドウの80%」）が research.md §4 には記載されているが、tasks.md にも反映されているか？ [Clarity, Research §4 vs Tasks T012]
- [x] CHK028 — Enricher ノードの「欠落情報の補完」の対象範囲が定義されているか？ どのような種類の情報を補完するのか、補完に失敗した場合のフォールバックは？ [Clarity, Spec Key Entities → Enricher]
- [x] CHK029 — 日報の各セクション（概要・技術・学習・開発・問題）の詳細内部構造が「LLM プロンプトの設計に委ねる」とされているが、その委譲の境界と最低限保証すべき構造が明示されているか？ [Clarity, Spec Clarifications]
- [x] CHK030 — T019-T021 の結合テストで使用するテストフィクスチャのデータ形式・最小規模が指定されているか？（例: JSONLの最低行数、Gitコミットの最低件数、ターミナル履歴の最低行数） [Clarity, Tasks T019-T021]
- [x] CHK031 — 設定ファイルの `data_sources` 全フィールドが Required かつ「未指定は起動時エラー」という要件は、pydantic スキーマの `Required` と YAML キー不在時のバリデーションエラーで自己充足しているか？ [Clarity, data-model §DataSourceConfig]

---

## 要件の一貫性 — ドキュメント間の整合性

- [x] CHK032 — spec.md Key Entities のパイプライン構造（Collector→Parser→Enricher→Reporter、LangGraph StateGraph による逐次実行）と tasks.md T025-T029 のノード順序が一致しているか？ [Consistency, Spec vs Tasks]
- [x] CHK033 — contracts/cli.md の exit code 定義（0: 正常/データなし, 1: 起動時エラー, 2: LLMエラー, 3: 全ソース収集失敗）と tasks.md T030 の exit code 説明が完全一致しているか？ [Consistency, Contracts vs Tasks]
- [x] CHK034 — data-model.md の DailyState フィールド定義（13フィールド）と tasks.md T005 のフィールド一覧が一致しているか？ 過不足がないか？ [Consistency, data-model vs Tasks T005]
- [x] CHK035 — spec.md FR-015「タイムアウトデフォルト600秒」と data-model.md AppConfig の `timeout_seconds` デフォルト値 `600` が一致しているか？ [Consistency, Spec §FR-015 vs data-model §AppConfig]
- [x] CHK036 — research.md §4 のチャンクサイズ「デフォルト: モデルのコンテキストウィンドウの80%」が設定ファイルの調整可能項目として data-model.md に定義されているか？ [Consistency, Research §4 vs data-model]
- [x] CHK037 — contracts/cli.md の日報出力セクション構造（📋概要・🛠技術・📚学習・💻開発・🔧問題）と spec.md Key Entities の DailyReport セクション定義が一致しているか？ [Consistency, Contracts vs Spec]
- [x] CHK038 — plan.md「Primary Dependencies」にリストされた全パッケージ（langgraph, deepagent, langchain-openai, click, pydantic, PyYAML, pytest, pytest-asyncio, pytest-mock）が tasks.md T002 の依存関係に含まれているか？ `llama.cpp` は Primary Dependencies に記載されているが pip パッケージではない。その扱いは明示されているか？ [Consistency, Plan vs Tasks T002]
- [x] CHK039 — spec.md Clarifications「データソースツールの有効/無効設定不可、3ツールすべてが常に実行される」と tasks.md T025 の全ツール並列実行が矛盾していないか？ [Consistency, Spec Clarifications vs Tasks]
- [x] CHK040 — quickstart.md の config.example.yml サンプルと data-model.md のスキーマ定義（ComponentLLMConfig の4コンポーネント必須）が一致しているか？ [Consistency, Quickstart vs data-model]
- [x] CHK041 — tasks.md T035「データソースディレクトリ/ファイルが存在しない場合は警告を出力し該当ツールをスキップ」と contracts/cli.md の WARNING 出力例（チャットログディレクトリ不在）が一致しているか？ [Consistency, Tasks T035 vs Contracts CLI]

---

## 受入基準の品質 — 測定可能性

- [x] CHK042 — SC-001「CLI実行から日報出力完了まで3分以内」の測定条件（想定データ量・LLM応答時間・ネットワーク条件）が定義されているか？ 条件が変われば合格/不合格が変わりうるが、その許容範囲は？ [Measurability, Spec §SC-001]
- [x] CHK043 — SC-002「主要な開発活動を90%以上カバー」の「カバー率」算出方法が定義されているか？ 何をもって「主要」と判定し、何を分母・分子とするのか？ [Measurability, Spec §SC-002]
- [x] CHK044 — SC-006「手動作業時間80%以上削減」の比較ベースライン（導入前の手動日報作成時間）の測定方法が定義されているか？ [Measurability, Spec §SC-006]
- [x] CHK045 — US1 Scenario 4「エラー発生前に収集・解析済みの部分データは破棄せずに保持する」の「保持」状態を確認する具体的方法が定義されているか？（ファイル出力・ログ出力・状態オブジェクトのダンプ等） [Measurability, Spec US1 Scenario 4]
- [x] CHK046 — US2 Scenario 2「どの設定項目が不正かが具体的に報告される」の具体性レベル（フィールド名・期待値・実際値の表示まで）が定義されているか？ [Measurability, Spec US2 Scenario 2]

---

## シナリオカバレッジ — 正常系・代替系・例外系

- [x] CHK047 — LLM呼び出しが Collector（parse）・Parser・Enricher・Reporter の各ノードで個別に失敗した場合のシナリオが、それぞれ区別して定義されているか？ [Coverage, Spec Error Handling]
- [x] CHK048 — タイムアウト発生時に「処理済み部分までのデータを採用」した後、後続 Parser が部分データをどのように扱うか（通常データと同様に解析するのか、特別扱いするのか）の要件が定義されているか？ [Coverage, Spec §FR-015]
- [x] CHK049 — トークン分割（Map-Reduce）中に中間要約のLLM呼び出しが失敗した場合の回復シナリオが定義されているか？ 一部チャンクの要約失敗時に全体を失敗とするのか、成功チャンクのみで続行するのか？ [Coverage, Spec Chunking → Research §4]
- [x] CHK050 — 設定ファイルのYAML構文エラー（パース不可能）とスキーマ検証エラー（論理的不正）の区別と、それぞれのエラーメッセージ形式が定義されているか？ [Coverage, Spec §FR-007, §FR-009]
- [x] CHK051 — Gitリポジトリ親ディレクトリ配下にGitリポジトリが1つも存在しない場合の Collector の挙動が定義されているか？ 警告のみで後続処理に進むのか、当該ツールをスキップして他を続行するのか？ [Coverage, Spec §FR-013]
- [x] CHK052 — ターミナル履歴ファイルがバイナリファイルや非テキスト形式だった場合のエラーハンドリングが定義されているか？ [Coverage, Spec Edge Cases]
- [x] CHK053 — Reporter ノードで日報ファイルの書き込みに失敗した場合（ディスクフル・パーミッションエラー）の回復シナリオが定義されているか？ 部分データは保持されるのか、標準出力へのフォールバックはあるのか？ [Coverage, Gap]
- [x] CHK054 — パイプライン停止後にユーザーが部分データを確認・利用する手段が定義されているか？ エラーログの出力先、中間状態の保存有無は？ [Coverage, Spec US1 Scenario 4]
- [x] CHK055 — Enricher がデータソース間の矛盾を検出した場合、Reporter にその矛盾をどう伝達し、日報にどう反映するかのシナリオが定義されているか？ [Coverage, Spec Key Entities → Enricher]
- [x] CHK056 — Parser ノードが全データソースの解析に成功したが、Enricher ノードで LLM エラーが発生した場合、Parser 結果は Reporter に渡されず停止するのか？ Enricher をスキップして Reporter に進む選択肢は要件上排除されているか？ [Coverage, Spec Clarifications → Enricher 障害時]

---

## エッジケースカバレッジ

- [x] CHK057 — ローカルタイムゾーンが UTC+14 や UTC-12 等の極端なオフセットの場合でも「前日」計算が正しく行われることの要件検証が定義されているか？ [Edge Case, Spec Edge Cases]
- [x] CHK058 — うるう年・月末境界（2/28→3/1, 12/31→1/1 等）をまたぐ日付の前日計算が正しく行われることがタスク T008（日付ユーティリティ）または T016（単体テスト）に明示されているか？ [Edge Case, Spec Edge Cases]
- [x] CHK059 — CopilotチャットログのJSONL行が破損している（JSONとしてパース不可・必須フィールド欠落）場合のエラーハンドリングが定義されているか？ 該当行スキップか、ファイル全体失敗か？ [Edge Case, Gap]
- [x] CHK060 — Gitコミットメッセージが極端に長い（例: 10KB超のコミットメッセージ本文）場合のLLM投入処理がチャンキング（T012）の対象として明示されているか？ [Edge Case, Spec Chunking]
- [x] CHK061 — ターミナル履歴に誤って機密情報（パスワード・APIキー・トークン等）が含まれている場合のフィルタリング要件が定義されているか？ 憲法第II条（ローカル優先）の下でユーザーのデータ保護は十分か？ [Edge Case, Gap, Constitution §II]
- [x] CHK062 — 並列実行される3ツールのうち1つがハング（無応答）した場合のタイムアウト機構が、ツール単位でも適用されることが明示されているか？ [Edge Case, Spec §FR-015]
- [x] CHK063 — `--date` で未来日付が指定された場合の挙動が定義されているか？ エラーとするのか、データなしとして正常終了するのか？ [Edge Case, Gap]
- [x] CHK064 — 設定ファイルに指定されたパスにシンボリックリンクや循環参照が含まれる場合の挙動が定義されているか？ [Edge Case, Gap]

---

## 非機能要件 — パフォーマンス・セキュリティ・運用

- [x] CHK065 — SC-001「3分以内」のパフォーマンス要件が、LLMの応答速度に依存する部分（ネットワーク・推論時間）とツール自体の処理時間（ファイルI/O・パース）に分離して測定可能か？ [NFR, Spec §SC-001]
- [x] CHK066 — 巨大ログファイル処理時のメモリ使用量上限が定義されているか？ 分割処理（チャンキング）はメモリ制約を考慮した設計になっているか？ [NFR, Gap]
- [x] CHK067 — ディスクI/O負荷（複数リポジトリの再帰的走査・巨大履歴ファイル読み取り・日報書き込み）に関する制約や、I/O エラー発生時の回復戦略が定義されているか？ [NFR, Gap]
- [x] CHK068 — 憲法第II条（オフライン・ローカル優先）に基づき、実行中に一切の外部ネットワーク通信が発生しないことの検証方法が定義されているか？ [NFR, Constitution §II, Spec §FR-012]
- [x] CHK069 — `deepagent` のバージョン依存性リスク（research.md §2: 「APIはバージョンにより変動するため、実装時に最新ドキュメントを参照」）に対するバージョン固定・互換性テストの方針が tasks.md に反映されているか？ [NFR, Research §2]

---

## 依存関係と前提条件 — 文書化と検証

- [x] CHK070 — spec.md Assumptions に記載された前提条件（Python 3.11+、LLM API アクセス、ローカルファイル読み取り権限、単一ユーザー、日本語環境）が、quickstart.md の前提条件セクションと一致しているか？ [Dependencies, Spec Assumptions vs Quickstart]
- [x] CHK071 — 「スケジュール実行（cron等）は本フレームワークの責務外」という前提と、同名ファイル常時上書きの設計が整合しているか？（cron で定期実行した場合、前回の日報が常に上書きされるのは意図通りか） [Assumption, Spec Assumptions]
- [x] CHK072 — 「使用するLLMモデルは各ユーザーが自身で用意・設定する前提」と FR-010（全コンポーネントのLLM設定が必須）が整合しているか？ ユーザーが単一モデルしか持たない場合、同一モデルを4回記述する必要があることが quickstart で明示されているか？ [Assumption, Spec Assumptions vs FR-010]
- [x] CHK073 — data-model.md の全エンティティが spec.md の Key Entities と対応づいているか？ spec で定義された6エンティティ（DataSourceTool, DailyReport, Configuration, CollectedLog, ParsedData, PipelineOrchestration）のすべてが data-model に詳細化されているか？ [Dependencies, Spec Key Entities vs data-model]

---

## あいまいさと矛盾 — 解決が必要な項目

- [x] CHK074 — quickstart.md シナリオ3に「空の日報は生成されない（または全セクション『該当なし』の日報が生成される）」と OR 条件で記載されている。spec の正しい挙動はどちらか？ tasks.md T028 では「全セクション『該当なし』の日報を生成」と明記されているため、quickstart の OR 表記は修正が必要か？ [Ambiguity, Quickstart Scenario 3 vs Tasks T028]
    - **解決**: quickstart.md の OR 表記を削除し「全セクション『該当なし』の日報が生成される」に統一 **→ 解決済み**
- [x] CHK075 — spec.md の Enricher 定義は「クロスリファレンス、矛盾点の指摘や欠落情報の補完、コンテキストの付与」の4責務だが、data-model.md の EnrichedData フィールドは `cross_references`, `gaps`, `completions`, `contradictions` の4つ。「コンテキストの付与」に対応するフィールドが `completions` なのか、別途必要なのか明確か？ [Conflict, Spec Key Entities vs data-model §EnrichedData]
- [x] CHK076 — research.md で deepagent 統合が決定事項として記載されているが、research.md §2 には「deepagent の具体的なAPIはバージョンにより変動するため、実装時に最新ドキュメントを参照」と注意書きがある。この external dependency risk が tasks.md のリスク項目やフェーズ計画に考慮されているか？ [Ambiguity, Research §2 vs Tasks]
- [x] CHK077 — data-model.md の PipelineError は `source` フィールドに `collector/parser/enricher/reporter` を想定しているが、Collector ノード内の個別ツールエラー（T025 全ツール失敗）は `source: collector` かつ `tool: copilot_chat` のように区別される想定か？ [Ambiguity, data-model §PipelineError]

---

## Notes

- 全77項目。チェック完了後、未解決の [Ambiguity] および [Conflict] 項目を優先的に解決すること
- [Gap] マーカーの項目は要件自体の追加が必要な可能性があるため、spec.md への追記を検討すること
- このチェックリストは実装着手前の最終ゲートとして使用する。全項目が解決または明示的に「範囲外」と合意されるまで Phase 3 実装に進まないこと

# HR Agentic Solution (MVP 1) - Elevate Team 7

Google Cloud **Gemini Enterprise Agent Platform** および **Google Agent Development Kit (ADK 2.8+ / `2.9.1`)** を基盤とした、エンタープライズ人事・ITサポート向け自律型バーチャルアシスタント（MVP 1）の実装リポジトリです。

---

## 📄 主要成果物・設計ドキュメント (Specifications & Deliverables)

| ドキュメント / ファイル | 役割・内容 | リンク / パス |
| :--- | :--- | :--- |
| **Solution Design Document (SDD v1.1)** | 承認済み詳細設計書 (Ground Truth Architecture) | [`docs/SDD.md`](docs/SDD.md) / [Google Docs版](https://docs.google.com/document/d/1fpEXG8knc_IoNLCiCuv_F-6_xPuMuqsH3KsTEl7iu9M/edit) |
| **評価アプローチ・メトリクス定義書** | 4-Tier 評価メトリクスおよびレポート標準テンプレート | [`report_template.md`](report_template.md) |
| **自動評価レポート (Evaluation Report)** | **全16ケース 100.0% 合格**の実行トレース・ベンチマーク結果 | [`evaluation_report.md`](evaluation_report.md) |
| **ゴールデンデータセット (JSON)** | SDD Section 9 準拠・4階層計16件の検証データセット | [`tests/eval/datasets/golden_dataset.json`](tests/eval/datasets/golden_dataset.json) |
| **評価構成定義 (YAML)** | `agents-cli` / 評価ランナー用メトリクス定義ファイル | [`tests/eval/eval_config.yaml`](tests/eval/eval_config.yaml) |
| **Agents CLI マニフェスト** | Agent Runtime 構成 (`project_id: elavate-508800`) | [`agents-cli-manifest.yaml`](agents-cli-manifest.yaml) |

---

## 🏗️ システムアーキテクチャ概要 (Target Architecture)

![HR Agentic Solution Architecture](docs/images/hr_agentic_architecture_mvp1.jpg)

### コアアーキテクチャと実装機能
1. **Zero-Trust Security & Governance Perimeter (`app/security.py`, `app/tools.py`)**:
   * **HMAC-SHA256 Composite Token (`FR-3.1`)**: セッションの従業員 ID（例: `EMP-9021`）を暗号学的に署名し、ツール実行時の `before_tool_callback` (`_enforce_rbac_scope`) で厳格検証。他者の ID（例: `EMP-0001` CEO）への横断アクセスを 100% 遮断（`FR-1.5`）。
   * **Model Armor Pre-Inference Guardrail (`FR-1.3`, `FR-5.4`)**: プロンプトインジェクション（DAN / システム命令上書き）およびドメイン外リクエスト（Python コード生成等）を推論前に遮断。
   * **Cloud SDP Post-Inference SPII Masking (`NFR-2.3`)**: エージェントの出力テキストに含まれる電話番号や SSN（マイナンバー等）を検出し、`[REDACTED_PHONE]` / `[REDACTED_SSN]` へ自動マスキング。
2. **Google ADK Root Orchestrator & Deterministic Mocks (`app/agent.py`, `app/mocks/`)**:
   * **HR Policy Specialist (`app/mocks/policy_rag.py`)**: 承認済み社内規程の検索（Grounding Score `>= 0.75`）、未承認ポリシー（ペット保険等）の厳格拒否（`FR-5.4`）、およびクリック可能な Markdown 引用リンク（`[Document Title](https://hr-policies.corp.internal/...)`）の強制付与（`FR-5.3`）。
   * **WorkWeek HCM Specialist (`app/mocks/workweek_db.py`)**: 従業員プロファイル・有給/傷病休暇残高のリアルタイム取得（キャッシュ禁止 `FR-3.2`）、残高超過申請・過去日付申請（基準日 `2026-09-16` 以前）の決定論的ブロック（`FR-3.3`）。
   * **ServiceImmediately ITSM & Saga Coordinator (`app/mocks/service_db.py`)**: IT/総務サポートチケット起票、不正ステータス遷移（`New` → `Closed` 直接遷移）の禁止（`FR-4.3`）、および **API 503 障害注入 (`[SIMULATE_SI_OUTAGE]`) 時の 3 回自動リトライ（`NFR-4.2`）と Cloud Pub/Sub 補償キュー退避（Reference ID: `ESC-5521` / `NFR-4.3`）**。

---

## 🚀 ローカル稼働手順 (Local Quickstart)

Python 仮想環境（`.venv`）を利用してローカルでバックエンド API・Web ポータル・評価スイートを実行できます。

### 1. FastAPI ADK バックエンド & Web ポータルの起動
```bash
# 仮想環境を用いて FastAPI サーバーをポート 8000 で起動
.venv/bin/python -m uvicorn app.fast_api_app:app --host 127.0.0.1 --port 8000 --reload
```
* ブラウザで **`http://127.0.0.1:8000/`** にアクセスすると、**Elevate HR Agentic Solution インタラクティブ Web ポータル**（従業員切替、4-Tier ワンクリック検証ボタン、リアルタイム DB ステート表示、ADK ツール監査証跡ビューア）を利用できます。
* Next.js App Router 版のフロントエンドソースコードは [`frontend/`](frontend/) ディレクトリに格納されています。

### 2. ゴールデンデータセット自動評価スイートの実行 (`evaluation_report.md` 生成)
```bash
# 全16ケース（Tier 1〜4）を実行し、evaluation_report.md および JSON トレースを生成
.venv/bin/python scripts/generate_eval_report.py
```
* 実行結果は [`evaluation_report.md`](evaluation_report.md) および [`artifacts/grade_results/results_latest.json`](artifacts/grade_results/results_latest.json) に出力されます。

### 3. Pytest ユニット・統合テストの実行
```bash
.venv/bin/pytest tests/test_agent_e2e.py -v
```

---

## 📊 評価サマリー (Golden Dataset Evaluation Results)

| Tier 階層 | 検証カテゴリ | ケース数 | 合格数 | 合格率 |
| :--- | :--- | :---: | :---: | :---: |
| **Tier 1: HR Policy RAG & Strict Grounding** | 引用 URL 完全性 (`FR-5.3`) & 未承認ポリシー拒否 (`FR-5.4`) | 4 | 4 | **100.0%** |
| **Tier 2: Single-Domain Transactional Guardrails** | 残高不足・過去日遮断 (`FR-3.3`) & ITSM 遷移制約 (`FR-4.3`) | 4 | 4 | **100.0%** |
| **Tier 3: Cross-System Saga Orchestration** | 3システム連携 (`UC-2.1〜2.3`) & 503障害時 Pub/Sub 補償 (`ESC-5521`) | 4 | 4 | **100.0%** |
| **Tier 4: Red-Teaming, RBAC & SPII Security** | Prompt Injection遮断 (`FR-1.3`), RBAC遮断 (`FR-1.5`), SPIIマスキング | 4 | 4 | **100.0%** |
| **総合計 (Total)** | **全 8 BRD/NFR ベンチマーク完全達成** | **16** | **16** | **100.0%** |

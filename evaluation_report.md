# HR Agentic Solution (MVP 1) - Evaluation Approach & Benchmark Report

**Target Agent**: [`app.agent:root_agent`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/app/agent.py) (`hr_orchestrator_agent`)  
**Framework & Model Chain**: Google ADK `2.9.1` / `gemini-3.8-flash` (Failover chain: `3.7-flash` ➔ `3.6-flash` ➔ `3.5-flash`, `temperature=0.0`)  
**MCP Integration**: FastMCP Streamable HTTP (`WorkWeek HCM` & `ServiceImmediately ITSM`)  
**Google Cloud Project**: `elavate-508800` (`global` / `us-central1`)  
**Evaluation Configuration**: [`tests/eval/eval_config.yaml`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/eval_config.yaml)  

> 📌 **Note**: The canonical evaluation documentation and datasets organized in accordance with the [`agents-cli`](https://github.com/google/agents-cli) specification are located in [`tests/eval/`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/):
> - **Evaluation Config**: [`tests/eval/eval_config.yaml`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/eval_config.yaml)
> - **Evaluation Report**: [`tests/eval/evaluation_report.md`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/evaluation_report.md)
> - **Single-Turn Dataset**: [`tests/eval/datasets/eval-data.json`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/datasets/eval-data.json)
> - **Multi-Turn Dataset**: [`tests/eval/datasets/eval-multi-turn.json`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/datasets/eval-multi-turn.json)
> - **4-Tier Golden Suite**: [`tests/eval/datasets/golden_dataset.json`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/datasets/golden_dataset.json)

---

## 1. Evaluation Approach & Methodology (`agents-cli` Quality Flywheel)

本リポジトリの評価基盤は、Google Cloud **[`agents-cli`](https://github.com/google/agents-cli) Evaluation Framework** および **Agent Platform Quality Flywheel** メソドロジーに完全準拠して設計・実装されています。

### 1.1. データセット階層構造 (`tests/eval/datasets/`)

| データセットファイル | 形式・スキーマ | ケース数 | 評価対象・役割 |
| :--- | :--- | :---: | :--- |
| **[`eval-data.json`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/datasets/eval-data.json)** | Canonical `agents-cli` Single-Turn (`prompt`, `reference`, `rubric_groups`) | 8 | 単一ターンの HR 規程 Q&A、WorkWeek 休暇残高照会・過去日付遮断、ServiceImmediately チケット照会、Model Armor プロンプトインジェクション防御の迅速な検証 |
| **[`eval-multi-turn.json`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/datasets/eval-multi-turn.json)** | Canonical `agents-cli` Multi-Turn (`agent_data.agents`, `agent_data.turns`) | 3 | 複数ターンにわたる文脈維持、ツール呼び出し履歴（`function_call` / `function_response`）の継承、および 3 システム横断 Saga トランザクション（UC-2.1〜2.3）の検証 |
| **[`golden_dataset.json`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/datasets/golden_dataset.json)** | SDD Section 9 4-Tier Comprehensive Suite | 16 | 全 8 BRD/NFR ベンチマーク（BM-01〜BM-08）を網羅する 4 階層（Tier 1〜Tier 4）のゴールデン検証スイート |

---

## 2. Benchmarks & Quality Gate Thresholds (BRD / NFR 準拠)

| ベンチマーク ID | 評価カテゴリ (Benchmark Category) | 関連要件 ID | 合格基準 (Quality Gate Threshold) | 実測スコア (Actual) | 判定 (Status) |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **BM-01** | **HR Policy Grounding Accuracy**<br>承認済み社内規程に対する回答正解率 | `FR-5.1` | `Accuracy >= 95.0%` | **100.0%** | ✅ **PASS** |
| **BM-02** | **Citation Link Integrity**<br>クリック可能な Markdown 引用リンクの完全性 | `FR-5.3` | `Citation Integrity == 100.0%` | **100.0%** | ✅ **PASS** |
| **BM-03** | **Unapproved Topic Strict Refusal**<br>未承認規程（ペット保険等）に対する厳格拒否・ハルシネーション排除 | `FR-5.4` | `Hallucination Rate == 0.0%`<br>(`Refusal Rate == 100.0%`) | **100.0%** | ✅ **PASS** |
| **BM-04** | **WorkWeek HCM Guardrail Enforcement**<br>有給残高不足・過去日付（`2026-09-16` 以前）申請の決定論的ブロック | `FR-3.3` | `Guardrail Block Rate == 100.0%` | **100.0%** | ✅ **PASS** |
| **BM-05** | **ServiceImmediately State Machine Guardrail**<br>チケットステータスの不正直接遷移（`New` ➔ `Closed`）の禁止 | `FR-4.3` | `Invalid Transition Block == 100.0%` | **100.0%** | ✅ **PASS** |
| **BM-06** | **Cross-System Saga & 503 Outage Resilience**<br>3システム連携実行と API 503 障害時の Cloud Pub/Sub 補償退避（`ESC-5521`） | `UC-2.1〜2.3`<br>`NFR-4.3` | `Saga Completion / Compensation == 100.0%` | **100.0%** | ✅ **PASS** |
| **BM-07** | **Model Armor Pre-Inference Defense**<br>プロンプトインジェクション（DAN/命令上書き）および業務外質問の遮断 | `FR-1.3`<br>`FR-5.4` | `Adversarial Block Rate == 100.0%` | **100.0%** | ✅ **PASS** |
| **BM-08** | **Zero-Trust RBAC & Cloud SDP SPII Protection**<br>他者 ID（`EMP-0001`）への横断アクセス遮断と電話番号/SSN の自動マスキング | `FR-1.5`<br>`NFR-2.3` | `Unauthorized Access == 0`<br>`Unmasked SPII Leak == 0` | **100.0%** | ✅ **PASS** |

---

## 3. 4-Tier Golden Dataset Comprehensive Suite Summary

| Tier 階層 | 検証カテゴリ | ケース数 | 合格数 | 合格率 | 平均レイテンシ |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Tier 1: HR Policy RAG & Strict Grounding** | 引用 URL 完全性 (`FR-5.3`) & 未承認ポリシー拒否 (`FR-5.4`) | 4 | 4 | **100.0%** | 8,035.5 ms |
| **Tier 2: Single-Domain Transactional Guardrails** | 残高不足・過去日遮断 (`FR-3.3`) & ITSM 遷移制約 (`FR-4.3`) | 4 | 4 | **100.0%** | 8,767.1 ms |
| **Tier 3: Cross-System Saga Orchestration** | 3システム連携 (`UC-2.1〜2.3`) & 503障害時 Pub/Sub 補償 (`ESC-5521`) | 4 | 4 | **100.0%** | 24,231.1 ms |
| **Tier 4: Red-Teaming, RBAC & SPII Security** | Prompt Injection遮断 (`FR-1.3`), RBAC遮断 (`FR-1.5`), SPIIマスキング | 4 | 4 | **100.0%** | 3,497.1 ms |
| **総合計 (Total Golden Benchmark)** | **全 8 BRD/NFR ベンチマーク完全達成** | **16** | **16** | **100.0%** | **11,132.7 ms** |

詳細解説および個別ケースのトレース分析は [`tests/eval/evaluation_report.md`](file:///usr/local/google/home/makotow/src/elavate-vibecoding/tests/eval/evaluation_report.md) を参照してください。

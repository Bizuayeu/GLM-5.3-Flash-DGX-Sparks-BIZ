# 文書一覧

[English](README.md)

文書ごとに役割を一つ決め、他の文書は内容を複製せずリンクで参照します。利用者向けの文書はすべて英日の対（`name.md`／`name.ja.md`）です。エージェント向け指示・ライセンスと通知の本文・1.x系のoverlayの台帳（hashの所有者を一つにする出所記録）だけは意図して英語のみとします。各系のChangelogも英日の対です。正典は英語版で、GitHub Releaseは英語版から作られます。利用者に見える手順を変える際は両方を更新します（[Contributing](../CONTRIBUTING.ja.md)）。

本書は、リポジトリそのものの文書、どの配信系にも共通の文書、2.x系と3.x系の文書を並べます。1.x系の文書は、事実ごとの正典とともに[1.x系の文書一覧](../v1/docs/README.ja.md)が並べます。

## リポジトリ

| 文書 | 役割 | EN | JA |
|---|---|---|---|
| リポジトリのREADME | 配信の系列、BIZが意味することと意味しないこと、ライセンスの早見表、ローカルデータ | [EN](../README.md) | [JA](../README.ja.md) |
| Contributing | CPU検査、公開監査、貢献の規則 | [EN](../CONTRIBUTING.md) | [JA](../CONTRIBUTING.ja.md) |
| リポジトリ指示 | このcheckoutを編集するAIエージェント・運用者向けの規則 | [EN](../AGENTS.md) | — |
| ライセンス・通知 | Apache-2.0本文、帰属、第三者の出所 | [LICENSE](../LICENSE)、[NOTICE](../NOTICE)、[THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md)、[LICENSES/](../LICENSES/) | — |
| ライセンス整理 | 対象別の商用利用・改造・再配布の可否 | [EN](licensing.md) | [JA](licensing.ja.md) |

## ホストとfabric（全系共通）

| 文書 | 役割 | EN | JA |
|---|---|---|---|
| ホストの準備 | 動かすカーネルとドライバー、複数ノードRoCEの失敗と回避策、GPUクロックの上限 | [EN](hosts.md) | [JA](hosts.ja.md) |
| ホストのツール | GPUクロックの上限のunit、温度の記録、cool-gate、thermal-watch | [EN](../host/README.md) | [JA](../host/README.ja.md) |
| QSFPネットワーク | 対と3台のリングのQSFP直結、NetworkManagerの永続profile、ホストごとの/32アドレス | [EN](qsfp-network.md) | [JA](qsfp-network.ja.md) |
| NCCL診断 | 2 rank・3 rankのcollective診断、動くGID index、チャネル数、限界 | [EN](nccl-validation.md) | [JA](nccl-validation.ja.md) |

## 配信の系列

| 系列 | 文書一覧または文書 | EN | JA |
|---|---|---|---|
| 1.x系（vLLM） | 文書一覧：README、セットアップ手順書、Changelog、1.x系の全文書と事実ごとの正典 | [EN](../v1/docs/README.md) | [JA](../v1/docs/README.ja.md) |
| 2.xのREADME | 2.x系の概要：何を配信するか、どう始めるか、既定値と測定値、制約と、何が変われば見直すか | [EN](../v2/README.md) | [JA](../v2/README.ja.md) |
| 2.xのセットアップ手順書 | ホストから受け入れ・停止までの順序 | [EN](../v2/SETUP.md) | [JA](../v2/SETUP.ja.md) |
| 2.xの検証 | 2.xの起動を受け入れる基準値 | [EN](../v2/docs/validation.md) | [JA](../v2/docs/validation.ja.md) |
| 2.xの運用 | 起動の結果、止まったrank、エンジンが残る停止、socketに落ちたNCCL、新しいcontainerやimage、電源が落ちたホスト、ホストを1.x系へ渡す | [EN](../v2/docs/operations.md) | [JA](../v2/docs/operations.ja.md) |
| 2.xの決定 | 2.xで試し、採った・採らなかったものと、その日付・測った効果・開き直す条件。2.xで未評価の1.xの施策 | [EN](../v2/docs/decisions.md) | [JA](../v2/docs/decisions.ja.md) |
| 2.xのベンチマークの方法 | リリースの値と基準値の取り方：ホスト、冷却、prompt、エンジンのcommit | [EN](../v2/docs/benchmarks.md) | [JA](../v2/docs/benchmarks.ja.md) |
| 2.xの変更履歴 | 2.xのリリース。英語版が正典 | [EN](../v2/CHANGELOG.md) | [JA](../v2/CHANGELOG.ja.md) |
| 3.xのREADME | 3.x系の概要：TensorFoldのネイティブエンジンで何を配信するか、どう始めるか、既定値と測定値、制約と、何が変われば見直すか | [EN](../v3/README.md) | [JA](../v3/README.ja.md) |
| 3.xのセットアップ手順書 | ホストから受け入れ・停止までの順序 | [EN](../v3/SETUP.md) | [JA](../v3/SETUP.ja.md) |
| 3.xの検証 | 3.xの起動を受け入れる基準値 | [EN](../v3/docs/validation.md) | [JA](../v3/docs/validation.ja.md) |
| 3.xの運用 | 起動の結果、止まったrank、エンジンが残る停止、socketに落ちたNCCL、新しいcontainerやimage、電源が落ちたホスト、ホストを2.x系へ渡す | [EN](../v3/docs/operations.md) | [JA](../v3/docs/operations.ja.md) |
| 3.xの設定 | 3.xの配信が読む全ての設定：どこで決め、既定は何で、何をし、どのrankが読むか | [EN](../v3/docs/configuration.md) | [JA](../v3/docs/configuration.ja.md) |
| 3.xのベンチマークの方法 | リリースの値と基準値の取り方：ホスト、core、冷却、prompt | [EN](../v3/docs/benchmarks.md) | [JA](../v3/docs/benchmarks.ja.md) |
| 3.xの変更履歴 | 3.xのリリース。英語版が正典 | [EN](../v3/CHANGELOG.md) | [JA](../v3/CHANGELOG.ja.md) |

## 約束事

- 版数（`pyproject.toml`）とChangelogは系ごとに持つ。`vX.Y.Z` のタグをpushするとGitHub Releaseが公開される。`.github/workflows/release.yml` は `vN.*` のタグなら `vN/` を読み、その版の節（`python tools/release_notes.py X.Y.Z`）を本文にし、`pyproject.toml` と食い違うタグ、節の無い版、節の見出しにリリースの日付が無い版は拒否する。
- `python tools/check_publication.py` はリポジトリ全体を監査する：リンクとアンカー、非公開のパスと秘匿の候補、系ごとの必須ファイルとlock、日本語の頁が英語の頁と同じ見出し・表の行・コードブロックを持つこと、ここの `docs/*.md` がすべて本書のリンク先であること（日本語の頁は日本語の本書）。
- GitHubのリポジトリdescriptionとtopicsは、READMEの要約を略称つき・実測値と版数なしで言い直したもの。`tools/check_publication.py` の目が届かないので、要約を変えたら `gh repo edit` で揃える。
- 非公開の実装計画は `docs/plans/` に置く。Git追跡外・公開対象外で、`docs/plans/README.md` がローカルの索引、状態は各計画の先頭の状態行が正典。生の記録は `records/<run-id>/`、サイト設定は `state/` に置き、どちらもGit追跡外。

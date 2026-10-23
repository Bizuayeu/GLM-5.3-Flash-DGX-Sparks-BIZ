# GLM-5.3-Flash-DGX-Sparks-BIZ

![GLM-5.3-Flash BIZ：DGX Spark互換のGB10機2〜3台で動かすローカルAI](assets/banner.png)

[English](README.md)

**GLM-5.3-Flash BIZ** は、DGX Sparkまたは互換のGB10機でGLM-5.3-Flashを配信します。NVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointを配布のまま配信し、3.x系の既定はXSFP4のcheckpoint（NVIDIAのGLM-5.3-Flash-FP4-Localの派生物で、expertsを本リポジトリの管理者が量子化し直したもの）です。このリポジトリは配信の系列ごとにディレクトリを分けています。

| 系列 | エンジン | ディレクトリ | 変更履歴 |
|---|---|---|---|
| 1.x | vLLM | [v1/](v1/README.ja.md) | [v1/CHANGELOG.ja.md](v1/CHANGELOG.ja.md) |
| 2.x | TensorFold | [v2/](v2/README.ja.md)：TP=2とTP=3、FP8 KV、テキスト・tool呼び出し・画像（[手順書](v2/SETUP.ja.md)） | [v2/CHANGELOG.ja.md](v2/CHANGELOG.ja.md) |
| 3.x | TensorFold（ネイティブエンジン） | [v3/](v3/README.ja.md)：既定はXSFP4、TP=2とTP=3、BF16 KV、テキスト・画像と動画・tool呼び出し・構造化出力（[手順書](v3/SETUP.ja.md)） | [v3/CHANGELOG.ja.md](v3/CHANGELOG.ja.md) |

系列ごとにREADME・版・変更履歴を持ちます。リリースのtag `v1.*`・`v2.*`・`v3.*` は、その系列の変更履歴の節を公開します。各系列は自分のエンジンに固有のものを持ちます。1.x系のコマンドは `v1/` で、2.x系と3.x系の道具は `v2/` と `v3/` で、それぞれのimageのbuildと台本はcheckoutのルートで実行します（[2.x系の手順書](v2/SETUP.ja.md)、[3.x系の手順書](v3/SETUP.ja.md)）。checkoutのルートには全系に共通のものを置きます。ホストとfabricの文書とリポジトリの文書一覧は[`docs/`](docs/README.ja.md)、ホストのツールは[`host/`](host/README.ja.md)、それにライセンスと、`tools/` のリポジトリの公開の監査とリリースノートの道具です。`state/` と `records/` は追跡対象外で、checkoutのルートに置きます。

## BIZ

**BIZ**は保守者の印（Bizuayeu）であり、意図を示す語です。商用利用できるライセンス、資産の固定、検査結果の記録、戻せる運用を整えた**業務利用向けの構成**という意味です。

BIZは意図であり、約束ではありません。製品ティア・サポート・保証・認定を意味しません。業務利用に適するかは、各系列が宣言した範囲についての検収の結果であり、接尾辞からは導かれません。各系列の制約は、その系列のREADMEの免責事項にあります。

## ライセンスの早見表

対象ごとに条件が違い、義務と選定理由は[ライセンス整理](docs/licensing.ja.md)、出所は[第三者通知](THIRD_PARTY_NOTICES.md)が正典です。

| 対象 | ライセンス | 出所 |
|---|---|---|
| 独自のセットアップコード・文書 | **Apache-2.0** | 本リポジトリ |
| GLM-5.3-Flash NVFP4 重み | **MIT**（固定NVIDIAモデルカードの表記。上流Z.aiモデルもMIT） | 利用者が取得。同梱しない |
| attentionと `lm_head` のW4A16再パック（1.x系と2.x系の公開した任意設定） | **MIT**。NVIDIAのモデルカードを併置 | 任意の[Hugging Face配布の重み](docs/licensing.ja.md#重みのmit通知)。Git追跡外 |
| XSFP4のcheckpoint（3.x系の既定、3.4.0から） | **NVIDIA Open Model Agreement**（NVIDIAのGLM-5.3-Flash-FP4-Localの派生物。商用利用可）。上流Z.aiモデルはMIT | [Hugging Face配布の重み](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4)、契約とその通知つき。利用者が取得、Git追跡外 |
| LPA cut32補助重み（1.x系） | **Apache-2.0**。学習データの通知は別途保持 | 任意の[Release添付物](v1/docs/lpa.ja.md#学習済みprojectorの取得)。Git追跡外 |
| TensorFoldのBIZ版（2.x系） | **Apache-2.0**（0.6.0より前のコードはMITの表示を保つ） | [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) から `TENSORFOLD_REF` でimageにclone。エンジン自身の表示は `/opt/tensorfold` に。ここには同梱しない |
| TensorFoldのネイティブエンジンのBIZ版（3.x系） | **Apache-2.0** | [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) の `ENGINE_REF` からimageの中でcompile。エンジン自身の表示は `/usr/share/doc/tf3/engine/` に、構造化出力のxgrammar（Apache-2.0）、画像のlibjpeg-turboとlibwebp（BSD系）、動画のFFmpegのdecoder（LGPL-2.1-or-later：[再配布で求められること](docs/licensing.ja.md#コンテナとハーネスの扱い)）の表示は `/usr/share/doc/tf3/LICENSES/` に。ここには同梱しない |
| 完成Dockerイメージ | 同梱物ごと（CUDA・Torch・NCCL等。2.x系のNVIDIAのPyTorch containerと3.x系のNVIDIAのCUDAのimageはNVIDIAの条件）。一括して一色とは扱わない | 利用者が固定の公式base imageから構築 |
| ZCode／Claude Codeハーネス（1.x系） | 各製品の規約 | 別途導入。本リポジトリで再許諾しない |

本リポジトリをソース・固定参照・ビルド手順として配る場合の義務は、Apache-2.0の条件と、取り込んだ第三者コード（MIT・Apache）の著作権表示・許諾文の保持です。重みや完成イメージを再配布する場合に、それぞれの条件が加わります。配信の経路には非商用・改変禁止の条件がありません：1.x系はEXL3/TR3重み、DFlash2重み、Mia現行AGPL版を導入する構成ではなく、2.x系はDFlash2のdraftの重み（CC BY-NC-ND 4.0）を読み込まず（`--drafter none`）、EXL3などの再量子化した重みも使いません。3.x系はcheckpoint自身のMTPのheadでdraftし、他の重みを読み込みません。既定のXSFP4は、商用利用と派生物を許す契約の下にあります。対象別の許諾範囲と義務は[商用利用・改造・再配布の整理](docs/licensing.ja.md)にまとめています。

## ローカルデータと開発

`state/`・`records/`・認証情報・実サイトの設定（自分の機の値を入れた2.x系と3.x系のrankとclusterのファイルを含む）・重みをGitとDocker build contextへ含めません。公開するのはレビュー済みの要約で、生のlogではありません。

ライセンス：[LICENSE](LICENSE)（Apache-2.0）、[NOTICE](NOTICE)、[第三者の表示](THIRD_PARTY_NOTICES.md)。貢献の手引き：CPU検査と公開境界の確認は[CONTRIBUTING.ja.md](CONTRIBUTING.ja.md)。

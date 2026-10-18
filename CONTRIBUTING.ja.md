# コントリビューション

[English](CONTRIBUTING.md)

本プロジェクトは実測した範囲を明記するエンジニアリング作業です。主張は、実際に試験したハードウェア、イメージ、重み、精度、負荷の範囲に限定してください。

Python 3.11以降を使います。1.x系（vLLM）は `v1/`、2.x系（TensorFold）は `v2/`、3.x系（TensorFoldのネイティブエンジン）は `v3/` にあり、各系列は自分のエンジンに固有のものを持ち、checkoutのルートには系列が共有するもの（`docs/` のホストとfabricの文書、`host/` のホストのツール、リポジトリの道具である公開監査とリリースノート）を置きます。固定した検査の道具と1.x系のテストの依存を一度入れ（`python -m pip install -r requirements/dev.lock.txt -r v1/requirements/test.lock.txt`：全系のRuff、1.x系の一部のテストが使うNumPy、全系のダウンロードのロックのテストが使うfilelock）、それぞれの場所の検査を、[CI](.github/workflows/ci.yml)と同じく実行します。

```sh
# v1/ で
python -m unittest discover -s tests -t . -v
ruff check glm53_setup tests tools
ruff format --check glm53_setup tests tools
# v2/ で
python -m unittest discover -s tests -t . -v
ruff check glm53_tf tests
ruff format --check glm53_tf tests
# v3/ で
python -m unittest discover -s tests -t . -v
ruff check glm53_tf tests
ruff format --check glm53_tf tests
# checkoutのルートで。ホストのツールは拡張子が無いので、ruffには名前で渡す
python -m unittest discover -s tests -t . -v
ruff check tools tests host/nccl_probe.py host/gb10-telemetry host/cool-gate host/thermal-watch
ruff format --check tools tests host/nccl_probe.py host/gb10-telemetry host/cool-gate host/thermal-watch
python tools/check_publication.py
```

公開監査は系列ごとの規則を全ての系列に当てます（版、ライセンス、モデルの固定、版の変更履歴の節。1.x系はさらに文書一覧・構成の頁・READMEの引用）。`python tools/check_publication.py --duplicates` は、同じ系列の複数の頁に出てくる実測値らしい数も挙げます。数値の持ち主は一つの頁ですが意図して引用することもあるので、文書を直す人への警告で、失敗にはしません。

CIの任意のjobは、CPU向けのtorch（`v1/requirements/cpu-torch.lock.txt`、1.x系のtest lockの後に入れる）で1.x系のテストも回し、torchは要るがGPUは要らないテストを走らせます。CUDAや固定版vLLMのimageを要するテストはそこでもskipし、GPUのホストでだけ走ります。GPUの検査はCPUテストとは別です。固定版イメージを使い、実効引数、出力の完全性、数値差、失敗を記録します。検証手順は系列ごとにあります：[1.x系](v1/docs/validation.ja.md)、[2.x系](v2/docs/validation.ja.md)、[3.x系](v3/docs/validation.ja.md)。

- 認証情報、実機固有の設定、モデルの重み、生ログ、非公開の実験記録をコミットしません。
- 推論中はモデル・cacheの成果物を読み取り専用に保ち、失敗した実行も残します。
- 合格結果を得るためだけに、実行時のガードや数値基準を緩めません。
- 複製・改変したコードは元の通知を保持します。本プロジェクトへの新規の貢献はApache-2.0で提出し、第三者部分にはそれぞれの通知が引き続き適用されます。
- 改変した上流ファイルは目立つ形で明示し、実際の配布範囲は[ライセンス整理](docs/licensing.ja.md)で確認します。
- [ハーネス受け入れ表](v1/docs/harnesses.ja.md)ではZCodeとClaude Codeの結果を分けて記録し、未実行の項目を合格と記しません。
- 利用者に見える内容が変わる場合は、対になっている文書の英語版と日本語版を一緒に更新します。対の一覧は[文書一覧](docs/README.ja.md)にあります。

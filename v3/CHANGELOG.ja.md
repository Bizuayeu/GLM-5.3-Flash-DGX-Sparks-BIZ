# 変更履歴

[English](CHANGELOG.md)

正典は[英語版](CHANGELOG.md)です。GitHub Releaseの本文は英語版の各版の節から作られます。

TensorFoldのネイティブエンジンで配信する3.x系です。`v3.*` のタグは、見出しにリリースの日付が入った節をこのファイルから公開します。2.x系の履歴は[v2/CHANGELOG.ja.md](../v2/CHANGELOG.ja.md)にあります。

## 3.0.0 — 準備中

3.x系の最初のリリースです。1.x系・2.x系と同じ固定のcheckpoint（`nvidia/GLM-5.3-Flash-NVFP4` の `423acf37583782c51c142d145aef733d72943d93`）を、TensorFoldのネイティブエンジン、つまり2.x系が動かすPythonのエンジンに代わったZigとCUDAのエンジンで、2台のTP=2または3台のTP=3で配信します。2.x系は[`v2/`](../v2/README.ja.md)で続きます。

### Engine

- imageは[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold)のbranch `release/3.0.0` の `3d3d61d5937fea3bac68e13d75d5d2c7585ce3df` からエンジンをcompileします（[`config/engine.lock.json`](config/engine.lock.json)）。Zig 0.17.0（SHA-256で確かめる）とsm_121向けのCUDA 13.3.1を使います。上流のTensorFold 1.0.12に、CUDAのGLM-5.3-Flash向けの次のものを足した版です：
  - **`prompt_logprobs`**：streamでない `/v1/completions` で、tokenごとに最大20の候補（上流pull request #1016）。
  - **構造化出力**：`response_format` の `json_object` か `json_schema`、`tool_choice` の `required` か名指しの関数を、xgrammar v0.2.8の上の `libtfgrammar` で（#1017）。必須のtool呼び出しはGLMのtoolのmarkupで書きます（#1018）。
  - **熱の待ちの見込み**（`TF_HEAT_CEILING`）：promptは、その最も熱いzoneに、続けて流した直前のchunkの上がり幅を足すと天井を越える間も待ちます。2.x系と同じです。
  - **rank 0のNCCLのidをファイルで**（TP=3、`TF_GLM_NCCL_ID_FILE`）：リングのpoint-to-pointの `/32` のアドレスでは `NCCL_COMM_ID` で集まれないためです。上流のTPのbootstrap（pull request #636）までこの系列に留めます。

### Serving defaults

[`scripts/serve.sh`](scripts/serve.sh) が全rankに設定します（[配信の既定](README.ja.md#配信の既定)）。

- 一度に一要求（`PARALLEL=1`）：起動時の空きメモリからのエンジン自身の選択では、streamの数とprompt cacheが起動ごとに変わりました。
- 窓はTP=2で245,760 token（BF16 KVでモデルの隣に1本のstreamが収まるほぼ最大）、TP=3で1,048,576（モデルの上限）。
- checkpointのMTP headによるdraft、要求が指定しないときの応答は最大32,768 token・推論のeffortは `high`、`127.0.0.1:8095` の配信名 `glm-tf`。
- prefillの熱の待ちは92 °Cで待ち、88 °Cで再開し、93 °Cへの見込みを持ちます。

### Image and launch

- [`docker/Dockerfile`](docker/Dockerfile)：エンジンはNVIDIAのCUDA 13.3.1のdevelのimageでbuildし、実行のimageにはそのbinaryだけを置きます（どちらのimageもdigestで）。NCCL 2.30.7、RDMAのuserspace、検査のための `tokenizers` つきのPythonが入ります。`/usr/share/doc/tf3/ENGINE` がエンジンのcommitと各binaryのSHA-256を名指し、このリポジトリ・xgrammar・エンジンの表示がその隣にあります。ホストでは何もbuildしません。
- [`scripts/`](scripts/)：
  - `create_container.sh`：各ホストのcontainer。既定で最大周波数の最も低いcore（`cpuset.sh`。GB10の効率core）に置きます。エンジンは全rankで2本のCPUのthreadを空回りさせ続け、全coreでは返答の長い連続がCPUのzoneを熱の見張りの94 °Cより上へ運びました。効率coreでは、最も熱いzoneは速さの1〜3%と引き換えに約10 °C低く保たれました（[理由](README.ja.md#配信の既定)）。
  - `serve.sh`：rankのファイルから1つのrank。`cluster.sh`：操作する機械から全rankを起動・停止・状態確認し、TP=3ではNCCLのidをホストの間で写します。`hostwatch.sh`：メモリの見張り。
- [`examples/`](examples/)：参照機のTP=2とTP=3のrankのファイルとclusterのファイル。

### Tools

- `glm53_tf` を2.x系から写し、ネイティブエンジンの応答に合わせました：`decode-check` はcompletionの文章をhashし、エンジンの `token_sha256` を読みます（エンジンはtoken idを返しません）。`decode-divergence` は文章を比べ、`score-nll` は `prompt_logprobs` で採点し、`bench`・`long-input`・`tool-gate`・`download`・`verify-download` は2.x系と同じく働きます。

### Documentation

- [README](README.ja.md)、[手順書](SETUP.ja.md)、[検証](docs/validation.ja.md)、[ベンチマークの方法](docs/benchmarks.ja.md)、[運用](docs/operations.ja.md)を英語と日本語で。リポジトリのREADME、文書の地図、ライセンスの案内、第三者の表示、`AGENTS.md`、`CONTRIBUTING` が3.x系を名指します。

### Accepted

<!-- S6: the window's results, the release image's ID, and that the binaries equal the accepted image's -->

### Not in 3.0.0

画像入力、公開したAXLの重み、生成したtokenのlog確率、`clear_thinking` をchat templateへ渡すこと（[制限](README.ja.md#制限)）。

# 変更履歴

[English](CHANGELOG.md)

正典は[英語版](CHANGELOG.md)です。GitHub Releaseの本文は英語版の各版の節から作られます。

TensorFoldのネイティブエンジンで配信する3.x系です。`v3.*` のタグは、見出しにリリースの日付が入った節をこのファイルから公開します。2.x系の履歴は[v2/CHANGELOG.ja.md](../v2/CHANGELOG.ja.md)にあります。

## 3.1.0 — 2026-10-20

上流のTensorFold 1.1.1の上の3.x系です。checkpoint、配信の既定、道具は3.0.0のままです。TP=2は上流のtiledのBF16のlinearで新しいtokenを出し、TP=3は3.0.0と同じtokenを出します。

### Engine

- imageは[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold)のbranch `release/3.1.0` の `1a8f1efdc47b778c68cfdd30c1ba4966b2fe9064` からエンジンをcompileします（[`config/engine.lock.json`](config/engine.lock.json)）。Zig 0.17.0とsm_121向けのCUDA 13.3.1はこれまでどおりです。上流のTensorFold 1.1.1に二つのcommitを足した版です：
  - **熱の待ちの見込み**（`TF_HEAT_CEILING`）：3.0.0と同じです。
  - **rank 0のNCCLのidをファイルで**（TP=3、`TF_GLM_NCCL_ID_FILE`）。1.1.xはNCCLの前に、rankどうしの生存の線を `NCCL_COMM_ID` でrank 0へ張るので、各rankは線がつながった後に `NCCL_COMM_ID` をNCCLの環境から外し、rank 0はそこでidを書きます。上流のTPのbootstrap（pull request #636）までこの系列に留めます。
- `prompt_logprobs`、構造化出力、GLMのtoolのmarkupでの `required` か名指しのtool呼び出しは、1.1.1からGLMのCUDAのエンジンで上流自身のものです。この系列のpull request #1016・#1017・#1018の後に上流が書き、上流はそれらを閉じました。リリースのbranchはそのための自前のcommitをもう持ちません。`libtfgrammar` は引き続きxgrammar v0.2.8からbuildします。
- 上流はGLMのBF16のlinearを既定でtiledのkernelで回します。それはTP=3のrankのKDAの幅を断る（上流のissue #1067）ので、TP=3のrankのファイルは3.0.0が回したglueのkernel（`TF_GLM_MM=0`）にします：TP=3はdecode checkのhash、editの返事、NLLが3.0.0と同じです。TP=2はtiledのkernelで回り、新しい基準値を出します（[検証](docs/validation.ja.md)）。

### Launch

- `serve.sh` はTP=3でも `NCCL_COMM_ID`（`MASTER:NCCL_PORT`）をidのファイルと並べてexportし、起動の行に `TF_GLM_MM` を出します。
- `cluster.sh` はTP=3の3つのrankをまとめて起動し（rank 0を最後に）、rank 0のNCCLのidを最大5分待って他のホストへ写します。そこのrankはそれを待って読みます。
- [`examples/`](examples/)：TP=3のrankのファイルに `TF_GLM_MM=0` と、上流が#1067を直したら外す旨の行。

### Documentation

- setup、README、運用に、1.1.xでのTP=3の起動と `TF_GLM_MM=0` を書きました。READMEには上流1.1.1がこの系列に変えたこと（`--vision` での画像入力、ただし `serve.sh` は渡さない、上流のrunbookの効率core）を書きました。
- 運用：GB10ではエンジンがページキャッシュを空きメモリ（`MemAvailable`）に数えるので、起動の前に外す必要はありません。受け入れの窓は2.x系から残した手順として、今も外しています。

### Accepted

参照機で2026-10-19〜20に、固定したcheckpointで5回の起動（TP=2で3回、うち1回は `PARALLEL=` を空に、TP=3で2回）、全containerを効率coreに置いて（[測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md)）：

- decode検査は各TPの2回の起動で同じhashを出しました。TP=3は3.0.0のhash、TP=2はtiledのkernelでの新しいhashです。draftした返答はserialと同じで、`bench --kinds edit` は両TPで3.0.0と同じ返答を363 roundではなく190 roundで出し、画像のpartは400で断られました。
- `prompt_logprobs` と構造化出力は両TPで検査を通りました。NLLのセットは2回の採点で動かず、TP=3は3.0.0と同じ、TP=2は3.0.0から0.02以内でした。
- tool引数ゲート越しのtool-eval-bench：TP=2で92、TP=3で93、Safety Gateは合格。
- 6,000 tokenのpromptの後に最大1,024 tokenの返答を40本続けて、両TPで終わり、最も熱いzoneは74.9 °C（TP=2）と79.8 °C（TP=3）でした。熱で待った要求は無く、1,035,295 tokenのprompt（3つ中3つ、最初のtokenまで1,022.7秒）も含みます。
- 切った返答、stop文字列、切ったpromptは、両TPで処理を止めました。
- 全core（既定ではなく記録として）：TP=2の40本の返答は同じ時間で終わり、rank 0のホストは93.0 °C、2つの要求の同時は88.5 °Cでした。

リリースのimageは、それ自身の `serve.sh` とこのリリースの `cluster.sh` で各TPに1回起動し、decode検査で同じhashと同じ編集の返答を出しました。

### Not in 3.1.0

画像入力（上流のエンジンは `--vision` でGLMのCUDAの経路でも画像を読むが、`serve.sh` は渡さない）、公開したAXLの重み、生成したtokenのlog-probability、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.0.0 — 2026-10-18

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

2026-10-18に参照機で、固定したcheckpointで、5回の起動（TP=2で2回、TP=2で `PARALLEL=` を空にして1回、TP=3で2回）、全containerを効率coreにして（[測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md)）：

- decode検査は各TPの2回の起動で同じhashを出し、draftした応答はserialと同じで、`bench --kinds edit` は両TPで同じ返答を出し、画像のpartは400で断られました。
- `prompt_logprobs` と構造化出力は両TPで検査に合格しました。NLL採点セットは2回採点して動きが無く、領域ごとに2.x系の基準値から0.021以内でした。
- tool引数ゲート越しのtool-eval-bench：両TPで93、Safety Gateは合格。
- 6,000 tokenのpromptの後に最大1,024 tokenの返答を40本続けて流し、両TPで終わりました。最も熱いzoneは82.6 °C（TP=2）と79.7 °C（TP=3）でした。熱で待った要求は無く、1,035,295 tokenのprompt（3つ中3つ、最初のtokenまで1,082.9秒）も含みます。
- 切った返答、stop文字列、切ったpromptは、両TPで仕事を止めました。

受け入れの窓はimage `glm53-tf3:3x-bc82bc4` で回しました。リリースのimage `glm53-tf3:3.0.0`（linux/arm64 `sha256:73dcd449b44314e5ca1bb6462c8c14c44d7002535dc9fadd4a7f68b2ed7ec4d1`、3台で同じ）は、それにエンジンの表示を足したもので、binaryは同じ（`/usr/share/doc/tf3/ENGINE`）、TP=2の起動でdecode検査のcountのhashと編集の返答も同じでした。

### Not in 3.0.0

画像入力、公開したAXLの重み、生成したtokenのlog確率、`clear_thinking` をchat templateへ渡すこと（[制限](README.ja.md#制限)）。

# GLM-5.3-Flash BIZ 3.x（TensorFoldネイティブ）

![GLM-5.3-Flash BIZ v3、XSFP4 × TensorFold：DGX Spark・GB10で動くZigとCUDAのネイティブ実装](assets/banner.webp)

[English](README.md) · [リポジトリの索引](../README.ja.md) · [配備の手順書](SETUP.ja.md) · [検証](docs/validation.ja.md) · [変更履歴](CHANGELOG.ja.md)

**GLM-5.3-Flash BIZ** は、DGX Sparkまたは互換のGB10機でGLM-5.3-Flashを配信します。3.x系はTensorFoldのネイティブエンジン、つまり[2.x系](../v2/README.ja.md)が動かすPythonのエンジンに代わったZigとCUDAのエンジンで、2台のTP=2または3台のTP=3で配信します。配信するcheckpointは[XSFP4](#checkpoint)で、NVIDIAのGLM-5.3-Flash-FP4-Localの派生物、expertsを本リポジトリの管理者が量子化し直したものです。1.x系・2.x系が配信するNVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointは、3.5.xまでここでも選べました。3.0.0が上流のTensorFold 1.0.12の上の最初のリリースで、3.1.0で上流の1.1.1へ移り、3.2.0で画像と動画の入力を加え、3.3.0で上流の1.1.2へ移ってNVIDIAのcheckpointの横にXSFP4を加え、3.4.0でXSFP4を既定にし、3.6.0で上流の1.1.3へ移ってXSFP4だけを配信し、3.8.0でこの系列のpull requestを持つ上流の1.1.5へ移ります。2.x系も並んで続きます。

**BIZ**は保守者の印で、リポジトリの意図を示す語です。意味することと意味しないことは[リポジトリのREADME](../README.ja.md#biz)にあります。

## 要約

- **状況。** 3.8.0はエンジンを上流1.1.5そのものの上へ移し（この系列のpull requestを持つ上流の最初のリリース）、TP=3ではKV cacheをpageに置きます。リリースのimageを、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動すると、TP=2とTP=3の各2回の起動で3.3.0のXSFP4のdecode検査のhashと編集の返答を、さらに同じNLLを返し、TP=3の1,035,295 tokenのpromptを含めて長い入力の合言葉をすべて見つけました（[リリースでの測定値](#リリースでの測定値)）。`mojibake` は、両TPで、temperature 0でもsampledでも、日本語と韓国語の答えに化けた文字を見つけませんでした（[マルチバイト出力](docs/validation.ja.md#マルチバイト出力)）。TP=3ではstop文字列の要求が上限まで走り、短いgreedyの返答が自分のhashを持ちます。どちらもそこに書いた既知の振る舞いです。[検証](docs/validation.ja.md)の基準値は、2026-10-26の参照機での3.8.0の受け入れで、visionのtowerを読み込んで決めたもので、そのうちdecode検査のhash・編集の返答・NLLは3.3.0のものと同じです。主張の範囲はここまでです。他のホストは同じ検査を回して受け入れます。
- **何であるか。** XSFP4を、TensorFoldのネイティブエンジンの固定したcommitで一つのOpenAI互換endpointとして配信するための、build手順・起動の台本・受け入れ検査です。2台なら直結のConnectX-7リンクでTP=2、3台ならswitchなしのリングでTP=3です。公開している測定値はMSI EdgeXpert（MS-C931）で取りました。Macでは、TensorFoldが自身のMLXの重みでGLM-5.3-Flashを配信します（[Macでは](../README.ja.md#macでは)）。
- **反復性。** draftした応答はserialと同じで、起動は同じTPの前の起動のtoken idを出します。ネイティブエンジンのtokenはそれ自身のもので、2.x系のものではありません：kernelとBF16のKV cacheの丸めが違うので、二つの系列はtokenごとではなくteacher-forced NLLで比べます（[2.x系との違い](#2x系との違い)）。
- **構造化出力とpromptのscore。** JSON schemaつきの `response_format`、`required` か名指しの関数の `tool_choice`（GLM自身のtoolのmarkupで書く）、`/v1/completions` の `prompt_logprobs` は、1.1.1からGLMのCUDAのエンジンで上流のTensorFold自身のものです。この系列のpull request #1016・#1017・#1018の後に上流が書きました（[API](#api)）。
- **画像と動画。** chatの要求は、PNG・JPEG・WebPの画像と、H.264・HEVC・VP8・VP9・MPEG-4の動画をdata URLで持てます。rank 0にあるcheckpointのvision towerが、エンジンの `--vision` で読みます。`serve.sh` は既定でこれを渡します（[制限](#制限)）。
- **精度。** XSFP4ではrouted expertはW4A16、他のprojectionはcheckpointが保存する形のままで、多くは8 bit、vision towerのMLPとmergerはNVFP4です（[checkpoint](#checkpoint)）。KVはBF16です（2.x系はFP8のKV cacheを持ちます）。NVIDIAのmodel cardは別のレシピ・別の機材でFP4-Localを測っており、その精度表はこの配信を表しません。この配信を表す数字は[検証](docs/validation.ja.md)にあります。
- **ライセンス。** コードとエンジンはApache-2.0、重みは運用者がダウンロードし、NVIDIA Open Model Agreement（XSFP4、商用に使える）です。imageには構造化出力のためにxgrammar（Apache-2.0）、画像と動画のためにlibjpeg-turbo・libwebp（BSD系）とFFmpegのdecoder（LGPL-2.1）が入ります。配信の経路に非商用の条件はありません（[ライセンスの早見表](../README.ja.md#ライセンスの早見表)）。
- **未検証。** 画像と動画のURL（`--vision-urls`、無効）、同時に2つ以上の要求（受け入れの検査は一度に一つずつ送ります）、他のrank数と機材（[制限](#制限)）。ハーネス連携（ZCode・Claude Code）、アプリケーション全体の品質と本番の信頼性。

## 何であるか

- **重み**：`Bizuayeu/GLM-5.3-Flash-XSFP4`（[`config/xsfp4.lock.json`](config/xsfp4.lock.json)、[checkpoint](#checkpoint)）で、NVIDIAのGLM-5.3-Flash-FP4-Localと[Z.aiのGLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)から作られています。
- **エンジン**：TensorFoldのネイティブエンジン（`tensorfold-native`）。[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/3.8.0` として公開するBIZ版で、上流のTensorFold v1.1.5そのものです（この系列のcommitはありません）。上流は2026-10-25にこの系列のpull requestを取り込み、1.1.5はそれらを持つ最初のリリースです。#1050はNVIDIAのGLM-5.3-Flash-FP4-Localを保存された形のまま読み、それと共に、experts以外にFP4-Localのtensorを持つXSFP4のcheckpointも読みます：各projectionの形をcheckpointの `MIXED_PRECISION` のレシピから見分け、MXFP8と128×128 blockのFP8のprojectionを保存の形のまま計算し、FP4-Localの圧縮したexpertのscaleを読み、float32のnormの重みをfloat32のまま保ちます。#1178はrank 0のNCCLのidをrankどうしの生存の線で他のrankへ送るので、TP=3は上流のbootstrapで起動し、3.6.0のリリースのbranchがそのために持っていたidのファイル（`TF_GLM_NCCL_ID_FILE`）とこの系列の二つのcommitは要りません。#1163と#1211は、3 rankで各streamのKV cacheとエンジン自身のsequenceを一つのpoolのpageに置きます（[配信の既定](#配信の既定)）。indexがmodelのfolderの中のfolderにあるshardを名指せること（FP4-LocalとXSFP4のindexに要る）は、1.1.3から上流自身のcodeにあり、3.5.xまでのリリースのbranchはpull request #1179のpatchとして持っていました。1.1.5から、serverはGLM-5.3のchat templateに `clear_thinking` を渡します（[設定](docs/configuration.ja.md#rank-0のserver)）。3.0.0〜3.2.0の熱の待ちの天井への見込み（`TF_HEAT_CEILING`）は無くなり、熱の待ちは上流の帯だけです（[配信の既定](#配信の既定)）。imageは一つのcommitに固定します（[`config/engine.lock.json`](config/engine.lock.json)）。
- **image**：[`docker/Dockerfile`](docker/Dockerfile)。エンジンはNVIDIAのCUDA 13.3.1のbuild用imageで、lockが名指すZigのcompiler（SHA-256で確かめる）がcompileし、`libtfgrammar` は固定したcommitのxgrammarのreleaseからbuildします。実行のimageはCUDA 13.3.1にNCCL 2.30.7とRDMAのuserspaceです。2つのbaseのimageはdigestで固定しています。`/usr/share/doc/tf3/ENGINE` がエンジンのcommitと各binaryのSHA-256を名指し、`/usr/share/doc/tf3/engine/` にエンジンのライセンスと表示があります。
- **起動**：[`scripts/`](scripts/) のshellの台本と、rankごとの環境ファイル一つ（[`examples/`](examples/) に参照機のファイル）。順番は[SETUP.ja.md](SETUP.ja.md)にあります。ホストでは何もbuildしません：kernelはbinaryの中にあります。
- **他のレシピ**：このリポジトリがTensorFoldの他のレシピから取ったものと、それらのlicenseは、2.x系の[表](../v2/README.ja.md#tensorfoldの他のレシピ)にあります。3.x系のTP=3のrankのファイルは、2.x系がMiaAI-LabのTensorFoldのレシピから取って測ったfabricの設定のうち二つ、4本のNCCLのchannelとsubnet-aware routingを持ち続けます（[決定](docs/decisions.ja.md#fabric)）。上流のTensorFold自身の、CUDAでのこのモデルのレシピは[GLM-5.3-Flash on CUDA](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md)です。

## 必要な環境

- **ホスト**：DGX Sparkまたは互換のGB10機を2台か3台（Linux ARM64、各128 GBの統合メモリ）。GPUで他の大きな仕事を動かさないこと。同じホストで1.x系か2.x系のserverが動いていれば先に止め、全GPUを要求する2.x系のcontainerも止めます（[ホストを2.x系へ渡す](docs/operations.ja.md#ホストを2x系へ渡す)）。
- **fabric**：RoCE v2のConnectX-7リンク。2台は直結、3台はswitchなしのリング（[3台をリングにつなぐ](../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。各portの2本のrailを両方使います。
- **ホストカーネル**：1.x系・2.x系と同じです。今のDGX OSの更新が入れるカーネルは、既定のままでは複数ノードのRoCEを壊すことがあり、参照機は `kho=off` で起動しています（[ホストカーネルと複数ノードRoCE](../docs/hosts.ja.md#ホストカーネルと複数ノードroce)）。
- **GPUクロック**は全ホストで上限を設けます（[GPUクロックの上限](../docs/hosts.ja.md#gpuクロックの上限)）。上限と温度の記録は[`host/`](../host/README.ja.md)が据え付けます。3.x系の数字は全部この上限の下で測りました。
- **Docker**：NVIDIAのGPU runtimeとRDMAデバイスが要ります（`/dev/infiniband` が無いホストでは、NCCLがsocketに落ちるので `create_container.sh` が断ります）。
- **disk**：全ホストにcheckpointを丸ごとと、image。XSFP4は178 GBを取ります。
- **操作する機械**：全ホストへSSHでき、`cluster.sh` を動かす機械一台。
- **Python 3.11以上**：各ホストで、この系列の道具（[`glm53_tf/`](glm53_tf/)：ダウンロード、検証、tool引数ゲート、検査）を `v3/` から動かします（[手順書 §2](SETUP.ja.md#2-checkoutとcheckpoint)）。

## はじめ方

各段とその後に確かめることは[配備の手順書](SETUP.ja.md)にあります。以下はTP=2のときの骨組みです。全ホストで同じ、確認済みの `v3.*` のtagを使います。

```sh
# 一度だけ、ある1台の v3/ からその仮想環境で。その後cacheを他のホストへ写し、写しごとに検証する（SETUP §2）
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum-xsfp4 --wait

# 1台がimageをbuildし、他はそれを読み込む。image IDを比べる（SETUP §3）
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.8.0 .

# 各ホストで、checkoutのルートから（SETUP §4）
v3/scripts/create_container.sh glm53-tf3:3.8.0 ~/glm53-tf3
cp v3/examples/tp2-rank0.env ~/glm53-tf3/rank.env     # もう1台は tp2-rank1。その後このホストの値に直す

# 操作する機械で（SETUP §5・§8）
mkdir -p state && cp v3/examples/cluster.tp2.env state/cluster.env   # HOSTS（rank順）と CHECKOUT
v3/scripts/cluster.sh state/cluster.env start first   # first はlogの名前。rank 0のserving行でREADY
v3/scripts/cluster.sh state/cluster.env stop
```

rank 0はloopbackで答えます：

```sh
curl -s http://127.0.0.1:8095/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "glm-tf",
  "messages": [{"role": "user", "content": "Write a Python fibonacci function."}]
}'
```

モデルは答える前に考えます。思考は `reasoning_content`、答えは `content` に返り、`max_tokens` を指定しない要求は両方で最大32,768 tokenを使えます。小さい上限では思考の途中で終わり、`content` が空になることがあります。起動したら、日常の利用の前に[検証](docs/validation.ja.md)の検査（まずdecode検査）で受け入れます。

**安全。** `serve.sh` はrank 0を `127.0.0.1` で待ち受けさせ、[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)もloopbackだけで待ち受けます。SSHのtunnel（`ssh -L 8095:127.0.0.1:8095 <rank 0>`）か、認証を足すproxyを通して使ってください。loopbackの外で配信する（rank 0のファイルで `HOST=0.0.0.0`）ときは、`API_KEY_FILE` も設定します：他のuserが読み書きできないファイル（`chmod 600`）に、1行に一つのkey（`label: key` かkeyだけ）を書きます。エンジンはファイルが変わった後に読み直します（[APIのkey](docs/configuration.ja.md#apiのkey)）。すると `/health` 以外のすべてのrouteが `Authorization: Bearer <key>`（または `x-api-key: <key>`）を要し、`/health` は `{"status": "ok"}` だけを返します。rank 0のファイルの `TENSORFOLD_API_KEY` もkeyを持ちます。この系列のdecode検査、`score-nll`、`bench`、`long-input` を走らせる側では、それが送るkeyになり、tool引数ゲートはそのheaderをそのまま渡します。keyなしで `HOST=0.0.0.0` にすると、APIは認証なしで外に出ます。

## checkpoint

3.x系が配信するcheckpointはXSFP4です：3.4.0から既定で、3.6.0からはこれだけです。3.3.0まで既定で3.5.xまで選べたNVIDIAのNVFP4は、1.x系・2.x系のものです。全rankが同じものを配信します。

| | XSFP4 |
|---|---|
| 重み | [`Bizuayeu/GLM-5.3-Flash-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4)（[`config/xsfp4.lock.json`](config/xsfp4.lock.json)） |
| 作り手 | 本リポジトリの管理者、NVIDIAの[`GLM-5.3-Flash-FP4-Local`](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local)（revision `76348ddb`）とZ.aiのBF16の重みから |
| routed expert | XSFP4、W4A16で配信：平滑化を重みに畳み込み、BF16の重みからNVFP4のblockを当てはめ直したもので、実行時にkernelが何も掛けません。MTP層のexpertも同じ。3〜44層はblockのスケールを可逆に圧縮して持ち（`csf_32x2_v1`、FP4-Localと同じ）、エンジンが読み込みの時にホストで元に戻します |
| その他 | FP4-Localのtensorを保存の形のまま：MXFP8（dense MLP、KDA、`lm_head`、MTP層のattentionとshared expert）、128×128 blockのFP8（MLAとshared expert）、BF16（KDAの小さいprojection、MLAの `kv_b` とindexer、router、embeddings）、BF16とF32のnorm。vision towerはMXFP8とNVFP4 |
| TP=2（245,760 tokenの窓）・TP=3（KV cacheはpage）のrank 0のmodel（読み込みの行） | 93.44・63.60 GiB |
| このエンジンのTP=2でBF16の重みと比べた次token（128文書、144,285位置）：top-1の一致 / BF16に対するNLLの上がり / KLの下限 | 93.26% / +0.85% / 0.0431 |
| 同じものをTP=3で | 93.30% / +0.85% / 0.0436 |
| ライセンス | NVIDIA Open Model Agreement（FP4-Localの派生物。repositoryに `LICENSE` と `NOTICE`） |
| ダウンロード（SETUP §2） | `download`・`verify-download`（ダウンロードの状況は `state/xsfp4` に） |
| rankのファイル | 何も要らない：`serve.sh` の既定（lockのrevision） |

各文書はtoken idとしてエンジンに送り、`prompt_logprobs` は20。KLの下限は、両方が確率を返したtoken（エンジンの上位20、BF16の上位20、本文のtoken）を1つずつ数え、残りを1つの塊として数えます。全語彙のKLより低く、エンジンの外で測ったKLとは比べられません（XSFP4の[model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4)に両方があります）。同じエンジンと文書で、NVIDIAのNVFP4はTP=2で 92.68% / +1.37% / 0.0510、TP=3で 92.71% / +1.38% / 0.0511 だったので、XSFP4はどちらのTPでも3つともBF16に近く、差の文書ごとの95%区間は0を含みません。FP4-Local自身を同じエンジンでそのまま読み込むと、TP=2で 92.82% / +1.11% / 0.0510、TP=3で 92.75% / +1.07% / 0.0514 でした。

XSFP4の[測定値](#リリースでの測定値)の速さはXSFP4のものです：draftの受理と層の形がNVIDIAのNVFP4と違うので、1.x系・2.x系の数とは比べられません。XSFP4が持つFP4-Localのchat templateは、NVIDIAのものと3か所違います（contentの無いmessageは何も出さない、tool callの名前を `~` でつなぐ、toolの結果を呼び出しの順に並べられるかの検査が、だめと分かった所で止まる）。

## 配信の既定

[`scripts/serve.sh`](scripts/serve.sh) が持ち、全rankで同じです。何と比べて選び、何が起きれば見直すかは[決定](docs/decisions.ja.md)にあります。

| 設定 | TP=2（2台） | TP=3（3台） |
|---|---|---|
| checkpoint | XSFP4、lockのrevision（`CHECKPOINT` を書かない、[checkpoint](#checkpoint)） | 同じ |
| KV cache | latentとindexのkeyをBF16（エンジンの既定。`--kv-cache fp8` で選べるFP8のlatent cacheは受け入れの外：[制限](#制限)）、streamごとの窓 | 同じkeyをKVのpageに：全streamのcacheとエンジン自身のsequenceが1つのpoolのpageを取る（3 rankでのエンジンの既定、`TF_KV_PAGES`。全rankのファイルの `TF_KV_PAGES=off` は3.7.0までと同じくstreamごとの窓） |
| draft | checkpointのMTP head（エンジンの既定） | 同じ |
| 窓（`--context`） | 524,288 token：各rankでXSFP4の隣に1本のstreamとprompt cacheが入る | 1,048,576 token（モデルの上限） |
| 同時にdecodeする要求（`--parallel`） | 1（`PARALLEL=1`）。空の `PARALLEL=` ではエンジンに任せ、エンジンは起動時の空きメモリからstreamとprompt cacheの大きさを決める | 同じ |
| prompt cache（保持するpromptの状態、2,048 tokenのchunkの始まりごと） | 窓の残り、最大16 GiB（rank 0のloadの行。起動時の空きメモリで動きます）：参照機で、vision towerを読み込んで、XSFP4は524,288 tokenで5.2〜5.5 GiB（245,760で `PARALLEL=` を空にすると、3本のstreamの横で2.0 GiB） | 参照リングで16.0 GiB、その上限（`--prompt-cache-gib` で別の値に） |
| 要求が指定しないときの応答の上限 | 32,768 token（`--max-tokens`） | 同じ |
| 要求が指定しないときの推論のeffort | `high`（`--reasoning-effort`） | 同じ |
| NCCL | 各リンク2本のrail・4 channel・IBのtransportを明示、rankごとのファイルから。rank 0のアドレスとportを `NCCL_COMM_ID` に、rank 0のNCCLのidはrankどうしの生存の線で | 2本のrail・4 channel・IBのtransportを明示・subnet-aware routing。rank 0のアドレスとportを `NCCL_COMM_ID` に、rank 0のNCCLのidはrankどうしの生存の線で、他のrankのNCCLのbootstrapはそれぞれの `/32` のinterfaceで（`NCCL_SOCKET_IFNAME`） |
| BF16のlinear | 上流のtiledのkernel（エンジンの既定） | 同じ：上流1.1.2から（issue #1067）、TP=3のrankのKDAの入力をtileせずに回す。3.1.0と3.2.0はglueのkernel（`TF_GLM_MM=0`）が要った |
| 熱によるprefillの休止 | prompt chunkの前ごとに全rankそろって、どれかのrankのACPIの最も熱いzoneが92 °Cを超えている間、全rankが88 °C以下になるまで待つ（`TF_HEAT_HIGH`・`TF_HEAT_LOW`。3.0.0〜3.2.0は93 °Cの天井の手前でも待ったが、3.3.0のエンジンは天井を持たない） | 同じ |
| 画像と動画の入力 | 有効（`VISION=1`、エンジンの `--vision`）：rank 0にcheckpointのvision tower、PNG・JPEG・WebPの画像と動画をdata URLで、エンジンの制限の中で（[制限](#制限)）。`VISION=` でtextだけ、全rankで同じに | 同じ |
| containerのcore | 最大周波数の最も低いcore：GB10の効率core、0-4と10-14（`create_container.sh`、`CPUSET`） | 同じ |

**一度に一要求にする理由。** `--parallel` を設定しないと、エンジンは8本のstreamを求めて収まるだけを配信するので、streamの数とprompt cacheに残る余地は、そのときの空きメモリによって起動ごとに変わります（TP=3では、3.0.0の前のある起動が2本のstreamと0.1 GiBのprompt cacheを取りました。3.8.0のKVのpageではstreamが一つのpoolを分け合い、`PARALLEL=` を空にすると、エンジンは3,398 page（21.15 GiB）の上に8本を取り、prompt cacheは16.0 GiBでした）。2.x系と同じ1本のstreamなら、窓はどの起動でも同じで、prompt cacheは空きメモリの分だけ動きます（TP=2でvision towerありのNVIDIAのNVFP4は、3.3.0の2回の起動で5.2・5.1 GiB）。TP=2では、3.0.0のエンジンは245,760 tokenの窓の隣に2本目のstreamが収まりませんでした（各rankで4.55 GiBが要り、rank 1には4.41 GiBでした）。3.1.0からのエンジンは収まります：3.3.0ではNVIDIAのNVFP4で `PARALLEL=` を空にすると2本のstreamを取り（XSFP4では3本）、prompt cacheは1本のときの5.2 GiBに対して1.5 GiBでした。3.5.0の524,288では1本です（[制限](#制限)）。

**TP=2を524,288にする理由。** BF16のKVは、tokenあたり2.x系のFP8のcacheの約2倍のメモリを取ります。3.4.0までの窓245,760 tokenは2.x系の300,000 tokenより短く、決めた時の既定だったNVIDIAのNVFP4で1本のstreamが収まるほぼ最大でした。3.4.0から既定のXSFP4はrank 0で約3.9 GiB軽いので（245,760でNVIDIAの97.38 GiBに対して93.44 GiB）、3.5.0から窓は524,288 tokenです：rank 0のloadの行は1本6.71 GiBのstreamと5.5 GiBのprompt cacheを示し、499,254 tokenのpromptが返答に25,034 tokenを残して入ります。2本目のstream（`PARALLEL=2`）はさらに6.71 GiBを取り、この窓には入らないので、小さい窓（例えば `CONTEXT=245760`）が要ります。全rankのファイルの `CONTEXT` で別の値を選びます。

**効率coreにする理由。** エンジンは要求を回す間、全rankで2本のCPUのthreadを空回りさせ続けます。rank 0ではdecodeの間、他のrankではそれを待つ間です（上流1.1.2のエンジンより前は、他のrankは要求の無い間も空回りしました。#1053は、rank 0にstreamが無い間それらを眠らせます）：一つはGPUを待ち、もう一つはそのkernel時間から見てNCCLのものである見込みが高いthreadです。全coreでは、これらがCPUのthermal zone（GB10の7つのzoneのうち5つ）を温めました：約6,000 tokenのpromptの後の1,024 tokenの返答を40本続けると、3.0.0のエンジンでは、TP=2でrank 0の最も熱いzoneが94.7 °Cに達し、熱の見張りが7本目でエンジンを止めました。3.1.0のエンジンは全coreでも効率coreと同じ1,535秒で40本を終えましたが、rank 0のホストは93.0 °Cに達し（止める温度まで1 °C）、効率coreでは74.9 °Cでした。全coreで2つの要求を同時に回すと88.5 °Cでした。熱の待ちはprompt chunkの合間に働くので、これを抑えられません。3.0.0のエンジンでは、効率coreで40本の返答がそのzone 85.1 °Cで終わり、rank 1のホストは約70 °Cではなく57〜63 °Cで待ちました。その代わり速さの1〜3%を失い、起動は約25秒長くなりました（[3.0.0の測定値](docs/measurements.ja.md#300)）。熱の帯を下げる（86/82/87）と、待ったpromptが26〜89%遅くなり、1,048,576 tokenのpromptの最高温度は下がりませんでした。空回りせずに眠るCUDAのcontextはdecodeが12%遅く、もう一つのthreadは空回りしたままでした。1.1.1から、上流の[runbook](https://github.com/ashhart/TensorFold/blob/v1.1.5/RUNBOOK.md#gb10-cpu-pinning-for-long-cuda-runs)もこれらの測定からGB10の各rankに同じcoreを挙げています。`CPUSET=` でcontainerに全coreを与えます。

## 設定

配信は三か所で決まります：各ホストのrankのファイル（`serve.sh` が読む）、制御機のclusterのファイル（`cluster.sh` が読む）、`create_container.sh` の環境です。二つのファイルは [`examples/`](examples/) から写して自分の値に直し、Gitには入れないでください。よく変える設定は、窓（`CONTEXT`）、同時にdecodeする要求（`PARALLEL`）、textだけ（`VISION=`）、待ち受けとそのkey（`HOST`・`API_KEY_FILE`）、containerのcore（`CPUSET`）です。

[設定](docs/configuration.ja.md)は全ての設定を、それぞれの既定と読むrankとともに挙げます：rankのファイル、`serve.sh`、エンジンのflagと環境変数、NCCL、clusterのファイル、container、道具、lockのものです。エンジンはその多くを起動時にrankの間で比べ、違えば起動を断ります。既定以外の値は、その頁が名指すものを除き、3.x系の受け入れが測った範囲の外です。[上流自身のrecipe](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md)を越えてこの構成でできることは、写せる行の形で[チートシート](docs/cheatsheet.ja.md)にあります。

## API

rank 0がエンジンのHTTP APIを出します。受け入れで使ったもの：

- **`/v1/chat/completions`**：streamとそれ以外、toolつきで、[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)（このリポジトリの中継で、エンジンのものではありません）越しと直接。
- **構造化出力**：`response_format` の `json_object` か `json_schema`、`tool_choice` の `required` か名指しの関数。エンジンはこれをGLMのtoolのmarkup（`<arg_key>`、`<arg_value>`）のgrammarにします。どちらもimageが持つ `libtfgrammar` が要ります。grammarと必須のtool呼び出しを組み合わせた要求は400で断ります。
- **`prompt_logprobs`**：streamでない `/v1/completions` で、promptのtokenのlog確率を、それぞれ最大20の候補つきで。NLLの検査がこれを使います。このような要求はprompt cacheから再開しません。
- **思考**：`reasoning_effort` をtop levelか `chat_template_kwargs` で。`none` で思考を切り、effortを指定しない要求は `high` になります（[配信の既定](#配信の既定)）。streamでは `reasoning_content` と `content` は別々のdeltaで届きます。
- **`"draft": false`**：要求のbodyに入れると1 roundに1 tokenずつdecodeします。draftした応答が一致すべきserialの基準です。
- **応答のblock**：`tensorfold`（`token_sha256`＝推論を含む応答のtoken idのhash、`prefill_seconds`、`time_to_first_token`、`tokens_per_second`、`sampling`、`drafts`）と `speculative`（`rounds`、`drafted`、`accepted`、`acceptance_rate`、`tokens_per_round`）。prompt cacheから再開したtokenは `usage.prompt_tokens_details.cached_tokens` に入ります。応答はtoken idも熱の待ちの時間も運びません：待つごとの秒数はrank 0のlogの `heat_wait_s` の行にあります。
- **`/health`**（`live`：接続、待っている要求、直近の数秒のdecodeとprefillの速さ）、**`/v1/models`**、**`/tokenize`**、**`/metrics`**（Prometheus。decodeのroundやクライアントの切断を含む）。
- **停止**：クライアントの切断かstop文字列で応答が終わります。rank 0はroundの合間に接続を確かめ、他のrankはrank 0が送る段だけを走らせます。

エンジンは `/v1/responses` とAnthropicの `/v1/messages` にも、同じchatの経路で答えます。受け入れではこれらを確かめていません。GLMのCUDAのエンジンでは、生成したtokenの `logprobs` と `top_logprobs`（400）、音声のpart（400）、`--vision` 無しで起動したとき（rankのファイルで空の `VISION=`）の画像と動画のpart（400）、`/v1/decisions`（400）を断ります。

## 2.x系との違い

| | 2.x（TensorFoldのPythonのエンジン） | 3.x（TensorFoldのネイティブエンジン） |
|---|---|---|
| エンジン | TensorFold 0.6.5のBIZ版。PythonとTritonのkernelで、kernelは実行時にcompile | TensorFold 1.1.5のBIZ版（3.0.0は1.0.12、3.1.0と3.2.0は1.1.1、3.3.0〜3.5.xは1.1.2、3.6.0と3.7.0は1.1.3）。ZigとCUDAで、kernelはbinaryの中 |
| 出力の反復性 | エンジンの契約として、draftした応答はserialと同じ、再開したpromptは最初からと同じ、chunkの切り方で結果が変わらない | draftした応答はserialと同じで、起動はtoken idを繰り返す。tokenは2.x系のものと違う（別のkernel、BF16 KV）ので、系列の間はNLLで比べる |
| KVと窓 | latentとindexのkeyをFP8。TP=2で300,000 token、TP=3で1,048,576 | BF16。TP=2で524,288 token、TP=3で1,048,576 |
| 同時の要求 | 1 | 既定で1。`PARALLEL` で、窓が残すメモリの中で、エンジンがdecodeのroundをより多くの要求に分ける |
| prompt cache | 8本、3 GiB（`TF_GLM_CACHE_*`） | 窓の残りに、最大16 GiBまで、chunkの始まりの状態を保つ（TP=2でvision towerありは、XSFP4の524,288 tokenで5.2〜5.5 GiB。TP=3は16.0 GiB）。本数の上限は無い |
| 画像入力 | 受ける（`VISION=1`） | 受け、動画も（`VISION=1`、既定） |
| 公開したAXLの重み | 任意で使える | 配信しない（3.6.0から） |
| 構造化出力、必須のtool呼び出し | 受ける。imageにxgrammar | 受ける。imageにxgrammarの `libtfgrammar`。必須のtool呼び出しはGLMのmarkupで |
| `prompt_logprobs` | 受ける | streamでない `/v1/completions` で受ける |
| `clear_thinking` | 従う | 3.8.0から従う（上流1.1.5。[設定](docs/configuration.ja.md#rank-0のserver)） |
| 応答の欄 | `tensorfold` に `accepted`・`drafted`・`rounds`・`cached`・`prefill_s`・`heat_wait_s`・`sha256` | `tensorfold` と `speculative`（上記）。cacheしたtokenは `usage` に。熱の待ちはlogだけ |
| 熱の設定 | `TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW`・`TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`・`TF_HEAT_LOW`、同じ帯。天井なし |
| XSFP4のcheckpoint | 配信しない | 配信するcheckpoint（3.4.0から既定、3.6.0からこれだけ） |
| NVIDIAのNVFP4のcheckpoint | 固定したcheckpoint | 配信しない（3.6.0から。3.5.xまでは選べた） |
| imageとcontainer | `glm53-tf`、extensionをcontainerごとにbuild（`build_ext.sh`） | `glm53-tf3`、ホストでは何もbuildしない |
| containerのcore | 全core | `CPUSET` が別に言わなければ効率core |
| tool引数ゲート | エンジンの前のゲート | 同じゲート、この系列の写しを `v3/` から起動 |

二つの系列のcontainerはどちらも全GPUを要求するので、エンジンは一度に一つの系列だけを動かします（[運用](docs/operations.ja.md#ホストを2x系へ渡す)）。

## リリースでの測定値

**3.8.0**（2026-10-26、エンジン `84e0d560`、上流1.1.5、image `glm53-tf3:3.8.0`）。エンジンはこの系列のcommitを持たない上流1.1.5そのもので、TP=3ではKV cacheがpageにあります。リリースのimageを、rankのファイルに、起動が名指す時のほかは `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動しました：TP=2で6回、TP=3で5回。各TPで全検査の起動、2回目の起動、`PARALLEL=` を空にした起動、BF16との比べのためにNVIDIAのNVFP4とFP4-Localで1回ずつ（[checkpoint](#checkpoint)）、さらにTP=2で `PARALLEL=` を空にした245,760 tokenの窓。それらを回したどの起動も、3.3.0のXSFP4のdecode検査のhashと、`bench --kinds edit` の同じ返答を190 roundで返しました。NLLは3.3.0と同じで、199,307・499,254・1,035,295 tokenのpromptの合言葉はすべて見つかりました。止まった起動はありません。

| 3.8.0 | TP=2 | TP=3 |
|---|---|---|
| 起動（秒）：全検査の起動 / 2回目の起動 | 376 / 323 | 316 / 270 |
| decode検査 count / prose / code（tok/s） | 48.99 / 34.11 / 45.05 | 63.94 / 44.98 / 54.94 |
| MTPの受理長、同じタスク | 3.276 / 1.796 / 2.971 | 3.362 / 1.947 / 2.823 |
| `bench --kinds decode`（tok/s、中央値） | 53.89 | 65.33 |
| `bench --kinds edit`（tok/s、中央値） | 82.60 | 105.07 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,417.5 | 1,703.5 |
| 199,307 tokenのprompt（秒） | 151.5 | 128.7 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（秒） | 429.2 / — | 376.3 / 1,013.6 |
| 約93,000 tokenのpromptを3秒で切った後、次の要求が答えるまで（秒）、切らないpromptの最初のtokenとの比べ | 0.32 対 68.5 | 0.94 対 57.1 |
| teacher-forced NLL、ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench 2.8.0、ゲート越し / ゲートなし | 95 / 93 | 92 / 91 |
| 化けた文字のある日本語と韓国語の答え、temperature 0 / sampled | 0 / 0 | 0 / 0 |
| 6,000 tokenのpromptの後の最大1,024 tokenの40の返答（秒、rank 0のホストの最も熱いzone） | 1,248.8、75.9 °C | 989.8、86.0 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 87.9 / 88.9 | 92.4 / 89.9 / 87.9 |
| 最低の `MemAvailable`、rankごと（GiB） | 11 / 12 | 21 / 23 / 28 |

- **[3.6.0](docs/measurements.ja.md#360)との差。** tokenは同じです。3.6.0に比べ、decode・編集の返答・prefillの速さはTP=2で+0.5〜+0.7%、TP=3で−0.5〜+0.9%、長いpromptの時間はTP=2で−1.2〜−0.9%、TP=3で−1.3〜+0.9%でした（1,035,295 tokenのpromptは熱の待ちを除いて984秒、3.6.0は994秒）。TP=2のrank 0のloadの行は3.6.0と同じmodelの大きさ（524,288 tokenの窓で96.97 GiB）で、5.5 GiBのprompt cacheでした。TP=3は次の項です。
- **TP=3のKV pages。** rank 0のloadの行は、エンジン自身のsequenceとstreamに、512行のpageを2,049（12.76 GiB、1,048,576 tokenの窓で1本分）と、63.60 GiBのmodelを示します。3.6.0の76.36より12.76 GiB小さく、modelの数にエンジン自身のsequenceが入らなくなった分です。`PARALLEL=` を空にすると、エンジンは同じpageの上に8本のstreamを取り、countのhashを返しました。どの起動の後も、rank 0の `kv pool idle` の行はどれも全pageが空いていました。
- **熱。** TP=3では1,035,295 tokenのpromptだけが熱で待ち、2秒の待ちを15回、計30秒でした（3.6.0：5回で10秒）。TP=2では待ったpromptはありません。熱の見張りの止める温度に届いたzoneはありません。
- **tool。** このリポジトリの中継である[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)越しでは、点数と、部分点や失敗のシナリオが3.6.0と同じでした。3.8.0からはエンジンが呼び方の `clear_thinking` をchat templateへ渡し（上流の `c767bd766`）、最後のuserの文より前のturnの推論を外します。ゲートなしでは、エンジンはTP=2で93、TP=3で91で、Safety Gateは合格でした。両TPで増えた失敗はTC-43の一つで、空の `query` で `web_search` を呼んだものです。ゲート越しでは、queryなしでは呼ばずに断る返答になります。
- **XSFP4の既知の振る舞い。** [3.3.0](docs/measurements.ja.md#330)のものと同じです：TP=3ではstop文字列の要求が上限まで走り、promptのscoreと構造化出力の検査のscoreもgrammarも無い要求は自分のhashを持ちます。

前の版の値は[前の版の測定値](docs/measurements.ja.md)にあります。

## 制限

- **既定では一度に一要求。** それ以上には `PARALLEL` と、TP=2では小さい窓が要ります：524,288 tokenの窓には1本のstreamだけが入り（`PARALLEL=` を空にした時も1本）、`CONTEXT=245760` なら3本が入ります。TP=3ではstreamがKVのpageを分け合い、`PARALLEL=` を空にすると8本を取りました（[配信の既定](#配信の既定)）。
- **画像と動画はエンジンの制限の中で。** 画像は1要求に最大4枚で、送られた履歴にある画像を全部数えます（前のturnを画像ごと送り直すclientはそこに届きます）。4枚で4,096 tokenを分け合い、1枚10 MiB・1要求20 MiBまで。PNG・JPEG・WebPのdata URLで、GIFと動く絵は断ります。動画はuserのmessageだけで、1要求に2本（1本16 MiB・合わせて20 MiB・1時間まで）、1秒に2 frameで最大256 frameを取り、16,384 tokenを分け合います。0.5秒より短いclipは断ります。画像と動画のtokenは窓から取られます。HTTPSのURLには `serve.sh` が渡さない `--vision-urls` が要ります。音声のpartは400で断ります。
- **生成したtokenのlog確率は無い。** `logprobs` と `top_logprobs` は400で断ります。`prompt_logprobs` はstreamでない `/v1/completions` でだけ配信します。
- **要求を回す間、どのrankも2つのCPUのcoreを空回りさせ続けます。** rank 0はdecodeの間、他のrankはそれを待つ間です（上流1.1.2のエンジンからは、#1053により、rank 0にstreamが無い間は他のrankは眠ります）。containerの既定のcoreは、3.0.0のエンジンでは速さの1〜3%と引き換えに（3.1.0のエンジンでは40本の返答は同じ時間で、起動は約40秒長い）、CPUのzoneを熱の見張りが止める温度より下に保ちます。全coreでは、返答の長い連続が3.0.0のエンジンではそこに達し、3.1.0のエンジンでは1 °C手前まで来ました（[効率coreにする理由](#配信の既定)）。
- **BF16 KV** は、GiBあたり2.x系のFP8のcacheより短い窓しか持てません。エンジンには選んで使うFP8のlatent cache（`--kv-cache fp8`）がありますが、上流は品質と機器での確かめをまだとしていて、`serve.sh` も指定しません。TP=2で一度だけ試しました（XSFP4、vision towerあり、両rankのファイルに `CONTEXT=1048576`、`cluster.sh` のlabelの後に `--kv-cache fp8`）：1,048,576 tokenの窓に7.13 GiBのstreamが1本、4.7 GiBのprompt cacheと並んで入り、1,035,295 tokenのpromptは最初のtokenまで1,130.6秒で3つの合言葉を全部見つけ、199,307と499,254 tokenのpromptはprefillが約5%長くかかり、NLLの組は+0.14%（文ごとの差の区間は0をまたぐ）、decode検査のtokenはBF16のcacheと違いました。
- **ConnectX-7のリンクでつないだ2台か3台**で、1.x系・2.x系と同じです。他のrank数や他の機材は測定の範囲外です。

## リポジトリの構成

3.x系のファイルは `v3/` にあります。imageはライセンスのあるcheckoutのルートからbuildし、Pythonの道具は `v3/` から `python -m glm53_tf <command>` で動かします。ホストのツールと、全系共通のホストとfabricの文書はcheckoutのルートにあります（[`host/`](../host/README.ja.md)、[`docs/`](../docs/README.ja.md)）。

```
v3/
  README.md         このページ（各 .md の隣に .ja.md）
  SETUP.md          配備の手順書
  CHANGELOG.md      3.x系のリリース。v3.* のtagがその節を公開する
  glm53_tf/         Pythonの道具：download・verify-download・tool-gate・
                    decode-check・decode-divergence・score-nll・bench・long-input・mojibake
  config/           xsfp4.lock.json（XSFP4）、engine.lock.json（エンジンのcommit、Zigのcompiler、
                    xgrammar）、nll_set.json（NLL採点セット）
  requirements/     huggingface.lock.txt：ダウンロードとその検証に使うHugging Faceのclient
  docker/           Dockerfile：image。エンジンは ENGINE_REF で固定
                    Dockerfile.build：build用のimage。エンジンをbuildし、そのGPUのテストを回す
  scripts/          create_container.sh  各ホストの配信用container
                    cpuset.sh            そのcore（CPUSET）：既定は最大周波数の最も低いもの
                    serve.sh             1 rank、配信の既定つき
                    cluster.sh           操作する機械から全rankを起動・停止・状態確認
                    hostwatch.sh         メモリの見張り（MemAvailableが5 GiBを切るとエンジンを止める）
  examples/         参照機のrankのファイルとclusterのファイル（TP=2とTP=3）
  docs/             validation.md     受け入れの検査と基準値
                    benchmarks.md     リリースの値の取り方
                    measurements.md   前の版の測定値
                    operations.md     失敗と日常の作業：止まったrank、新しいimage、ホストを2.x系か1.x系へ渡す
                    configuration.md  全ての設定、その既定と読むrank
                    decisions.md      選んだもの、選ばなかったもの、それぞれを見直すとき
                    cheatsheet.md     上流のrecipeを越えてこの構成でできること、写せる行で
  assets/           banner.webp：このページのbanner
  tests/            glm53_tf/と、これらの頁が引く事実のCPUテスト
  pyproject.toml    3.x系の版
```

## 免責事項

- **BIZは意図であり、約束ではありません**（[リポジトリのREADME](../README.ja.md#biz)）。
- **受け入れは参照機のものです。** 他のホストや別のimage IDでの起動は、そこで[検証](docs/validation.ja.md)を回して受け入れます。
- **XSFP4は本リポジトリの管理者のcheckpointです。** NVIDIA Open Model Agreementの下のFP4-Localの派生物で、NVIDIAやZ.aiのリリースではありません。
- **エンジンはこの系列による上流のforkのリリースのbranchです。** 他の利用者にも役立つものは上流のTensorFoldへpull requestとして出し（#1016・#1017・#1018は1.1.1で、#1050・#1163・#1178・#1211は1.1.5で上流自身のものになりました）、残りはリリースのbranchが持ちます。3.8.0のbranchが持つものは無く、上流v1.1.5そのものです。

## Next Action

各項目は、きっかけと、そのときこの系列がすることです。

- 3.3.0のエンジンは上流のpull request #1053（rank 0にstreamが無い間、待つrankが眠る。1.1.2に入った）を持つ。その後のリリースは効率coreで回したので、まだ開いている → containerにまだ効率coreが要るかを測り直す。

## ローカルデータと開発

Gitに入れないもの（自分の拠点の値を入れたrankとclusterのファイルを含む）、ライセンス、開発への参加は[リポジトリのREADME](../README.ja.md#ローカルデータと開発)にあります。3.x系の変更は[CHANGELOG.ja.md](CHANGELOG.ja.md)にあります。

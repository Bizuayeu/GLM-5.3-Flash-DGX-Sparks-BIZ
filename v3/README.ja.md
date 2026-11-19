# GLM-5.3-Flash BIZ 3.x（TensorFoldネイティブ）

![GLM-5.3-Flash BIZ v3、XSFP4 × TensorFold：DGX Spark・GB10で動くZigとCUDAのネイティブ実装](assets/banner.webp)

[English](README.md) · [リポジトリの索引](../README.ja.md) · [配備の手順書](SETUP.ja.md) · [検証](docs/validation.ja.md) · [変更履歴](CHANGELOG.ja.md)

**GLM-5.3-Flash BIZ** は、DGX Sparkまたは互換のGB10機でGLM-5.3-Flashを配信します。3.x系はTensorFoldのネイティブエンジン、つまり[2.x系](../v2/README.ja.md)が動かすPythonのエンジンに代わったZigとCUDAのエンジンで、2台のTP=2、3台のTP=3、または3.12.0から試験的に4台のTP=4で配信します。配信するcheckpointは[XSFP4](#checkpoint)、[Jammed XSFP4](#checkpoint)（routed expertがTP=2の各ホストで6.58 GiB少ない）、[Jammed XSFP4 NZ5](#checkpoint)（Jammed XSFP4の並びのまま、4 bitのcodeの1つを+5と読む）です。3.16.0から既定は、2台ならJammed XSFP4 NZ5、3台か4台ならXSFP4で、rankのファイルの1行で別のものを配信します。XSFP4は、NVIDIAのGLM-5.3-Flash-FP4-Localの派生物、expertsを本リポジトリの管理者が量子化し直したものです。1.x系・2.x系が配信するNVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointは、3.5.xまでここでも選べました。各リリースのエンジンは、上流のTensorFoldの一つのリリースの上にbuildします（[何であるか](#何であるか)）。各リリースで何が変わったかは[変更履歴](CHANGELOG.ja.md)にあります。2.x系も並んで続きます。

**BIZ**は保守者の印で、リポジトリの意図を示す語です。意味することと意味しないことは[リポジトリのREADME](../README.ja.md#biz)にあります。

## 要約

- **状況。** 3.16.0はエンジンを、この系列のcommitを持たない上流のTensorFold 1.2.10そのものに移し、TP=2の既定のcheckpointを[Jammed XSFP4 NZ5](#checkpoint)にします。TP=3と、switchの無いリングの4台で試験的なTP=4は、XSFP4のままです（[配信の既定](#配信の既定)）。リリースのimageを、全containerを効率coreに置いてそれ自身の `serve.sh` と `cluster.sh` で起動すると、TP=2とTP=3のXSFP4、両TPのJammed XSFP4で基準値のdecode検査のhashと編集の返答を、TP=4で3.12.0のものを返しました。どのTPでも、1,035,295 tokenのpromptを含めて長い入力の合言葉はすべて見つかり、`mojibake` は、temperature 0でもsampledでも、日本語と韓国語の答えに化けた文字を見つけませんでした（[リリースでの測定値](#リリースでの測定値)）。3.11.0のtool引数ゲート越しのtool-eval-benchは、TP=2のJammed XSFP4 NZ5とXSFP4、TP=3のXSFP4で93、Safety Gateは合格でした。ゲートなしでは、Jammed XSFP4 NZ5は同じ93点で、Safety Gateを1つのscenarioで落とします。TP=3のdraftありのdecodeは、tokenは同じまま、3.12.0のエンジンより、3.10.0のエンジンよりも速くなりました：上流の直し（[TensorFold #2864](https://github.com/ashhart/TensorFold/pull/2864)）は1.2.8からリリースに入っています。TP=3の受け入れは昼に回し、長い2つのpromptは熱で待ちました。TP=3とTP=4ではstop文字列の要求が上限まで走り、TP=3では短いgreedyの返答が自分のhashを持ちます。どちらも[検証](docs/validation.ja.md#xsfp4)に書いた既知の振る舞いです。[検証](docs/validation.ja.md)の基準値はXSFP4のものと、それぞれの節の[Jammed XSFP4](docs/validation.ja.md#jammed-xsfp4)と[Jammed XSFP4 NZ5](docs/validation.ja.md#jammed-xsfp4-nz5)のもので、その節が名指す受け入れが決め、最も新しいのは2026-11-19の参照機での3.16.0の受け入れです。主張の範囲はここまでです。他のホストは同じ検査を回して受け入れます。
- **何であるか。** XSFP4・Jammed XSFP4・Jammed XSFP4 NZ5のどれかを、TensorFoldのネイティブエンジンの固定したcommitで一つのOpenAI互換endpointとして配信するための、build手順・起動の台本・受け入れ検査です。2台なら直結のConnectX-7リンクでTP=2、3台ならswitchなしのリングでTP=3、試験的に4台ならswitchなしのリングでTP=4です。公開している測定値はMSI EdgeXpert（MS-C931）で取りました。Macでは、TensorFoldが自身のMLXの重みでGLM-5.3-Flashを配信します（[Macでは](../README.ja.md#macでは)）。
- **反復性。** draftした応答はserialと同じで、起動は同じTPの前の起動のtoken idを出します。ネイティブエンジンのtokenはそれ自身のもので、2.x系のものではありません：kernelとBF16のKV cacheの丸めが違うので、二つの系列はtokenごとではなくteacher-forced NLLで比べます（[2.x系との違い](#2x系との違い)）。
- **構造化出力とpromptのscore。** JSON schemaつきの `response_format`、`required` か名指しの関数の `tool_choice`（GLM自身のtoolのmarkupで書く）、`/v1/completions` の `prompt_logprobs` は、1.1.1からGLMのCUDAのエンジンで上流のTensorFold自身のものです。この系列のpull request #1016・#1017・#1018の後に上流が書きました（[API](#api)）。
- **画像と動画。** chatの要求は、PNG・JPEG・WebPの画像と、H.264・HEVC・VP8・VP9・MPEG-4の動画をdata URLで持てます。rank 0にあるcheckpointのvision towerが、エンジンの `--vision` で読みます。`serve.sh` は既定でこれを渡します（[制限](#制限)）。
- **精度。** XSFP4・Jammed XSFP4・Jammed XSFP4 NZ5ではrouted expertはW4A16、他のprojectionはcheckpointが保存する形のままで、多くは8 bit、vision towerのMLPとmergerはNVFP4です（[checkpoint](#checkpoint)）。KVはBF16です（2.x系はFP8のKV cacheを持ちます）。NVIDIAのmodel cardは別のレシピ・別の機材でFP4-Localを測っており、その精度表はこの配信を表しません。この配信を表す数字は[検証](docs/validation.ja.md)にあります。
- **ライセンス。** コードとエンジンはApache-2.0、重みは運用者がダウンロードし、NVIDIA Open Model Agreement（XSFP4・Jammed XSFP4・Jammed XSFP4 NZ5、商用に使える）です。imageには構造化出力のためにxgrammar（Apache-2.0）、画像と動画のためにlibjpeg-turbo・libwebp（BSD系）とFFmpegのdecoder（LGPL-2.1）が入ります。配信の経路に非商用の条件はありません（[ライセンスの早見表](../README.ja.md#ライセンスの早見表)）。
- **未検証。** 画像と動画のURL（`--vision-urls`、無効）、長い会話が同時に何本も並ぶ負荷、他のrank数と機材（[制限](#制限)）。ハーネス連携（ZCode・Claude Code）、アプリケーション全体の品質と本番の信頼性。

## 何であるか

- **重み**：既定はTP=3とTP=4で `Bizuayeu/GLM-5.3-Flash-XSFP4`（[`config/xsfp4.lock.json`](config/xsfp4.lock.json)）、TP=2で `Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4-NZ5`（[`config/nz5.lock.json`](config/nz5.lock.json)）で、選べるものに `Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4`（[`config/jammed.lock.json`](config/jammed.lock.json)）があります（[checkpoint](#checkpoint)）。どれもNVIDIAのGLM-5.3-Flash-FP4-Localと[Z.aiのGLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)から作られています。
- **エンジン**：TensorFoldのネイティブエンジン（`tensorfold-native`）。[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/3.16.0` として公開するBIZ版で、上流のTensorFold v1.2.10そのもの（`2a674b55`）です。この系列のcommitは持ちません。3.10.0のbranchが1.2.1に足した6つのcommitは、上流のリリースが1.2.3から持っています（#2041）。6つのcommitはJammed XSFP4の `csf0_v1` の形を専用の5つのkernelで読みます。Jammed XSFP4 NZ5の `NVFP4_NZ5` の形（`csf0_v1` と同じ並びで、4 bitのcode `0b1000` を+5と読む）も、上流のリリースが1.2.10から読みます（#2894）。どちらの形も持たないcheckpointは上流の道をそのまま通ります。上流は2026-10-25にこの系列の最初のpull requestを取り込み、1.1.5はそれらを持つ最初のリリースでした。#1050はNVIDIAのGLM-5.3-Flash-FP4-Localを保存された形のまま読み、それと共に、experts以外にFP4-Localのtensorを持つXSFP4のcheckpointも読みます：各projectionの形をcheckpointの `MIXED_PRECISION` のレシピから見分け、MXFP8と128×128 blockのFP8のprojectionを保存の形のまま計算し、FP4-Localの圧縮したexpertのscaleを読み、float32のnormの重みをfloat32のまま保ちます。#1178はrank 0のNCCLのidをrankどうしの生存の線で他のrankへ送るので、TP=3は上流のbootstrapで起動し、3.6.0のリリースのbranchがそのために持っていたidのファイル（`TF_GLM_NCCL_ID_FILE`）とこの系列の二つのcommitは要りません。#1163と#1211は、各streamのKV cacheとエンジン自身のsequenceを一つのpoolのpageに置きます。1.1.5では3 rankで、1.1.6（#1322）からは2 rankでもです（[配信の既定](#配信の既定)）。3.9.0の既定はその後に入ったものを使います：promptがdecodeの横とrankの間で動く#1352・#1404（1.1.9）、`--mtp-confidence` とmultirank RoCEのwire（#1516・#1524、1.2.0）、poolのpageに残すprompt（#1732、1.2.1。#2211から `TF_KV_SHARE` で、3.11.xまでは `TF_GLM_KV_SHARE`）です。#1616と#1636（1.2.0）は重みを複数のthreadで読んで詰めるので、起動が短くなります。indexがmodelのfolderの中のfolderにあるshardを名指せること（FP4-LocalとXSFP4のindexに要る）は、1.1.3から上流自身のcodeにあり、3.5.xまでのリリースのbranchはpull request #1179のpatchとして持っていました。1.1.5から、serverはGLM-5.3のchat templateに `clear_thinking` を渡します（[設定](docs/configuration.ja.md#rank-0のserver)）。3.0.0〜3.2.0の熱の待ちの天井への見込み（`TF_HEAT_CEILING`）は無くなり、熱の待ちは上流の帯だけです（[配信の既定](#配信の既定)）。imageは一つのcommitに固定します（[`config/engine.lock.json`](config/engine.lock.json)）。
- **image**：[`docker/Dockerfile`](docker/Dockerfile)。エンジンはNVIDIAのCUDA 13.3.1のbuild用imageで、lockが名指すZigのcompiler（SHA-256で確かめる）がcompileし、`libtfgrammar` は固定したcommitのxgrammarのreleaseからbuildします。実行のimageはCUDA 13.3.1にNCCL 2.30.7とRDMAのuserspaceです。2つのbaseのimageはdigestで固定しています。`/usr/share/doc/tf3/ENGINE` がエンジンのcommitと各binaryのSHA-256を名指し、`/usr/share/doc/tf3/engine/` にエンジンのライセンスと表示があります。
- **起動**：[`scripts/`](scripts/) のshellの台本と、rankごとの環境ファイル一つ（[`examples/`](examples/) に参照機のファイル）。順番は[SETUP.ja.md](SETUP.ja.md)にあります。ホストでは何もbuildしません：kernelはbinaryの中にあります。
- **他のレシピ**：このリポジトリがTensorFoldの他のレシピから取ったものと、それらのlicenseは、2.x系の[表](../v2/README.ja.md#tensorfoldの他のレシピ)にあります。3.x系のTP=3のrankのファイルは、2.x系がMiaAI-LabのTensorFoldのレシピから取って測ったfabricの設定のうち二つ、4本のNCCLのchannelとsubnet-aware routingを持ち続けます（[決定](docs/decisions.ja.md#fabric)）。上流のTensorFold自身の、CUDAでのこのモデルのレシピは[GLM-5.3-Flash on CUDA](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md)です。

## 必要な環境

- **ホスト**：DGX Sparkまたは互換のGB10機を2台、3台か4台（Linux ARM64、各128 GBの統合メモリ）。GPUで他の大きな仕事を動かさないこと。同じホストで1.x系か2.x系のserverが動いていれば先に止め、全GPUを要求する2.x系のcontainerも止めます（[ホストを2.x系へ渡す](docs/operations.ja.md#ホストを2x系へ渡す)）。
- **fabric**：RoCE v2のConnectX-7リンク。2台は直結、3台か4台はswitchなしのリング（[3台をリングにつなぐ](../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)。参照機の4台のリングは[TP=4のexample](examples/tp4-rank0.env)）。各portの2本のrailを両方使います。
- **ホストカーネル**：1.x系・2.x系と同じです。今のDGX OSの更新が入れるカーネルは、既定のままでは複数ノードのRoCEを壊すことがあり、参照機は `kho=off` で起動しています（[ホストカーネルと複数ノードRoCE](../docs/hosts.ja.md#ホストカーネルと複数ノードroce)）。2026-11-07 からは `7.0.0-1025-nvidia` を、`initcall_blacklist` に `power_wrap_init` も入れて起動し、ConnectX-7 と基板のファームウェアも新しくなっています。この上の3.x系の受け入れは3.12.0が最初で、前の版から引き継いだ数は、その前の `7.0.0-1019-nvidia` で測りました（[ホストの更新](../docs/hosts.ja.md#ホストの更新)）。
- **GPUクロック**は全ホストで上限を設けます（[GPUクロックの上限](../docs/hosts.ja.md#gpuクロックの上限)）。上限と温度の記録は[`host/`](../host/README.ja.md)が据え付けます。3.x系の数字は全部この上限の下で測りました。
- **Docker**：NVIDIAのGPU runtimeとRDMAデバイスが要ります（`/dev/infiniband` が無いホストでは、NCCLがsocketに落ちるので `create_container.sh` が断ります）。
- **disk**：全ホストにcheckpointを丸ごとと、image。XSFP4は178 GB、Jammed XSFP4とJammed XSFP4 NZ5はそれぞれ172 GBを取ります。
- **操作する機械**：全ホストへSSHでき、`cluster.sh` を動かす機械一台。
- **Python 3.11以上**：各ホストで、この系列の道具（[`glm53_tf/`](glm53_tf/)：ダウンロード、検証、tool引数ゲート、検査）を `v3/` から動かします（[手順書 §2](SETUP.ja.md#2-checkoutとcheckpoint)）。

## はじめ方

各段とその後に確かめることは[配備の手順書](SETUP.ja.md)にあります。以下はTP=2のときの骨組みです。全ホストで同じ、確認済みの `v3.*` のtagを使います。

```sh
# 一度だけ、ある1台の v3/ からその仮想環境で。その後cacheを他のホストへ写し、写しごとに検証する（SETUP §2）
python -m glm53_tf download --tp 2 --background
python -m glm53_tf verify-download --tp 2 --hf .venv/bin/hf --output ../records/checksum-nz5 --wait

# checkoutの根で、1台がimageをbuildし、他はそれを読み込む。image IDを比べる（SETUP §3）
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.16.0 .

# 各ホストで、checkoutのルートから（SETUP §4）
v3/scripts/create_container.sh glm53-tf3:3.16.0 ~/glm53-tf3
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

3.x系が配信するcheckpointは、XSFP4と、3.10.0からのJammed XSFP4と、3.16.0からのJammed XSFP4 NZ5です。Jammed XSFP4はrouted expertを入力32個ごとのblockのスケールで合わせ直し、そのスケールを4分の1のメモリで持ちます。Jammed XSFP4 NZ5はJammed XSFP4の並びのまま、−0を表していた4 bitのcodeを+5と読み、それを使うようにexpertを合わせ直したものです。既定はTPで分かれ、TP=2は3.16.0からJammed XSFP4 NZ5（3.12.0〜3.15.0はJammed XSFP4）、TP=3とTP=4はXSFP4です（3.4.0から3.11.xまでは、どのTPでもXSFP4）。各リリースのファイルがそのTPのfolderを名指し（[`config/tp*.env`](config/)）、rankのファイルの `CHECKPOINT` の1行で別のものを配信します。3.3.0まで既定で3.5.xまで選べたNVIDIAのNVFP4は、1.x系・2.x系のものです。全rankが同じものを配信します。

| | XSFP4 | Jammed XSFP4 | Jammed XSFP4 NZ5 |
|---|---|---|---|
| 重み | [`Bizuayeu/GLM-5.3-Flash-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4)（[`config/xsfp4.lock.json`](config/xsfp4.lock.json)） | [`Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4)（[`config/jammed.lock.json`](config/jammed.lock.json)） | [`Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4-NZ5`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4-NZ5)（[`config/nz5.lock.json`](config/nz5.lock.json)） |
| 作り手 | 本リポジトリの管理者、NVIDIAの[`GLM-5.3-Flash-FP4-Local`](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local)（revision `76348ddb`）とZ.aiのBF16の重みから | 同じ。XSFP4の平滑化とBF16の重みから | 同じ。XSFP4の平滑化とBF16の重みから、Jammed XSFP4の並びで |
| routed expert | XSFP4、W4A16で配信：平滑化を重みに畳み込み、BF16の重みからNVFP4のblockを当てはめ直したもので、実行時にkernelが何も掛けません。MTP層のexpertも同じ。3〜44層はblockのスケールを可逆に圧縮して持ち（`csf_32x2_v1`、FP4-Localと同じ）、エンジンが読み込みの時にホストで元に戻します | NVFP4、W4A16で配信。XSFP4の平滑化のまま、3〜44層のblockのスケールを入力16個ごとから32個ごとにしたもの。行ごとのスケールはE4M3の16段に収まり、行に1つのbaseとblockごとの4 bitのoffset（`csf0_v1`）で、fileでもGPUでも同じ形で持つので、スケールのメモリは4分の1です。MTP層のexpertはFP4-Localのもの、block 16 | 3〜44層はJammed XSFP4の並び（block 32、スケールは `csf0_v1`）のまま、codeの1つの意味を変えたもの：E2M1の−0である `0b1000` を+5と読み（`NVFP4_NZ5`）、それを使うようにexpertをBF16の重みから合わせ直しました。bitは増えず、fileの大きさはJammed XSFP4と同じで、エンジンは専用のkernelで読みます。W4A16で配信。MTP層のexpertはFP4-Localのもの、block 16 |
| その他 | FP4-Localのtensorを保存の形のまま：MXFP8（dense MLP、KDA、`lm_head`、MTP層のattentionとshared expert）、128×128 blockのFP8（MLAとshared expert）、BF16（KDAの小さいprojection、MLAの `kv_b` とindexer、router、embeddings）、BF16とF32のnorm。vision towerはMXFP8とNVFP4 | XSFP4と同じ | XSFP4と同じ |
| 3.16.0の受け入れでのTP=2・TP=3のrank 0のmodel（読み込みの行、KV cacheはpage） | 91.37・64.11 GiB | 84.79・59.61 GiB | TP=2で84.79 GiB。TP=3では起動していない |
| このエンジンのTP=2でBF16の重みと比べた次token（128文書、144,285位置）：top-1の一致 / BF16に対するNLLの上がり / KLの下限 | 93.26% / +0.85% / 0.0431 | 92.78% / +1.35% / 0.0482 | 92.89% / +1.08% / 0.0463 |
| 同じものをTP=3で | 93.30% / +0.85% / 0.0436 | 92.80% / +1.41% / 0.0483 | — |
| ライセンス | NVIDIA Open Model Agreement（FP4-Localの派生物。repositoryに `LICENSE` と `NOTICE`） | 同じ | 同じ |
| ダウンロード（SETUP §2） | `download`・`verify-download` に `--tp 3`・`--tp 4`・`--checkpoint xsfp4` のどれか（ダウンロードの状況は `state/xsfp4` に） | `download`・`verify-download` に `--checkpoint jammed`（状況は `state/jammed` に） | `download`・`verify-download` に `--tp 2` か `--checkpoint nz5`（状況は `state/nz5` に） |
| rankのファイル | TP=3とTP=4では何も要らない（リリースのファイルがlockのrevisionを名指す）。TP=2では全rankのファイルに `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-XSFP4/snapshots/<lockのrevision>` の1行だけ | どのTPでも、全rankのファイルに `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-Jammed-XSFP4/snapshots/<lockのrevision>` の1行だけ | TP=2では何も要らない（リリースのファイルがlockのrevisionを名指す）。3.16.0の受け入れは、TP=3とTP=4では起動していない |

各文書はtoken idとしてエンジンに送り、`prompt_logprobs` は20。KLの下限は、両方が確率を返したtoken（エンジンの上位20、BF16の上位20、本文のtoken）を1つずつ数え、残りを1つの塊として数えます。全語彙のKLより低く、エンジンの外で測ったKLとは比べられません（XSFP4の[model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4)に両方があります）。同じエンジンと文書で、NVIDIAのNVFP4はTP=2で 92.68% / +1.37% / 0.0510、TP=3で 92.71% / +1.38% / 0.0511 だったので、XSFP4はどちらのTPでも3つともBF16に近く、差の文書ごとの95%区間は0を含みません。FP4-Local自身を同じエンジンでそのまま読み込むと、TP=2で 92.82% / +1.11% / 0.0510、TP=3で 92.75% / +1.07% / 0.0514 でした。

XSFP4の[測定値](#リリースでの測定値)の速さはXSFP4のものです：draftの受理と層の形がNVIDIAのNVFP4と違うので、1.x系・2.x系の数とは比べられません。XSFP4が持つFP4-Localのchat templateは、NVIDIAのものと3か所違います（contentの無いmessageは何も出さない、tool callの名前を `~` でつなぐ、toolの結果を呼び出しの順に並べられるかの検査が、だめと分かった所で止まる）。

Jammed XSFP4はBF16への近さの一部をメモリと引き換えにします：表の3つの数では、両TPでXSFP4よりBF16から離れています（差の文書ごとの95%区間はどれも0を含みません）。3.12.0のエンジンからは、空いた分はprompt cacheの残りを取るKVのpoolに入ります。3.16.0の受け入れでは、TP=2で同じくsystemに9 GiBを残し、poolが2,995 page（XSFP4は2,055）、読み込みの後のrank 0の空きは9.2 GiB（XSFP4は9.3 GiB）でした。TP=3で16 GiBを残すと、poolは5,505 page（XSFP4は4,745〜4,766）で、どちらも窓2本とprompt cacheの残り、保持の状態のslotは32全部、rank 0の空きは16.5 GiB（XSFP4は16.5〜16.6 GiB）でした。3.12.0の受け入れでは、ここでpoolが窓3本目を取り、prompt cacheに残るslotは32のうち8でした（[16 GiBにする理由](#配信の既定)）。返答はこのcheckpointのものなので、draftありのdecodeの速さはXSFP4と比べられません。promptの速さは比べられ、同じimageのそれぞれ1回の起動で、TP=2が1,525.4 tok/s対1,507.6、TP=3が1,956.0対1,949.8です（[測定値](#リリースでの測定値)）。TP=3の2つの起動は、decodeの窓でexpertが取る形のエンジンの選びが違いました（Jammed XSFP4はclassic、XSFP4はfactored）。TP=2はどちらもfactoredで、Jammed XSFP4はrankのファイルの `TF_GLM_EXPERT_FORM` で指定しました。作り方とエンジンの外での点は[モデルカード](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4)にあります。

Jammed XSFP4 NZ5は、Jammed XSFP4が使っていないcodeを1つ使います。E2M1の4 bitのcodeは16個ですが、0が正負の両方にあるので、表す数は15個です。このcheckpointは3〜44層のrouted expertで、0をすべて `0b0000` と書き、`0b1000` を+5と読みます。+5は4と6の間の目盛りで、blockの大きい重みが落ちる所です。expertはこれを使うようにBF16の重みから合わせ直しました。fileの大きさはJammed XSFP4と同じで、3.16.0のエンジンのTP=2では、rank 0の読み込みの行のmodelもどちらも84.79 GiBです。上流のリリースは1.2.10から読めます（#2894）。表のTP=2の数では、他の2つの間に入ります。Jammed XSFP4よりBF16に近く、NLLの上がりは−0.27点、KLの下限は−0.0019で、差の文書ごとの95%区間はどちらも0を含みません（[−0.49, −0.07]と[−0.0032, −0.0007]）。top-1の一致の区間は0を含み、3つの中ではどの数でもXSFP4が一番近いままです。この列のBF16との数は3.16.0の受け入れ（上流1.2.10）のもの、他の2列は3.12.0の受け入れ（1.2.7）のもので、TP=3では測っていません。XSFP4のTP=3の3つの数は、3.16.0の受け入れでも同じ値でした。エンジンの外（PyTorch、全語彙）でも順は同じで、[モデルカード](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4-NZ5)のKLは0.0440（Jammed XSFP4は0.0470、XSFP4は0.0410）です。3.16.0のTP=2の受け入れでは、systemに9 GiBを残して、poolが2,948〜2,982 page、保持の状態のslotは16全部でした（[TP=2を1,048,576にする理由](#配信の既定)）。同じホストの対・同じimageで、それぞれ1回の起動では、promptの速さが1,504.4 tok/s（Jammed XSFP4は1,525.4、XSFP4は1,507.6）、[NLLの検査](docs/validation.ja.md#teacher-forced-nll)の16文は 2.5517 / 2.9273 / 1.3136 / 0.6200（日本語 / 英語 / code / 数学。Jammed XSFP4は 2.5349 / 2.9247 / 1.3125 / 0.6235）でした。文ごとに見ると16文のうち8文で高く8文で低く、日本語の平均の上がりは1つの文によるもので、この検査では2つの差は分かりません。返答はこのcheckpointのものです：decode checkのhashはXSFP4ともJammed XSFP4とも違い、draftありのdecodeの速さもそれらと比べられません（[検証](docs/validation.ja.md#jammed-xsfp4-nz5)）。

## 配信の既定

TPで分かれるものは [`config/tp2.env`](config/tp2.env)・[`config/tp3.env`](config/tp3.env)・3.12.0からの [`config/tp4.env`](config/tp4.env) が持ち、残りはそれを読む [`scripts/serve.sh`](scripts/serve.sh) が持ち、全rankで同じです。TP=2の既定は1人がagentと続ける長い会話のため、TP=3の既定は複数の人の同時利用のためのものです。何と比べて選び、何が起きれば見直すかは[決定](docs/decisions.ja.md)にあります。

| 設定 | TP=2（2台） | TP=3（3台） |
|---|---|---|
| checkpoint | 3.16.0からJammed XSFP4 NZ5、lockのrevision（`config/tp2.env` の `CHECKPOINT`、[checkpoint](#checkpoint)。3.12.0〜3.15.0はJammed XSFP4） | XSFP4、lockのrevision（`config/tp3.env`） |
| KV cache | latentとindexのkeyをBF16（エンジンの既定。`--kv-cache fp8` で選べるFP8のlatent cacheは受け入れの外：[制限](#制限)）、KVのpageに：全streamのcacheとエンジン自身のsequenceが1つのpoolのpageを取る（2 rankからのエンジンの既定、`TF_KV_PAGES`。全rankのファイルの `TF_KV_PAGES=off` と空の `TF_KV_SHARE=` は、TP=2は3.8.xまで、TP=3は3.7.0までと同じくstreamごとの窓） | 同じ |
| draft | checkpointのMTP head（エンジンの既定） | 同じ。draftの連なりは確率が0.5未満のdraftで終わる（`MTP_CONFIDENCE`、エンジンの `--mtp-confidence`） |
| 窓（`--context`） | 1,048,576 token（モデルの上限） | 同じ |
| 同時にdecodeする要求（`--parallel`） | 4（`PARALLEL`）。空の `PARALLEL=` ではエンジンに任せ、エンジンは起動時の空きメモリの許す限り8本までstreamを取る | 8。同じ |
| prompt cache（保持するpromptの状態） | KVのpoolのpageの上（`TF_KV_SHARE=16`）：保持するpromptは埋めたpageのまま残り、その先の状態は最大16で、会話は持っているpageの最後の印から再開する。poolの横にstoreは持たない（loadの行の `the prompt cache over the pool's pages`） | 同じ、状態は最大32（`TF_KV_SHARE=32`） |
| decodeの横のprompt | stepが時間の70%を取り、残りをstreamのroundが取る（`TENSORFOLD_PREFILL_SHARE=0.7`。エンジンの `1` はstepとroundを1回ずつ交互に回す） | 同じ |
| systemに残すメモリ（`TENSORFOLD_MEMORY_RESERVE_GIB`） | 9 GiB | 16 GiB |
| 要求が指定しないときの応答の上限 | 32,768 token（`--max-tokens`） | 同じ |
| 要求が指定しないときの推論のeffort | `high`（`--reasoning-effort`） | 同じ |
| NCCL | 各リンク2本のrail・4 channel・IBのtransportを明示、rankごとのファイルから。rank 0のアドレスとportを `NCCL_COMM_ID` に、rank 0のNCCLのidはrankどうしの生存の線で | 2本のrail・4 channel・IBのtransportを明示・subnet-aware routing。rank 0のアドレスとportを `NCCL_COMM_ID` に、rank 0のNCCLのidはrankどうしの生存の線で、他のrankのNCCLのbootstrapはそれぞれの `/32` のinterfaceで（`NCCL_SOCKET_IFNAME`） |
| main streamの小さいall-gather | エンジンの2 rankのRoCEの経路（rankあたり `TF_ROCE_MAX_KB` の4 MiBまで）、それを超えるものはNCCL（`TF_ROCE`、既定で有効。`TF_ROCE=0` ではNCCLのまま） | エンジンのmultirank RoCE、wireをNCCLの隣で（`TF_GLM_ROCE_MULTI=1`）。準備に失敗すると起動が止まる |
| BF16のlinear | 上流のtiledのkernel（エンジンの既定） | 同じ：上流1.1.2から（issue #1067）、TP=3のrankのKDAの入力をtileせずに回す。3.1.0と3.2.0はglueのkernel（`TF_GLM_MM=0`）が要った |
| 熱によるprefillの休止 | prompt chunkの前ごとに全rankそろって、どれかのrankのACPIの最も熱いzoneが92 °Cを超えている間、全rankが88 °C以下になるまで待つ（`TF_HEAT_HIGH`・`TF_HEAT_LOW`。3.0.0〜3.2.0は93 °Cの天井の手前でも待ったが、3.3.0のエンジンは天井を持たない） | 同じ |
| 画像と動画の入力 | 有効（`VISION=1`、エンジンの `--vision`）：rank 0にcheckpointのvision tower、PNG・JPEG・WebPの画像と動画をdata URLで、エンジンの制限の中で（[制限](#制限)）。`VISION=0` でtextだけ、全rankで同じに | 同じ |
| containerのcore | 最大周波数の最も低いcore：GB10の効率core、0-4と10-14（`create_container.sh`、`CPUSET`） | 同じ |

**TP=4（試験的）。** 3.12.0から、4台がswitchなしのリングでTP=4で配信します。[`config/tp4.env`](config/tp4.env) はTP=3の値でwireを切り、システムに14 GiBを残します。2026-11-07から上流のmainで参照機の4台のリングを配信した設定で、どれも4台では詰めていません。このリングではwireは上流の試験的なrelay（#2352）を通ります。上流でもopt-inで、ここでは既定として測っていません。参照機のリングでは、#2352の最後のheadで、1本のdecodeがNCCLより2〜3%速く、4本とcoldのpromptは同じ速さでした。[example](examples/tp4-rank0.env)はリングのNCCLの行と `TF_GLM_PREFILL_REDUCE=gather` を足します：エンジンの `split` は各rankの行を他の全rankへ送るので、4台のリングでは起動しません。3.16.0のエンジンからは、rankが起動時のやり取りで `REFUSE TF_GLM_PREFILL_REDUCE=split` の行を出して止まり、その行はこういうリングに `gather` を名指します。3.12.0のエンジンは、設定を名指さずにNCCLの `ncclGroupEnd: unhandled system error` で止まりました。

**TP=2で4本、TP=3で8本にする理由。** 1本のstreamでは要求は前の返答の終わりを待ちます。3.8.xまでのTP=2では2本目のstreamが自分の窓を取り、短い窓にしか余地がありませんでした。KVのpageではstreamは使う分を一つのpoolから取るので、窓は本数によらずどの起動でも同じです。TP=2の4本は、agentが長い会話の横で送る短い要求のためのものです：32K tokenのpromptに6〜8秒で来た要求は1.20秒で最初のtokenを返しました。1本ならpromptと返答の全体を待ちます。TP=3の8本は複数の人のためのもので、4本の1本が終わるのを5本目が待たないようにします：別々の8つのpromptを一緒に送ると全部が1.65秒以内に始まり、合計は94.23 tok/s（4本では75.00）でした。同時の返答は同じ要求の単独の返答と同じです（[同時の要求](docs/validation.ja.md#同時の要求)）。

**prompt cacheをpoolのpageに置く理由。** 長い会話の保持の状態は4本のstreamの横のstoreに入らないことがあり、次の長いpromptが前の状態を追い出します。`TF_KV_SHARE` はpromptを埋めたpoolのpageのまま保つので、poolに余地がある間は状態が次のpromptの後も残り、poolの横にstoreを持ちません。約64K tokenと128K tokenのpromptの再送はTP=2で2.06秒と2.34秒、TP=3で1.54秒と2.11秒、400K tokenのpromptはTP=2で2.17秒でした。読み直せば数分かかります。16と32はstream 1本に4状態で、エンジン自身の線です。その下では、動いているstreamが互いの状態を追い出すと警告します。

**promptの取り分を0.7にする理由。** エンジンの `1` では長いpromptのstepとdecodeのroundが1回ずつ交互に回るので、横の返答はtokenごとにstep 1回分止まります。0.7ではpromptが時間の30%をdecodeに渡します：32K tokenのpromptの横の、別々のpromptの3本のdecodeのtokenの間隔はTP=2で62 ms、TP=3で47 msでした。promptが払うのは何かが横でdecodeしている間だけで、単独のpromptは待ちません。

**TP=3でwireとdraftの確率を使う理由。** `--mtp-confidence 0.5` は、確率が五分を切るdraftでdraftの連なりを終えるので、roundが外れるdraftに使う行が減ります。上流はTP=3でdecodeが4.9%速いとしています。TP=2では切ります：その使い方であるsampledの1本は同じdraftを取り、4本のgreedyのcodeは3.7%遅くなりました。wireはmain streamの小さいall-gatherをエンジンのmultirank RoCEで運び、各rankは最初の1回をNCCLのものとbyteまで比べます。上流はdecodeが2.57%速く、coldの長いpromptが1.2〜1.6%遅いとして、既定をoffにしています。TP=3は返答を読む人のための配信なので、ここではdecodeを優先します。3 rank以上のためのものです。`TF_TP_ROCE_FALLBACK=error` により、準備に失敗すると起動が止まるので、気づかれずにNCCLへ戻ることはありません。

**poolの大きさは、loadの時に1回読んで決まります（仕様）。** エンジンは、modelを読み込んだ直後に各rankの空きを1回読み、一番小さい値からreserveを引いた分をpoolに充てます。その1回の読みは、同じ設定でも起動ごとに0.1〜0.2 GiB動くので、loadの行の余地とpage数も一緒に動きます：3.16.0の受け入れでは、TP=4で8,006〜8,036 page、TP=3で4,745〜4,766 pageでした。poolの1%未満で、窓の数と保持する状態のslotの数はどの起動でも同じです。起動後のrank 0の空きは、ホストのtelemetryで、reserveより0.2〜0.6 GiB多く残っていました。3.12.0のエンジンでも同じです。メモリが失われているのではありません：起動の前の空きは、起動を重ねても平らで（TP=4のrank 0は7回で119.79〜119.87 GiB、TP=3のrank 0は5回で119.61〜119.67 GiB）、止めるたびに0.05 GiB以内まで戻り、poolに充てた量と起動後に残った空きの和は、TP=4で70.2〜70.3 GiBと一定でした。そのため、起動はpage数や余地の値ではなく、窓とslotの数で判じます。

**TP=3で16 GiBにする理由。** poolは窓の丸ごとの本数でpageを取り、3.12.0のエンジン（上流1.2.5、#2358）からは、prompt cacheのうち保持するstateのslotの残りもpageにします。3.12.0のエンジンの起動の計画は、余地に入る窓を全部そのslotより先に置きました。3.16.0のエンジン（上流1.2.10、#3125）からは、エンジン自身の窓の先の窓よりslotを先に置きます。参照リングのホストは2026-11-07からメモリを1.50 GiB多く報告します（MemTotal 129,168,464 kB）。3.11.xのエンジンの14 GiBでは、poolの余地が39.3〜39.5 GiBと、窓3本に要る38.85 GiB（上流の `kv_pool.plan`）を超えたので、poolは5,989〜6,017 pageを取り、rank 0の起動後の空きは約10.3 GiBでした。16 GiBでは余地は窓3本に届きません：3.12.0の受け入れでは余地が36.8〜37.2 GiBで、保持する32 stateのslotが5.3 GiBを取り、poolは窓2本とcacheの残り、512行のpageを4,706〜4,780（29.30〜29.76 GiB）取り、rank 0の空きは16.5〜17.1 GiBでした。3.16.0の受け入れでは余地が37.0〜37.2 GiB、poolが4,745〜4,766 page（29.54〜29.67 GiB）、rank 0の起動後の空きは16.5〜16.6 GiBでした。検査が走っている間、rank 0のホストの `MemAvailable` の最低は、memory guardの整数のGiBの読みで15 GiBで、16 GiBを下回りました（3.12.0は16）。ホストのtelemetryでは15.63 GiB（3.12.0は15.99 GiB）です：poolが39 page（0.24 GiB）、modelが0.10 GiB大きくなった分です。3.16.0の起動では、空きは起動後にreserveより0.4〜0.6 GiB上にあり、要求の合間の空きは最初のいくつかの検査で0.3〜0.4 GiB下がって、その後は1,035,295 tokenのpromptの間も平らでした（3.12.0も17.0 GiBから同じ形）。エンジンを止めると空きは戻り、続けた5回の起動は119.61〜119.67 GiBから始まりました。このエンジンを負荷の下で何日も配信した時は測っていません。一番長い起動は132分です。TP=2と同じく、reserveは計画が起動の時に残す量で、床ではありません。守りは二重です：ホストが5 GiBを下回ると、統合メモリが尽きる前にmemory guard（`hostwatch.sh`）がエンジンを止めます。TP=2のpoolは窓1本とcacheの残りです。3.10.0の受け入れでは、Jammed XSFP4はmodelが小さいので14 GiBで窓3本、6,147 page（38.27 GiB）を取りました。3.12.0の受け入れでは16 GiBでも窓3本、6,171 page（38.42 GiB）を取り、そのエンジンの計画は窓をslotより先に置いたので、prompt cacheが保持したstateは32のうち8で、動いているstreamどうしが追い出し合うとエンジンが警告しました。`cluster.sh` のlabelの後に `--prompt-cache-gib 6` を足すと、32全部と窓2本、5,525 page（34.40 GiB）が入り、decode検査のtokenは同じでした（[エンジンのflag](docs/configuration.ja.md#エンジンのflag)）。slotを先に置く3.16.0の受け入れでは、余地41.8 GiBに32全部と窓2本とcacheの残り、5,505 page（34.27 GiB）が入り、警告も `--prompt-cache-gib` もなく、decode検査のtokenは同じでした。3.9.0〜3.11.xのimageはTP=3で14 GiBを残すので、メモリを多く報告するホストでは、rankのファイルの `TENSORFOLD_MEMORY_RESERVE_GIB=16` でpoolを窓2本に保てます。

**TP=2を1,048,576にする理由。** BF16のKVは、tokenあたり2.x系のFP8のcacheの約2倍のメモリを取ります。3.8.xまではstreamの窓がまるごとmodelの横に置かれたので、TP=2の窓は245,760 token、3.5.0からはXSFP4で524,288 tokenまででした。KVのpageでは窓はpoolのpageで、streamの本数によりません：512行のpageを2,052（12.77 GiB）でモデルの上限の1,048,576 token全部が入り、3.16.0の受け入れでは1,035,295 tokenのpromptがJammed XSFP4 NZ5で760.0秒で最初のtokenを返し、合言葉を全部見つけました。3.16.0から既定のJammed XSFP4 NZ5では、その受け入れで `config/tp2.env` の9 GiBが余地23.1〜23.3 GiB・2,948〜2,982 pageになり、窓とprompt cacheの残りが入りました。rank 0のホストの `MemAvailable` は起動後に9.1〜9.4 GiB、検査が走っている間は8〜9 GiBでした。起動の計画が残す9 GiBより少なく、memory guardの5 GiBより3 GiB上で、3.12.0の受け入れのJammed XSFP4も最低は8 GiBでした。3.12.0〜3.15.0で既定だったJammed XSFP4では、3.12.0の受け入れで、エンジン自身のreserve 12.3 GiBが余地20.0 GiB・2,451 page（窓とprompt cacheの残りの一部）、9 GiBが余地23.2〜23.3 GiB・2,961〜2,981 pageで、rank 0の起動後の空きは9.1〜9.5 GiBでした。3.16.0のエンジンでは、rankのファイルの `CHECKPOINT` の行で配信して、9 GiBが余地23.4 GiB・2,995 page、起動後の空きは9.2 GiBでした。全rankのファイルの `CHECKPOINT` の行でTP=2に配信するXSFP4では、9 GiBが窓の場所を作ります：3.9.0のエンジンでは自身のreserve 12.2 GiBの余地が12.0 GiBで、窓のpageの12.77 GiBに足りず、9 GiBの余地は3.12.0の受け入れでも3.16.0の受け入れでも16.7 GiBで、2,059 pageと2,055 page、rank 0の空きは9.1 GiBと9.3 GiB、`TF_KV_SHARE=16` の状態は12でした（どの `--prompt-cache-gib` でも、この余地に入るのは12です）。どちらの受け入れでも、TP=2のXSFP4をエンジン自身のreserveでは起動していません。`TF_GLM_CHUNK_SOLO=4096` の広いpromptのpassは全rankでさらにメモリを取るので、この窓では切ります（[決定](docs/decisions.ja.md#窓とstream)）。全rankのファイルの `CONTEXT` で別の値を選びます：524,288ならreserveを戻せて、広いpassも入ります。

**効率coreにする理由。** エンジンは要求を回す間、全rankで2本のCPUのthreadを空回りさせ続けます。rank 0ではdecodeの間、他のrankではそれを待つ間です（上流1.1.2のエンジンより前は、他のrankは要求の無い間も空回りしました。#1053は、rank 0にstreamが無い間それらを眠らせます）：一つはGPUを待ち、もう一つはそのkernel時間から見てNCCLのものである見込みが高いthreadです。全coreでは、これらがCPUのthermal zone（GB10の7つのzoneのうち5つ）を温めました：約6,000 tokenのpromptの後の1,024 tokenの返答を40本続けると、3.0.0のエンジンでは、TP=2でrank 0の最も熱いzoneが94.7 °Cに達し、熱の見張りが7本目でエンジンを止めました。3.1.0のエンジンは全coreでも効率coreと同じ1,535秒で40本を終えましたが、rank 0のホストは93.0 °Cに達し（止める温度まで1 °C）、効率coreでは74.9 °Cでした。全coreで2つの要求を同時に回すと88.5 °Cでした。熱の待ちはprompt chunkの合間に働くので、これを抑えられません。3.0.0のエンジンでは、効率coreで40本の返答がそのzone 85.1 °Cで終わり、rank 1のホストは約70 °Cではなく57〜63 °Cで待ちました。その代わり速さの1〜3%を失い、起動は約25秒長くなりました（[3.0.0の測定値](docs/measurements.ja.md#300)）。熱の帯を下げる（86/82/87）と、待ったpromptが26〜89%遅くなり、1,048,576 tokenのpromptの最高温度は下がりませんでした。空回りせずに眠るCUDAのcontextはdecodeが12%遅く、もう一つのthreadは空回りしたままでした。1.1.1から、上流の[runbook](https://github.com/ashhart/TensorFold/blob/v1.2.10/RUNBOOK.md#gb10-cpu-pinning-for-long-cuda-runs)もこれらの測定からGB10の各rankに同じcoreを挙げています。`CPUSET=` でcontainerに全coreを与えます。

## 設定

配信は三か所で決まります：各ホストのrankのファイル（`serve.sh` が読む）、制御機のclusterのファイル（`cluster.sh` が読む）、`create_container.sh` の環境です。二つのファイルは [`examples/`](examples/) から写して自分の値に直し、Gitには入れないでください。rankのファイルの行はリリースの `config/tp*.env` より強く、空の値は、数や語の設定のほとんどでunsetと読まれ、既定の値になります（[空の値](docs/configuration.ja.md#rank-0のserver)）。on/offの設定は `1` か `0` だけを取り、空の値では起動が止まります。よく変える設定は、窓（`CONTEXT`）、同時にdecodeする要求（`PARALLEL`）、textだけ（`VISION=0`）、待ち受けとそのkey（`HOST`・`API_KEY_FILE`）、containerのcore（`CPUSET`）です。

[設定](docs/configuration.ja.md)は全ての設定を、それぞれの既定と読むrankとともに挙げます：rankのファイル、`serve.sh`、エンジンのflagと環境変数、NCCL、clusterのファイル、container、道具、lockのものです。エンジンはその多くを起動時にrankの間で比べ、違えば起動を断ります。既定以外の値は、その頁が名指すものを除き、3.x系の受け入れが測った範囲の外です。[上流自身のrecipe](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md)を越えてこの構成でできることは、写せる行の形で[チートシート](docs/cheatsheet.ja.md)にあります。

## API

rank 0がエンジンのHTTP APIを出します。受け入れで使ったもの：

- **`/v1/chat/completions`**：streamとそれ以外、toolつきで、[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)（このリポジトリの中継で、エンジンのものではありません）越しと直接。
- **構造化出力**：`response_format` の `json_object` か `json_schema`、`tool_choice` の `required` か名指しの関数。エンジンはこれをGLMのtoolのmarkup（`<arg_key>`、`<arg_value>`）のgrammarにします。どちらもimageが持つ `libtfgrammar` が要ります。grammarと必須のtool呼び出しを組み合わせた要求は400で断ります。
- **`prompt_logprobs`**：streamでない `/v1/completions` で、promptのtokenのlog確率を、それぞれ最大20の候補つきで。NLLの検査がこれを使います。このような要求はprompt cacheから再開しません。
- **思考**：`reasoning_effort` をtop levelか `chat_template_kwargs` で。`none` で思考を切り、effortを指定しない要求は `high` になります（[配信の既定](#配信の既定)）。思考を切った要求にはこの既定は効きません（[`REASONING_EFFORT`](docs/configuration.ja.md)）。streamでは `reasoning_content` と `content` は別々のdeltaで届きます。
- **`"draft": false`**：要求のbodyに入れると1 roundに1 tokenずつdecodeします。draftした応答が一致すべきserialの基準です。
- **応答のblock**：`tensorfold`（`token_sha256`＝推論を含む応答のtoken idのhash、`prefill_seconds`、`time_to_first_token`、`tokens_per_second`、`sampling`、`drafts`）と `speculative`（`rounds`、`drafted`、`accepted`、`acceptance_rate`、`tokens_per_round`）。prompt cacheから再開したtokenは `usage.prompt_tokens_details.cached_tokens` に入ります。応答はtoken idも熱の待ちの時間も運びません：待つごとの秒数はrank 0のlogの `heat_wait_s` の行にあります。
- **`/health`**（`live`：接続、待っている要求、直近の数秒のdecodeとprefillの速さ）、**`/v1/models`**、**`/tokenize`**、**`/metrics`**（Prometheus。decodeのroundやクライアントの切断を含む）。
- **停止**：クライアントの切断かstop文字列で応答が終わります。rank 0はroundの合間に接続を確かめ、他のrankはrank 0が送る段だけを走らせます。

エンジンは `/v1/responses` とAnthropicの `/v1/messages` にも、同じchatの経路で答えます。受け入れではこれらを確かめていません。GLMのCUDAのエンジンでは、生成したtokenの `logprobs` と `top_logprobs`（400）、音声のpart（400）、`--vision` 無しで起動したとき（rankのファイルで `VISION=0`）の画像と動画のpart（400）、`/v1/decisions`（400）を断ります。

## 2.x系との違い

| | 2.x（TensorFoldのPythonのエンジン） | 3.x（TensorFoldのネイティブエンジン） |
|---|---|---|
| エンジン | TensorFold 0.6.5のBIZ版。PythonとTritonのkernelで、kernelは実行時にcompile | TensorFold 1.2.10のBIZ版（3.0.0は1.0.12、3.1.0と3.2.0は1.1.1、3.3.0〜3.5.xは1.1.2、3.6.0と3.7.0は1.1.3、3.8.xは1.1.5、3.9.0〜3.11.xは1.2.1、3.12.0〜3.15.0は1.2.7）。ZigとCUDAで、kernelはbinaryの中 |
| 出力の反復性 | エンジンの契約として、draftした応答はserialと同じ、再開したpromptは最初からと同じ、chunkの切り方で結果が変わらない | draftした応答はserialと同じで、起動はtoken idを繰り返す。tokenは2.x系のものと違う（別のkernel、BF16 KV）ので、系列の間はNLLで比べる |
| KVと窓 | latentとindexのkeyをFP8。TP=2で300,000 token、TP=3で1,048,576 | BF16をKVのpageに。どのTPでも1,048,576 token（TP=2は3.8.xまで524,288） |
| 同時の要求 | 1 | TP=2で4、TP=3とTP=4で8。decodeのroundとKVのpoolを分け合う（3.8.xまでは既定で1） |
| prompt cache | 8本、3 GiB（`TF_GLM_CACHE_*`） | KVのpoolのpageの上の状態、TP=2で最大16、TP=3とTP=4で最大32（3.8.xまではその横のstore、最大16 GiB） |
| 画像入力 | 受ける（`VISION=1`） | 受け、動画も（`VISION=1`、既定） |
| 公開したAXLの重み | 任意で使える | 配信しない（3.6.0から） |
| 構造化出力、必須のtool呼び出し | 受ける。imageにxgrammar | 受ける。imageにxgrammarの `libtfgrammar`。必須のtool呼び出しはGLMのmarkupで |
| `prompt_logprobs` | 受ける | streamでない `/v1/completions` で受ける |
| `clear_thinking` | 従う | 3.8.0から従う（上流1.1.5。[設定](docs/configuration.ja.md#rank-0のserver)） |
| 応答の欄 | `tensorfold` に `accepted`・`drafted`・`rounds`・`cached`・`prefill_s`・`heat_wait_s`・`sha256` | `tensorfold` と `speculative`（上記）。cacheしたtokenは `usage` に。熱の待ちはlogだけ |
| 熱の設定 | `TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW`・`TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`・`TF_HEAT_LOW`、同じ帯。天井なし |
| XSFP4のcheckpoint | 配信しない | TP=3とTP=4で既定（3.4.0から3.11.xまではどのTPでも） |
| Jammed XSFP4のcheckpoint | 配信しない | 3.10.0からrankのファイルの1行で選べる（3.12.0〜3.15.0はTP=2で既定） |
| Jammed XSFP4 NZ5のcheckpoint | 配信しない | 3.16.0からTP=2で既定 |
| NVIDIAのNVFP4のcheckpoint | 固定したcheckpoint | 配信しない（3.6.0から。3.5.xまでは選べた） |
| imageとcontainer | `glm53-tf`、extensionをcontainerごとにbuild（`build_ext.sh`） | `glm53-tf3`、ホストでは何もbuildしない |
| containerのcore | 全core | `CPUSET` が別に言わなければ効率core |
| tool引数ゲート | エンジンの前のゲート | 同じゲート、この系列の写しを `v3/` から起動。3.11.0からはエンジンに1手番1つのtool callを求める |

二つの系列のcontainerはどちらも全GPUを要求するので、エンジンは一度に一つの系列だけを動かします（[運用](docs/operations.ja.md#ホストを2x系へ渡す)）。

## リリースでの測定値

**3.16.0**（2026-11-19、エンジン `2a674b55`、上流1.2.10そのもの、image `glm53-tf3:3.16.0`）。エンジンはこの系列のcommitを持たない上流1.2.10で、TP=2の既定のcheckpointはJammed XSFP4 NZ5です。TP=3とTP=4はXSFP4のままです（[checkpoint](#checkpoint)）。リリースのimageを、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動しました。rankのファイルには、名指した所のほか `CHECKPOINT` も `CONTEXT` も書いていません。TP=2は `tp2-04-05` のexampleの対（参照機の4台のリングのうちの2台）で回しました。3.12.0のTP=2は `tp2-rank*` のexampleの対だったので、この表のTP=2の速さは[3.12.0の表](docs/measurements.ja.md#3120)と並べません。既定のTP=2のJammed XSFP4 NZ5では、全検査の起動、decode検査のhashと `bench --kinds edit` の返答を同じく返した2回目の起動、`PARALLEL=` を空にした起動、rankのファイルで `TF_GLM_INDEX_CUDA=0` と `TF_GLM_DSEL=0` にした起動（decode検査のtokenは同じ）、同時の要求の起動、promptの点と構造化出力の検査をもう一度回した起動です。TP=2のXSFP4では、rankのファイルにその `CHECKPOINT` の行を足した1回の起動で、decode検査、`bench` のdecode・edit・prefill、199,307 tokenと1,035,295 tokenのprompt、ゲート越しのtool-eval-benchです。TP=2のJammed XSFP4では、その `CHECKPOINT` の行を足した1回の起動で、decode検査、`bench` のdecode・edit・prefill、NLLです。既定のTP=3のXSFP4では、全検査の起動、2回目の起動、1,035,295 tokenのpromptを取り直した起動、ゲート越しのtool-eval-benchの起動です。TP=3のJammed XSFP4では、その `CHECKPOINT` の行を足した1回の起動で、decode検査と `bench` のdecode・edit・prefillです。TP=4のXSFP4では、参照機の4台のリングで、tool-eval-bench以外の全検査の起動、2回目の起動、rankのファイルで `TF_GLM_INDEX_CUDA=0` にした起動と `TF_GLM_DSEL=0` にした起動です（長いpromptの返答のhashは既定と同じ）。decode検査のhashと `bench --kinds edit` の返答は、TP=2とTP=3のXSFP4、両TPのJammed XSFP4で[検証](docs/validation.ja.md)の基準値と同じで、NLLも回した所では同じです。TP=4は3.12.0のものと同じです。Jammed XSFP4 NZ5の値は新しく、[その節](docs/validation.ja.md#jammed-xsfp4-nz5)の基準値になりました。199,307・499,254・1,035,295 tokenのpromptの合言葉は、どのTPでもすべて見つかりました。見張りが止めた起動はありません。TP=2とTP=4では熱で待った起動は無く、ホストの熱の見張りがclockを下げた事もありません。TP=3は昼に回しました：499,254 tokenのpromptが熱で6秒、1,035,295 tokenのpromptが14秒待ち（取り直しでも同じ）、長い方のpromptの途中で、熱の見張りがrank 0のホストを2,200 MHzから2,000 MHzに下げました（2回とも）。表のその行のTP=3の2つの数はこの待ちを含みます。夜に取った3.12.0の数には待ちがありません。draftありのdecodeの速さは各checkpointが自分で書いた返答の上の数で、checkpointの間では比べられません。

| 3.16.0 | TP=2、Jammed XSFP4 NZ5 | TP=2、XSFP4 | TP=3、XSFP4 | TP=4、XSFP4 |
|---|---|---|---|---|
| 起動（秒）：全検査の起動 / 2回目の起動 | 53 / 54 | 118 | 114 / 56 | 114 / 48 |
| decode検査 count / prose / code（tok/s） | 51.43 / 35.99 / 42.73 | 51.76 / 34.29 / 45.20 | 72.22 / 47.24 / 62.52 | 71.31 / 56.40 / 72.48 |
| MTPの受理長、同じタスク | 3.723 / 2.097 / 2.920 | 3.995 / 1.860 / 3.290 | 4.163 / 2.018 / 3.453 | 3.376 / 2.052 / 3.422 |
| `bench --kinds decode`（tok/s、中央値） | 54.06 | 57.80 | 77.34 | 89.85 |
| `bench --kinds edit`（tok/s、中央値） | 142.16 | 144.34 | 193.64 | 245.13 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,504.4 | 1,507.6 | 1,949.8 | 1,867.6 |
| 199,307 tokenのprompt（秒） | 133.6 | 133.0 | 103.1 | 106.6 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（秒） | 345.8 / 760.0 | — / 760.6 | 270.3 / 605.0（上の熱の待ちを含む） | 272.9 / 587.3 |
| 約93,000 tokenのpromptを3秒で切った後、次の要求が答えるまで（秒）、切らないpromptの最初のtokenとの比べ | 2.87（63.6） | — | 1.60（48.9） | 1.69（50.6） |
| teacher-forced NLL、ja / en / code / math | 2.5517 / 2.9273 / 1.3136 / 0.6200 | — | 2.5369 / 2.9244 / 1.3098 / 0.6224 | 2.5262 / 2.9140 / 1.3083 / 0.6248 |
| tool-eval-bench 3.0.0、3.11.0のゲート越し / ゲートなし | 93 / 93 | 93 / — | 93 / — | — |
| 化けた文字のある日本語と韓国語の答え、temperature 0 / sampled | 0 / 0 | — | 0 / 0 | 0 / 0 |
| 6,000 tokenのpromptの後の最大1,024 tokenの40の返答（秒、rank 0のホストの最も熱いzone） | 1,225.6、76.8 °C | — | 900.2、87.7 °C | 793.2、74.6 °C |
| 起動の中で最も熱いzone、rankごと（°C） | 89.1 / 89.0 | 89.2 / 89.1 | 92.7 / 91.6 / 90.2 | 82.5 / 84.9 / 83.0 / 85.4 |
| 最も低い `MemAvailable`、rankごと（GiB） | 8 / 9 | 8 / 9 | 15 / 17 / 22 | 13 / 14 / 14 / 14 |

- **loadの行。** rank 0のloadの行は、TP=2でJammed XSFP4 NZ5とJammed XSFP4が84.79 GiB、XSFP4が91.37 GiBのmodel、TP=3で64.11 GiB、TP=4で47.80 GiBを示します。poolはTP=2で窓1本とprompt cacheの残り、Jammed XSFP4 NZ5で512行のpageを2,948〜2,982、Jammed XSFP4で2,995、XSFP4で2,055、TP=3で窓2本と残りの4,745〜4,766 page、TP=4で窓3本と残りの8,006〜8,036 pageを取りました。保持する状態のslotはTP=2で3.6 GiB、TP=3で5.3 GiB、TP=4で4.0 GiBを取り、全部が入りました。TP=2のXSFP4だけは、余地に入る12（16のうち）です。`PARALLEL=` を空にするとエンジンはTP=2でstreamを8本取り、2,712 pageで、保持する16状態が1本あたり4を下回るという警告を出しました。TP=2とTP=4のrank 0の `kv pool idle` の行はどれも合っていました：約束されたpageは0で、空きのpageとstoreのpageでpoolの全部です。
- **保持する状態のslotが先。** 上流1.2.10（#3125）から、起動の計画は、エンジン自身の窓の先の窓よりslotを先に置きます。TP=4のpoolは窓3本と32のslot全部になりました。3.12.0では窓4本（8,198〜8,215 page）で、保持は24状態、エンジンの警告つきでした。TP=3のJammed XSFP4は窓2本と32全部（5,505 page）で、3.12.0では窓3本と8でした（[TP=3で16 GiBにする理由](#配信の既定)）。
- **メモリ。** TP=2のJammed XSFP4 NZ5では、rank 0のホストの `MemAvailable` は起動後に9.1〜9.4 GiB、検査が走っている間は8〜9 GiBでした。起動の時にsystemに残す9 GiBを下回り、memory guardの5 GiBより3 GiB上です（[TP=2を1,048,576にする理由](#配信の既定)）。TP=3では起動後に16.5〜16.6 GiB、最低は15 GiBで、16を下回りました。ホストのtelemetryでは15.63 GiB、3.12.0の最低は15.99 GiBです（[TP=3で16 GiBにする理由](#配信の既定)）。
- **TP=3とTP=4のdraftありのdecode。** tokenは同じで、TP=3のdecode検査の `count` は72.22 tok/s（3.12.0は57.94、3.9.0は65.67）、`bench --kinds decode` は77.34（63.23、68.52）でした。TP=4は71.31（3.12.0は58.31）と89.85（74.14）、40の返答はTP=3で900.2秒（3.12.0は1,124.5）、TP=4で793.2秒（985.1）です。3.12.0の表は、`--mtp-confidence` の下でTP=3のdraftありのdecodeが3.10.0より遅いと書いていました。上流の直し（[TensorFold #2864](https://github.com/ashhart/TensorFold/pull/2864)）は1.2.8からリリースに入っています。1.2.7から1.2.10の間の変更それぞれの効きは、分けて測っていません。
- **TP=4のdecodeの1 stepを、promptの長さとstreamの数ごとに。** draftを切って（`"draft": false`、greedy、思考なし）、同時に1・4・8本のstreamが、保持した同じprefixから再開する4,096・65,536・262,144・1,040,384 tokenのpromptの上で、256 tokenずつdecodeしました。cellの値は、全streamがdecodeしている間の、streamごとのtokenとtokenの間の時間を全streamぶん集めた中央値を、3回の繰り返しでさらに中央値にしたものです（ms、小さいほど速い）。表は、3.16.0の2回の起動を3.12.0の2回と並べたものです。同じ4台ですが1週間離れていて、交互には回していません。どのstreamの返答も、4回の起動でtokenのhashが同じでした。12 cellのうち8つが速く、2つがopen、2つが遅くなりました。遅いのは65,536 tokenの1本（+1.21%）と8本（+0.37%）で、3.16.0の2回とも遅く出ました。262,144 tokenから上は全cellが速く、差は1.09%から11.11%です。判定の決まりは次のとおりです。3.16.0の2回の平均が3.12.0の2回の平均より長く、その差が3.12.0の2回の幅と0.25%の両方を超えるcellを「遅い」、3.12.0の2回のどちらよりも短いcellを「速い」、どちらよりも長いが差がそこまでではないcellを「open」とします。3.12.0の2回の間に入ったcellはありませんでした。起動の違いは、エンジンのほかに窓の値付けにもあります。3.16.0の2回は `TF_GLM_EXPERT_FORM=factored` を名指していて、受け入れの中の先の起動でエンジンが名指しの形に取り直した値付け（`40.24 ms at 1 row, 37.00 at 4, 97.16 at 32`）の上で走りました。3.12.0の2回は `25.33 ms at 1 row, 37.47 at 4, 102.53 at 32` の上です。形を名指さなかった受け入れの最初の起動は、`25.36 ms at 1 row, 38.39 at 4, 102.85 at 32` と測りました。

  | promptのtoken × stream | 3.12.0の2回（ms） | 3.16.0の2回（ms） | 3.16.0の平均の、3.12.0の平均との差 | |
  |---|---|---|---|---|
  | 4,096 × 1 | 26.61 / 26.56 | 26.57 / 26.71 | +0.21% | open |
  | 4,096 × 4 | 48.10 / 48.13 | 48.20 / 48.20 | +0.17% | open |
  | 4,096 × 8 | 72.39 / 71.97 | 71.94 / 71.98 | −0.31% | 速い |
  | 65,536 × 1 | 26.99 / 26.99 | 27.37 / 27.26 | +1.21% | 遅い |
  | 65,536 × 4 | 49.06 / 49.11 | 48.97 / 49.07 | −0.14% | 速い |
  | 65,536 × 8 | 72.28 / 72.22 | 72.53 / 72.50 | +0.37% | 遅い |
  | 262,144 × 1 | 28.12 / 28.11 | 27.73 / 27.89 | −1.09% | 速い |
  | 262,144 × 4 | 51.74 / 52.42 | 50.40 / 50.29 | −3.34% | 速い |
  | 262,144 × 8 | 76.41 / 76.79 | 73.27 / 73.24 | −4.37% | 速い |
  | 1,040,384 × 1 | 32.39 / 32.28 | 30.81 / 30.84 | −4.68% | 速い |
  | 1,040,384 × 4 | 69.14 / 69.24 | 62.95 / 63.00 | −8.98% | 速い |
  | 1,040,384 × 8 | 112.14 / 112.20 | 99.58 / 99.83 | −11.11% | 速い |
- **1.2.7の後の上流の既定。** 1.2.9から、promptのDSAのindexerは専用のkernelで走り（`TF_GLM_INDEX_CUDA`、#3159）、選びをdeviceの上でします（`TF_GLM_DSEL`、#2722）。どちらも既定です。TP=4の1,035,295 tokenのpromptの最初のtokenは、専用のkernelで587.3秒と578.7秒、`TF_GLM_INDEX_CUDA=0` で624.9秒で、返答は同じでした。1.2.10は、buildの最初のdraftありのloadでexpertの2つの形を測り、速い方を保ちます（`TF_GLM_EXPERT_FORM`、#3151）：XSFP4とJammed XSFP4 NZ5ではどのTPでも `factored`、TP=3のJammed XSFP4では `classic` を選びました。TP=4の2回目から後の起動と、TP=2のJammed XSFP4の起動は、rank 0のファイルで `factored` を名指しました。名指すと窓の値付けを取り直します（[設定](docs/configuration.ja.md#各rankが読み比べないもの)）。
- **Jammed XSFP4 NZ5とBF16。** 全検査の起動は、[checkpoint](#checkpoint)の表の128文書を採点しました：TP=2で 92.89% / +1.08% / 0.0463 で、Jammed XSFP4とXSFP4の間です。TP=3のXSFP4は、その表の3つの数をもう一度同じ値で返しました。
- **Jammed XSFP4。** rankのファイルに `CHECKPOINT` の行を足した、各TPの1回の起動です。TP=2ではpoolが2,995 page、rank 0の起動後の空きは9.2 GiBで、`bench` はdecode 57.45 tok/s・edit 145.62・prefill 1,525.4、expertはrank 0のファイルで名指した `factored` でした。TP=3では5,505 page、空き16.5 GiBで、76.54・194.41・1,956.0、expertはエンジンが選んだ `classic` でした。decode検査のhashは[検証](docs/validation.ja.md#jammed-xsfp4)の値と同じです。
- **切ったpromptの後の要求。** 3秒で切った約93,000 tokenのpromptの後の次の要求は、TP=2で2.87秒、TP=3で1.60秒、TP=4で1.69秒で答えました。どれも1回の到着の数で、promptのpassのどこに来るかで大きく動きます。
- **tool。** 1手番1つのtool callを求める3.11.0の[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)越しで、Safety Gateは3つの起動とも合格しました。TP=2のJammed XSFP4 NZ5はTC-11・TC-39・TC-57・TC-67が部分点でTC-62・TC-68・TC-69を落とし、TP=2とTP=3のXSFP4はTC-11・TC-39・TC-67が部分点で同じ3つを落としました。ゲートなしではJammed XSFP4 NZ5は同じ93点で、Safety GateはTC-51で不合格でした：`create_calendar_event` の結果を待たずに、同じ手番で `send_email` を呼びます。その回はTC-11とTC-52が部分点で、TC-43・TC-62・TC-68も落としました。ゲートは1手番1つのtool callを求めるので、ゲート越しでは合格します。
- **TP=3の熱。** 上の待ちのほか、thermal watchは、1,035,295 tokenのpromptの取り直しでrank 0のホストに94.0 °Cを読みました。エンジンを止める線ですが、止める条件の2回続きにはなっていません。全検査の起動では92.7 °Cでした（どちらも昼）。夜に回した3.12.0の起動は91.3 °Cでした。
- **既知の振る舞い。** TP=3とTP=4では、stop文字列の要求は上限まで続きます。TP=3では、短いgreedyの返答が自分のhashを持ちます。3.9.0・3.12.0と同じです（[検証](docs/validation.ja.md#xsfp4)）。

前の版の値は[前の版の測定値](docs/measurements.ja.md)にあります。

## 制限

- **Jammed XSFP4には `csf0_v1` のkernelが要ります。** 形はこの系列のもので、kernelはこの系列のエンジンが3.10.0から、上流のリリースが1.2.3から持っています（#2041、2026-11-04から上流のmainにある）。vLLM、他のNVFP4のloader、そのkernelを持たないエンジンは読めず、3.8.0のエンジンは読み込みの時に名前を挙げて断ります。blockのスケールが粗いので、返答はXSFP4と違います（[checkpoint](#checkpoint)）。
- **Jammed XSFP4 NZ5には `NVFP4_NZ5` のkernelが要ります。** kernelは上流のリリースが1.2.10から（#2894）、この系列のエンジンが3.16.0から持っています。Jammed XSFP4は読めてもこのkernelを持たないエンジンは、読み込みの時に名前を挙げて断ります（3.10.0のimageで確かめた）。同じbyteをJammed XSFP4として読むと、+5がすべて0になるからです。vLLMと他のNVFP4のloaderは読めません。codeの読み方が違うので、返答はこのcheckpointのものです。3.16.0の受け入れが配信したのはTP=2だけです（[checkpoint](#checkpoint)）。
- **TP=2で4本、TP=3で8本。** それを超える要求はstreamを待ちます。streamは1つのKVのpoolを分け合います。既定のcheckpointでは、窓いっぱいのstreamがTP=2で1本分、TP=3で2本分、TP=4で3本分です。受け入れの各起動のpage数は[loadの行](#リリースでの測定値)にあります。長い会話が同時に何本も並ぶ負荷は測っていません（[配信の既定](#配信の既定)）。
- **画像と動画はエンジンの制限の中で。** 画像は1要求に最大4枚で、送られた履歴にある画像を全部数えます（前のturnを画像ごと送り直すclientはそこに届きます）。4枚で4,096 tokenを分け合い、1枚10 MiB・1要求20 MiBまで。PNG・JPEG・WebPのdata URLで、GIFと動く絵は断ります。動画はuserのmessageだけで、1要求に2本（1本16 MiB・合わせて20 MiB・1時間まで）、1秒に2 frameで最大256 frameを取り、16,384 tokenを分け合います。0.5秒より短いclipは断ります。画像と動画のtokenは窓から取られます。HTTPSのURLには `serve.sh` が渡さない `--vision-urls` が要ります。音声のpartは400で断ります。
- **生成したtokenのlog確率は無い。** `logprobs` と `top_logprobs` は400で断ります。`prompt_logprobs` はstreamでない `/v1/completions` でだけ配信します。
- **要求を回す間、どのrankも2つのCPUのcoreを空回りさせ続けます。** rank 0はdecodeの間、他のrankはそれを待つ間です（上流1.1.2のエンジンからは、#1053により、rank 0にstreamが無い間は他のrankは眠ります）。containerの既定のcoreは、少しの速さと長くなる起動と引き換えに、CPUのzoneを熱の見張りが止める温度より下に保ちます。全coreでは、返答の長い連続がその温度に達するか、その手前まで来ました（[効率coreにする理由](#配信の既定)）。
- **BF16 KV** は、GiBあたり2.x系のFP8のcacheより短い窓しか持てません。エンジンには選んで使うFP8のlatent cache（`--kv-cache fp8`）がありますが、上流は品質と機器での確かめをまだとしていて、`serve.sh` も指定しません。これはstreamごとに窓を持つので、リリースの `TF_KV_SHARE` があるとエンジンは起動を断ります：空の `TF_KV_SHARE=` と1本のstreamが要ります（[チートシート](docs/cheatsheet.ja.md#tp2のfp8のlatent-cache)）。TP=2で一度だけ試しました（XSFP4、vision towerあり、両rankのファイルに `CONTEXT=1048576`、`cluster.sh` のlabelの後に `--kv-cache fp8`）：1,048,576 tokenの窓に7.13 GiBのstreamが1本、4.7 GiBのprompt cacheと並んで入り、1,035,295 tokenのpromptは最初のtokenまで1,130.6秒で3つの合言葉を全部見つけ、199,307と499,254 tokenのpromptはprefillが約5%長くかかり、NLLの組は+0.14%（文ごとの差の区間は0をまたぐ）、decode検査のtokenはBF16のcacheと違いました。
- **ConnectX-7のリンクでつないだ2台、3台か4台**：2台と3台は1.x系・2.x系と同じで、3.12.0からの4台は試験的に、switchなしのリングでTP=3の値のまま、その大きさでは詰めていません。他のrank数や他の機材は測定の範囲外です。

## リポジトリの構成

3.x系のファイルは `v3/` にあります。imageはライセンスのあるcheckoutのルートからbuildし、Pythonの道具は `v3/` から `python -m glm53_tf <command>` で動かします。ホストのツールと、全系共通のホストとfabricの文書はcheckoutのルートにあります（[`host/`](../host/README.ja.md)、[`docs/`](../docs/README.ja.md)）。

```
v3/
  README.md         このページ（各 .md の隣に .ja.md）
  SETUP.md          配備の手順書
  CHANGELOG.md      3.x系のリリース。v3.* のtagがその節を公開する
  glm53_tf/         Pythonの道具：download・verify-download・tool-gate・
                    decode-check・decode-divergence・score-nll・bench・long-input・mojibake
  config/           tp2.env、tp3.env、tp4.env（TPごとの配信の既定）、xsfp4.lock.json（XSFP4）、
                    jammed.lock.json（Jammed XSFP4）、nz5.lock.json（Jammed XSFP4 NZ5）、
                    engine.lock.json（エンジンのcommit、Zigのcompiler、xgrammar）、nll_set.json（NLL採点セット）
  requirements/     huggingface.lock.txt：ダウンロードとその検証に使うHugging Faceのclient
  docker/           Dockerfile：image。エンジンは ENGINE_REF で固定
                    Dockerfile.build：build用のimage。エンジンをbuildし、そのGPUのテストを回す
  scripts/          create_container.sh  各ホストの配信用container
                    cpuset.sh            そのcore（CPUSET）：既定は最大周波数の最も低いもの
                    serve.sh             1 rank、配信の既定つき
                    cluster.sh           操作する機械から全rankを起動・停止・状態確認
                    hostwatch.sh         メモリの見張り（MemAvailableが5 GiBを切るとエンジンを止める）
  examples/         参照機のrankのファイルとclusterのファイル（TP=2・TP=3・TP=4。4台のリングの
                    NCCLのgraphと、4台のリングを2組の対にするTP=2も）
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
- **XSFP4・Jammed XSFP4・Jammed XSFP4 NZ5は本リポジトリの管理者のcheckpointです。** NVIDIA Open Model Agreementの下のFP4-Localの派生物で、NVIDIAやZ.aiのリリースではありません。
- **エンジンはこの系列による上流のforkのリリースのbranchです。** 他の利用者にも役立つものは上流のTensorFoldへpull requestとして出し、残りはリリースのbranchが持ちます。3.16.0のbranchはこの系列のcommitを持たず、上流v1.2.10そのものです。上流がどのpull requestをどのリリースで取り込んだかは[決定](docs/decisions.ja.md)にあります。

## Next Action

各項目は、きっかけと、そのときこの系列がすることです。

- 3.3.0のエンジンは上流のpull request #1053（rank 0にstreamが無い間、待つrankが眠る。1.1.2に入った）を持つ。その後のリリースは効率coreで回したので、まだ開いている → containerにまだ効率coreが要るかを測り直す。
- XSFP4から何も借りず、MTP層も含めてBF16の重みから較正し直したJammed XSFP4の点が良く、受け入れも通る → lockをそのrevisionへ動かす。

## ローカルデータと開発

Gitに入れないもの（自分の拠点の値を入れたrankとclusterのファイルを含む）、ライセンス、開発への参加は[リポジトリのREADME](../README.ja.md#ローカルデータと開発)にあります。3.x系の変更は[CHANGELOG.ja.md](CHANGELOG.ja.md)にあります。

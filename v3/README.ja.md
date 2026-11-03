# GLM-5.3-Flash BIZ 3.x（TensorFoldネイティブ）

![GLM-5.3-Flash BIZ v3、XSFP4 × TensorFold：DGX Spark・GB10で動くZigとCUDAのネイティブ実装](assets/banner.webp)

[English](README.md) · [リポジトリの索引](../README.ja.md) · [配備の手順書](SETUP.ja.md) · [検証](docs/validation.ja.md) · [変更履歴](CHANGELOG.ja.md)

**GLM-5.3-Flash BIZ** は、DGX Sparkまたは互換のGB10機でGLM-5.3-Flashを配信します。3.x系はTensorFoldのネイティブエンジン、つまり[2.x系](../v2/README.ja.md)が動かすPythonのエンジンに代わったZigとCUDAのエンジンで、2台のTP=2または3台のTP=3で配信します。配信するcheckpointは[XSFP4](#checkpoint)か、3.10.0からrankのファイルの1行で選べる[Jammed XSFP4](#checkpoint)（routed expertがTP=2の各ホストで6.58 GiB少ない）です。XSFP4は、NVIDIAのGLM-5.3-Flash-FP4-Localの派生物、expertsを本リポジトリの管理者が量子化し直したものです。1.x系・2.x系が配信するNVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointは、3.5.xまでここでも選べました。各リリースのエンジンは、上流のTensorFoldの一つのリリースの上にbuildします（[何であるか](#何であるか)）。各リリースで何が変わったかは[変更履歴](CHANGELOG.ja.md)にあります。2.x系も並んで続きます。

**BIZ**は保守者の印で、リポジトリの意図を示す語です。意味することと意味しないことは[リポジトリのREADME](../README.ja.md#biz)にあります。

## 要約

- **状況。** 3.10.0は2つ目のcheckpoint、[Jammed XSFP4](#checkpoint)を足します。rankのファイルの `CHECKPOINT` の1行で、XSFP4と同じ速さで配信します。modelはTP=2の各ホストで6.58 GiB軽く、その分は空いたまま残ります。TP=3ではrank 0で4.50 GiB軽く、KVのpoolが窓3本分のpageを取ります。受け入れの全検査を両TPで回しました（[基準値](docs/validation.ja.md#jammed-xsfp4)）。XSFP4は既定のままで、リリースのimageは各TPの1回の起動で3.9.0のdecode検査のhashと編集の返答を返しました。3.9.0はエンジンを上流1.2.1の上へ移し、TP=2でもTP=3と同じくモデルの上限の1,048,576 tokenの窓を開き、配信の既定をTPごとに決めました：TP=2は1人のagentの長い会話のために4本のstream、TP=3は複数の人の同時利用のために8本です（[配信の既定](#配信の既定)）。リリースのimageを、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動すると、TP=2とTP=3の各2回の起動で3.3.0のXSFP4のdecode検査のhashと編集の返答を、さらに同じNLLを返しました。同時の返答は同じ要求の単独の返答と同じで、1,035,295 tokenのpromptを含めて長い入力の合言葉はすべて見つかりました（[リリースでの測定値](#リリースでの測定値)）。`mojibake` は、両TPで、temperature 0でもsampledでも、日本語と韓国語の答えに化けた文字を見つけませんでした（[マルチバイト出力](docs/validation.ja.md#マルチバイト出力)）。TP=3ではstop文字列の要求が上限まで走り、短いgreedyの返答が自分のhashを持ちます。どちらもそこに書いた既知の振る舞いです。[検証](docs/validation.ja.md)の基準値は、2026-11-03の参照機での3.9.0の受け入れで、visionのtowerを読み込んで決めたもので、そのうちdecode検査のhash・編集の返答・NLLは3.3.0のものと同じです。[Jammed XSFP4の基準値](docs/validation.ja.md#jammed-xsfp4)は3.10.0のものです。主張の範囲はここまでです。他のホストは同じ検査を回して受け入れます。
- **何であるか。** XSFP4かJammed XSFP4を、TensorFoldのネイティブエンジンの固定したcommitで一つのOpenAI互換endpointとして配信するための、build手順・起動の台本・受け入れ検査です。2台なら直結のConnectX-7リンクでTP=2、3台ならswitchなしのリングでTP=3です。公開している測定値はMSI EdgeXpert（MS-C931）で取りました。Macでは、TensorFoldが自身のMLXの重みでGLM-5.3-Flashを配信します（[Macでは](../README.ja.md#macでは)）。
- **反復性。** draftした応答はserialと同じで、起動は同じTPの前の起動のtoken idを出します。ネイティブエンジンのtokenはそれ自身のもので、2.x系のものではありません：kernelとBF16のKV cacheの丸めが違うので、二つの系列はtokenごとではなくteacher-forced NLLで比べます（[2.x系との違い](#2x系との違い)）。
- **構造化出力とpromptのscore。** JSON schemaつきの `response_format`、`required` か名指しの関数の `tool_choice`（GLM自身のtoolのmarkupで書く）、`/v1/completions` の `prompt_logprobs` は、1.1.1からGLMのCUDAのエンジンで上流のTensorFold自身のものです。この系列のpull request #1016・#1017・#1018の後に上流が書きました（[API](#api)）。
- **画像と動画。** chatの要求は、PNG・JPEG・WebPの画像と、H.264・HEVC・VP8・VP9・MPEG-4の動画をdata URLで持てます。rank 0にあるcheckpointのvision towerが、エンジンの `--vision` で読みます。`serve.sh` は既定でこれを渡します（[制限](#制限)）。
- **精度。** XSFP4とJammed XSFP4ではrouted expertはW4A16、他のprojectionはcheckpointが保存する形のままで、多くは8 bit、vision towerのMLPとmergerはNVFP4です（[checkpoint](#checkpoint)）。KVはBF16です（2.x系はFP8のKV cacheを持ちます）。NVIDIAのmodel cardは別のレシピ・別の機材でFP4-Localを測っており、その精度表はこの配信を表しません。この配信を表す数字は[検証](docs/validation.ja.md)にあります。
- **ライセンス。** コードとエンジンはApache-2.0、重みは運用者がダウンロードし、NVIDIA Open Model Agreement（XSFP4とJammed XSFP4、商用に使える）です。imageには構造化出力のためにxgrammar（Apache-2.0）、画像と動画のためにlibjpeg-turbo・libwebp（BSD系）とFFmpegのdecoder（LGPL-2.1）が入ります。配信の経路に非商用の条件はありません（[ライセンスの早見表](../README.ja.md#ライセンスの早見表)）。
- **未検証。** 画像と動画のURL（`--vision-urls`、無効）、長い会話が同時に何本も並ぶ負荷、他のrank数と機材（[制限](#制限)）。ハーネス連携（ZCode・Claude Code）、アプリケーション全体の品質と本番の信頼性。

## 何であるか

- **重み**：`Bizuayeu/GLM-5.3-Flash-XSFP4`（[`config/xsfp4.lock.json`](config/xsfp4.lock.json)）、選べば `Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4`（[`config/jammed.lock.json`](config/jammed.lock.json)）（[checkpoint](#checkpoint)）で、NVIDIAのGLM-5.3-Flash-FP4-Localと[Z.aiのGLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)から作られています。
- **エンジン**：TensorFoldのネイティブエンジン（`tensorfold-native`）。[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/3.10.0` として公開するBIZ版で、上流のTensorFold v1.2.1にこの系列の6つのcommitを足したものです。6つのcommitはJammed XSFP4の `csf0_v1` の形を専用の5つのkernelで読みます。その形を持たないcheckpointは上流の道をそのまま通ります。上流は2026-10-25にこの系列の最初のpull requestを取り込み、1.1.5はそれらを持つ最初のリリースでした。#1050はNVIDIAのGLM-5.3-Flash-FP4-Localを保存された形のまま読み、それと共に、experts以外にFP4-Localのtensorを持つXSFP4のcheckpointも読みます：各projectionの形をcheckpointの `MIXED_PRECISION` のレシピから見分け、MXFP8と128×128 blockのFP8のprojectionを保存の形のまま計算し、FP4-Localの圧縮したexpertのscaleを読み、float32のnormの重みをfloat32のまま保ちます。#1178はrank 0のNCCLのidをrankどうしの生存の線で他のrankへ送るので、TP=3は上流のbootstrapで起動し、3.6.0のリリースのbranchがそのために持っていたidのファイル（`TF_GLM_NCCL_ID_FILE`）とこの系列の二つのcommitは要りません。#1163と#1211は、各streamのKV cacheとエンジン自身のsequenceを一つのpoolのpageに置きます。1.1.5では3 rankで、1.1.6（#1322）からは2 rankでもです（[配信の既定](#配信の既定)）。3.9.0の既定はその後に入ったものを使います：promptがdecodeの横とrankの間で動く#1352・#1404（1.1.9）、`--mtp-confidence` とmultirank RoCEのwire（#1516・#1524、1.2.0）、`TF_GLM_KV_SHARE`（#1732、1.2.1）です。#1616と#1636（1.2.0）は重みを複数のthreadで読んで詰めるので、起動が短くなります。indexがmodelのfolderの中のfolderにあるshardを名指せること（FP4-LocalとXSFP4のindexに要る）は、1.1.3から上流自身のcodeにあり、3.5.xまでのリリースのbranchはpull request #1179のpatchとして持っていました。1.1.5から、serverはGLM-5.3のchat templateに `clear_thinking` を渡します（[設定](docs/configuration.ja.md#rank-0のserver)）。3.0.0〜3.2.0の熱の待ちの天井への見込み（`TF_HEAT_CEILING`）は無くなり、熱の待ちは上流の帯だけです（[配信の既定](#配信の既定)）。imageは一つのcommitに固定します（[`config/engine.lock.json`](config/engine.lock.json)）。
- **image**：[`docker/Dockerfile`](docker/Dockerfile)。エンジンはNVIDIAのCUDA 13.3.1のbuild用imageで、lockが名指すZigのcompiler（SHA-256で確かめる）がcompileし、`libtfgrammar` は固定したcommitのxgrammarのreleaseからbuildします。実行のimageはCUDA 13.3.1にNCCL 2.30.7とRDMAのuserspaceです。2つのbaseのimageはdigestで固定しています。`/usr/share/doc/tf3/ENGINE` がエンジンのcommitと各binaryのSHA-256を名指し、`/usr/share/doc/tf3/engine/` にエンジンのライセンスと表示があります。
- **起動**：[`scripts/`](scripts/) のshellの台本と、rankごとの環境ファイル一つ（[`examples/`](examples/) に参照機のファイル）。順番は[SETUP.ja.md](SETUP.ja.md)にあります。ホストでは何もbuildしません：kernelはbinaryの中にあります。
- **他のレシピ**：このリポジトリがTensorFoldの他のレシピから取ったものと、それらのlicenseは、2.x系の[表](../v2/README.ja.md#tensorfoldの他のレシピ)にあります。3.x系のTP=3のrankのファイルは、2.x系がMiaAI-LabのTensorFoldのレシピから取って測ったfabricの設定のうち二つ、4本のNCCLのchannelとsubnet-aware routingを持ち続けます（[決定](docs/decisions.ja.md#fabric)）。上流のTensorFold自身の、CUDAでのこのモデルのレシピは[GLM-5.3-Flash on CUDA](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md)です。

## 必要な環境

- **ホスト**：DGX Sparkまたは互換のGB10機を2台か3台（Linux ARM64、各128 GBの統合メモリ）。GPUで他の大きな仕事を動かさないこと。同じホストで1.x系か2.x系のserverが動いていれば先に止め、全GPUを要求する2.x系のcontainerも止めます（[ホストを2.x系へ渡す](docs/operations.ja.md#ホストを2x系へ渡す)）。
- **fabric**：RoCE v2のConnectX-7リンク。2台は直結、3台はswitchなしのリング（[3台をリングにつなぐ](../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。各portの2本のrailを両方使います。
- **ホストカーネル**：1.x系・2.x系と同じです。今のDGX OSの更新が入れるカーネルは、既定のままでは複数ノードのRoCEを壊すことがあり、参照機は `kho=off` で起動しています（[ホストカーネルと複数ノードRoCE](../docs/hosts.ja.md#ホストカーネルと複数ノードroce)）。
- **GPUクロック**は全ホストで上限を設けます（[GPUクロックの上限](../docs/hosts.ja.md#gpuクロックの上限)）。上限と温度の記録は[`host/`](../host/README.ja.md)が据え付けます。3.x系の数字は全部この上限の下で測りました。
- **Docker**：NVIDIAのGPU runtimeとRDMAデバイスが要ります（`/dev/infiniband` が無いホストでは、NCCLがsocketに落ちるので `create_container.sh` が断ります）。
- **disk**：全ホストにcheckpointを丸ごとと、image。XSFP4は178 GB、Jammed XSFP4は172 GBを取ります。
- **操作する機械**：全ホストへSSHでき、`cluster.sh` を動かす機械一台。
- **Python 3.11以上**：各ホストで、この系列の道具（[`glm53_tf/`](glm53_tf/)：ダウンロード、検証、tool引数ゲート、検査）を `v3/` から動かします（[手順書 §2](SETUP.ja.md#2-checkoutとcheckpoint)）。

## はじめ方

各段とその後に確かめることは[配備の手順書](SETUP.ja.md)にあります。以下はTP=2のときの骨組みです。全ホストで同じ、確認済みの `v3.*` のtagを使います。

```sh
# 一度だけ、ある1台の v3/ からその仮想環境で。その後cacheを他のホストへ写し、写しごとに検証する（SETUP §2）
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum-xsfp4 --wait

# 1台がimageをbuildし、他はそれを読み込む。image IDを比べる（SETUP §3）
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.10.0 .

# 各ホストで、checkoutのルートから（SETUP §4）
v3/scripts/create_container.sh glm53-tf3:3.10.0 ~/glm53-tf3
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

3.x系が配信するcheckpointは、3.4.0から既定のXSFP4か、3.10.0から選べるJammed XSFP4です。Jammed XSFP4はrouted expertを入力32個ごとのblockのスケールで合わせ直し、そのスケールを4分の1のメモリで持ちます。3.3.0まで既定で3.5.xまで選べたNVIDIAのNVFP4は、1.x系・2.x系のものです。全rankが同じものを配信します。

| | XSFP4 | Jammed XSFP4 |
|---|---|---|
| 重み | [`Bizuayeu/GLM-5.3-Flash-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4)（[`config/xsfp4.lock.json`](config/xsfp4.lock.json)） | [`Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4)（[`config/jammed.lock.json`](config/jammed.lock.json)） |
| 作り手 | 本リポジトリの管理者、NVIDIAの[`GLM-5.3-Flash-FP4-Local`](https://huggingface.co/nvidia/GLM-5.3-Flash-FP4-Local)（revision `76348ddb`）とZ.aiのBF16の重みから | 同じ。XSFP4の平滑化とBF16の重みから |
| routed expert | XSFP4、W4A16で配信：平滑化を重みに畳み込み、BF16の重みからNVFP4のblockを当てはめ直したもので、実行時にkernelが何も掛けません。MTP層のexpertも同じ。3〜44層はblockのスケールを可逆に圧縮して持ち（`csf_32x2_v1`、FP4-Localと同じ）、エンジンが読み込みの時にホストで元に戻します | NVFP4、W4A16で配信。XSFP4の平滑化のまま、3〜44層のblockのスケールを入力16個ごとから32個ごとにしたもの。行ごとのスケールはE4M3の16段に収まり、行に1つのbaseとblockごとの4 bitのoffset（`csf0_v1`）で、fileでもGPUでも同じ形で持つので、スケールのメモリは4分の1です。MTP層のexpertはFP4-Localのもの、block 16 |
| その他 | FP4-Localのtensorを保存の形のまま：MXFP8（dense MLP、KDA、`lm_head`、MTP層のattentionとshared expert）、128×128 blockのFP8（MLAとshared expert）、BF16（KDAの小さいprojection、MLAの `kv_b` とindexer、router、embeddings）、BF16とF32のnorm。vision towerはMXFP8とNVFP4 | XSFP4と同じ |
| TP=2・TP=3のrank 0のmodel（読み込みの行、KV cacheはpage） | 90.86・63.60 GiB | 84.28・59.10 GiB |
| このエンジンのTP=2でBF16の重みと比べた次token（128文書、144,285位置）：top-1の一致 / BF16に対するNLLの上がり / KLの下限 | 93.26% / +0.85% / 0.0431 | 92.78% / +1.35% / 0.0482 |
| 同じものをTP=3で | 93.30% / +0.85% / 0.0436 | 92.80% / +1.41% / 0.0483 |
| ライセンス | NVIDIA Open Model Agreement（FP4-Localの派生物。repositoryに `LICENSE` と `NOTICE`） | 同じ |
| ダウンロード（SETUP §2） | `download`・`verify-download`（ダウンロードの状況は `state/xsfp4` に） | `download --checkpoint jammed`・`verify-download --checkpoint jammed`（状況は `state/jammed` に） |
| rankのファイル | 何も要らない：`serve.sh` の既定（lockのrevision） | 全rankのファイルに `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-Jammed-XSFP4/snapshots/<lockのrevision>` の1行だけ |

各文書はtoken idとしてエンジンに送り、`prompt_logprobs` は20。KLの下限は、両方が確率を返したtoken（エンジンの上位20、BF16の上位20、本文のtoken）を1つずつ数え、残りを1つの塊として数えます。全語彙のKLより低く、エンジンの外で測ったKLとは比べられません（XSFP4の[model card](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4)に両方があります）。同じエンジンと文書で、NVIDIAのNVFP4はTP=2で 92.68% / +1.37% / 0.0510、TP=3で 92.71% / +1.38% / 0.0511 だったので、XSFP4はどちらのTPでも3つともBF16に近く、差の文書ごとの95%区間は0を含みません。FP4-Local自身を同じエンジンでそのまま読み込むと、TP=2で 92.82% / +1.11% / 0.0510、TP=3で 92.75% / +1.07% / 0.0514 でした。

XSFP4の[測定値](#リリースでの測定値)の速さはXSFP4のものです：draftの受理と層の形がNVIDIAのNVFP4と違うので、1.x系・2.x系の数とは比べられません。XSFP4が持つFP4-Localのchat templateは、NVIDIAのものと3か所違います（contentの無いmessageは何も出さない、tool callの名前を `~` でつなぐ、toolの結果を呼び出しの順に並べられるかの検査が、だめと分かった所で止まる）。

Jammed XSFP4はBF16への近さの一部をメモリと引き換えにします：表の3つの数では、両TPでXSFP4よりBF16から離れています（差の文書ごとの95%区間はどれも0を含みません）。TP=2で空いた分は空いたまま残ります：読み込みの後のrank 0の空きは14.16 GiBで、XSFP4は8.33 GiBです。TP=3では同じ14 GiBのreserveの下で窓3本分のpage（6,147、38.27 GiB、XSFP4は4,098）を取るので、poolは1.5倍になり、rank 0の空きは12.15 GiB、XSFP4は20.69 GiBです。メモリの見張りの5 GiBより上です。返答はこのcheckpointのものなので、draftありのdecodeの速さはXSFP4と比べられません。promptの速さは比べられ、同じimageでTP=2が1,437.8 tok/s対1,415.1、TP=3が1,682.5対1,675.3です（[測定値](#リリースでの測定値)）。作り方とエンジンの外での点は[モデルカード](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4)にあります。

## 配信の既定

TPで分かれるものは [`config/tp2.env`](config/tp2.env) と [`config/tp3.env`](config/tp3.env) が持ち、残りはそれを読む [`scripts/serve.sh`](scripts/serve.sh) が持ち、全rankで同じです。TP=2の既定は1人のagentの長い会話のため、TP=3の既定は複数の人の同時利用のためのものです。何と比べて選び、何が起きれば見直すかは[決定](docs/decisions.ja.md)にあります。

| 設定 | TP=2（2台） | TP=3（3台） |
|---|---|---|
| checkpoint | XSFP4、lockのrevision（`CHECKPOINT` を書かない、[checkpoint](#checkpoint)） | 同じ |
| KV cache | latentとindexのkeyをBF16（エンジンの既定。`--kv-cache fp8` で選べるFP8のlatent cacheは受け入れの外：[制限](#制限)）、KVのpageに：全streamのcacheとエンジン自身のsequenceが1つのpoolのpageを取る（2 rankからのエンジンの既定、`TF_KV_PAGES`。全rankのファイルの `TF_KV_PAGES=off` と空の `TF_GLM_KV_SHARE=` は、TP=2は3.8.xまで、TP=3は3.7.0までと同じくstreamごとの窓） | 同じ |
| draft | checkpointのMTP head（エンジンの既定） | 同じ。draftの連なりは確率が0.5未満のdraftで終わる（`MTP_CONFIDENCE`、エンジンの `--mtp-confidence`） |
| 窓（`--context`） | 1,048,576 token（モデルの上限） | 同じ |
| 同時にdecodeする要求（`--parallel`） | 4（`PARALLEL`）。空の `PARALLEL=` ではエンジンに任せ、エンジンは起動時の空きメモリの許す限り8本までstreamを取る | 8。同じ |
| prompt cache（保持するpromptの状態） | KVのpoolのpageの上（`TF_GLM_KV_SHARE=16`）：保持するpromptは埋めたpageのまま残り、その先の状態は最大16で、会話は持っているpageの最後の印から再開する。poolの横にstoreは持たない（loadの行の `the prompt cache over the pool's pages`） | 同じ、状態は最大32（`TF_GLM_KV_SHARE=32`） |
| decodeの横のprompt | stepが時間の70%を取り、残りをstreamのroundが取る（`TENSORFOLD_PREFILL_SHARE=0.7`。エンジンの `1` はstepとroundを1回ずつ交互に回す） | 同じ |
| systemに残すメモリ（`TENSORFOLD_MEMORY_RESERVE_GIB`） | 9 GiB | 14 GiB |
| 要求が指定しないときの応答の上限 | 32,768 token（`--max-tokens`） | 同じ |
| 要求が指定しないときの推論のeffort | `high`（`--reasoning-effort`） | 同じ |
| NCCL | 各リンク2本のrail・4 channel・IBのtransportを明示、rankごとのファイルから。rank 0のアドレスとportを `NCCL_COMM_ID` に、rank 0のNCCLのidはrankどうしの生存の線で | 2本のrail・4 channel・IBのtransportを明示・subnet-aware routing。rank 0のアドレスとportを `NCCL_COMM_ID` に、rank 0のNCCLのidはrankどうしの生存の線で、他のrankのNCCLのbootstrapはそれぞれの `/32` のinterfaceで（`NCCL_SOCKET_IFNAME`） |
| main streamの小さいall-gather | NCCL | エンジンのmultirank RoCE、wireをNCCLの隣で（`TF_GLM_ROCE_MULTI=1`）。準備に失敗すると起動が止まる |
| BF16のlinear | 上流のtiledのkernel（エンジンの既定） | 同じ：上流1.1.2から（issue #1067）、TP=3のrankのKDAの入力をtileせずに回す。3.1.0と3.2.0はglueのkernel（`TF_GLM_MM=0`）が要った |
| 熱によるprefillの休止 | prompt chunkの前ごとに全rankそろって、どれかのrankのACPIの最も熱いzoneが92 °Cを超えている間、全rankが88 °C以下になるまで待つ（`TF_HEAT_HIGH`・`TF_HEAT_LOW`。3.0.0〜3.2.0は93 °Cの天井の手前でも待ったが、3.3.0のエンジンは天井を持たない） | 同じ |
| 画像と動画の入力 | 有効（`VISION=1`、エンジンの `--vision`）：rank 0にcheckpointのvision tower、PNG・JPEG・WebPの画像と動画をdata URLで、エンジンの制限の中で（[制限](#制限)）。`VISION=` でtextだけ、全rankで同じに | 同じ |
| containerのcore | 最大周波数の最も低いcore：GB10の効率core、0-4と10-14（`create_container.sh`、`CPUSET`） | 同じ |

**TP=2で4本、TP=3で8本にする理由。** 1本のstreamでは要求は前の返答の終わりを待ちます。3.8.xまでのTP=2では2本目のstreamが自分の窓を取り、短い窓にしか余地がありませんでした。KVのpageではstreamは使う分を一つのpoolから取るので、窓は本数によらずどの起動でも同じです。TP=2の4本は、agentが長い会話の横で送る短い要求のためのものです：32K tokenのpromptに6〜8秒で来た要求は1.20秒で最初のtokenを返しました。1本ならpromptと返答の全体を待ちます。TP=3の8本は複数の人のためのもので、4本の1本が終わるのを5本目が待たないようにします：別々の8つのpromptを一緒に送ると全部が1.65秒以内に始まり、合計は94.23 tok/s（4本では75.00）でした。同時の返答は同じ要求の単独の返答と同じです（[同時の要求](docs/validation.ja.md#同時の要求)）。

**prompt cacheをpoolのpageに置く理由。** 長い会話の保持の状態は4本のstreamの横のstoreに入らないことがあり、次の長いpromptが前の状態を追い出します。`TF_GLM_KV_SHARE` はpromptを埋めたpoolのpageのまま保つので、poolに余地がある間は状態が次のpromptの後も残り、poolの横にstoreを持ちません。約64K tokenと128K tokenのpromptの再送はTP=2で2.06秒と2.34秒、TP=3で1.54秒と2.11秒、400K tokenのpromptはTP=2で2.17秒でした。読み直せば数分かかります。16と32はstream 1本に4状態で、エンジン自身の線です。その下では、動いているstreamが互いの状態を追い出すと警告します。

**promptの取り分を0.7にする理由。** エンジンの `1` では長いpromptのstepとdecodeのroundが1回ずつ交互に回るので、横の返答はtokenごとにstep 1回分止まります。0.7ではpromptが時間の30%をdecodeに渡します：32K tokenのpromptの横のdecodeのtokenの間隔はTP=2で45 ms、TP=3で37 msでした。promptが払うのは何かが横でdecodeしている間だけで、単独のpromptは待ちません。

**TP=3でwireとdraftの確率を使う理由。** `--mtp-confidence 0.5` は、確率が五分を切るdraftでdraftの連なりを終えるので、roundが外れるdraftに使う行が減ります。上流はTP=3でdecodeが4.9%速いとしています。TP=2では切ります：その使い方であるsampledの1本は同じdraftを取り、4本のgreedyのcodeは3.7%遅くなりました。wireはmain streamの小さいall-gatherをエンジンのmultirank RoCEで運び、各rankは最初の1回をNCCLのものとbyteまで比べます。上流はdecodeが2.57%速く、coldの長いpromptが1.2〜1.6%遅いとして、既定をoffにしています。TP=3は返答を読む人のための配信なので、ここではdecodeを優先します。3 rank以上のためのものです。`TF_TP_ROCE_FALLBACK=error` により、準備に失敗すると起動が止まるので、気づかれずにNCCLへ戻ることはありません。

**TP=3で14 GiBにする理由。** poolは窓の丸ごとの本数でpageを取ります。エンジン自身の12.2 GiBでは、参照リングの余地は窓3本に要る量の約0.6 GiB上にあるので、空きが少し少ないホストは2本を取り、その2つの間でrank 0の起動後の空きが約12 GiB変わります。14 GiBはpoolを窓2本、512行のpageを4,098（25.51 GiB）に保ち、その線から離します。TP=2のpoolは窓1本です。Jammed XSFP4はmodelが小さいので、同じreserveで窓3本、6,147 page（38.27 GiB）を取ります。

**TP=2を1,048,576にする理由。** BF16のKVは、tokenあたり2.x系のFP8のcacheの約2倍のメモリを取ります。3.8.xまではstreamの窓がまるごとmodelの横に置かれたので、TP=2の窓は245,760 token、3.5.0からはXSFP4で524,288 tokenまででした。KVのpageでは窓はpoolのpageで、streamの本数によりません：512行のpageを2,052（12.77 GiB）でモデルの上限の1,048,576 token全部が入り、1,035,295 tokenのpromptは917.4秒で最初のtokenを返し、合言葉を全部見つけました。エンジン自身のreserve 12.2 GiBでは余地が12.0 GiBで、このpageに足りないので、`config/tp2.env` はsystemに9 GiBを残します：pageとstreamの固定分に15.3 GiBで、それらを1.5 GiB上回り、起動ごとの揺れより離れます。rank 0の起動後の空きは8.03 GiBで、memory guardの5 GiBの上です。`TF_GLM_CHUNK_SOLO=4096` の広いpromptのpassは全rankでさらにメモリを取るので、この窓では切ります（[決定](docs/decisions.ja.md#窓とstream)）。全rankのファイルの `CONTEXT` で別の値を選びます：524,288ならreserveを戻せて、広いpassも入ります。

**効率coreにする理由。** エンジンは要求を回す間、全rankで2本のCPUのthreadを空回りさせ続けます。rank 0ではdecodeの間、他のrankではそれを待つ間です（上流1.1.2のエンジンより前は、他のrankは要求の無い間も空回りしました。#1053は、rank 0にstreamが無い間それらを眠らせます）：一つはGPUを待ち、もう一つはそのkernel時間から見てNCCLのものである見込みが高いthreadです。全coreでは、これらがCPUのthermal zone（GB10の7つのzoneのうち5つ）を温めました：約6,000 tokenのpromptの後の1,024 tokenの返答を40本続けると、3.0.0のエンジンでは、TP=2でrank 0の最も熱いzoneが94.7 °Cに達し、熱の見張りが7本目でエンジンを止めました。3.1.0のエンジンは全coreでも効率coreと同じ1,535秒で40本を終えましたが、rank 0のホストは93.0 °Cに達し（止める温度まで1 °C）、効率coreでは74.9 °Cでした。全coreで2つの要求を同時に回すと88.5 °Cでした。熱の待ちはprompt chunkの合間に働くので、これを抑えられません。3.0.0のエンジンでは、効率coreで40本の返答がそのzone 85.1 °Cで終わり、rank 1のホストは約70 °Cではなく57〜63 °Cで待ちました。その代わり速さの1〜3%を失い、起動は約25秒長くなりました（[3.0.0の測定値](docs/measurements.ja.md#300)）。熱の帯を下げる（86/82/87）と、待ったpromptが26〜89%遅くなり、1,048,576 tokenのpromptの最高温度は下がりませんでした。空回りせずに眠るCUDAのcontextはdecodeが12%遅く、もう一つのthreadは空回りしたままでした。1.1.1から、上流の[runbook](https://github.com/ashhart/TensorFold/blob/v1.2.1/RUNBOOK.md#gb10-cpu-pinning-for-long-cuda-runs)もこれらの測定からGB10の各rankに同じcoreを挙げています。`CPUSET=` でcontainerに全coreを与えます。

## 設定

配信は三か所で決まります：各ホストのrankのファイル（`serve.sh` が読む）、制御機のclusterのファイル（`cluster.sh` が読む）、`create_container.sh` の環境です。二つのファイルは [`examples/`](examples/) から写して自分の値に直し、Gitには入れないでください。rankのファイルの行はリリースの `config/tp*.env` より強く、空の値はその設定を切ります。よく変える設定は、窓（`CONTEXT`）、同時にdecodeする要求（`PARALLEL`）、textだけ（`VISION=`）、待ち受けとそのkey（`HOST`・`API_KEY_FILE`）、containerのcore（`CPUSET`）です。

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
| エンジン | TensorFold 0.6.5のBIZ版。PythonとTritonのkernelで、kernelは実行時にcompile | TensorFold 1.2.1のBIZ版（3.0.0は1.0.12、3.1.0と3.2.0は1.1.1、3.3.0〜3.5.xは1.1.2、3.6.0と3.7.0は1.1.3、3.8.xは1.1.5）。ZigとCUDAで、kernelはbinaryの中 |
| 出力の反復性 | エンジンの契約として、draftした応答はserialと同じ、再開したpromptは最初からと同じ、chunkの切り方で結果が変わらない | draftした応答はserialと同じで、起動はtoken idを繰り返す。tokenは2.x系のものと違う（別のkernel、BF16 KV）ので、系列の間はNLLで比べる |
| KVと窓 | latentとindexのkeyをFP8。TP=2で300,000 token、TP=3で1,048,576 | BF16をKVのpageに。両TPで1,048,576 token（TP=2は3.8.xまで524,288） |
| 同時の要求 | 1 | TP=2で4、TP=3で8。decodeのroundとKVのpoolを分け合う（3.8.xまでは既定で1） |
| prompt cache | 8本、3 GiB（`TF_GLM_CACHE_*`） | KVのpoolのpageの上の状態、TP=2で最大16、TP=3で最大32（3.8.xまではその横のstore、最大16 GiB） |
| 画像入力 | 受ける（`VISION=1`） | 受け、動画も（`VISION=1`、既定） |
| 公開したAXLの重み | 任意で使える | 配信しない（3.6.0から） |
| 構造化出力、必須のtool呼び出し | 受ける。imageにxgrammar | 受ける。imageにxgrammarの `libtfgrammar`。必須のtool呼び出しはGLMのmarkupで |
| `prompt_logprobs` | 受ける | streamでない `/v1/completions` で受ける |
| `clear_thinking` | 従う | 3.8.0から従う（上流1.1.5。[設定](docs/configuration.ja.md#rank-0のserver)） |
| 応答の欄 | `tensorfold` に `accepted`・`drafted`・`rounds`・`cached`・`prefill_s`・`heat_wait_s`・`sha256` | `tensorfold` と `speculative`（上記）。cacheしたtokenは `usage` に。熱の待ちはlogだけ |
| 熱の設定 | `TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW`・`TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`・`TF_HEAT_LOW`、同じ帯。天井なし |
| XSFP4のcheckpoint | 配信しない | 既定（3.4.0から） |
| Jammed XSFP4のcheckpoint | 配信しない | 選べる、rankのファイルの1行で（3.10.0から） |
| NVIDIAのNVFP4のcheckpoint | 固定したcheckpoint | 配信しない（3.6.0から。3.5.xまでは選べた） |
| imageとcontainer | `glm53-tf`、extensionをcontainerごとにbuild（`build_ext.sh`） | `glm53-tf3`、ホストでは何もbuildしない |
| containerのcore | 全core | `CPUSET` が別に言わなければ効率core |
| tool引数ゲート | エンジンの前のゲート | 同じゲート、この系列の写しを `v3/` から起動 |

二つの系列のcontainerはどちらも全GPUを要求するので、エンジンは一度に一つの系列だけを動かします（[運用](docs/operations.ja.md#ホストを2x系へ渡す)）。

## リリースでの測定値

**3.10.0**（2026-11-03、エンジン `a9642aef`、上流1.2.1にこの系列の6つのcommit、image `glm53-tf3:3.10.0`）。エンジンはJammed XSFP4の `csf0_v1` の形を読む6つのcommitを足し、配信の既定は3.9.0のままです。リリースのimageを、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動しました。rankのファイルに `CHECKPOINT` も `CONTEXT` も書かないXSFP4の各TPの1回は、3.9.0のdecode検査のhashと `bench --kinds edit` の同じ返答を返しました（decodeはTP=2が54.08 tok/s、TP=3が68.72、prefillは1,415.1と1,675.3で、3.9.0は53.78と68.52、1,422.2と1,673.8です）。Jammed XSFP4の各TPの4回は、rankのファイルにその `CHECKPOINT` の1行だけを足した起動で、全検査の起動、同じhashと返答を返した2回目の起動、`PARALLEL=` を空にした起動、同時の要求の起動です。199,307・499,254・1,035,295 tokenのpromptの合言葉はすべて見つかりました。止まった起動はありません。表はJammed XSFP4のものです。XSFP4の値は下の3.9.0のものです。

| 3.10.0、Jammed XSFP4 | TP=2 | TP=3 |
|---|---|---|
| 起動（秒）：全検査の起動 / 2回目の起動 | 96 / 53 | 46 / 46 |
| decode検査 count / prose / code（tok/s） | 44.48 / 35.12 / 44.72 | 55.89 / 44.74 / 58.72 |
| MTPの受理長、同じタスク | 2.808 / 1.889 / 2.937 | 2.792 / 2.020 / 3.042 |
| `bench --kinds decode`（tok/s、中央値） | 53.31 | 68.55 |
| `bench --kinds edit`（tok/s、中央値） | 83.31 | 108.30 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,437.8 | 1,682.5 |
| 199,307 tokenのprompt（秒） | 144.5 | 122.3 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（秒） | 389.0 / 911.0 | 327.1 / 758.1 |
| 約93,000 tokenのpromptを3秒で切った後、次の要求が答えるまで（秒）、切らないpromptの最初のtokenとの比べ | 0.29 対 66.8 | 0.99 対 56.4 |
| 約40,000 tokenの会話に500 / 3,000 tokenを足すturn、最初のtoken（秒） | 1.21 / 2.97 | 1.00 / 2.55 |
| 約64K / 128K tokenの同じpromptの再送、返答の全体（秒） | 1.97 / 2.40 | 1.78 / 2.03 |
| 約400K tokenの同じpromptの再送、返答の全体（秒） | 2.22 | — |
| 32K tokenのpromptに6〜8秒で来た短い要求、最初のtoken（秒） | 1.48 | 0.95 |
| 32K tokenのpromptの横の3本のdecode、tokenの間隔の中央値（ms） | 46 | 36 |
| 別々の4つのpromptを同時に：合計のtok/s、最初のtokenの最悪（秒） | 55.16、1.00 | 78.43、0.77 |
| 別々の8つのpromptを同時に：合計のtok/s、最初のtokenの最悪（秒） | — | 96.75、1.70 |
| teacher-forced NLL、ja / en / code / math | 2.5349 / 2.9247 / 1.3125 / 0.6235 | 2.5320 / 2.9090 / 1.3107 / 0.6249 |
| tool-eval-bench 2.8.0、ゲート越し / ゲートなし | 93 / 92 | 92 / 91 |
| 化けた文字のある日本語と韓国語の答え、temperature 0 / sampled | 0 / 0 | 0 / 0 |
| 6,000 tokenのpromptの後の最大1,024 tokenの40の返答（秒、rank 0のホストの最も熱いzone） | 1,269.3、75.6 °C | 951.7、82.9 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 87.6 / 88.8 | 90.5 / 88.8 / 88.9 |
| 最低の `MemAvailable`、rankごと（GiB） | 13 / 14 | 11 / 12 / 16 |

- **loadの行。** rank 0のloadの行は、TP=2で84.28 GiBのmodelと512行のpageを2,052（12.77 GiB）、TP=3で59.10 GiBと6,147（38.27 GiB）を示します。同じimageのXSFP4は90.86 GiBと2,052、63.60 GiBと4,098です。全streamがそのpageの上に、prompt cacheがpageの上にあります。読み込みの後のrank 0の空きはTP=2で14.16 GiB（XSFP4は8.33 GiB）、poolが窓3本を取るTP=3で12.15 GiB（XSFP4は20.69 GiB）でした。`PARALLEL=` を空にすると、エンジンはTP=2で8本、TP=3で8本のstreamを取り、countのhashを返しました。rank 0の `kv pool idle` の行はどれも合っていました：約束されたpageは0で、空きのpageとprompt cacheのpageでpoolの全部です。
- **同時の要求。** 1本と4本、TP=3では8本も、TP=2で20本、TP=3で52本の返答が同じ要求の単独の返答と同じでした（[同時の要求](docs/validation.ja.md#同時の要求)）。
- **画像と動画。** draftした応答はserialと同じでした（絵を含む要求も）。H.264とVP9の動画はdraftしても `"draft": false` でも同じ応答で、GIFとaudioの部分は400で断られました。両TPで同じです。
- **熱。** 熱で待った要求はありません。熱の見張りの止める温度に届いたzoneはありません。
- **tool。** [tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)越しで、TP=2はTC-11・TC-14・TC-39・TC-52・TC-60が部分点でTC-62とTC-68を落としました。TP=3はTC-14・TC-39・TC-52・TC-57・TC-63が部分点でTC-51・TC-62・TC-68を落としました。Safety GateはTP=2ではゲート越しでもゲートなしでも合格し、TP=3ではどちらもTC-51で落ちました（下の既知の振る舞い）。
- **返答を止める。** stop文字列の要求は両TPで299で止まり、`finish_reason` は `stop` でした。
- **Jammed XSFP4の既知の振る舞い。** TP=3では、tool-eval-benchのSafety GateがTC-51（Goal-Level Planning）で、ゲート越しでもゲートなしでも落ちます：Jammed XSFP4は `create_calendar_event` の結果を待たずに、同じ手番で `send_email` を呼びます。temperature 0、seed 42の実行です。TP=2では通り、3.9.0のTP=3のXSFP4も通りました。decode検査の `count` はXSFP4より遅く、TP=2で44.48 tok/s対49.18、TP=3で55.89対65.67、受理長は2.81対3.28と2.79対3.41です。`prose` と `code` の差は3.1%以内です。検査は `ignore_eos` で512 tokenを求めるので、返答は手番の終わりの先まで続き、そこで2つのcheckpointは別のものを書きます：512 tokenのうち数字の行は、XSFP4がTP=2で約422、TP=3で約400、思考を書き続けるJammed XSFP4が約296と約200です。数字の行は思考の文より、1 roundで多くのdraftを受理します。`ignore_eos` を外すと、返答はクライアントの要求と同じく手番の終わりで止まります：TP=2ではJammed XSFP4が100まで249 token、46.05 tok/s、受理長2.95で数え、XSFP4は204まで452 token、49.52、3.32。TP=3では両方とも100まで数え、Jammed XSFP4が241 token、63.87 tok/s、受理長3.30、XSFP4が228 token、68.62、3.62。思考なしで1から100までの数を求めると、TP=2ではJammed XSFP4が求めたとおりに51.67 tok/s、受理長3.70で書き、XSFP4は37を2回書きました（40.53、2.86）。TP=3ではJammed XSFP4が求めたとおりに65.90 tok/s、受理長3.57で書き、XSFP4は37を2回書きました（59.75、3.24）。検査でも `ignore_eos` なしでも、Jammed XSFP4の返答は思考の文の割合が大きく、思考の文は数字の行より1 roundで受理されるdraftが少なくなります。

**3.9.0**（2026-11-03、エンジン `1db3edbe`、上流1.2.1、image `glm53-tf3:3.9.0`）。エンジンはこの系列のcommitを持たない上流1.2.1そのもので、配信の既定はTPごとに決めています（[配信の既定](#配信の既定)）。リリースのimageを、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動しました：各TPで4回、全検査の起動、2回目の起動、`PARALLEL=` を空にした起動、同時の要求の起動です。それらを回したどの起動も、3.3.0のXSFP4のdecode検査のhashと `bench --kinds edit` の同じ返答を返しました。NLLは3.3.0と同じで、199,307・499,254・1,035,295 tokenのpromptの合言葉はすべて見つかりました。止まった起動はありません。

| 3.9.0 | TP=2 | TP=3 |
|---|---|---|
| 起動（秒）：全検査の起動 / 2回目の起動 | 107 / 53 | 93 / 46 |
| decode検査 count / prose / code（tok/s） | 49.50 / 34.34 / 45.50 | 65.67 / 44.69 / 58.20 |
| MTPの受理長、同じタスク | 3.276 / 1.796 / 2.971 | 3.413 / 2.024 / 3.078 |
| `bench --kinds decode`（tok/s、中央値） | 53.78 | 68.52 |
| `bench --kinds edit`（tok/s、中央値） | 83.28 | 107.57 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,422.2 | 1,673.8 |
| 199,307 tokenのprompt（秒） | 145.7 | 122.5 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（秒） | 392.8 / 917.4 | 327.6 / 758.4 |
| 約93,000 tokenのpromptを3秒で切った後、次の要求が答えるまで（秒）、切らないpromptの最初のtokenとの比べ | 0.31 対 67.5 | 1.01 対 56.8 |
| 約40,000 tokenの会話に500 / 3,000 tokenを足すturn、最初のtoken（秒） | 1.22 / 3.00 | 1.01 / 2.50 |
| 約64K / 128K tokenの同じpromptの再送、返答の全体（秒） | 2.06 / 2.34 | 1.54 / 2.11 |
| 約400K tokenの同じpromptの再送、返答の全体（秒） | 2.17 | — |
| 32K tokenのpromptに6〜8秒で来た短い要求、最初のtoken（秒） | 1.20 | 1.38 |
| 32K tokenのpromptの横の3本のdecode、tokenの間隔の中央値（ms） | 45 | 37 |
| 別々の4つのpromptを同時に：合計のtok/s、最初のtokenの最悪（秒） | 55.63、1.00 | 75.00、0.79 |
| 別々の8つのpromptを同時に：合計のtok/s、最初のtokenの最悪（秒） | — | 94.23、1.65 |
| teacher-forced NLL、ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench 2.8.0、ゲート越し / ゲートなし | 95 / 93 | 92 / 91 |
| 化けた文字のある日本語と韓国語の答え、temperature 0 / sampled | 0 / 0 | 0 / 0 |
| 6,000 tokenのpromptの後の最大1,024 tokenの40の返答（秒、rank 0のホストの最も熱いzone） | 1,240.8、75.6 °C | 958.0、83.6 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 89.2 / 88.9 | 90.0 / 88.9 / 88.5 |
| 最低の `MemAvailable`、rankごと（GiB） | 6 / 8 | 19 / 21 / 25 |

- **[3.8.0](docs/measurements.ja.md#380)との差。** tokenは同じです。3.8.0に比べ、decode・編集の返答・prefillの速さはTP=2で−0.2〜+0.8%、TP=3で−1.7〜+4.9%、長いpromptの時間はTP=2で−8.5〜−3.8%、TP=3で−22.9〜−4.8%でした（熱の待ちを除く）。既定を決めた腕の比べでは、TP=3のdecodeはdraftの確率とwireの分だけ得をしました（[決定](docs/decisions.ja.md#窓とstream)）。腕はこの長さのpromptを測っていないので、TP=3で長いpromptほど大きい短縮を一つの変更のせいとは書きません。起動はTP=2で107 / 53秒、TP=3で93 / 46秒で、3.8.0の376 / 323秒と316 / 270秒より上流の速い読み込みの分だけ短くなりました。
- **loadの行。** rank 0のloadの行は、TP=2で90.86 GiBのmodelと512行のpageを2,052（12.77 GiB）、TP=3で63.60 GiBと4,098（25.51 GiB）を示し、エンジン自身のsequenceと全streamがそのpageの上に、prompt cacheがpageの上にあります。`[serve.sh]` の行はどの起動でも `config/tp*.env` の設定を出しました。`PARALLEL=` を空にすると、エンジンはTP=2で8本、TP=3で8本のstreamを取り、countのhashを返しました。rank 0の `kv pool idle` の行はどれも合っていました：約束されたpageは0で、空きのpageとprompt cacheのpageでpoolの全部です。
- **同時の要求。** 1本と4本、TP=3では8本も、TP=2で20本、TP=3で52本の返答が同じ要求の単独の返答と同じでした（[同時の要求](docs/validation.ja.md#同時の要求)）。表のwarm turnから8つのpromptまでの行は同時の要求の起動のもので（[方法](docs/benchmarks.ja.md#同時の要求)）、比べる前の版の値はありません。
- **熱。** TP=3でも熱で待ったpromptはありません（3.8.0：1,035,295 tokenのpromptが15回で30秒）。TP=2では待ったpromptはありません。熱の見張りの止める温度に届いたzoneはありません。
- **tool。** このリポジトリの中継である[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)越しでは、部分点や失敗のシナリオが3.8.0と同じでした。ゲートなしでは、エンジンはTP=2で93、TP=3で91で、Safety Gateは合格でした。両TPで増えた失敗はTC-43の一つで、空の `query` で `web_search` を呼んだものです。ゲート越しでは、queryなしでは呼ばずに断る返答になります。
- **XSFP4の既知の振る舞い。** [3.3.0](docs/measurements.ja.md#330)のものと同じです：TP=3ではstop文字列の要求が上限まで走り、promptのscoreと構造化出力の検査のscoreもgrammarも無い要求は自分のhashを持ちます。

前の版の値は[前の版の測定値](docs/measurements.ja.md)にあります。

## 制限

- **Jammed XSFP4を読むのはこの系列のエンジンだけです。** `csf0_v1` の形はこの系列のもので、vLLM、他のNVFP4のloader、そのkernelを持たないエンジン（上流のリリースを含む）は読めず、3.8.0のエンジンは読み込みの時に名前を挙げて断ります。blockのスケールが粗いので、返答はXSFP4と違います（[checkpoint](#checkpoint)）。
- **TP=2で4本、TP=3で8本。** それを超える要求はstreamを待ちます。streamは1つのKVのpoolを分け合います：TP=2で2,052 page（窓いっぱいの1本分）、TP=3で4,098 page（2本分、Jammed XSFP4は6,147 pageで3本分）です。長い会話が同時に何本も並ぶ負荷は測っていません（[配信の既定](#配信の既定)）。
- **画像と動画はエンジンの制限の中で。** 画像は1要求に最大4枚で、送られた履歴にある画像を全部数えます（前のturnを画像ごと送り直すclientはそこに届きます）。4枚で4,096 tokenを分け合い、1枚10 MiB・1要求20 MiBまで。PNG・JPEG・WebPのdata URLで、GIFと動く絵は断ります。動画はuserのmessageだけで、1要求に2本（1本16 MiB・合わせて20 MiB・1時間まで）、1秒に2 frameで最大256 frameを取り、16,384 tokenを分け合います。0.5秒より短いclipは断ります。画像と動画のtokenは窓から取られます。HTTPSのURLには `serve.sh` が渡さない `--vision-urls` が要ります。音声のpartは400で断ります。
- **生成したtokenのlog確率は無い。** `logprobs` と `top_logprobs` は400で断ります。`prompt_logprobs` はstreamでない `/v1/completions` でだけ配信します。
- **要求を回す間、どのrankも2つのCPUのcoreを空回りさせ続けます。** rank 0はdecodeの間、他のrankはそれを待つ間です（上流1.1.2のエンジンからは、#1053により、rank 0にstreamが無い間は他のrankは眠ります）。containerの既定のcoreは、3.0.0のエンジンでは速さの1〜3%と引き換えに（3.1.0のエンジンでは40本の返答は同じ時間で、起動は約40秒長い）、CPUのzoneを熱の見張りが止める温度より下に保ちます。全coreでは、返答の長い連続が3.0.0のエンジンではそこに達し、3.1.0のエンジンでは1 °C手前まで来ました（[効率coreにする理由](#配信の既定)）。
- **BF16 KV** は、GiBあたり2.x系のFP8のcacheより短い窓しか持てません。エンジンには選んで使うFP8のlatent cache（`--kv-cache fp8`）がありますが、上流は品質と機器での確かめをまだとしていて、`serve.sh` も指定しません。これはstreamごとに窓を持つので、リリースの `TF_GLM_KV_SHARE` があるとエンジンは起動を断ります：空の `TF_GLM_KV_SHARE=` と1本のstreamが要ります（[チートシート](docs/cheatsheet.ja.md#tp2のfp8のlatent-cache)）。TP=2で一度だけ試しました（XSFP4、vision towerあり、両rankのファイルに `CONTEXT=1048576`、`cluster.sh` のlabelの後に `--kv-cache fp8`）：1,048,576 tokenの窓に7.13 GiBのstreamが1本、4.7 GiBのprompt cacheと並んで入り、1,035,295 tokenのpromptは最初のtokenまで1,130.6秒で3つの合言葉を全部見つけ、199,307と499,254 tokenのpromptはprefillが約5%長くかかり、NLLの組は+0.14%（文ごとの差の区間は0をまたぐ）、decode検査のtokenはBF16のcacheと違いました。
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
  config/           tp2.env、tp3.env（TPごとの配信の既定）、xsfp4.lock.json（XSFP4）、
                    jammed.lock.json（Jammed XSFP4）、
                    engine.lock.json（エンジンのcommit、Zigのcompiler、xgrammar）、nll_set.json（NLL採点セット）
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
- **XSFP4とJammed XSFP4は本リポジトリの管理者のcheckpointです。** NVIDIA Open Model Agreementの下のFP4-Localの派生物で、NVIDIAやZ.aiのリリースではありません。
- **エンジンはこの系列による上流のforkのリリースのbranchです。** 他の利用者にも役立つものは上流のTensorFoldへpull requestとして出し（#1016・#1017・#1018は1.1.1で、#1050・#1163・#1178・#1211は1.1.5で、#1352・#1404・#1424は1.1.9で、#1516・#1524・#1616・#1636は1.2.0で、#1823は1.2.1で上流自身のものになりました）、残りはリリースのbranchが持ちます。3.10.0のbranchは上流v1.2.1の上に `csf0_v1` の6つのcommitを持ち、これらは次に上流へ出します。

## Next Action

各項目は、きっかけと、そのときこの系列がすることです。

- 3.3.0のエンジンは上流のpull request #1053（rank 0にstreamが無い間、待つrankが眠る。1.1.2に入った）を持つ。その後のリリースは効率coreで回したので、まだ開いている → containerにまだ効率coreが要るかを測り直す。
- 上流が#1423（promptのstepを2つ組む）か#1580（routed expertのL2の先読み）を取り込む → 3.9.0の既定を選んだ時のように腕として足し、出たものを受け入れる。
- 上流が `csf0_v1` のcommitを取り込む → リリースのbranchを上流のリリースへ戻す。
- XSFP4から何も借りず、MTP層も含めてBF16の重みから較正し直したJammed XSFP4の点が良く、受け入れも通る → lockをそのrevisionへ動かす。

## ローカルデータと開発

Gitに入れないもの（自分の拠点の値を入れたrankとclusterのファイルを含む）、ライセンス、開発への参加は[リポジトリのREADME](../README.ja.md#ローカルデータと開発)にあります。3.x系の変更は[CHANGELOG.ja.md](CHANGELOG.ja.md)にあります。

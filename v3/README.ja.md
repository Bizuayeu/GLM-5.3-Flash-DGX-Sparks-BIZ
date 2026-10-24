# GLM-5.3-Flash BIZ 3.x（TensorFoldネイティブ）

![GLM-5.3-Flash BIZ v3、XSFP4 × TensorFold：DGX Spark・GB10で動くZigとCUDAのネイティブ実装](assets/banner.webp)

[English](README.md) · [リポジトリの索引](../README.ja.md) · [配備の手順書](SETUP.ja.md) · [検証](docs/validation.ja.md) · [変更履歴](CHANGELOG.ja.md)

**GLM-5.3-Flash BIZ** は、DGX Sparkまたは互換のGB10機でGLM-5.3-Flashを配信します。3.x系はTensorFoldのネイティブエンジン、つまり[2.x系](../v2/README.ja.md)が動かすPythonのエンジンに代わったZigとCUDAのエンジンで、2台のTP=2または3台のTP=3で配信します。配信するcheckpointは[XSFP4](#checkpoint)で、NVIDIAのGLM-5.3-Flash-FP4-Localの派生物、expertsを本リポジトリの管理者が量子化し直したものです。1.x系・2.x系が配信するNVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointは、3.5.xまでここでも選べました。3.0.0が上流のTensorFold 1.0.12の上の最初のリリースで、3.1.0で上流の1.1.1へ移り、3.2.0で画像と動画の入力を加え、3.3.0で上流の1.1.2へ移ってNVIDIAのcheckpointの横にXSFP4を加え、3.4.0でXSFP4を既定にし、3.6.0で上流の1.1.3へ移ってXSFP4だけを配信します。2.x系も並んで続きます。

**BIZ**は保守者の印で、リポジトリの意図を示す語です。意味することと意味しないことは[リポジトリのREADME](../README.ja.md#biz)にあります。

## 要約

- **状況。** 3.6.0はエンジンを上流1.1.3の上へ移し、XSFP4だけを配信します。リリースのimageを、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動すると、TP=2とTP=3の各2回の起動で3.3.0のXSFP4のdecode検査のhashと編集の返答を、さらに同じNLLを返し、TP=3の1,035,295 tokenのpromptを含めて長い入力の合言葉をすべて見つけました（[リリースでの測定値](#リリースでの測定値)）。TP=3ではstop文字列の要求が上限まで走り、短いgreedyの返答が自分のhashを持ちます。どちらもそこに書いた既知の振る舞いです。[検証](docs/validation.ja.md)の基準値は、2026-10-22の参照機での3.3.0の受け入れで、visionのtowerを読み込んで決めました。主張の範囲はここまでです。他のホストは同じ検査を回して受け入れます。
- **何であるか。** XSFP4を、TensorFoldのネイティブエンジンの固定したcommitで一つのOpenAI互換endpointとして配信するための、build手順・起動の台本・受け入れ検査です。2台なら直結のConnectX-7リンクでTP=2、3台ならswitchなしのリングでTP=3です。公開している測定値はMSI EdgeXpert（MS-C931）で取りました。
- **反復性。** draftした応答はserialと同じで、起動は同じTPの前の起動のtoken idを出します。ネイティブエンジンのtokenはそれ自身のもので、2.x系のものではありません：kernelとBF16のKV cacheの丸めが違うので、二つの系列はtokenごとではなくteacher-forced NLLで比べます（[2.x系との違い](#2x系との違い)）。
- **構造化出力とpromptのscore。** JSON schemaつきの `response_format`、`required` か名指しの関数の `tool_choice`（GLM自身のtoolのmarkupで書く）、`/v1/completions` の `prompt_logprobs` は、1.1.1からGLMのCUDAのエンジンで上流のTensorFold自身のものです。この系列のpull request #1016・#1017・#1018の後に上流が書きました（[API](#api)）。
- **画像と動画。** chatの要求は、PNG・JPEG・WebPの画像と、H.264・HEVC・VP8・VP9・MPEG-4の動画をdata URLで持てます。rank 0にあるcheckpointのvision towerが、エンジンの `--vision` で読みます。`serve.sh` は既定でこれを渡します（[制限](#制限)）。
- **精度。** XSFP4ではrouted expertはW4A16、他のprojectionはcheckpointが保存する形のままで、多くは8 bit、vision towerのMLPとmergerはNVFP4です（[checkpoint](#checkpoint)）。KVはBF16です（2.x系はFP8のKV cacheを持ちます）。NVIDIAのmodel cardは別のレシピ・別の機材でFP4-Localを測っており、その精度表はこの配信を表しません。この配信を表す数字は[検証](docs/validation.ja.md)にあります。
- **ライセンス。** コードとエンジンはApache-2.0、重みは運用者がダウンロードし、NVIDIA Open Model Agreement（XSFP4、商用に使える）です。imageには構造化出力のためにxgrammar（Apache-2.0）、画像と動画のためにlibjpeg-turbo・libwebp（BSD系）とFFmpegのdecoder（LGPL-2.1）が入ります。配信の経路に非商用の条件はありません（[ライセンスの早見表](../README.ja.md#ライセンスの早見表)）。
- **未検証。** 画像と動画のURL（`--vision-urls`、無効）、同時に2つ以上の要求（受け入れは一度に一つずつ送りました）、他のrank数と機材（[制限](#制限)）。ハーネス連携（ZCode・Claude Code）、アプリケーション全体の品質と本番の信頼性。

## 何であるか

- **重み**：`Bizuayeu/GLM-5.3-Flash-XSFP4`（[`config/xsfp4.lock.json`](config/xsfp4.lock.json)、[checkpoint](#checkpoint)）で、NVIDIAのGLM-5.3-Flash-FP4-Localと[Z.aiのGLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)から作られています。
- **エンジン**：TensorFoldのネイティブエンジン（`tensorfold-native`）。[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/3.6.0` として公開するBIZ版です：上流のTensorFold v1.1.3に、上流のpull request #1050のcodeと、この系列のcommitを二つ足したものです。indexがmodelのfolderの中のfolderにあるshardを名指せること（FP4-LocalとXSFP4のindexに要る）は、1.1.3から上流自身のcodeにあり、3.5.xまでのリリースのbranchはpull request #1179のpatchとして持っていました。#1050のcode（15のcommit。pull requestは上流でopen）はNVIDIAのGLM-5.3-Flash-FP4-Localを保存された形のまま読み、それと共に、experts以外にFP4-Localのtensorを持つXSFP4のcheckpointも読みます：各projectionの形をcheckpointの `MIXED_PRECISION` のレシピから見分け、MXFP8と128×128 blockのFP8のprojectionを保存の形のまま計算し、FP4-Localの圧縮したexpertのscaleを読み、float32のnormの重みをfloat32のまま保ちます。この系列のcommitはTP=3のためにこの系列に留めるもので、rank 0がNCCLのidをファイルで他のrankへ渡し（`TF_GLM_NCCL_ID_FILE`）、各rankはその後、rankどうしの生存の線がrank 0に届くための `NCCL_COMM_ID` をNCCLの環境から外します。リングのpoint-to-pointの `/32` のアドレスでは、NCCLはそれで集まれないためです。二つ目のcommitはそのcodeのcommentだけを変えます。上流はTPのbootstrap（pull request #636）を閉じ、idをrankどうしの線で送るこの系列のpull request #1178はopenです。3.0.0〜3.2.0の熱の待ちの天井への見込み（`TF_HEAT_CEILING`）は無くなり、熱の待ちは上流の帯だけです（[配信の既定](#配信の既定)）。imageは一つのcommitに固定します（[`config/engine.lock.json`](config/engine.lock.json)）。
- **image**：[`docker/Dockerfile`](docker/Dockerfile)。エンジンはNVIDIAのCUDA 13.3.1のbuild用imageで、lockが名指すZigのcompiler（SHA-256で確かめる）がcompileし、`libtfgrammar` は固定したcommitのxgrammarのreleaseからbuildします。実行のimageはCUDA 13.3.1にNCCL 2.30.7とRDMAのuserspaceです。2つのbaseのimageはdigestで固定しています。`/usr/share/doc/tf3/ENGINE` がエンジンのcommitと各binaryのSHA-256を名指し、`/usr/share/doc/tf3/engine/` にエンジンのライセンスと表示があります。
- **起動**：[`scripts/`](scripts/) のshellの台本と、rankごとの環境ファイル一つ（[`examples/`](examples/) に参照機のファイル）。順番は[SETUP.ja.md](SETUP.ja.md)にあります。ホストでは何もbuildしません：kernelはbinaryの中にあります。

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
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.6.0 .

# 各ホストで、checkoutのルートから（SETUP §4）
v3/scripts/create_container.sh glm53-tf3:3.6.0 ~/glm53-tf3
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
| TP=2（245,760 tokenの窓）・TP=3のrank 0のmodel（読み込みの行） | 93.44・76.36 GiB |
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
| KV cache | latentとindexのkeyをBF16（エンジンの既定。`--kv-cache fp8` で選べるFP8のlatent cacheは受け入れの外：[制限](#制限)） | 同じ |
| draft | checkpointのMTP head（エンジンの既定） | 同じ |
| 窓（`--context`） | 524,288 token：各rankでXSFP4の隣に1本のstreamとprompt cacheが入る | 1,048,576 token（モデルの上限） |
| 同時にdecodeする要求（`--parallel`） | 1（`PARALLEL=1`）。空の `PARALLEL=` ではエンジンに任せ、エンジンは起動時の空きメモリからstreamとprompt cacheの大きさを決める | 同じ |
| prompt cache（保持するpromptの状態、2,048 tokenのchunkの始まりごと） | 窓の残り、最大16 GiB（rank 0のloadの行。起動時の空きメモリで動きます）：参照機で、vision towerを読み込んで、XSFP4は524,288 tokenで5.2〜5.5 GiB（245,760では8.9 GiB） | 参照リングで16.0 GiB、その上限（`--prompt-cache-gib` で別の値に） |
| 要求が指定しないときの応答の上限 | 32,768 token（`--max-tokens`） | 同じ |
| 要求が指定しないときの推論のeffort | `high`（`--reasoning-effort`） | 同じ |
| NCCL | 各リンク2本のrail・4 channel・IBのtransportを明示、rankごとのファイルから。rank 0のアドレスとportを `NCCL_COMM_ID` に | 2本のrail・4 channel・IBのtransportを明示・subnet-aware routing。rank 0のアドレスとportを `NCCL_COMM_ID` に（rankどうしの生存の線のためだけ）、rank 0のNCCLのidをファイルで渡す |
| BF16のlinear | 上流のtiledのkernel（エンジンの既定） | 同じ：上流1.1.2から（issue #1067）、TP=3のrankのKDAの入力をtileせずに回す。3.1.0と3.2.0はglueのkernel（`TF_GLM_MM=0`）が要った |
| 熱によるprefillの休止 | prompt chunkの前ごとに全rankそろって、どれかのrankのACPIの最も熱いzoneが92 °Cを超えている間、全rankが88 °C以下になるまで待つ（`TF_HEAT_HIGH`・`TF_HEAT_LOW`。3.0.0〜3.2.0は93 °Cの天井の手前でも待ったが、3.3.0のエンジンは天井を持たない） | 同じ |
| 画像と動画の入力 | 有効（`VISION=1`、エンジンの `--vision`）：rank 0にcheckpointのvision tower、PNG・JPEG・WebPの画像と動画をdata URLで、エンジンの制限の中で（[制限](#制限)）。`VISION=` でtextだけ、全rankで同じに | 同じ |
| containerのcore | 最大周波数の最も低いcore：GB10の効率core、0-4と10-14（`create_container.sh`、`CPUSET`） | 同じ |

**一度に一要求にする理由。** `--parallel` を設定しないと、エンジンは8本のstreamを求めて収まるだけを配信するので、streamの数とprompt cacheに残る余地は、そのときの空きメモリによって起動ごとに変わります（TP=3では、ある起動が2本のstreamと0.1 GiBのprompt cacheを取りました）。2.x系と同じ1本のstreamなら、窓はどの起動でも同じで、prompt cacheは空きメモリの分だけ動きます（TP=2でvision towerありのNVIDIAのNVFP4は、3.3.0の2回の起動で5.2・5.1 GiB）。TP=2では、3.0.0のエンジンは245,760 tokenの窓の隣に2本目のstreamが収まりませんでした（各rankで4.55 GiBが要り、rank 1には4.41 GiBでした）。3.1.0からのエンジンは収まります：3.3.0ではNVIDIAのNVFP4で `PARALLEL=` を空にすると2本のstreamを取り（XSFP4では3本）、prompt cacheは1本のときの5.2 GiBに対して1.5 GiBでした。3.5.0の524,288では1本です（[制限](#制限)）。

**TP=2を524,288にする理由。** BF16のKVは、tokenあたり2.x系のFP8のcacheの約2倍のメモリを取ります。3.4.0までの窓245,760 tokenは2.x系の300,000 tokenより短く、決めた時の既定だったNVIDIAのNVFP4で1本のstreamが収まるほぼ最大でした。3.4.0から既定のXSFP4はrank 0で約3.9 GiB軽いので（245,760でNVIDIAの97.38 GiBに対して93.44 GiB）、3.5.0から窓は524,288 tokenです：rank 0のloadの行は1本6.71 GiBのstreamと5.5 GiBのprompt cacheを示し、499,254 tokenのpromptが返答に25,034 tokenを残して入ります。2本目のstream（`PARALLEL=2`）はさらに6.71 GiBを取り、この窓には入らないので、小さい窓（例えば `CONTEXT=245760`）が要ります。全rankのファイルの `CONTEXT` で別の値を選びます。

**効率coreにする理由。** エンジンは要求を回す間、全rankで2本のCPUのthreadを空回りさせ続けます。rank 0ではdecodeの間、他のrankではそれを待つ間です（上流1.1.2のエンジンより前は、他のrankは要求の無い間も空回りしました。#1053は、rank 0にstreamが無い間それらを眠らせます）：一つはGPUを待ち、もう一つはそのkernel時間から見てNCCLのものである見込みが高いthreadです。全coreでは、これらがCPUのthermal zone（GB10の7つのzoneのうち5つ）を温めました：約6,000 tokenのpromptの後の1,024 tokenの返答を40本続けると、3.0.0のエンジンでは、TP=2でrank 0の最も熱いzoneが94.7 °Cに達し、熱の見張りが7本目でエンジンを止めました。3.1.0のエンジンは全coreでも効率coreと同じ1,535秒で40本を終えましたが、rank 0のホストは93.0 °Cに達し（止める温度まで1 °C）、効率coreでは74.9 °Cでした。全coreで2つの要求を同時に回すと88.5 °Cでした。熱の待ちはprompt chunkの合間に働くので、これを抑えられません。3.0.0のエンジンでは、効率coreで40本の返答がそのzone 85.1 °Cで終わり、rank 1のホストは約70 °Cではなく57〜63 °Cで待ちました。その代わり速さの1〜3%を失い、起動は約25秒長くなりました（[リリースでの測定値](#リリースでの測定値)）。熱の帯を下げる（86/82/87）と、待ったpromptが26〜89%遅くなり、1,048,576 tokenのpromptの最高温度は下がりませんでした。空回りせずに眠るCUDAのcontextはdecodeが12%遅く、もう一つのthreadは空回りしたままでした。1.1.1から、上流の[runbook](https://github.com/ashhart/TensorFold/blob/v1.1.1/RUNBOOK.md)もこれらの測定からGB10の各rankに同じcoreを挙げています。`CPUSET=` でcontainerに全coreを与えます。

## 設定

配信は三か所で決まります：各ホストのrankのファイル（`serve.sh` が読む）、制御機のclusterのファイル（`cluster.sh` が読む）、`create_container.sh` の環境です。二つのファイルは [`examples/`](examples/) から写して自分の値に直し、Gitには入れないでください。よく変える設定は、窓（`CONTEXT`）、同時にdecodeする要求（`PARALLEL`）、textだけ（`VISION=`）、待ち受けとそのkey（`HOST`・`API_KEY_FILE`）、containerのcore（`CPUSET`）です。

[設定](docs/configuration.ja.md)は全ての設定を、それぞれの既定と読むrankとともに挙げます：rankのファイル、`serve.sh`、エンジンのflagと環境変数、NCCL、clusterのファイル、container、道具、lockのものです。エンジンはその多くを起動時にrankの間で比べ、違えば起動を断ります。既定以外の値は、その頁が名指すものを除き、3.x系の受け入れが測った範囲の外です。上流自身のrecipeを越えてこの構成でできることは、写せる行の形で[チートシート](docs/cheatsheet.ja.md)にあります。

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
| エンジン | TensorFold 0.6.5のBIZ版。PythonとTritonのkernelで、kernelは実行時にcompile | TensorFold 1.1.3のBIZ版（3.0.0は1.0.12、3.1.0と3.2.0は1.1.1、3.3.0〜3.5.xは1.1.2）。ZigとCUDAで、kernelはbinaryの中 |
| 出力の反復性 | エンジンの契約として、draftした応答はserialと同じ、再開したpromptは最初からと同じ、chunkの切り方で結果が変わらない | draftした応答はserialと同じで、起動はtoken idを繰り返す。tokenは2.x系のものと違う（別のkernel、BF16 KV）ので、系列の間はNLLで比べる |
| KVと窓 | latentとindexのkeyをFP8。TP=2で300,000 token、TP=3で1,048,576 | BF16。TP=2で524,288 token、TP=3で1,048,576 |
| 同時の要求 | 1 | 既定で1。`PARALLEL` で、窓が残すメモリの中で、エンジンがdecodeのroundをより多くの要求に分ける |
| prompt cache | 8本、3 GiB（`TF_GLM_CACHE_*`） | 窓の残りに、最大16 GiBまで、chunkの始まりの状態を保つ（TP=2でvision towerありは、XSFP4の524,288 tokenで5.2〜5.5 GiB。TP=3は16.0 GiB）。本数の上限は無い |
| 画像入力 | 受ける（`VISION=1`） | 受け、動画も（`VISION=1`、既定） |
| 公開したAXLの重み | 任意で使える | 配信しない（3.6.0から） |
| 構造化出力、必須のtool呼び出し | 受ける。imageにxgrammar | 受ける。imageにxgrammarの `libtfgrammar`。必須のtool呼び出しはGLMのmarkupで |
| `prompt_logprobs` | 受ける | streamでない `/v1/completions` で受ける |
| `clear_thinking` | 従う | chat templateに渡さない（[制限](#制限)） |
| 応答の欄 | `tensorfold` に `accepted`・`drafted`・`rounds`・`cached`・`prefill_s`・`heat_wait_s`・`sha256` | `tensorfold` と `speculative`（上記）。cacheしたtokenは `usage` に。熱の待ちはlogだけ |
| 熱の設定 | `TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW`・`TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`・`TF_HEAT_LOW`、同じ帯。天井なし |
| XSFP4のcheckpoint | 配信しない | 配信するcheckpoint（3.4.0から既定、3.6.0からこれだけ） |
| NVIDIAのNVFP4のcheckpoint | 固定したcheckpoint | 配信しない（3.6.0から。3.5.xまでは選べた） |
| imageとcontainer | `glm53-tf`、extensionをcontainerごとにbuild（`build_ext.sh`） | `glm53-tf3`、ホストでは何もbuildしない |
| containerのcore | 全core | `CPUSET` が別に言わなければ効率core |
| tool引数ゲート | エンジンの前のゲート | 同じゲート、この系列の写しを `v3/` から起動 |

二つの系列のcontainerはどちらも全GPUを要求するので、エンジンは一度に一つの系列だけを動かします（[運用](docs/operations.ja.md#ホストを2x系へ渡す)）。

## リリースでの測定値

**3.6.0**（2026-10-24、エンジン `21778b05`、上流1.1.3にpull request #1050、image `glm53-tf3:3.6.0`）。エンジンを上流1.1.3の上へ移し、3.x系はXSFP4だけを配信します。リリースのimageを、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動しました：TP=2で3回（うち1回は `PARALLEL=` を空に）、TP=3で2回、さらに各TPで1回、ゲートなしのtool-eval-benchのために（TP=3ではprefillも測り直し。最初の起動のものは、rank 2のホストでimageを書き出した時間と重なりました）。それらを回したどの起動も、3.3.0のXSFP4のdecode検査のhashと、`bench --kinds edit` の同じ返答を190 roundで返しました。NLLと199,307 tokenのpromptへの返答は3.3.0と同じで、499,254 tokenと1,035,295 tokenのpromptの合言葉はすべて見つかりました。`PARALLEL=` を空にすると、エンジンはTP=2の524,288 tokenの窓で1本のstreamを取り、countのhashを返しました。止まった起動はありません。

| 3.6.0 | TP=2 | TP=3 |
|---|---|---|
| 起動（秒）：全検査の起動 / 2回目の起動 | 377 / 334 | 330 / 283 |
| decode検査 count / prose / code（tok/s） | 48.83 / 33.74 / 44.86 | 64.28 / 45.24 / 55.33 |
| MTPの受理長、同じタスク | 3.276 / 1.796 / 2.971 | 3.362 / 1.947 / 2.823 |
| `bench --kinds decode`（tok/s、中央値） | 53.53 | 65.65 |
| `bench --kinds edit`（tok/s、中央値） | 82.19 | 104.12 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,409.4 | 1,694.3 |
| 199,307 tokenのprompt（秒） | 152.8 | 130.4 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（秒） | 434.6 / — | 380.5 / 1,004.1 |
| 約93,000 tokenのpromptを3秒で切った後、次の要求が答えるまで（秒）、切らないpromptの最初のtokenとの比べ | 0.36 対 69.0 | 0.98 対 58.2 |
| teacher-forced NLL、ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench 2.8.0、ゲート越し / ゲートなし | 95 / 93 | 92 / 91 |
| 6,000 tokenのpromptの後の最大1,024 tokenの40の返答（秒、rank 0のホストの最も熱いzone） | 1,255.9、75.1 °C | 985.5、83.3 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 86.4 / 88.9 | 92.4 / 89.4 / 87.0 |
| 最低の `MemAvailable`、rankごと（GiB） | 12 / 13 | 21 / 22 / 27 |

- **3.3.0との差。** tokenは同じです。速さはTP=2で0.4〜1.2%、TP=3で0.7〜2.2%低く、TP=3の長いpromptは約2%長くかかりました（1,035,295 tokenのpromptは熱の待ちを除いて994秒、3.3.0は974秒）。TP=3のprefillは別の起動のもので、最初の起動の1,669.2 tok/sは、rank 2のホストでimageを書き出した時間と重なっていました。rank 0のloadの行は同じmodelの大きさ（TP=2の524,288 tokenの窓で96.97 GiB、TP=3で76.36 GiB）で、TP=2では4.6 GiBのprompt cache（`PARALLEL=` を空にすると5.5 GiB）でした。
- **熱。** TP=3では1,035,295 tokenのpromptだけが熱で待ち、2秒の待ちを5回、計10秒でした（3.3.0：21回で42秒）。TP=2では待ったpromptはありません。熱の見張りの止める温度に届いたzoneはありません。
- **tool。** このリポジトリの中継である[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)越しでは、点数と、部分点や失敗のシナリオが、tool-eval-bench 2.8.0での3.5.3のimageと同じでした。ゲートなしでは、エンジンはTP=2で93、TP=3で91で、Safety Gateは合格でした。両TPで増えた失敗はTC-43の一つで、空の `query` で `web_search` を呼んだものです。ゲート越しでは、queryなしでは呼ばずに断る返答になります。
- **XSFP4の既知の振る舞い**は下の3.3.0のものと同じです：TP=3ではstop文字列の要求が上限まで走り、promptのscoreと構造化出力の検査のscoreもgrammarも無い要求は自分のhashを持ちます。

**3.5.0**（2026-10-23、エンジンは3.3.0・3.4.0と同じ `d2d95b11`、image `glm53-tf3:3.5.0`）。TP=2の既定の窓が524,288 tokenになりました。imageが3.4.0と違うのは `serve.sh` だけで、エンジンのbinaryはbyteまで3.4.0のものです（buildが層を使い回した）。そのためTP=3は起動し直していません。TP=2で、リリースのimageを、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かずにそれ自身の `serve.sh` と `cluster.sh` で、全containerを効率coreに置いて起動すると：XSFP4のdecode検査は3.3.0のhashを、`bench --kinds edit` は同じ返答を190 roundで（80.7〜81.0 tok/s、3.4.0の起動は82.8〜83.0。後に同じimageで245,760と524,288を2回ずつ起動すると、中央値はどちらの窓でも82.4〜82.8 tok/sでした）、NLLは同じ値を返しました。199,307 tokenのpromptは151.7秒で3.3.0と同じ返答を、499,254 tokenのpromptは最初のtokenまで431.5秒で3つの合言葉を全部見つけました。熱を待ったpromptは無く（最も熱いzoneはrank 0のホストで87.3 °C、rank 1で89.0 °C）、最低の `MemAvailable` は両rankで12 GiBでした。rank 0のloadの行は、最初のstreamの窓を含めてmodel 96.97 GiB、1本6.71 GiBのstreamと5.5 GiBのprompt cacheでした（`PARALLEL=` を空にした2回目の起動では5.2 GiBで、エンジンは1本を取り、countのhashを返しました）。NVIDIAのNVFP4は同じ窓で100.90 GiBと1.0 GiBのprompt cacheで、countのhashを返しました。止まった起動はありません。

**3.4.0**（2026-10-23、エンジンは3.3.0と同じ `d2d95b11`、image `glm53-tf3:3.4.0`）。XSFP4が既定になりました。エンジンと配信の道は3.3.0のものです。3.4.0で回し直したのはこの段落の検査だけで、ほかは下の3.3.0のXSFP4の測定値を基準とします。imageの入力が3.3.0と違うのは、`serve.sh` の既定のcheckpoint（XSFP4の `59c49ac9`。fileはmodel cardのほかは `dbcb7b65` と同じ）と表示だけです。同じcommitからbuildし直したエンジンは、binaryのbyteは揃いませんが、3.3.0と同じ答えを返しました。リリースのimageを、rankのファイルに `CHECKPOINT` を書かずにそれ自身の `serve.sh` と `cluster.sh` で、全containerを効率coreに置いて各TPで1回起動すると、TP=2とTP=3で、decode検査は3.3.0のXSFP4のhashを、`bench --kinds edit` は同じ返答を、NLLは同じ値を返し、rank 0の読み込みの行のmodelの大きさも同じでした。止まった起動はありません。

**3.3.0**（2026-10-23、エンジン `d2d95b11`、上流1.1.2にpull request #1050と#1179、image `glm53-tf3:3.3.0`）。リリースの `serve.sh`（既定でvisionのtowerを読み込みます）と `cluster.sh` で起動し、全containerを効率coreに置き、両TPで `TF_GLM_MM` は無しです：各checkpointでTP=2で3回（うち1回は `PARALLEL=` を空に）、TP=3で2回。XSFP4の起動はリリースのimageで回し、読んだのは素のblockのスケールのrevisionです。公開するrevisionは、各TPでもう1回の起動で、decode検査のhash、編集の返答、NLL、rank 0のmodelの大きさ（読み込みの行）が同じでした。NVIDIAのNVFP4の起動は、エンジンが一つ前のcommitのimage（`aa12d8df`。indexがfolderの中のshardを名指せるようにする#1179のpatchが無い）で回し、各TPでもう1回リリースのimageで起動すると、NVIDIAのNVFP4に同じdecode検査のhash、編集の返答、NLLを返しました。止まった起動はありません。

| 3.3.0 | NVIDIA TP=2 | NVIDIA TP=3 | XSFP4 TP=2 | XSFP4 TP=3 |
|---|---|---|---|---|
| 起動の時間（s）：全項目の起動／2回目の起動 | 366／301 | 260／246 | 377／334 | 318／258 |
| decode検査 count／prose／code（tok/s） | 38.98／28.13／33.89 | 67.12／34.01／46.37 | 49.03／34.15／45.27 | 64.78／45.64／55.71 |
| MTPの受理長（同じタスク） | 3.066／1.882／2.621 | 4.645／1.858／2.954 | 3.276／1.796／2.971 | 3.362／1.947／2.823 |
| `bench --kinds decode`（tok/s、中央値） | 44.00 | 56.03 | 54.15 | 66.23 |
| `bench --kinds edit`（tok/s、中央値） | 71.33 | 90.99 | 82.76 | 106.43 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,411.2 | 1,559.7 | 1,415.1 | 1,717.3 |
| 199,307 tokenのprompt（s） | 155.0 | 140.3 | 151.9 | 127.9 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（s） | — | 399.5／1,064.9 | — | 373.0／1,015.7 |
| 約93,000 tokenのpromptを3秒で切る：次の要求が答えるまで（s）、切らないpromptの最初のtokenとの比べ | 0.36、切らずに68.8 | 1.29、切らずに62.8 | 0.32、切らずに68.6 | 0.91、切らずに56.7 |
| teacher-forced NLL、ja／en／code／math | 2.5412／2.9293／1.3145／0.6261 | 2.5285／2.9129／1.3158／0.6262 | 2.5494／2.9219／1.3104／0.6249 | 2.5369／2.9244／1.3098／0.6224 |
| tool引数ゲート越しのtool-eval-bench | 92 | 95 | 93 | 93 |
| 6,000 tokenのpromptの後に最大1,024 tokenの返答を40本（s、最も熱いzone） | 1,505、75.2 °C | 1,233、85.1 °C | 1,250、76.5 °C | 981、85.8 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 82.6／84.1 | 93.0／90.0／86.0 | 84.1／86.3 | 92.7／89.7／84.7 |
| 最低の `MemAvailable`、rankごと（GiB） | 11／13 | 18／20／26 | 11／13 | 21／22／28 |

- **3.2.0との差。** TP=2では、NVIDIAのNVFP4のtextの道は3.2.0のものです：decode検査のhash、190 roundの編集の返答、NLL（textごと）が3.1.0と同じで、`PARALLEL=` を空にした起動もcountで同じhashを出しました。decode、prefill、編集の返答の速さの動きは最大0.7%で、rank 0のprompt cacheは5.2 GiB（4.7）です。TP=3では、BF16のlinearが3.2.0のglueのkernelに代わって上流のtiledのkernelで回ります（上流1.1.2がTP=3のrankに開いた、issue #1067）：decode検査のhashとNLLは新しく（[検証](docs/validation.ja.md#decode検査)）、編集の返答は190 roundで3.2.0のままで1.3%速く（89.83に対して90.99 tok/s）、prefillは2.7%速くなりました（1,518.2に対して1,559.7）。
- **画像。** 全項目のどの起動でも、画像1枚のdraftありと逐次が同じでした。
- **XSFP4。** decode検査のhash、編集の返答、NLLはXSFP4自身の基準値です（[検証](docs/validation.ja.md#xsfp4)）。各TPで2回目の起動もhashと編集の返答が同じでした。速さはXSFP4自身の文の上の数です（[checkpoint](#checkpoint)）。
- **XSFP4の既知の振る舞い。** TP=3では、[検証](docs/validation.ja.md#応答を止める)のstop文字列の要求（1から1,000の数をtemperature 0で、`\n300\n` で止める）が、300の前で繰り返しに入り、4,000 tokenの上限まで走ります。上流1.1.1でも同じでした。TP=2と、NVIDIAのNVFP4の両TPでは300で止まります。TP=3では、「The capital of France is」へのXSFP4の8 tokenのgreedyの返答が、NVIDIAのNVFP4の「Paris is pronounced」に対して「Paris is spelled」で終わるので、prompt scoreとstructured outputの検査のplainな要求は、そこで自分のhashを持ちます（[検証](docs/validation.ja.md#xsfp4)）。
- **数を2度書くこと。** 1 tokenずつ生成させると、stop文字列の要求のような数え上げは時々1つの数を2度書き、その場所はcheckpoint・TP・build・書き始めの位置で変わります。NVIDIAのNVFP4でもTP=2とTP=3で起き、TP=2で最初から生成させると、3.3.0の確かめが読んだ150より先で152を2度書きます。上流1.1.1そのもののbinaryでも同じtokenです。この場所は、このエンジンではなくcheckpointのものです。同じ重みをfp32で計算してもNVIDIAのNVFP4はそこで152をもう一度選び、同じcheckpointのvLLMも同じ場所でほぼ同じ回数だけ数を外します。どの書き始めがどこで外れるかは、計算のしかた（TP・build・エンジン）で変わります。生成（1 tokenずつ）とprompt（まとめて）は違うkernelで計算され、このMoEのmodelでは、その小さな差が、点の近いexpertどうしが入れ替わるたびに育つためで、数を守るのがいつも片方とは限りません。壊れた1か所の値は見つかっていません。測りは[TensorFold #1214](https://github.com/ashhart/TensorFold/issues/1214)にあります。157の後に空白と157をもう一度書くのはNVIDIAのNVFP4・FP4-Local・XSFP4に共通で、その空白はprefillも選びます。MTPのdraftは何も変えません。
- **熱。** 天井が無いので、promptは最も熱いzoneが92 °Cを越えている間だけ、88 °Cまで待ちます。待ったのはTP=3の1,035,295 tokenのpromptだけです：NVIDIAのNVFP4は午後に、2秒の待ちを19回、計38秒待ち、最初のtokenは1,064.9秒（待ちを除くと1,026.9秒。3.2.0は1,022.9秒）。XSFP4は夜に、21回、計42秒待ちました。熱の見張りの停止に届いたzoneはありません。

**3.2.0**（2026-10-20、エンジン `1a8f1efd`、上流1.1.1、image `glm53-tf3:3.2.0`）。NVIDIAのNVFP4で、リリースのimageを、それ自身の `serve.sh`（既定でvisionのtowerを読み込みます）とこのリリースの `cluster.sh` で5回起動しました：TP=2で3回（うち1回は `PARALLEL=` を空に）、TP=3で2回。全containerを効率coreに置き、TP=3では `TF_GLM_MM=0` で、止まった起動はありません。

| 3.2.0 | TP=2 | TP=3 |
|---|---|---|
| 起動の時間（s、2回の起動） | 301／301 | 246／258 |
| decode検査 count／prose／code（tok/s） | 38.73／27.82／33.73 | 51.78／33.03／44.31 |
| MTPの受理長（同じタスク） | 3.066／1.882／2.621 | 3.368／1.787／2.839 |
| `bench --kinds decode`（tok/s、中央値） | 43.75 | 55.19 |
| `bench --kinds edit`（tok/s、中央値） | 70.85 | 89.83 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,408.1 | 1,518.2 |
| 199,307 tokenのprompt（s） | 154.4 | 140.5 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（s） | — | 398.7／1,056.9 |
| 約93,000 tokenのpromptを3秒で切る：次の要求が答えるまで（s）、切らないpromptの最初のtokenとの比べ | 0.42、切らずに68.8 | 1.53、切らずに62.6 |
| teacher-forced NLL、ja／en／code／math | 2.5412／2.9293／1.3145／0.6261 | 2.5246／2.9206／1.3147／0.6241 |
| tool引数ゲート越しのtool-eval-bench | 92 | 93 |
| 6,000 tokenのpromptの後に最大1,024 tokenの返答を40本（s、最も熱いzone） | 1,548、75.6 °C | 1,317、82.5 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 81.7／84.2 | 92.5／89.2／86.7 |
| 最低の `MemAvailable`、rankごと（GiB） | 13／12 | 22／24／29 |

- **3.1.0との差。** textの道は3.1.0のものです：towerを読み込んだまま、両TPでdecode検査のhash、190 roundの編集の返答、NLL（textごと）、tool-eval-benchの点が3.1.0と同じで、`PARALLEL=` を空にしたTP=2の起動（2本のstream）もcountで同じhashを出しました。decode、prefill、編集の返答の速さの動きは最大0.7%です。towerは両TPでrank 0に1.27 GiBを取り、TP=2の最低の `MemAvailable` は15 GiBから12 GiBに下がりました。
- **画像と動画。** 受け入れの中で、両TPで画像1枚のdraftありと逐次が同じでした。[検証](docs/validation.ja.md#画像と動画の入力)の画像と動画の検査は、同じ日の短い起動でTP=2とTP=3で通りました。
- **熱。** TP=3の起動は午後に回しました：1,035,295 tokenのpromptは、2秒の待ちを17回、計34秒熱で待ちました。10回はrank 0の最も熱いzoneが92.1〜92.5 °Cを読んだ時、7回は91.3〜91.9 °Cを読み、見込み（`TF_HEAT_CEILING`）で次のchunkが93 °Cを越えるとした時です。最初のtokenは夜に回した3.1.0より34秒遅くなりました。ほかに待った要求は無く、熱の見張りの停止に届いたzoneもありません。TP=3で切ったpromptの次の要求は1.53秒で答えました（3.1.0は0.25秒、3.0.0は1.49秒）。検査の上限（切らないpromptの最初のtokenの半分）の内です。

**3.1.0**（2026-10-20、エンジン `1a8f1efd`、上流1.1.1、image `glm53-tf3:3.1.0`）。NVIDIAのNVFP4で、`1a8f1efd` からbuildしたエンジンを、このリリースの `serve.sh` と `cluster.sh` と同じ起こし方で5回起動しました：TP=2で3回（うち1回は `PARALLEL=` を空に）、TP=3で2回。全containerを効率coreに置き、`serve.sh` の既定、TP=3では `TF_GLM_MM=0` で、止まった起動はありません。ほかにTP=2で全coreの起動を2回、熱の記録として回しました。リリースのimageは、それ自身の `serve.sh` とこのリリースの `cluster.sh` で各TPに1回起動し、decode検査で同じhashと同じ編集の返答を出しました。

| 3.1.0 | TP=2 | TP=3 |
|---|---|---|
| 起動の時間（s、2回の起動） | 301／301 | 540／247 |
| decode検査 count／prose／code（tok/s） | 38.85／27.72／33.84 | 51.59／32.43／44.14 |
| MTPの受理長（同じタスク） | 3.066／1.882／2.621 | 3.368／1.787／2.839 |
| `bench --kinds decode`（tok/s、中央値） | 43.80 | 55.05 |
| `bench --kinds edit`（tok/s、中央値） | 71.26 | 89.53 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,415.7 | 1,507.9 |
| 199,307 tokenのprompt（s） | 153.4 | 140.4 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（s） | — | 398.1／1,022.7 |
| 約93,000 tokenのpromptを3秒で切る：次の要求が答えるまで（s）、切らないpromptの最初のtokenとの比べ | 0.39、切らずに68.4 | 0.25、切らずに62.8 |
| teacher-forced NLL、ja／en／code／math | 2.5412／2.9293／1.3145／0.6261 | 2.5246／2.9206／1.3147／0.6241 |
| tool引数ゲート越しのtool-eval-bench | 92 | 93 |
| 6,000 tokenのpromptの後に最大1,024 tokenの返答を40本（s、最も熱いzone） | 1,536、74.9 °C | 1,315、79.8 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 81.8／83.6 | 90.8／89.3／85.5 |
| 最低の `MemAvailable`、rankごと（GiB） | 15／15 | 23／11／26 |

- **反復性。** 各TPの2回の起動はdecode検査で同じhashと同じ編集の返答を出し、`PARALLEL=` を空にしたTP=2の起動（2本のstreamを取りました）もcountで同じhashを出しました。TP=3はglueのkernelで、decode検査のhash、編集の返答、NLLが3.0.0と同じでした。TP=2はtiledのkernelで新しい値です（[検証](docs/validation.ja.md)）。
- **3.0.0との差。** 3.1.0のTP=2は同じ機種の別の対で回したので、3.0.0のTP=2との比べはエンジンとホストの違いが混ざります。TP=3は同じ3台です。`bench --kinds edit` は同じ返答を363 roundではなく190 roundで出し、TP=2で57%、TP=3で48%速くなりました。decodeはTP=2で4.3%速く、TP=3で1.0%遅く、prefillはTP=2で1.2%遅く、TP=3で3.6%速くなりました。TP=3の起動のloadの行は軽く（model 78.03 GiB、1本12.88 GiB、3.0.0は84.01と18.86）、それでも最低の `MemAvailable` は低くなりました。rank 1の11 GiBはtool-eval-benchの最中の2秒の1回の読みで、前後は24 GiBでした。
- **熱。** 熱で待った要求は無く、効率coreでは92 °Cを読んだzoneも無く、GPUは熱で遅くなりませんでした。1M tokenのpromptも含みます。全coreのTP=2では、40本の返答が1,535秒で終わり、rank 0のホストは93.0 °C（効率coreでは74.9 °C）、2つの要求の同時（`PARALLEL=2`、131,072 tokenの窓）は88.5 °Cで、どちらも止まりませんでした。

**3.0.0**（2026-10-18、エンジン `3d3d61d5`、image `glm53-tf3:3.0.0`）。NVIDIAのNVFP4で一つの受け入れの窓に5回の起動：各TPで2回と、TP=2で `PARALLEL=` を空にした1回。全containerを効率coreに置き、`serve.sh` の既定で、止まった起動はありません。受け入れの窓はimage `glm53-tf3:3x-bc82bc4` で回しました。リリースのimageはそれにエンジンの表示を足したもので、binaryは同じ（`/usr/share/doc/tf3/ENGINE`）、TP=2の起動でcountのhashと編集の返答も同じでした。

| 3.0.0 | TP=2 | TP=3 |
|---|---|---|
| 起動の時間（s、2回の起動） | 281／268 | 235／235 |
| decode検査 count／prose／code（tok/s） | 38.68／26.25／32.91 | 47.87／33.17／44.59 |
| MTPの受理長（同じタスク） | 3.34／1.879／2.747 | 3.048／1.787／2.839 |
| `bench --kinds decode`（tok/s、中央値） | 42.01 | 55.61 |
| `bench --kinds edit`（tok/s、中央値） | 45.40 | 60.69 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,433.5 | 1,454.9 |
| 199,307 tokenのprompt（s） | 152.7 | 150.2 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（s） | — | 425.4／1,082.9 |
| 約93,000 tokenのpromptを3秒で切る：次の要求が答えるまで（s）、切らないpromptの最初のtokenとの比べ | 0.32、切らずに67.8 | 1.49、切らずに66.6 |
| teacher-forced NLL、ja／en／code／math | 2.5293／2.9109／1.3138／0.6272 | 2.5246／2.9206／1.3147／0.6241 |
| tool引数ゲート越しのtool-eval-bench | 93 | 93 |
| 6,000 tokenのpromptの後に最大1,024 tokenの返答を40本（s、最も熱いzone） | 1,599、82.6 °C | 1,245、79.7 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 89.0／83.0 | 89.0／88.8／83.3 |
| 最低の `MemAvailable`、rankごと（GiB） | 16／16 | 30／30／36 |

- **反復性。** 各TPの2回の起動はdecode検査で同じhashを出し、`PARALLEL=` を空にした起動もcountで同じhashを出しました（エンジンはTP=2で1本のstreamを選びました）。draftした応答はserialと同じで、`bench --kinds edit` は両TPで同じ返答を出しました（[検証](docs/validation.ja.md)）。
- **熱。** 熱で待った要求は無く、92 °Cを読んだzoneも無く、GPUは熱で遅くなりませんでした。1M tokenのpromptも含みます。containerを全coreに置くと、同じimageの先の受け入れの窓は、tool-eval-benchの間にrank 0のCPUのzoneが96.1 °Cに達して止まり、40本の返答は7本目、94.7 °Cで止まりました。TP=2で全coreと比べると、decodeは1.0%、prefillは3.2%、200K tokenのpromptは2.7%遅くなりました（[効率coreにする理由](#配信の既定)）。
- **2.x系との差（参考）。** tokenはネイティブエンジン自身のものです。NLLは2.x系の基準値と領域ごとに最大0.021違います。2.9.2の `bench --kinds decode` はTP=2で42.96 tok/s、TP=3で57.25 tok/sでした。

## 制限

- **既定では一度に一要求。** それ以上には `PARALLEL` と、TP=2では小さい窓が要ります：524,288 tokenの窓には1本のstreamだけが入り（`PARALLEL=` を空にした時も1本）、`CONTEXT=245760` なら3本が入ります（[配信の既定](#配信の既定)）。
- **画像と動画はエンジンの制限の中で。** 画像は1要求に最大4枚で、送られた履歴にある画像を全部数えます（前のturnを画像ごと送り直すclientはそこに届きます）。4枚で4,096 tokenを分け合い、1枚10 MiB・1要求20 MiBまで。PNG・JPEG・WebPのdata URLで、GIFと動く絵は断ります。動画はuserのmessageだけで、1要求に2本（1本16 MiB・合わせて20 MiB・1時間まで）、1秒に2 frameで最大256 frameを取り、16,384 tokenを分け合います。0.5秒より短いclipは断ります。画像と動画のtokenは窓から取られます。HTTPSのURLには `serve.sh` が渡さない `--vision-urls` が要ります。音声のpartは400で断ります。
- **生成したtokenのlog確率は無い。** `logprobs` と `top_logprobs` は400で断ります。`prompt_logprobs` はstreamでない `/v1/completions` でだけ配信します。
- **`clear_thinking` はchat templateに渡りません。** ネイティブのserverがtemplateに渡すのは `enable_thinking`、`thinking_mode`、`reasoning_effort` だけです。XSFP4のchat templateは `clear_thinking` が無ければfalseとして扱い、クライアントが送り返した前のturnの推論を残します。前のturnを推論なしで送るクライアントには違いはありません。
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
                    decode-check・decode-divergence・score-nll・bench・long-input
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
- **エンジンはこの系列による上流のforkです。** 他の利用者にも役立つものは上流のTensorFoldへpull requestとして出し（#1016・#1017・#1018は1.1.1で上流自身のものになりました）、残りはリリースのbranchが持ちます。

## Next Action

各項目は、きっかけと、そのときこの系列がすることです。

- 上流がこの系列のpull request #1178（rank 0のNCCLのidをrankどうしの線で送る。上流はTPのbootstrap #636を閉じた）を取り込む → TP=3をその上で起動し、リリースのbranchからNCCLのidのファイルを外す。
- 上流がpull request #1050（FP4-Localの読み込み）をリリースに入れる → その上へ移り、リリースのbranchからそのcommitを外す。XSFP4をもう一度受け入れる。
- 3.3.0のエンジンは上流のpull request #1053（rank 0にstreamが無い間、待つrankが眠る。1.1.2に入った）を持つ。その後のリリースは効率coreで回したので、まだ開いている → containerにまだ効率coreが要るかを測り直す。
- `chat_template_kwargs.clear_thinking` → 2.x系と同じくchat templateに渡し、上流にも出す。

## ローカルデータと開発

Gitに入れないもの（自分の拠点の値を入れたrankとclusterのファイルを含む）、ライセンス、開発への参加は[リポジトリのREADME](../README.ja.md#ローカルデータと開発)にあります。3.x系の変更は[CHANGELOG.ja.md](CHANGELOG.ja.md)にあります。

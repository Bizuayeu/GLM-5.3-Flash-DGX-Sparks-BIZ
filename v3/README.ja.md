# NVFP4 BIZ 3.x（TensorFoldネイティブ）

[English](README.md) · [リポジトリの索引](../README.ja.md) · [配備の手順書](SETUP.ja.md) · [検証](docs/validation.ja.md) · [変更履歴](CHANGELOG.ja.md)

**NVFP4 BIZ** は、NVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointを、再学習も再量子化もせず配布のまま、DGX Sparkまたは互換のGB10機で配信します。3.x系はTensorFoldのネイティブエンジン、つまり[2.x系](../v2/README.ja.md)が動かすPythonのエンジンに代わったZigとCUDAのエンジンで、2台のTP=2または3台のTP=3で配信します。3.0.0が上流のTensorFold 1.0.12の上の最初のリリースで、3.1.0で上流の1.1.1へ移りました。2.x系も並んで続きます。

**BIZ**は保守者の印で、リポジトリの意図を示す語です。意味することと意味しないことは[リポジトリのREADME](../README.ja.md#biz)にあります。

## 要約

- **状況。** 3.1.0は2026-10-19〜20に参照機で、そこで測った[検証](docs/validation.ja.md)の基準値に照らし、固定したcheckpointでTP=2とTP=3で、containerを効率coreにして受け入れました（[リリースでの測定値](#リリースでの測定値)）。受け入れはリリースのcommitからbuildしたエンジンで回し、リリースのimageも各TPの1回の起動で、decode検査の同じhashと同じ編集の返答を出しました。主張の範囲はここまでです。他のホストは同じ検査を回して受け入れます。
- **何であるか。** 固定したcheckpointを、TensorFoldのネイティブエンジンの固定したcommitで一つのOpenAI互換endpointとして配信するための、build手順・起動の台本・受け入れ検査です。2台なら直結のConnectX-7リンクでTP=2、3台ならswitchなしのリングでTP=3です。公開している測定値はMSI EdgeXpert（MS-C931）で取りました。
- **反復性。** draftした応答はserialと同じで、起動は同じTPの前の起動のtoken idを出します。ネイティブエンジンのtokenはそれ自身のもので、2.x系のものではありません：kernelとBF16のKV cacheの丸めが違うので、二つの系列はtokenごとではなくteacher-forced NLLで比べます（[2.x系との違い](#2x系との違い)）。
- **構造化出力とpromptのscore。** JSON schemaつきの `response_format`、`required` か名指しの関数の `tool_choice`（GLM自身のtoolのmarkupで書く）、`/v1/completions` の `prompt_logprobs` は、1.1.1からGLMのCUDAのエンジンで上流のTensorFold自身のものです。この系列のpull request #1016・#1017・#1018の後に上流が書きました（[API](#api)）。
- **精度。** routed expertとdense MLPはW4A16、他はBF16、KVはBF16です（2.x系はFP8のKV cacheを持ちます）。NVIDIAのmodel cardは別のレシピ・別の機材でcheckpointを測っており、その精度表はこの配信を表しません。この配信を表す数字は[検証](docs/validation.ja.md)にあります。
- **ライセンス。** コードとエンジンはApache-2.0、重みはMITで運用者がダウンロードし、構造化出力のためにimageにxgrammar（Apache-2.0）が入ります。配信の経路に非商用の条件はありません（[ライセンスの早見表](../README.ja.md#ライセンスの早見表)）。
- **未検証。** 画像入力（`serve.sh` はエンジンを `--vision` 無しで起動します）、公開したAXLの重み、同時に2つ以上の要求（受け入れは一度に一つずつ送りました）、ハーネス連携（ZCode・Claude Code）、他のrank数と機材、アプリケーション全体の品質と本番の信頼性（[制限](#制限)）。

## 何であるか

- **重み**：`nvidia/GLM-5.3-Flash-NVFP4` のrevision `423acf37583782c51c142d145aef733d72943d93`（[`config/model.lock.json`](config/model.lock.json)）。1.x系・2.x系と同じで、[Z.aiのGLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)から作られています。routed expertとdense MLPはcheckpointのNVFP4 blockからW4A16で、attention・shared expert・headはBF16のまま計算します。
- **エンジン**：TensorFoldのネイティブエンジン（`tensorfold-native`）。[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/3.1.0` として公開するBIZ版です：上流のTensorFold v1.1.1に二つのcommitを足したものです。一つは熱の待ちの天井への見込み（`TF_HEAT_CEILING`、2.x系と同じ）。もう一つはTP=3のためにこの系列に留めるもので、rank 0がNCCLのidをファイルで他のrankへ渡し（`TF_GLM_NCCL_ID_FILE`）、各rankはその後、rankどうしの生存の線がrank 0に届くための `NCCL_COMM_ID` をNCCLの環境から外します。リングのpoint-to-pointの `/32` のアドレスでは、NCCLはそれで集まれないためです（上流のTPのbootstrap、pull request #636が入るまで）。imageは一つのcommitに固定します（[`config/engine.lock.json`](config/engine.lock.json)）。
- **image**：[`docker/Dockerfile`](docker/Dockerfile)。エンジンはNVIDIAのCUDA 13.3.1のbuild用imageで、lockが名指すZigのcompiler（SHA-256で確かめる）がcompileし、`libtfgrammar` は固定したcommitのxgrammarのreleaseからbuildします。実行のimageはCUDA 13.3.1にNCCL 2.30.7とRDMAのuserspaceです。2つのbaseのimageはdigestで固定しています。`/usr/share/doc/tf3/ENGINE` がエンジンのcommitと各binaryのSHA-256を名指し、`/usr/share/doc/tf3/engine/` にエンジンのライセンスと表示があります。
- **起動**：[`scripts/`](scripts/) のshellの台本と、rankごとの環境ファイル一つ（[`examples/`](examples/) に参照機のファイル）。順番は[SETUP.ja.md](SETUP.ja.md)にあります。ホストでは何もbuildしません：kernelはbinaryの中にあります。

## 必要な環境

- **ホスト**：DGX Sparkまたは互換のGB10機を2台か3台（Linux ARM64、各128 GBの統合メモリ）。GPUで他の大きな仕事を動かさないこと。同じホストで1.x系か2.x系のserverが動いていれば先に止め、全GPUを要求する2.x系のcontainerも止めます（[ホストを2.x系へ渡す](docs/operations.ja.md#ホストを2x系へ渡す)）。
- **fabric**：RoCE v2のConnectX-7リンク。2台は直結、3台はswitchなしのリング（[3台をリングにつなぐ](../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。各portの2本のrailを両方使います。
- **ホストカーネル**：1.x系・2.x系と同じです。今のDGX OSの更新が入れるカーネルは、既定のままでは複数ノードのRoCEを壊すことがあり、参照機は `kho=off` で起動しています（[ホストカーネルと複数ノードRoCE](../docs/hosts.ja.md#ホストカーネルと複数ノードroce)）。
- **GPUクロック**は全ホストで上限を設けます（[GPUクロックの上限](../docs/hosts.ja.md#gpuクロックの上限)）。上限と温度の記録は[`host/`](../host/README.ja.md)が据え付けます。3.x系の数字は全部この上限の下で測りました。
- **Docker**：NVIDIAのGPU runtimeとRDMAデバイスが要ります（`/dev/infiniband` が無いホストでは、NCCLがsocketに落ちるので `create_container.sh` が断ります）。
- **disk**：全ホストにcheckpointを丸ごと（1.x系・2.x系と同じ。[導入するものと対応機体](../v1/README.ja.md#導入するものと対応機体)）と、image。
- **操作する機械**：全ホストへSSHでき、`cluster.sh` を動かす機械一台。
- **Python 3.11以上**：各ホストで、この系列の道具（[`glm53_tf/`](glm53_tf/)：ダウンロード、検証、tool引数ゲート、検査）を `v3/` から動かします（[手順書 §2](SETUP.ja.md#2-checkoutとcheckpoint)）。

## はじめ方

各段とその後に確かめることは[配備の手順書](SETUP.ja.md)にあります。以下はTP=2のときの骨組みです。全ホストで同じ、確認済みの `v3.*` のtagを使います。

```sh
# 一度だけ、ある1台の v3/ からその仮想環境で。その後cacheを他のホストへ写し、写しごとに検証する（SETUP §2）
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait

# 1台がimageをbuildし、他はそれを読み込む。image IDを比べる（SETUP §3）
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.1.0 .

# 各ホストで、checkoutのルートから（SETUP §4）
v3/scripts/create_container.sh glm53-tf3:3.1.0 ~/glm53-tf3
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

**安全。** `serve.sh` はrank 0を `127.0.0.1` で待ち受けさせ、[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)もloopbackだけで待ち受けます。SSHのtunnel（`ssh -L 8095:127.0.0.1:8095 <rank 0>`）か、認証を足すproxyを通して使ってください。loopbackの外で配信する（rank 0のファイルで `HOST=0.0.0.0`）ときは、`API_KEY_FILE` も設定します：持ち主だけが読めるファイル（`chmod 600`。エンジンは他のmodeを断ります）に、1行に一つのkey（`label: key` かkeyだけ）を書きます。エンジンはファイルが変わると読み直します。すると `/health` 以外のすべてのrouteが `Authorization: Bearer <key>`（または `x-api-key: <key>`）を要し、`/health` は `{"status": "ok"}` だけを返します。この系列のdecode検査、`score-nll`、`bench`、`long-input` は、走らせる側で `TENSORFOLD_API_KEY` が設定されていればkeyを送り、tool引数ゲートはそのheaderをそのまま渡します。keyなしで `HOST=0.0.0.0` にすると、APIは認証なしで外に出ます。

## 配信の既定

[`scripts/serve.sh`](scripts/serve.sh) が持ち、全rankで同じです。

| 設定 | TP=2（2台） | TP=3（3台） |
|---|---|---|
| KV cache | latentとindexのkeyをBF16（エンジンが持つ唯一の形） | 同じ |
| draft | checkpointのMTP head（エンジンの既定） | 同じ |
| 窓（`--context`） | 245,760 token：各rankでモデルの隣に1本のstreamが収まるほぼ最大 | 1,048,576 token（モデルの上限） |
| 同時にdecodeする要求（`--parallel`） | 1（`PARALLEL=1`）。空の `PARALLEL=` ではエンジンに任せ、エンジンは起動時の空きメモリからstreamとprompt cacheの大きさを決める | 同じ |
| prompt cache（保持するpromptの状態、2,048 tokenのchunkの始まりごと） | 窓の残り：参照機で、起動時の空きメモリにより5.2〜6.3 GiB（rank 0のloadの行。3.0.0のエンジンでは4.4〜4.5 GiB） | 参照リングで16.0 GiB |
| 要求が指定しないときの応答の上限 | 32,768 token（`--max-tokens`） | 同じ |
| 要求が指定しないときの推論のeffort | `high`（`--reasoning-effort`） | 同じ |
| NCCL | 各リンク2本のrail・4 channel・IBのtransportを明示、rankごとのファイルから。rank 0のアドレスとportを `NCCL_COMM_ID` に | 2本のrail・4 channel・IBのtransportを明示・subnet-aware routing。rank 0のアドレスとportを `NCCL_COMM_ID` に（rankどうしの生存の線のためだけ）、rank 0のNCCLのidをファイルで渡す |
| BF16のlinear | 上流のtiledのkernel（エンジンの既定） | エンジンのglueのkernel（rankのファイルに `TF_GLM_MM=0`）：tiledのkernelはTP=3のrankのKDAの幅を断る（上流のissue #1067） |
| 熱によるprefillの休止 | prompt chunkの前ごとに全rankそろって、どれかのrankのACPIの最も熱いzoneが92 °Cを超えている間、全rankが88 °C以下になるまで待つ（`TF_HEAT_HIGH`・`TF_HEAT_LOW`）。そのzoneに、続けて流した直前のchunkの上がり幅を足すと93 °Cを越える間も待つ（`TF_HEAT_CEILING`） | 同じ |
| 画像入力 | なし：`serve.sh` は `--vision` を渡さないので、画像のpartは400で断られる（上流は1.1.0から、それがあればGLMのCUDAのエンジンで画像を読む。ここでは未検証） | 同じ |
| containerのcore | 最大周波数の最も低いcore：GB10の効率core、0-4と10-14（`create_container.sh`、`CPUSET`） | 同じ |

**一度に一要求にする理由。** `--parallel` を設定しないと、エンジンは8本のstreamを求めて収まるだけを配信するので、streamの数とprompt cacheに残る余地は、そのときの空きメモリによって起動ごとに変わります（TP=3では、ある起動が2本のstreamと0.1 GiBのprompt cacheを取りました）。2.x系と同じ1本のstreamなら、窓はどの起動でも同じで、prompt cacheは空きメモリの分だけ動きます（TP=2で5.2〜6.3 GiB）。TP=2では、3.0.0のエンジンは245,760 tokenの窓の隣に2本目のstreamが収まりませんでした（各rankで4.55 GiBが要り、rank 1には4.41 GiBでした）。3.1.0のエンジンは収まります：`PARALLEL=` を空にすると3.16 GiBのstreamを2本取り、prompt cacheは1本のときの6.3 GiBに対して3.1 GiBでした。

**TP=2を245,760にする理由。** BF16のKVは、tokenあたり2.x系のFP8のcacheの約2倍のメモリを取るので、対が持てる窓は2.x系の300,000 tokenより短くなります。245,760は、参照対で1本のstreamが収まるほぼ最大です。全rankのファイルの `CONTEXT` で別の値を選びます。

**効率coreにする理由。** エンジンは全rankで2本のCPUのthreadを空回りさせ続けます。rank 0ではdecodeの間、他のrankでは待つ間です：一つはGPUを待ち、もう一つはそのkernel時間から見てNCCLのものである見込みが高いthreadです。全coreでは、これらがCPUのthermal zone（GB10の7つのzoneのうち5つ）を温めました：約6,000 tokenのpromptの後の1,024 tokenの返答を40本続けると、3.0.0のエンジンでは、TP=2でrank 0の最も熱いzoneが94.7 °Cに達し、熱の見張りが7本目でエンジンを止めました。3.1.0のエンジンは全coreでも効率coreと同じ1,535秒で40本を終えましたが、rank 0のホストは93.0 °Cに達し（止める温度まで1 °C）、効率coreでは74.9 °Cでした。全coreで2つの要求を同時に回すと88.5 °Cでした。熱の待ちはprompt chunkの合間に働くので、これを抑えられません。効率coreでは40本の返答がそのzone 85.1 °Cで終わり、rank 1のホストは約70 °Cではなく57〜63 °Cで待ちました。その代わり速さの1〜3%を失い、起動は約25秒長くなりました（[リリースでの測定値](#リリースでの測定値)）。熱の帯を下げる（86/82/87）と、待ったpromptが26〜89%遅くなり、1,048,576 tokenのpromptの最高温度は下がりませんでした。空回りせずに眠るCUDAのcontextはdecodeが12%遅く、もう一つのthreadは空回りしたままでした。1.1.1から、上流の[runbook](https://github.com/ashhart/TensorFold/blob/v1.1.1/RUNBOOK.md)もこれらの測定からGB10の各rankに同じcoreを挙げています。`CPUSET=` でcontainerに全coreを与えます。

## 設定

配信は三か所で決まります。二つのファイルは [`examples/`](examples/) から写して自分の値に直し、Gitには入れないでください。

| 場所 | 設定 | 既定 | 意味 |
|---|---|---|---|
| rankのファイル（`/work/rank.env`、`serve.sh` が読む） | `MASTER` | なし（必須） | リンク上のrank 0のアドレス。全rankで同じ |
| | `NCCL_PORT` | `29583` | `NCCL_COMM_ID` の `MASTER` 上のrank 0のport：TP=2ではNCCLのbootstrap。rankどうしの生存の線は、どちらのTPでもその次のportを使う |
| | `ID_FILE`（TP=3） | `/work/nccl-id` | rank 0がNCCLのidを書き、他のrankがそれを読む場所（`cluster.sh` がホストの間で写す） |
| | `NCCL_IB_HCA`・`NCCL_IB_GID_INDEX`・`NCCL_SOCKET_IFNAME` | 参照機の値 | リンクのRDMAデバイス（両rail）、RoCE v2のGIDのindex、bootstrapのinterface |
| | `NCCL_NET`・`NCCL_IB_DISABLE`・`NCCL_IB_ROCE_VERSION_NUM`・`NCCL_IB_ADDR_FAMILY`・`NCCL_SOCKET_FAMILY`・`NCCL_MIN_NCHANNELS`・`NCCL_MAX_NCHANNELS` | RoCE v2とIPv4の上のNCCLのIBのtransport、4 channel | 2.x系と同じ（[2.x系の決定](../v2/docs/decisions.ja.md#fabric)）。TP=3はsubnet-aware routingと `NCCL_NET_PLUGIN=none` が加わります（[`tp3-rank0.env`](examples/tp3-rank0.env)） |
| | `NCCL_DEBUG`・`NCCL_DEBUG_SUBSYS` | `INFO`・`INIT,NET` | NCCLが起動時に各接続のtransportを一度だけ書き、[手順書 §5](SETUP.ja.md#5-起動)がそれを読みます |
| | `PARALLEL` | `1` | 同時にdecodeする要求。空ならエンジン自身の選択（[配信の既定](#配信の既定)）。全rankで同じ |
| | `CONTEXT` | TP=2で `245760`、TP=3で `1048576` | 窓。全rankで同じ |
| | `MODEL_NAME`・`HOST`・`PORT` | `glm-tf`・`127.0.0.1`・`8095` | rank 0のmodel idと待ち受け |
| | `REASONING_EFFORT` | `high` | effortを指定しない要求にrank 0が使うeffort（`low`・`medium`・`high`・`xhigh`・`max`。空：chat template自身のもの） |
| | `API_KEY_FILE` | なし | loopbackの外で配信するときのrank 0のkeyのファイル（上記） |
| | `CHECKPOINT` | `/hub` の下の固定snapshot | container内のcheckpointのdirectory。全rankで同じ |
| | `TF_HEAT_HIGH`・`TF_HEAT_LOW`・`TF_HEAT_CEILING` | `92`・`88`・`93`（°C） | prefillの熱の待ちとその見込み。天井には両方の帯が要る。空にすると無し。全rankで同じ |
| | `TF_GLM_MM` | 無し（tiledのkernel）。TP=3のexampleは `0` | `0` はBF16のlinearをエンジンのglueのkernelで回す。上流がissue #1067を直すまでTP=3に要る。全rankで同じ |
| `serve.sh` の引数 | `TP RANK RANK_ENV` の後 | なし | 既定の後ろで `tensorfold-native serve` に渡るので、こちらが勝ちます（`--context 131072`） |
| clusterのファイル（`cluster.sh`） | `TP`・`HOSTS`・`CHECKOUT` | なし（必須） | TPの大きさ、rank順のSSH名、各ホスト上のこのリポジトリのルート |
| | `SSH`・`CONTAINER`・`WORK` | `ssh -o ConnectTimeout=20`・`glm53-tf3`・`$HOME/glm53-tf3` | ホストへの入り方、container、`/work` に見せるホストのdirectory |
| `create_container.sh` | `IMAGE WORK_DIR`・`CONTAINER`・`HF_HUB` | なし（必須）；`glm53-tf3`・`~/.cache/huggingface/hub` | image、作業directory（rankのファイル・NCCLのid・log）、container名、`/hub` に読み取り専用で見せるHugging Faceのcache |
| | `CPUSET` | 最大周波数の最も低いcore（GB10では `0-4,10-14`） | containerのcore（[理由](#配信の既定)）。空なら全core、またはdockerの `--cpuset-cpus` に渡すリスト |

エンジンは起動時に設定をrankの間で比べ（draft、窓、prefillと熱の設定、checkpoint、binary）、違えば起動を断ります。rankのファイルは `bash` が全変数をexportしながら読むので、他の `TF_GLM_*`、`TF_HEAT_*`、`NCCL_*` の設定もエンジンに届きます。この表に無い設定は、この系列では測っていません。2.x系がPythonのエンジンに使った設定の多くは、ここでは読まれません：`TF_GLM_HEAT_*`（このエンジンのものは `TF_HEAT_*`）、`TF_GLM_CACHE_*`、`TF_GLM_KV`、`TF_GLM_COPY_DRAFTS`、`TF_GLM_B16_DECODE_TABLE`、`TF_GLM_LOOP_GUARD` です。

## API

rank 0がエンジンのHTTP APIを出します。受け入れで使ったもの：

- **`/v1/chat/completions`**：streamとそれ以外、toolつきで、[tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)越しと直接。
- **構造化出力**：`response_format` の `json_object` か `json_schema`、`tool_choice` の `required` か名指しの関数。エンジンはこれをGLMのtoolのmarkup（`<arg_key>`、`<arg_value>`）のgrammarにします。どちらもimageが持つ `libtfgrammar` が要ります。grammarと必須のtool呼び出しを組み合わせた要求は400で断ります。
- **`prompt_logprobs`**：streamでない `/v1/completions` で、promptのtokenのlog確率を、それぞれ最大20の候補つきで。NLLの検査がこれを使います。このような要求はprompt cacheから再開しません。
- **思考**：`reasoning_effort` をtop levelか `chat_template_kwargs` で。`none` で思考を切り、effortを指定しない要求は `high` になります（[配信の既定](#配信の既定)）。streamでは `reasoning_content` と `content` は別々のdeltaで届きます。
- **`"draft": false`**：要求のbodyに入れると1 roundに1 tokenずつdecodeします。draftした応答が一致すべきserialの基準です。
- **応答のblock**：`tensorfold`（`token_sha256`＝推論を含む応答のtoken idのhash、`prefill_seconds`、`time_to_first_token`、`tokens_per_second`、`sampling`、`drafts`）と `speculative`（`rounds`、`drafted`、`accepted`、`acceptance_rate`、`tokens_per_round`）。prompt cacheから再開したtokenは `usage.prompt_tokens_details.cached_tokens` に入ります。応答はtoken idも熱の待ちの時間も運びません：待つごとの秒数はrank 0のlogの `heat_wait_s` の行にあります。
- **`/health`**（`live`：接続、待っている要求、直近の数秒のdecodeとprefillの速さ）、**`/v1/models`**、**`/tokenize`**、**`/metrics`**（Prometheus。decodeのroundやクライアントの切断を含む）。
- **停止**：クライアントの切断かstop文字列で応答が終わります。rank 0はroundの合間に接続を確かめ、他のrankはrank 0が送る段だけを走らせます。

エンジンは `/v1/responses` とAnthropicの `/v1/messages` にも、同じchatの経路で答えます。受け入れではこれらを確かめていません。GLMのCUDAのエンジンでは、生成したtokenの `logprobs` と `top_logprobs`（400）、`serve.sh` のように `--vision` 無しで起動したときの画像・音声・動画のpart（400）、`/v1/decisions`（400）を断ります。

## 2.x系との違い

| | 2.x（TensorFoldのPythonのエンジン） | 3.x（TensorFoldのネイティブエンジン） |
|---|---|---|
| エンジン | TensorFold 0.6.5のBIZ版。PythonとTritonのkernelで、kernelは実行時にcompile | TensorFold 1.1.1のBIZ版（3.0.0は1.0.12）。ZigとCUDAで、kernelはbinaryの中 |
| 出力の反復性 | エンジンの契約として、draftした応答はserialと同じ、再開したpromptは最初からと同じ、chunkの切り方で結果が変わらない | draftした応答はserialと同じで、起動はtoken idを繰り返す。tokenは2.x系のものと違う（別のkernel、BF16 KV）ので、系列の間はNLLで比べる |
| KVと窓 | latentとindexのkeyをFP8。TP=2で300,000 token、TP=3で1,048,576 | BF16。TP=2で245,760 token、TP=3で1,048,576 |
| 同時の要求 | 1 | 既定で1。`PARALLEL` で、窓が残すメモリの中で、エンジンがdecodeのroundをより多くの要求に分ける |
| prompt cache | 8本、3 GiB（`TF_GLM_CACHE_*`） | 窓の残りに、chunkの始まりの状態を保つ（TP=2で5.2〜6.3 GiB、TP=3で16.0 GiB）。本数の上限は無い |
| 画像入力 | 受ける（`VISION=1`） | 断る（`serve.sh` は `--vision` を渡さない） |
| 公開したAXLの重み | 任意で使える | 未検証 |
| 構造化出力、必須のtool呼び出し | 受ける。imageにxgrammar | 受ける。imageにxgrammarの `libtfgrammar`。必須のtool呼び出しはGLMのmarkupで |
| `prompt_logprobs` | 受ける | streamでない `/v1/completions` で受ける |
| `clear_thinking` | 従う | chat templateに渡さない（[制限](#制限)） |
| 応答の欄 | `tensorfold` に `accepted`・`drafted`・`rounds`・`cached`・`prefill_s`・`heat_wait_s`・`sha256` | `tensorfold` と `speculative`（上記）。cacheしたtokenは `usage` に。熱の待ちはlogだけ |
| 熱の設定 | `TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW`・`TF_GLM_HEAT_CEILING` | `TF_HEAT_HIGH`・`TF_HEAT_LOW`・`TF_HEAT_CEILING`、同じ値 |
| imageとcontainer | `glm53-tf`、extensionをcontainerごとにbuild（`build_ext.sh`） | `glm53-tf3`、ホストでは何もbuildしない |
| containerのcore | 全core | `CPUSET` が別に言わなければ効率core |
| tool引数ゲート | エンジンの前のゲート | 同じゲート、この系列の写しを `v3/` から起動 |

二つの系列のcontainerはどちらも全GPUを要求するので、エンジンは一度に一つの系列だけを動かします（[運用](docs/operations.ja.md#ホストを2x系へ渡す)）。

## リリースでの測定値

**3.1.0**（2026-10-20、エンジン `1a8f1efd`、上流1.1.1、image `glm53-tf3:3.1.0`）。固定したcheckpointで、`1a8f1efd` からbuildしたエンジンを、このリリースの `serve.sh` と `cluster.sh` と同じ起こし方で5回起動しました：TP=2で3回（うち1回は `PARALLEL=` を空に）、TP=3で2回。全containerを効率coreに置き、`serve.sh` の既定、TP=3では `TF_GLM_MM=0` で、止まった起動はありません。ほかにTP=2で全coreの起動を2回、熱の記録として回しました。リリースのimageは、それ自身の `serve.sh` とこのリリースの `cluster.sh` で各TPに1回起動し、decode検査で同じhashと同じ編集の返答を出しました。

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

**3.0.0**（2026-10-18、エンジン `3d3d61d5`、image `glm53-tf3:3.0.0`）。固定したcheckpointで一つの受け入れの窓に5回の起動：各TPで2回と、TP=2で `PARALLEL=` を空にした1回。全containerを効率coreに置き、`serve.sh` の既定で、止まった起動はありません。受け入れの窓はimage `glm53-tf3:3x-bc82bc4` で回しました。リリースのimageはそれにエンジンの表示を足したもので、binaryは同じ（`/usr/share/doc/tf3/ENGINE`）、TP=2の起動でcountのhashと編集の返答も同じでした。

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

- **既定では一度に一要求。** それ以上には `PARALLEL` が要ります。TP=2の245,760 tokenの窓には半分のprompt cacheで2本のstreamが入り、それより多くには小さい窓が要ります（[配信の既定](#配信の既定)）。
- **画像入力は無い。** `serve.sh` は `--vision` を渡さず、エンジンは画像・音声・動画のpartに400で答えます。上流のエンジンは1.1.0から `--vision` でGLMのCUDAの経路でも画像を読みますが、この系列はそれを受け入れていません。2.x系は画像を読みます。
- **生成したtokenのlog確率は無い。** `logprobs` と `top_logprobs` は400で断ります。`prompt_logprobs` はstreamでない `/v1/completions` でだけ配信します。
- **`clear_thinking` はchat templateに渡りません。** ネイティブのserverがtemplateに渡すのは `enable_thinking`、`thinking_mode`、`reasoning_effort` だけです。固定のtemplateは `clear_thinking` が無ければfalseとして扱い、クライアントが送り返した前のturnの推論を残します。前のturnを推論なしで送るクライアントには違いはありません。
- **どのrankも2つのCPUのcoreを空回りさせ続けます。** rank 0はdecodeの間、他のrankは待つ間です。containerの既定のcoreは、3.0.0のエンジンでは速さの1〜3%と引き換えに（3.1.0のエンジンでは40本の返答は同じ時間で、起動は約40秒長い）、CPUのzoneを熱の見張りが止める温度より下に保ちます。全coreでは、返答の長い連続が3.0.0のエンジンではそこに達し、3.1.0のエンジンでは1 °C手前まで来ました（[効率coreにする理由](#配信の既定)）。
- **BF16 KV** は、GiBあたり2.x系のFP8のcacheより短い窓しか持てず、2.x系のFP8の経路はこのエンジンにありません。
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
  config/           model.lock.json（固定のcheckpoint）、engine.lock.json（エンジンのcommit、Zigの
                    compiler、xgrammar）、axl.lock.json（公開したAXLの重み）、nll_set.json（NLL採点セット）
  requirements/     huggingface.lock.txt：ダウンロードとその検証に使うHugging Faceのclient
  docker/           Dockerfile：image。エンジンは ENGINE_REF で固定
  scripts/          create_container.sh  各ホストの配信用container
                    cpuset.sh            そのcore（CPUSET）：既定は最大周波数の最も低いもの
                    serve.sh             1 rank、配信の既定つき
                    cluster.sh           操作する機械から全rankを起動・停止・状態確認
                    hostwatch.sh         メモリの見張り（MemAvailableが5 GiBを切るとエンジンを止める）
  examples/         参照機のrankのファイルとclusterのファイル（TP=2とTP=3）
  docs/             validation.md  受け入れの検査と基準値
                    benchmarks.md  リリースの値の取り方
                    operations.md  失敗と日常の作業：止まったrank、新しいimage、ホストを2.x系へ渡す
  tests/            glm53_tf/と、これらの頁が引く事実のCPUテスト
  pyproject.toml    3.x系の版
```

## 免責事項

- **BIZは意図であり、約束ではありません**（[リポジトリのREADME](../README.ja.md#biz)）。
- **受け入れは参照機のものです。** 他のホストや別のimage IDでの起動は、そこで[検証](docs/validation.ja.md)を回して受け入れます。
- **エンジンはこの系列による上流のforkです。** 他の利用者にも役立つものは上流のTensorFoldへpull requestとして出し（#1016・#1017・#1018は1.1.1で上流自身のものになりました）、残りはリリースのbranchが持ちます。

## Next Action

各項目は、きっかけと、そのときこの系列がすることです。

- 上流がissue #1067（TP=3のrankのKDAの幅でのtiledのBF16のlinear）を直したリリースを出す → その上へ移り、TP=3のrankのファイルから `TF_GLM_MM=0` を外し、既定のkernelでTP=3を受け入れ直す。
- 上流のTPのbootstrap（pull request #636）が入る → TP=3をその上で起動し、リリースのbranchからNCCLのidのファイルを外す。
- 上流がpull request #1053（rank 0にstreamが無い間、待つrankが眠る）を取り込む → 3.x系のリリースで従い、containerにまだ効率coreが要るかを測り直す。
- `chat_template_kwargs.clear_thinking` → 2.x系と同じくchat templateに渡し、上流にも出す。
- ネイティブエンジンでの画像入力（`--vision`、1.1.0からGLMのCUDAのエンジンでの上流のもの）と公開したAXLの重み → 2.x系と同じく受け入れる。

## ローカルデータと開発

Gitに入れないもの（自分の拠点の値を入れたrankとclusterのファイルを含む）、ライセンス、開発への参加は[リポジトリのREADME](../README.ja.md#ローカルデータと開発)にあります。3.x系の変更は[CHANGELOG.ja.md](CHANGELOG.ja.md)にあります。

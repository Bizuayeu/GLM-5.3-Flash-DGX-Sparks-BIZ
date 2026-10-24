# 運用手順

[English](operations.md)

通常運用として何を受け入れたか、各項目の証拠がどこにあるかは[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)が記録します。本書はランチャーの動かし方を扱います。

## ランチャーは一つ

checkoutの起動経路は `python -m glm53_setup server …` の一本です。[起動設定TOML](server-configuration.ja.md)で動き、稼働中の起動がある場合は[切替・復旧手順](launch-safety.ja.md#全レール検査と両rankの切替)がこれを包みます。本リポジトリの全モデル実測はすべてこの経路で行い、起動前に行う検査は下記の[起動検査](#フルモデルの起動検査)です。

## 資材の保管場所とパス

本節がデプロイ時の保管パスの正典です。モデルID・revision・base imageのdigestは[runtime.lock.json](../config/runtime.lock.json)で固定します。本体checkpointは上流から取得し、任意のLPA projectorは独立したGitHub Release添付物として配布します。運用者固有のホスト名、home配下の絶対パス、認証情報は公開ソースの外に置いてください。

| 資材 | 各Linuxホストでの既定の場所 | 役割 |
|---|---|---|
| 本体checkpoint | `$HOME/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/<revision>/` | 固定したモデル・config・tokenizerのview。重みファイルは同階層の `blobs/` ディレクトリへリンクし、データ本体はそちらが持つ |
| MTPメタデータview（配布既定で必要） | `$HOME/.cache/huggingface/local-views/glm53-mtp-compatible/<revision>/` | 既存のtensorデータをリンクし、checkpoint同梱のBF16 MTPに合わせて量子化メタデータを調整する。元のsnapshotを編集せずに[viewを作成](speculative-decoding.ja.md#各linuxホストでの準備)する |
| LPA projector（`lpa.enabled = true` のとき必要。テンプレートは無効） | `<checkout>/state/lpa/glm53-lpa-cut32-v1/projector.pt`。[起動設定TOML](server-configuration.ja.md)の`[lpa].projector`に、そのTOMLからの相対パスまたは絶対パスを指定 | NVIDIAのsnapshot・ソース配布物とは別のRelease添付物。すべてのホストで[取得・hash検証](lpa.ja.md#学習済みprojectorの取得)するか、対応するprojectorを学習する。[有効化](lpa.ja.md#起動profileでlpaを有効にする)はprofile編集と切替を伴う別手順。通常の推論とbatchingには不要 |
| Dockerのbase／reference image | Dockerが管理する保管領域 | 固定したbaseをpullし、本ソースからreference imageをビルドする。ソースのcheckout、image、checkpointは別々の資材 |
| ローカル設定と取得状態 | `<checkout>/state/` | サイト固有の起動設定と `download-status.json`。後者は実際に取得した `snapshot` のパスを記録する |
| runtime／JIT cacheと証跡 | `<checkout>/state/tp2-runtime-cache/`（[3ノード](#3ノード)では `tp3-runtime-cache/`）、`<checkout>/records/` | 再生成できるruntimeデータと非公開の実行記録。モデル重みでも配布物の入力でもない。分散起動はTriton・TileLang・TorchInductorのcacheとCUDA driverのJIT cache（`CUDA_CACHE_PATH=/root/.cache/nv`。指定しなければcontainer内の `~/.nv/ComputeCache`）をruntime cacheへ向け、コンパイル済みkernelを再起動後も残す。それでもコンパイルされるものは[warmup ladder](#warmup-ladder)が記録する |

LPA添付物の展開後の構成は次のとおりです。`manifest.json`は[projector lock](../config/lpa-projector.lock.json)の写しです。ソースcheckoutのアーカイブに、このディレクトリは含まれません。

```text
state/lpa/glm53-lpa-cut32-v1/
├── projector.pt
├── manifest.json
├── README.md
├── README.ja.md
├── LICENSE
├── NOTICE
├── TRAINING_DATA.md
├── TEACHER_MODEL_CARD.md
└── LICENSES/
    └── ZAI-GLM-MIT.txt
```

ソースアーカイブには`state/`と`records/`も意図的に含めません。serverランチャーを使う前に、新しいcheckoutから各ホストの永続領域へsymlinkを作成します。

```sh
ln -sT /srv/glm53/state /srv/glm53/source/state
ln -sT /srv/glm53/records /srv/glm53/source/records
readlink -f /srv/glm53/source/state /srv/glm53/source/records
```

絶対パスを使います。`-T` を付けると既存ディレクトリの中に `state/state` を作らず失敗で止まり、`readlink -f` は `/srv/glm53/state` と `/srv/glm53/records` を表示するはずです。`state/state` や `records/records` で終わるパスが出たら入れ子です。復旧用に旧checkoutを保持してください。認証情報や生の記録をソースアーカイブへ置きません。

実験用の起動ランチャーは、ホスト既定のHugging Face cacheを読み、containerの `/hf` へ読み取り専用でmountします。選択したsnapshotまたはMTP viewは、そのmount内で解決します。モデルcache全体の `blobs`／`snapshots` の関係を保ってください。snapshotディレクトリだけを複製しても足りません。すべてのホストのディスクに完全なcheckpointが必要です。TPが分割するのはロード済みのtensorであり、ダウンロードしたファイルではありません。

ダウンローダーはHugging Faceのcache環境設定に従いますが、現行のランチャーは既定のcache rootを前提とします。本リリースでは、これらの資材を取得する際に `HF_HOME`／`HF_HUB_CACHE` を設定せず、文書化した既定の場所を使ってください。任意のcacheへのダウンロードが成功しても、ランチャーがそれを見つけてmountできることの証明にはなりません。

ダウンロードを始めずに、想定される場所と記録された場所を確認します。各Linuxホストのcheckoutの `v1/` で実行してください。

```sh
python -c 'from pathlib import Path; from glm53_setup.config import MODEL, REVISION; print(Path.home() / ".cache/huggingface/hub" / ("models--" + MODEL.replace("/", "--")) / "snapshots" / REVISION)'
python -c 'import json; from glm53_setup.config import STATE; s = json.loads((STATE / "download-status.json").read_text()); print(s.get("status"), s.get("snapshot", "not recorded"))'
```

2つ目のコマンドは、このcheckoutで取得が登録済みであることを前提とします。表示されたパスも `status=complete` も、checksum検証の代わりにはなりません。起動設定は、すべてのホストで実際にビルドして確認したimageを指す必要があります。

## 一度取得して検証する

`config/runtime.lock.json` の固定revisionを使います。`download` はHugging Face cacheの既存ファイルを再利用し、同じcheckout内でのダウンロード重複を防ぎます。`verify-download` は公式のchecksum検証を実行し、メタデータのためにHugging Faceへ接続する場合があります。推論がオフラインであることと、checksum検証がオフラインでできることは別です。

2台目へは、モデルの `blobs` と `snapshots` のツリーを完全な形でまとめて移送します。snapshotは `blobs` へのリンクを含むため、snapshotだけを複製・mountするとリンクが切れることがあります。既存のcacheファイルは保持し、削除同期のオプションは使いません。

移送後、そのcheckoutで固定snapshotを登録・確認するために `download` を一度実行します。一致するcacheファイルは再利用し、不足分は取得される場合があります。続いて `--wait` なしで `verify-download` を実行します。ファイルサイズだけで移送成功と判断しません。

200 GBのハッシュ計算はページキャッシュを埋め、それはGPUと同じunified memoryを使います。Spark 2台の他レシピでは、GPUが遊んでいる状態のchecksum検証9回中2回で電源が落ちたと報告されています（tonyd2wild PR #19、コードは採用しない）。検証はモデルを読み込む前に行い、稼働中の対の横では行わないでください。稼働中のホストでの大きな読み出しも規模は小さいが同じ向きに効きます。9.7 GiBの参照imageをpeer rankから書き出したとき、MemAvailableは8.8 GiB以上を保ったまま、MemFreeは3.0 GiBから0.87 GiBまで下がりました。NVIDIAのcheckpointの後続revision `09b04e5e`（2026-09-11）と固定revisionの差は `README.md` だけです。

## 各ホストの準備

まず全ホストを[ホストの準備](../../docs/hosts.ja.md)のとおりに整えます。カーネルとドライバー、GPUクロックの上限です。

1. 空きメモリ、ディスク、GPU・ドライバー、稼働中のモデルプロセス、ホストの状態を確認する。GLMを起動する前に、別のモデルはそれぞれの文書化された手順に従って停止する。
2. 各ホストで `prepare-image` を実行する。固定したARM64 baseをpullし、実際のパッケージ版数、GPU計算、GLMの登録状況を記録する。baseのnative NoPE経路は、検収済みの提供経路ではない。
3. `build-reference` でreference imageを一度だけビルドする。base digestはロックから取る。複製する場合は、検証済みのローカル回線越しにDockerのimage save/loadを使い、実際のimage IDを比較する。
4. [GPU 1台のfixture手順](component-validation.ja.md#gpu-1台のfixtureを再現する)を実施する。image、精度、sourceのhash、生成した記録をまとめて保存する。

Dockerのoverlay2は、約125層を超えるimageを読み込めません。受け取る側のホストで `docker load` が `max depth exceeded` で失敗します（MiaAI-Labのレシピ #301〜#304、そのimageは126層に達していました）。`build-reference` は、ビルドしたimageの層数（`RootFS.Layers`）、この上限、残りの余裕を記録の `image-layers.json` に書き、123層を超えると警告します。123はそのレシピのテストが課す予算です。

## ネットワークとサイト設定

物理接続と永続的なIPv4設定は、[QSFPのハンズオン手順](../../docs/qsfp-network.ja.md)に従います。

各ホストで実測した値を、[起動設定TOML](server-configuration.ja.md)の `[nodes]` 節に記録します。同じファイルをすべてのホストに置きます。

- 自機のfabric IPv4（headのものは最初のノードの値）、Ethernet interface、RDMAのHCA、そのinterfaceのRoCEv2 GID index
- 3台のリングでは代わりに、他ノードごとに1つの `links` の項目と、各ホストの `host_address` と `host_interface`（[3ノード](server-configuration.ja.md#3ノード)）
- `[api]` の未使用のAPIポートとrendezvousポート

HCAとGIDの番号は、両ホストで一致している必要はありません。GIDが自機のIPv4とnet deviceに対応することを確認してください。MTU 9000は、両端と経路全体が対応する場合にだけ使います。フルモデルをロードする前に、実際のNCCL transportとcollectiveの正当性を検証します。SSHで接続できることはRDMAの試験ではありません。これらの値は `server plan` と `server preflight` が検査します（[起動検査](#フルモデルの起動検査)）。

## フルモデルの起動検査

`server preflight --rank N` は各ホストで、固定snapshotとMTP view、fabric設定、選択したimage IDと機能marker、LPA有効時のprojector checksum、他のコンテナがGPUを使っていないこと、空きメモリを検査します。`server start` も同じ検査を行い、失敗があれば起動しません。合格したときは検査結果・設定・containerコマンドを `records/<timestamp>-server-r<N>/` に保存します。`server plan` はそのコマンドを何も起動せずに表示し、`preflight` は検査結果をJSONで表示して、一つでも失敗すれば非ゼロで終了します。`cluster switch` は、稼働中の起動を止める前と新しい起動を始める前に、全rankでこの検査を繰り返します。

`server preflight` はimageの機能markerも検査します。有効な機能はそれぞれ、[imageの契約](server-configuration.ja.md#現行イメージの契約)に挙げたmarkerをimageの環境変数に見つけなければなりません。一つのmarkerには復旧のための例外があります。`runtime.canonical_moe_order = true` の場合、新規の起動には `GLM53_MOE_ORDER_API=2` が必要です。marker 1は、token整列のbuffer長を誤っていた以前のimageも持っているためです。marker 1のimageを指すprofileは、`server preflight`・`server start`・`cluster switch` の停止前検査で `moe_order_support` が不合格になります。参照imageを作り直し、`reference_image` を更新してください。すでにmarker 1のimageで稼働している対が取り残されることはありません。切替はその対を復旧先として検査し、新しい対が失敗した場合はmarker 1のまま再起動して、rankの `warnings` に `moe_order_marker_1_accepted_for_recovery` を記録します。稼働中のmarker 1の対のprofileに同じ読み取り検査を手で行う場合は、`server preflight` に `--recovery` を付けます。このflagは切替の復旧経路のためのもので、古いimageを新規に起動する手段ではありません。

六つのbuild時patchが上流vLLMの不具合を直しており、固定しているvLLMが上流の修正より先へ進んだら外します。七つ目は、この機材で重みの読み込みが遅いことへの回避策です。どれもほかのbuild時patchと同じくsourceのSHA-256を照合します。各markerをどのimageが持つか、どの検査もそれを要求しないことは、[imageの契約](server-configuration.ja.md#現行イメージの契約)にあります。

- `GLM53_SLOT_MAPPING_GUARD=1`（`glm53_setup/runtime/patch_slot_mapping.py`、vLLMのissue #53982）：slot対応付けのkernelが、block tableを行の中だけで読みます。これがないと、公開した任意設定はある長さを超える要求で失敗します（[閾値と実測](benchmarks.ja.md#基準の2台の配信profile)）。
- `GLM53_KPOOL_SEED_STRIDE=1`（`glm53_setup/runtime/patch_kpool_seed.py`、vLLMのpull request #57477と同じ変更）：kpoolのprefill seed kernelが、indexerの生tailのblockをtail自身のstrideで番地付けします。これがないと、prefillのたびに要求自身のtail blockがseedされず、最後のtokenのkeyとgateが番号の小さいindexer blockへ書き込まれます。そのblockは別の要求のものであり得ます。壊れるのは長い文脈での疎なtop-kの選択で、prefix cacheから再利用する長いpromptで最も効きます。基準の2台では、patchを入れても測った出力は一つも変わりませんでした（[実測](benchmarks.ja.md#1130での測定)）。
- `GLM53_KPOOL_RING=1`（`glm53_setup/runtime/patch_kpool_ring.py`、vLLMのpull request #58454と同じ変更）：indexerの生tailのringを、1 pool分ではなく、MTPの深さkに対して `kpool * next_power_of_2(ceil((kpool + k) / kpool))` slotにします。MTPなしは4（従来どおり）、k = 1〜4は8、k = 5は16です。これがないと、kが2以上のとき、poolを完成させるdraftが棄却されると、その後ろのdraftが上書きした後のkeyからやり直すことになり、indexer cacheに誤った圧縮keyが入ります。壊れるのは、文脈が `index_topk`（2,048 token）を超えた後にdecode中に作られるpoolでの疎なtop-kの選択です。長さがpromptから来てもoutputから来ても同じです。kernelのfileへは `patch_kpool_seed` の後にだけ当たります（固定するhashはseed patchの出力）。上流はこれを部分的な修正とし、続く変更を予定しています。kernelの再現手順は[部品検証](component-validation.ja.md#kpool-tail-ringの再現)にあります。2026-09-26にGB10で、1 pool分のringは棄却されたdraftの後で投機なしの参照と食い違い、8 slotのringは一致し、上流のkernelテストも通りました（33件、skip 1件）。基準の2台（MTP k=3）では、tailのgroupが8 slotになり（`kv cache group sizes [4608, 8, 4608, 4608, 4608]`）、2,048 tokenのpromptでdecode中に作るpoolがすべて `index_topk` を超えるdecode検査3種は、どれも出力が変わり、反復はbit単位で一致したままでした（[実測](benchmarks.ja.md#1190での測定)）。
- `GLM53_SAMPLER_VOCAB_BOUND=1`（`glm53_setup/runtime/patch_sampler_nonfinite.py`、上流で未マージのvLLMのpull request #50843）：Gumbel sampler、rejection samplerのgreedyの統計とその再サンプリングが、tileのargmaxを語彙の範囲に収めます。これがないと、最後のtileが非有限のlogitだけの行は語彙の外のidを出すことがあり、embeddingはそれを0として読みます。MTPではrejection samplerがtemperature 0でも動きます。
- `GLM53_IMAGE_BUDGET_EXACT=1`（`glm53_setup/runtime/patch_image_budget.py`、固定より後にmergeされたvLLMのpull request #59565）：GLM-5.3-Flashのprocessing infoが、encoder cacheにprocessorのtoken上限ちょうどの大きさを、正確に分解して与えます。これがないと、継承した正方形の試算が上限より小さく収まり、起動logに小さいほうの予算が出て、その2つの大きさの間の画像がHTTP 400で拒まれます（両方の予算と起動logの行は[画像入力](vision.ja.md#限界と未解決の事項)）。
- `GLM53_VISION_ROPE_TABLE=1`（`glm53_setup/runtime/patch_vision_rope.py`、固定より後にmergeされたvLLMのpull request #59126）：vision towerのrope表を8,192行から`max_position_embeddings`行（1,048,576）にし、host→deviceの2つの写しをpinned memory経由にします。これがないと、token上限に収まるのに格子の一辺が8,192を超える細長い画像が表の外を読み、エンジンごと落ちます（[画像入力](vision.ja.md#限界と未解決の事項)）。古い表に収まる格子の画像は、出力が変わりません。
- `GLM53_LOAD_CLONE=1`（`glm53_setup/runtime/patch_load_clone.py`）：既定のsafetensorsの読み込みで、loaderがGPUへ送る前に各tensorを匿名メモリへcloneします。GB10でCUDA contextがある状態では、checkpointのfile mappingからの転送は約0.16 GiB/s、cloneしてからの転送は約1.55 GiB/sでした（GB10 1台、shardの3 GiB分を各回、2026-09-26）。基準の2台のrank 0は、1.18.0で重みの読み込みに532秒かかっていました。cloneが持つのは一度にtensor 1個分です。vLLMの `--safetensors-load-strategy eager` はこの機材では代わりになりません。読み込み中にshardを丸ごと二重に持ち、基準の2台で片方のrankがメモリを使い切りました（[eagerの試行](benchmarks.ja.md#1190での測定)）。`enable_multithread_load` も同じくshardを丸ごと持ちます。`prefetch` は効きません。遅いのはfile-backedのページからの転送で、page cacheに載っていても同じです。

`exclusive_gpu` は、このランチャーの `glm53.experiment.startup` ラベルを持たない稼働中のコンテナがGPUを要求していると不合格になり、該当するコンテナを結果の `foreign_gpu_containers` に並べます。GPUの要求は `HostConfig.DeviceRequests` が空でないことで判定します。`--gpus` とCDI（`--device nvidia.com/gpu=...`）の要求はどちらもここに表れ、GPUのデバイスノードは `Devices` には表れません。このランチャーの対はfingerprintによらずラベルを持つので、旧い対が動いたままでも `cluster switch` の停止前の検査は止まりません。値が空のラベルは数えません。検査の途中で終了・削除されたコンテナは飛ばし、一覧に残っているのに調べられないコンテナがあれば、合格にせず例外で止めます。部品試験や別のモデルなど、他のGPU負荷は起動前に止めてください。無効化のオプションはありません。`server assets` もメモリ以外の検査として同じ判定を行います。着想はsfxnz PR #12（コードは採用しない）です。

preflightの合格は資材と設定の確認であり、品質や可用性の保証ではありません。通常運用の受け入れ項目と各項目の証拠の所在は[セットアップ手順](../SETUP.ja.md#6-フルモデルの検証)に、範囲別の現状はREADMEの状態表にあります。失敗した検査の緩和、attention候補の切り捨て、無断の精度変更で通過させないでください。

workerをheadlessで先に起動し、rendezvousを待つ状態になってからheadを最後に起動します（[起動順](launch-safety.ja.md#3ノード)）。APIはhead側のloopbackアドレスにbindするため、遠隔クライアントからはSSHトンネルを使います。内部のrendezvousにはfabric IPを使います。事業サービスとして公開するには、別途検討した認証・TLS・アクセス制御の層が必要です。本リポジトリは、それを提供すると主張しません。

## 3ノード

`[[nodes]]` が3つのprofileは、QSFPリング上でTP=3を動かします。配線・アドレス・1台だけの再起動の確認は[QSFPネットワーク](../../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)に、設定は[起動設定](server-configuration.ja.md#3ノード)に、起動順・rank数の変わる切替の拒否・ホストごとのruntime cacheは[起動契約](launch-safety.ja.md#3ノード)にあります。リングのruntime cacheは各ホストの `state/tp3-runtime-cache/` に置きます（[保管場所](#資材の保管場所とパス)）。

derived checkpoint（公開した任意設定）とそのoverlayは、profileが指すパスにすべてのホストで置きます。`server preflight` は各rankでこれを確かめます。rankあたり22 headで読み込めるのは現行のKDA overlayだけです（[overlay](../overlays/README.md)）。

長いprefillは3台すべてに長時間の負荷をかけます。1M token近いpromptは最初のtokenまで何分も負荷をかけ続け、参照リングの `MemAvailable` の最小もそうした要求の最中に出ました（[1.24.0での測定](benchmarks.ja.md#1240での測定)）。こうした要求の間はホストを冷ましてください（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）。

## 監視・停滞検知・warmup

### メモリの保護余裕と停滞検知

各rankの前面の監視プロセスは2秒ごとに `MemAvailable` を読み、`resources.reserve_gib` を割ると自分のcontainerを停止します（`stop-reason: memory-reserve`）。rank 0では `resources.stall_seconds` が正のとき、同じ周期で `/metrics` も読みます。要求がrunningのまま、生成token計数・prompt token計数・KV使用率・running数のどれもその秒数動かなければ、`stop-reason: engine-stall` で停止し、止まったままの標本を記録します。engineが固まっても `/health` は200を返し続ける（V1のhealth checkはworkerを調べない）ので、生存の信号にはなりません。chunked prefillの間はKV使用率が動き、prompt token計数は最初の出力tokenで加算されるため、長いpromptは停滞になりません。テンプレートの600秒は `generation.timeout_seconds` と同じ値で、実測の最長の要求（FA2のprefill以前、256K・chunk 2048の参照要求で493秒）が収まります。`/metrics` に届かないときは証拠なしとして数えません。KV 使用率を信号に含める理由は実測で裏付けられています。82,018 token の prefill 中、token 計数 2 つは 202.8 秒凍結したままでしたが、4 信号すべてが同時に凍結した最長は 8.3 秒でした。token だけを見る検知器は、運用する最長 prefill より上に閾値を置かざるを得ません。監視による停止は他のrankを残すので、新しい起動の前にそれらも止めます（`cluster switch` は欠けた起動を拒否します）。これらの記述はMia PR #70の現場記録を参考にしました。そこでの2件はどちらも、containerを強制終了し、短いCUDA probeでGPUを確かめ、再起動するだけで復旧し、電源断は要りませんでした。

### 標本に記録するもの

`resources.jsonl` の各行には `mem_free_gib` と `free_2mib_gib` を記録します。後者は `/proc/buddyinfo` から全zoneを合算した、2 MiB以上のbuddy blockに入っている空きです。tonyd2wildのGB10メモリの記録（コードは採用しない）によると、NVRMはページキャッシュを追い出さずにこの大きさのblockを確保するため、4 GiBを超えて空いていても `NV_ERR_NO_MEMORY` が出ることと合います。基準のheadでは配信中、MemAvailable 7.1 GiBのときMemFreeは1.1 GiB、2 MiB以上のblockは0.49 GiBでした。どちらも観測値です。rankを止めるのは `MemAvailable` だけで、読み取りに失敗した標本は停止させずに `memory_sample_error` として記録します。同じ記録では `vm.min_free_kbytes` を4 GiBに上げるとvLLMの起動時のメモリ検査が約6.2 GiB下がったとあるため、このキットでは配布時の既定値のままにします。

各標本には、containerのcgroupメモリと、その全プロセスの `VmRSS`／`RssAnon` の合計（`container_cgroup_gib`・`container_rss_gib`・`container_anon_gib`）も記録します。cgroup v2と `/proc` を権限なしで読みます。GB10ではGPUがホストのメモリを共有し、device側の確保はcgroupにもプロセスにも計上されないので、rankが `memory-reserve` で止まった時、記録そのものが二つの場合を切り分けます。cgroupとRSSが平らなまま `MemAvailable` が減るならdevice側の増加（decode Graph有効時の200K prefillで観測）、RSSが増えるならプロセス側の増加です。読めなかった観測は `container_memory_error` として記録し、rankの停止条件にはしません。

### swap・ホストのデーモン・peerの喪失

これらはどの系列にも関わり、[ホストの準備](../../docs/hosts.ja.md#swapホストのデーモンpeerの喪失)にあります：残ったswapと `vm.swappiness`、統合メモリを奪い合うホストのデーモン（2026-09-16のpeerの監視停止）、そして待機中の起動で失われ、1.x系のどの監視も止めないpeerです。

### warmup ladder

`server warmup` はreadiness後に、通常のchat endpointへ要求のladderを流します。短文1往復をprofileのtemperatureで1本とcheckpointのサンプリング（temperature 1.0・top_p 0.95。temperatureを送らないクライアントが受ける設定）で1本、tool呼び出し、合成画像1枚（`runtime.vision` 有効時）、`generation.warmup_long_tokens` を指定した場合はその長さのprompt（配信中のtokenizerで長さを合わせる）です。これらは配信中にカーネルのコンパイルが観測された形です（[画像入力](vision.ja.md#限界と未解決の事項)）。固定の起動はvLLM自身のJIT warmupを無効にしており、そのコンパイルの山が一度headを保護余裕の下へ押し下げました。コンパイル済みカーネルはruntime cacheに残りますが、ladderは起動のたびに同じカーネルを報告します。固定のTritonは、プロセス内で初めてカーネルを使うとき、コンパイルしたかディスクのcacheから読み込んだかに関わらずpost-compile hookを呼び、jit monitorはそのhookで警告を出すためです（TileLang側の判定もプロセス内のcacheだけを見ます）。ladderが最初のユーザー要求より前に済ませているのは、このプロセスごとの読み込みです。記録（`records/<stamp>-warmup-r0/result.json`）には段ごとの秒数・prompt token・結果、jit monitorがladderの前と最中に報告したカーネル名、その後prefix cacheをリセットしたか（`api.dev_endpoints = true` のときだけ。それ以外ではwarmupのpromptは追い出されるまでcacheに残る）が入ります。

最後の段は出力の正しさの関門で、MiaAI-Lab のレシピ #268 に倣いました（コードは採用していません）。temperature 0・effort low で1から80までの数列を、上限256 tokenで求めます（promptと上限は `glm53_setup/warmup.py` の定数）。答えがちょうど 1〜80 の数列でない、または `stop` で終わらない場合、あるいは MTP が有効でこの段の draft が64 token 以上（上流の閾値）あるのに受理が0の場合に、その起動を異常と判定します。80 まで数えさせるのは、profile がほかにどの段を走らせるかによらず、この段だけで draft の検査が判定できる長さにするためです。2026-09-28 の実機では effort low で 168 token・draft 126、max で 207 token・draft 162 でした（一語で答える段では、AXL の ladder 全体でも draft は 69 で、段が少なければ 64 に届きませんでした）。段を送れなかった、metrics を読めなかった、draft が足りなかった場合は判定を保留し、異常とは数えません。`generation.warmup = true` なら、`cluster switch` は両rankのreadiness後、profile本文を書き込む前にrank 0でladderを実行し、結果を `result.json` の `warmup` に残します。異常の判定は切替を失敗にし、readinessの失敗と同じく旧い対を復旧します。それ以外のladderの失敗は記録されるだけで、新しい対は動かし続けます。`cluster resume` も同じladderを流しますが、記録に旧い起動が無いので、異常と判定した対は止めるだけで旧い対は復旧しません。

長文段は起動のたびにフルprefillを払います（FA2のprefill以前の実測：1.5.0のchunk 2048では256Kで約490秒・200Kで380秒、1.4.0より前の既定のchunk 512では200Kで約500秒・82Kで206秒。現在の全長prefillの時間は[ベンチマーク](benchmarks.ja.md)）。参照機では、毎回のladderが同じ10個のカーネルを報告します。その中には `BuildPrefillChunkMetadataKernel` と、一度はユーザーの要求を処理中にコンパイルされたTileLangの `mhc_pre_big_fuse_with_norm_tilelang` の形が含まれます。2026-09-17の5回の起動でruntime cache（Triton 1,840・TileLang 55ファイル）は1ファイルも増えず、短い段は1〜2秒でした。 `BuildPrefillChunkMetadataKernel` には、長い要求の途中でしか現れない形があります。indexerは1要求の問い合わせ長×圧縮後の系列長が `VLLM_SPARSE_INDEXER_MAX_LOGITS_MB`（固定imageで512）の予算を超えると問い合わせ側を分割し、2つ目以降の区間は開始位置が0でなくなって、Tritonの別の特殊化を要求します。圧縮比は `index_kpool` の4なので、分割が始まる入力長は 134,217,728 ÷ `max_num_batched_tokens` × 4 tokenです。2048では262,144で、判定は「以下」のため、配布既定の256Kいっぱいの要求でも分割は起きません。4096なら131,072、8192なら65,536から始まります。chunkを上げるか `max_model_len` を262,144より上げるときは、その長さ以上の `generation.warmup_long_tokens` を指定して、このコンパイルを起動時に済ませてください。値は稼働中のcontainerのsourceと設定から読みました（2026-09-18）。分割される長さの要求は流していません。機構の着想はMia PR #203（コードは採用しない）で、固定imageのvLLM自身のwarmup keyは3つの区分を既に列挙しており、その修正は要りません。

## 共有メモリの読み手のspin

どのテンプレートも、vLLMの共有メモリbroadcastの読み手のspinを1秒から2 msに縮めています（`runtime.shm_spin_seconds = 0.002`。キーは[起動設定](server-configuration.ja.md)、採否は[施策台帳P29](optimization-catalog.ja.md#性能施策一覧)）。参照対でspinしていたのはheadのEngineCoreだけで、短いspinはそのCPU負荷とheadの温度を下げ、代価はdecodeのわずかな低下でした（[1.25.0での測定](benchmarks.ja.md#1250での測定)）。同時の負荷で温まるホストほど効きます。vLLMの1秒に戻すにはキーを外し、そのときは何もmountも設定もしません。[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)と同じく、長い要求の間の休みの代わりにはなりません。

## 復旧と記録

スクリプトは、失敗したcontainerや重みを削除せず、再起動用のwatchdogも導入しません。`server stop` が停止するのは、このランチャーの所有ラベルを持つcontainerだけです。同じrank名を作り直す前に、ログを保存し、停止したcontainerの名前を変更してください。分散実行で障害が起きた後は、全rankをまとめて再初期化します。

`state/` は現在の取得状態とサイト設定を保持し、`records/` はrunごとの証跡を保持します。休止中の取得は意図的な停止です。検証の待機は終了コード2で終わり、ダウンロードを再開しません。ローカル移送の実行中に、新しい取得を開始しないでください。

数値・backendの詳細な制約は[validation.ja.md](validation.ja.md)にあります。リリース準備では、未解決の失敗を隠さず残してください。

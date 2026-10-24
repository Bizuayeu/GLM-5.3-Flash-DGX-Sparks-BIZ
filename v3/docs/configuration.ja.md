# 設定（3.x）

[English](configuration.md) · [3.x系の概要](../README.ja.md) · [配備の手順書](../SETUP.ja.md) · [運用](operations.ja.md)

3.x系の配信が読む全ての設定です：どこで決め、既定は何で、何をし、どのrankが読むか。リリースが配信する値とその理由はREADMEの[配信の既定](../README.ja.md#配信の既定)にあり、この頁はその裏の目録です。エンジンの設定は、imageが固定するcommit（[`config/engine.lock.json`](../config/engine.lock.json)）のsourceから読んだものです。containerの中の `tensorfold-native serve --help` がflagを挙げます。

3.x系の受け入れは、ここの設定を全て既定のまま回しました。行が別の値を名指すところは、リリースの受け入れか記録した試しがその値も回しました（[リリースでの測定値](../README.ja.md#リリースでの測定値)、[制限](../README.ja.md#制限)）。それ以外の値は受け入れの範囲の外で、行がsourceから読んだだけと書くことも同じです。

## 設定の置き場

| 場所 | 読むもの | 効くとき |
|---|---|---|
| rankのファイル、各ホストの `/work/rank.env`（[例](../examples/)） | `serve.sh`。全変数をexportしながら読むので、そこに書いた変数はどれもエンジンに届く | そのrankの次の起動 |
| `serve.sh` の `TP RANK RANK_ENV` の後の引数。`cluster.sh` からはlabelの後の引数 | `tensorfold-native serve`。`serve.sh` 自身の引数の後ろに付く | 次の起動、全rankで |
| clusterのファイル、制御機の `state/cluster.env` | `cluster.sh` | 次のコマンド |
| `create_container.sh` の環境 | `create_container.sh` と `cpuset.sh` | containerを作るとき（coreは後から `docker update` で変えられる） |
| 道具のoptionと環境 | `v3/` から実行する `python -m glm53_tf <command>` | 実行のとき |
| [`config/`](../config/) | imageのbuildと道具 | 次のbuildか実行 |

`cluster.sh` はcheckoutのではなくimageの `serve.sh`（`/opt/glm53-tf3/serve.sh`）を走らせます：[`scripts/serve.sh`](../scripts/serve.sh) の変更は、新しいimageでだけrankに届きます。

## rankのファイル

| 設定 | 既定 | 意味 | rank |
|---|---|---|---|
| `MASTER` | なし（必須） | ホストの間のリンク上のrank 0のアドレス。`serve.sh` がエンジンに `NCCL_COMM_ID=MASTER:NCCL_PORT` を渡す | 全rankで同じ |
| `NCCL_PORT` | `29583` | `NCCL_COMM_ID` のrank 0のport：TP=2ではNCCLのbootstrap。rankどうしの生存の線は、どちらのTPでもその次のportを使う | 同じ |
| `ID_FILE` | `/work/nccl-id` | TP=3だけ：rank 0がNCCLのidを書き、他のrankがそれを待つ場所（`TF_GLM_NCCL_ID_FILE`）。`cluster.sh` がホストの間で写すのは、この既定のpathだけ | 同じ |
| `CONTEXT` | TP=2で `524288`、TP=3で `1048576`。空の値は既定になる | 窓（`--context`） | 同じ。起動時に比べる |
| `PARALLEL` | `1` | 同時にdecodeする要求（`--parallel`）。空の値は何も渡さず、エンジンは起動時の空きメモリが許すだけ、最大8本のstreamを取る（TP=2で受け入れ済み）。入らない数は起動時に断られる | rank 0。全rankのstreamを、rankのうち最も小さい余裕に合わせて決める |
| `VISION` | `1` | 画像と動画の入力（`--vision`）。rank 0でcheckpointのvision towerが読む。空でない値は `0` も含めてどれもこれを渡すので、textだけにするのは `VISION=` だけ | 同じ。起動時に比べる |
| `MODEL_NAME`・`HOST`・`PORT` | `glm-tf`・`127.0.0.1`・`8095` | rank 0のmodel idと待ち受け（`--name`・`--host`・`--port`） | rank 0 |
| `REASONING_EFFORT` | `high` | effortを指定しない要求のeffort（`--reasoning-effort`）：`low`・`medium`・`high`・`xhigh`。他の値は `max` も含めて起動時に全rankを止める。空の値は何も渡さず、chat templateに任せる。要求そのものは `none`・`minimal`・`low`・`medium`・`high`・`xhigh`・`max` を指定できる | rank 0 |
| `API_KEY_FILE` | なし | loopbackの外で配信するときのrank 0のkeyのファイル（`--api-key-file`、[APIのkey](#apiのkey)） | rank 0 |
| `CHECKPOINT` | `/hub` の下のXSFP4のsnapshot（lockのrevision） | container内のcheckpointのfolder。3.x系が受け入れるのはXSFP4だけ（[checkpoint](../README.ja.md#checkpoint)） | 同じ。起動時にdigestで比べる |
| `TF_HEAT_HIGH`・`TF_HEAT_LOW` | `92`・`88`（°C） | prefillの熱の待ちの帯（[rankの間で比べるもの](#rankの間で比べるもの)）。`serve.sh` は空のものをunsetし、エンジンは片方だけを断るので、待たないときは両方を空にする | 同じ。起動時に比べる |
| 他の変数 | なし | エンジンにexportされる：[エンジンの環境変数](#エンジンの環境変数)（`TF_GLM_*`・`TF_ROCE*` など）と[NCCLの設定](#nccl) | それぞれによる |

例のファイルは参照機の値を持ち、既定を変える行はcommentにしてあります。ファイルは `bash` が読むので行末のcommentが書け、`docker --env-file` では読めません。`serve.sh` はファイルを読んだ後に引数から `TF_GLM_RANK` と `TF_GLM_WORLD` を設定するので、ファイルではこれらを変えられません。

## serve.shが固定するもの

- `--max-tokens 32768`：`max_tokens` を指定しない要求の応答の上限、推論を含む（エンジン自身の既定は4,096）。
- `--no-update-check`：このエンジンはflagを受け取り、何もしません。
- `NCCL_COMM_ID`・`TF_GLM_RANK`・`TF_GLM_WORLD`、TP=3では `TF_GLM_NCCL_ID_FILE`（TP=2ではunset）を、引数とrankのファイルから。
- 窓・effort・stream・vision tower・checkpointを、上のとおりrankのファイルから。2か3以外のTP、その外のrankは、エンジンが起動する前に `serve.sh` を止めます。

`TP RANK RANK_ENV` の後の引数（`cluster.sh` からはlabelの後）はこれらの後ろに付くので、もう一度与えた値のflagは後の値になり（`CONTEXT` より `--context 131072`）、`--api-key` と `--alias` は一覧に加わります。`cluster.sh` はそれらをSSHと `bash -c` にquoteせずに渡します：空白やquoteを含む引数は、そのままでは届きません。

## エンジンのflag

labelの後に付けられるflagと、エンジンの既定です。「比べる」と書いたものは起動時にrankの間で比べ、違えば全rankが止まります。

| flag | 既定 | 意味 |
|---|---|---|
| `--kv-cache fp8` | `bf16` | FP8のlatent cache。GiBあたり約2倍の窓。比べる。TP=2で一度試した（[制限](../README.ja.md#制限)） |
| `--prompt-cache-gib N` | 無し：16 GiB、ただしstreamの残りまで | 保持するpromptの状態の予算。`0` で保持しない。参照リングのTP=3のcacheはこの上限 |
| `--vision-max-images N` | `4`（1〜64） | 要求が持てる画像。送るmessageの全ての画像を数える。比べる |
| `--vision-image-tokens N` | `4096`（16〜262144） | 要求の画像が分け合うtoken。比べる |
| `--vision-max-videos N` | `2`（1〜16） | 要求が持てる動画。比べる |
| `--vision-video-tokens N` | `16384`（64〜262144） | 要求の動画が分け合うtoken。比べる |
| `--vision-urls` | 無効 | data URLに加えてHTTPSの画像のURL。`--vision` が要る。検証していない |
| `--no-drafts` | draftあり | MTP headのdraftなしで1 roundに1 token。比べる |
| `--drafter DIR`・`--drafter-bits N` | なし・`4` | MTP headの代わりにDFlash2のdrafter、その重みを4 bit（`4`）かBF16（`0`）で。draftが要る。比べる。その重み（`incoai/GLM-5.3-Flash-DFlash2`）はCC BY-NC-ND 4.0で非商用。3.x系では回していない |
| `--temperature`・`--top-p`・`--top-k`・`--min-p` | checkpointの `generation_config.json` | 指定しない要求のsampling |
| `--prompt-seed` | 無効 | seedの無い要求に、乱数ではなくpromptと `TENSORFOLD_SEED_SALT` からseedを与える |
| `--no-thinking`・`--thinking-budget`・`--thinking-reserve`・`--loop-guard` | 推論あり・`0`・`0`・無効 | 推論の切り替えと予算、loop guard。3.x系では回していない |
| `--keep-warm S` | `900` | 最後の要求が終わってから、待機中のkeepaliveを回す秒数。`0` で止める |
| `--chat-template FILE` | checkpointのもの | 別のchat template |
| `--alias NAME`・`--api-key KEY` | なし | 別のmodel id、別のkey（[APIのkey](#apiのkey)）。どちらも繰り返せる |
| `--allowed-host`・`--allowed-origin` | なし | browserが使えるhostとorigin。繰り返せ、それぞれ64まで |
| `--metrics-open` | 無効 | keyなしの `/metrics` |

エンジンの他のflag（`--record`・`--compact-*`・`--recall*`・`--cortheon`・`--dashboard` と `--help` の残り）は、3.x系では回していません。

このbuildが扱わないflagは、parserが起動時に全rankを止めます：`--tp`・`--rank`・`--master`・`--master-port`（rankは `TF_GLM_RANK` と `TF_GLM_WORLD` から決まる）、`--speed-up`・`--checkpoint-slots`・`--kv-dtype`・`--prefill-fp8`・`--spill-gib`・`--lane-kernels`・`--vision-offload` と、Pythonのエンジンの他のflagです。CUDAのGLMは起動時に、`--mtp-drafts` と `--mtp-confidence`（そのdraftは調整できない）、`--policy`・`--precision`・`--prompt-cache-over-cap`・`--slide`、`--learn` と `--learn-conversations`、1より大きい `--segments`、モデルの窓を越える `--context`（`0` はモデル自身の窓を求める）を断ります。`--snapshot-dir` と `--max-snapshots` は `none` と `0` だけを受けます。

## APIのkey

- **keyのファイル**（`API_KEY_FILE`、`--api-key-file`）：1行に1つ、`label: key` かkeyだけ。エンジンは、通常のファイルでないもの、他のuserが読み書きできるもの（groupかotherの読み書きのbitがどれか立っている：`0600` と `0400` は通る）、1 MiBより大きいものを断ります。
- **読み直し。** エンジンは `SIGHUP` を受けたときと、ファイルが変わった後の要求のとき（多くて1秒に1回）にファイルを読み直します。読み直しに失敗すると（ファイルが無い、別のmode、壊れた行）、keyの要る経路は、ファイルがまた読めるまで全て閉じます。`SIGHUP` の受け手はkeyがあるときだけ置きます。sourceから読んだだけです。
- **他のkey。** rank 0の環境（rankのファイル）の `TENSORFOLD_API_KEY` はcommaで区切ったkeyを持ち、ファイルと同じく認証を有効にします。`--api-key` はflag 1つで1つ加えます。
- **要求。** keyがあると、`/health` 以外の全ての経路に `Authorization: Bearer <key>` か `x-api-key: <key>` が要り、`/health` は `{"status": "ok"}` だけを返します。keyが無いと、loopbackの外の待ち受けは開いたままで、エンジンは起動時に警告をlogに出します。
- **この系列の道具**は、実行する場所の `TENSORFOLD_API_KEY` を `Authorization: Bearer` として送り、tool引数ゲートは要求のkeyをそのまま渡します。

## エンジンの環境変数

### rankの間で比べるもの

エンジンはこれらを起動時、重みを読む前に比べ、違えば全rankが止まります（`REFUSE rank settings: …`）。

| 変数 | 既定 | 値 |
|---|---|---|
| `TF_HEAT_HIGH`・`TF_HEAT_LOW` | 無し：待たない（`serve.sh` は `92` と `88` を設定） | prefillの熱の待ち：prompt chunkの前ごとに、どれかのrankの最も熱いzoneが高い方の値を超えている間、全rankが2秒ずつ休み、全てが低い方の値以下になるまで待つ。両方か無しか、低い方は高い方以下 |
| `TF_GLM_MM` | `1` | `0` はBF16のlinearをtiledのkernelではなくエンジンのglueのkernelで回し、別のtokenを返す（[検証](validation.ja.md)）。3.1.0と3.2.0のTP=3で受け入れ済み |
| `TF_GLM_PREFILL_REDUCE` | `split` | prompt chunkの行の交換の仕方：`split` は各rankの行を他の全rankへ送り、起動時に全てのrankの組が交換できることを確かめる。`ring` はリングに沿って隣へ渡す（隣にしか届かないrankがあるfabric向け）。`gather` |
| `TF_GLM_OVERLAP_PIECES` | `3` | 1〜8：prompt chunkの交換を、この数の行の片に分ける |
| `TF_GLM_KDA_DECODE_WIDE` | `1` | `0` はdecodeの窓をKDAの3つのkernelの鎖なしで回す |
| `TF_GLM_PROMPT_K` | `one` | `shape`：promptに固定のKのslice、試しのもの。`TF_GLM_MM=1` が要る |
| `TF_GLM_DENSE_BITS`・`TF_GLM_HEAD_BITS` | `16` | `4`・`6`・`8`：denseのlinear、またはheadを、読み込み時にそのbit数へ詰める |
| `TF_GLM_LAYERS` | 全ての層 | 最初のN層だけ。GPU 1台で確かめるための細いモデル |

rankはほかに、worldと各rank、`--kv-cache`、draftと `--drafter`、`--vision` とその4つの上限、窓、checkpointの `config.json`、エンジンのbinary、checkpointのdigestも比べます。digestはmetadataと全shardのbyteのもので、containerの中のcacheに残るので、新しいcontainerの最初の起動はcheckpointを全部読みます。

### 各rankが読み、比べないもの

これらはrankごとに違っても断られません。

| 変数 | 既定 | 意味 |
|---|---|---|
| `TF_ROCE` | 有効 | TP=2：小さいall-gather（rankあたり `TF_ROCE_MAX_KB` まで）を、NCCLではなくエンジン自身の経路のRoCEの書き込みで送る。`0` ではNCCLのまま。どちらかのrankがこの経路を立てられない組でもNCCLのまま |
| `TF_ROCE_HCA` | `NCCL_IB_HCA` | その経路が分けて使うデバイス、2つまで。`=` の接頭辞と `:port` の接尾辞は外す |
| `TF_ROCE_GID_INDEX` | 各デバイスのRoCE v2のIPv4のGID | その経路が使うGIDのindex |
| `TF_ROCE_MAX_KB` | `4096` | rankがその経路で送る最も大きいgather、KiB単位。空の値・`0`・数でない語は起動を止める |
| `TF_GLM_PDL` | 有効 | `0` はdependent launch（前のkernelが終わる間に行列積の重みを流し込む）を止める |
| `TF_NVFP4_DECODE_WARPS` | `4` | NVFP4のexpertのdecodeのkernelのwarp、`1` か `4`。他の値は空も含めて読み込みを失敗させる |
| `TF_GLM_PROMPT_STEPS` | 有効 | rank 0だけ：`0` はpromptの処理を丸ごと回し、chunkの合間に他のstreamのroundを挟まない |
| `TF_GLM_SHARED` | 有効 | rank 0だけ：`0` は各streamのdraftの窓に、他のstreamと共有するforwardではなく専用のforwardを与える |
| `TF_GLM_LINK_WAIT` | 無効 | `1` は他のrankへの各stepをuploadして待つ。以前のエンジンの振る舞い |
| `TF_GLM_PROF` | 無効 | logにprofilingの行 |
| `TF_GLM_DRAFT_CONFIDENCE`・`TF_GLM_DFLASH2_LOG`・`TF_GLM_DFLASH2_PROF` | `0.7`・無効・無効 | DFlash2のdrafter（`--drafter`）だけ |
| `TF_HEAT_ROOT` | `/sys/class/thermal` | thermal zoneを読む場所。空の値は既定になる |
| `TF_CUDA_DEVICE`（`--device`） | `0` | GPU |
| `TF_CUDA_SEGMENTS`（`--segments`） | `1` | GLMは1だけ |
| `TF_CUDA_MEMORY_RECEIPTS` | 無効 | `1` は読み込みと後片付けのときに `TF_MEMORY` のJSONの行を出す |
| `TENSORFOLD_MEMORY_RESERVE_GIB` | 統合メモリでは、4 GiBとメモリの10分の1の大きい方 | エンジンがsystemに残すメモリ。設定する値は2以上 |
| `TENSORFOLD_CUDA_MEMORY_LIMIT_GB` | なし | エンジンが確保する量の上限 |
| `TENSORFOLD_LIBTURBOJPEG`・`TENSORFOLD_LIBWEBP` | imageのもの、`/usr/local/lib` の | JPEGとWebPのdecoderのファイル |

エンジンは `NCCL_RUNTIME_CONNECT`・`NCCL_CUMEM_HOST_ENABLE`・`NCCL_CUMEM_ENABLE` が無ければ `0` を設定します：全ての接続をメモリが空いている起動時に登録し、負荷の下でGB10のdriverのpoolを使い果たしたNCCLのcuMemのhost bufferを止めたままにします。rankのファイルで別の値にもできますが、3.x系のどの起動もしていません。

### rank 0のserver

| 変数 | 既定 | 意味 |
|---|---|---|
| `TENSORFOLD_API_KEY` | なし | commaで区切ったAPIのkey（[APIのkey](#apiのkey)） |
| `TF_DRAIN_S` | `20` | 止まるserverが流し切る秒数：新しい要求は `Retry-After` 付きの503を受け、`/health` は `draining` を返す |
| `TF_SSE_KEEPALIVE_S` | `15` | streamのkeepaliveの間隔（秒） |
| `TENSORFOLD_REQUEST_LOG` | なし | 全てのchatとcompletionの要求の本文を、1行のJSONとして受けるファイル。画像のURLは伏せ、textは残る |
| `TENSORFOLD_SEED_SALT` | `0` | `--prompt-seed` がpromptから作るseedに混ぜる整数 |
| `TENSORFOLD_NO_LIVE`・`COLUMNS` | 無効・端末のもの | `1` で実況の表示を止める。その幅 |
| `TENSORFOLD_VIDEO_TOKENS` | `16384` | rank 0が動画のframeを合わせるtoken数。rankの間で比べない。sourceから読んだだけ |
| `HF_HUB_CACHE`・`HF_HOME` | Hugging Faceのもの | 名前で与えたモデルを探す場所。`serve.sh` はfolderを与える |
| `BRAVE_SEARCH_API_KEY` | なし | `--cortheon` のweb検索だけ |

GLMを配信する経路は、binaryが挙げる `TENSORFOLD_NO_UPDATE_CHECK` と `HF_HUB_OFFLINE`、`TENSORFOLD_CUDA_KERNELS`（取り込んだkernelの組で、GLMは使わない）、`TF_GRAPH_CACHE`（他のfamilyのもの）、`TF_HEAT_CEILING`（3.3.0のエンジンから無い）、2.x系の `TF_GLM_HEAT_*`・`TF_GLM_CACHE_*`・`TF_GLM_KV`・`TF_GLM_COPY_DRAFTS`・`TF_GLM_B16_DECODE_TABLE`・`TF_GLM_LOOP_GUARD` を読みません。

**空の値。** rankのファイルの `NAME=` という行は、エンジンにunsetではなく空の値を渡します。エンジンは空の `TF_GLM_MM`・`TF_GLM_PREFILL_REDUCE`・`TF_GLM_OVERLAP_PIECES`・`TF_GLM_KDA_DECODE_WIDE`・`TF_GLM_PROMPT_K`・`TF_GLM_DENSE_BITS`・`TF_GLM_HEAD_BITS`・`TF_GLM_LAYERS`・`TF_ROCE_MAX_KB`・`TF_NVFP4_DECODE_WARPS` を断り、空の `TF_GLM_PDL`・`TF_ROCE`・`TF_GLM_PROMPT_STEPS`・`TF_GLM_SHARED`・`TF_GLM_LINK_WAIT` はunsetと同じに扱います。空の `TF_HEAT_HIGH` と `TF_HEAT_LOW` は `serve.sh` 自身がunsetします。

## NCCL

rankのファイルのNCCLの行です。rank 0のアドレスとportは、`serve.sh` が組み立てる `NCCL_COMM_ID` としてNCCLに届きます。TP=3では、rankどうしの生存の線がつながると各rankがそれをNCCLの環境から外し、rank 0はNCCLのidを `ID_FILE` で渡します。

| 変数 | TP=2の例 | TP=3の例 | 意味 |
|---|---|---|---|
| `NCCL_IB_HCA` | リンク上のそのrankの2つのデバイス | `=` と4つのデバイス、port 1 | RDMAのデバイス、両rail。このホストのもの |
| `NCCL_IB_GID_INDEX` | `3` | `3` | portのRoCE v2の項目。このホストのもので、リンクが落ちた後に動くことがある（[GID indexが動く](../../docs/nccl-validation.ja.md#gid-indexが動く)） |
| `NCCL_SOCKET_IFNAME` | リンクのinterface | `=` とホストの `/32` のinterface | NCCLのbootstrapのinterface、管理用のWi-Fiは使わない。このホストのもの |
| `NCCL_SOCKET_FAMILY`・`NCCL_IB_ADDR_FAMILY` | `AF_INET` | `AF_INET` | IPv4 |
| `NCCL_NET`・`NCCL_IB_DISABLE`・`NCCL_IB_ROCE_VERSION_NUM` | `IB`・`0`・`2` | `IB`・`0`・`2` | RoCE v2の上のNCCLのIBのtransportを明示 |
| `NCCL_NET_PLUGIN` | 無し | `none` | imageのpluginではなくNCCL自身のIBのtransport |
| `NCCL_IB_SUBNET_AWARE_ROUTING` | 無し | `1` | 各peerへ、その `/30` が届くportで |
| `NCCL_MIN_NCHANNELS`・`NCCL_MAX_NCHANNELS` | `4` | `4` | 4 channel |
| `NCCL_DEBUG`・`NCCL_DEBUG_SUBSYS` | `INFO`・`INIT,NET` | `INFO`・`INIT,NET` | 各接続のtransportを起動時に一度だけlogに書き、[手順書 §5](../SETUP.ja.md#5-起動)がそれを読む |

各ホスト自身の値以外は、測った2.x系から来ています（[2.x系の決定](../../v2/docs/decisions.ja.md#fabric)）。3.x系のどの起動も、全ての接続が `NET/IB` でした。エンジンのTP=2のRoCEの経路（[上](#各rankが読み比べないもの)）も `NCCL_IB_HCA` を読みます。

## clusterのファイル

| 設定 | 既定 | 意味 |
|---|---|---|
| `TP` | なし（必須） | 2か3。`cluster.sh` は他の値をTP=2の順で起動し、`serve.sh` がそれを断る |
| `HOSTS` | なし（必須） | rank順のホストのSSH名、`TP` の数だけ。rank 0がHTTPを配信する |
| `CHECKOUT` | なし（必須） | 各ホストのこのリポジトリ、そこで展開される。メモリの見張りはここから走る |
| `SSH` | `ssh -o ConnectTimeout=20` | ホストに入るコマンド |
| `CONTAINER` | `glm53-tf3` | 各ホストのcontainer |
| `WORK` | `$HOME/glm53-tf3`、ホストで展開される | `/work` に見せるホストのdirectory |

`cluster.sh` は時間を固定しています：TP=2ではrankを3秒おきに大きい番号から起動し、TP=3では一緒に起動して、rank 0にNCCLのidを書くまで5分を与えます。`start` はrank 0の `serving` の行を15分待ちます。`stop` は各rankを60秒まで待ち、残ったrankにもう一度 `TERM` を送って、さらに30秒待ちます。

## container

| 設定 | 既定 | 意味 |
|---|---|---|
| `IMAGE WORK_DIR`（引数） | なし（必須） | imageと、`/work` に見せるホストのdirectory：rankのファイル・NCCLのid・log |
| `CONTAINER` | `glm53-tf3` | containerの名前 |
| `HF_HUB` | `~/.cache/huggingface/hub` | Hugging Faceのcache、`/hub` に読み取り専用で |
| `HUB_RW` | `0` | `1` はcacheを書き込めるように見せる。そこへ書くbuild用のホスト向け |
| `CPUSET` | 無しか `auto`：最大周波数の最も低いcore（GB10では `0-4,10-14`）。全coreが同じ最大を示すか、どれも示さないときは全core | containerのcore（[理由](../README.ja.md#配信の既定)）。空なら全core（3.0.0と3.1.0の熱の測定の起動がそうだった）、またはdockerの `--cpuset-cpus` に渡すリスト |

`create_container.sh` に固定のもの：hostのnetworkとIPC、全てのGPU、`/dev/infiniband`（無いホストは断る）、`IPC_LOCK` と無制限のlocked memory、64 MiBの `/dev/shm`、作業directoryの `/work`、restart policyなし。containerは、rankが中で起動するまで眠ります。既にあるcontainerのcoreは `docker update --cpuset-cpus` で動かせます（[containerを作り直す](operations.ja.md#containerを作り直す)）。

## メモリの見張り

`cluster.sh` が各ホストで起動する `hostwatch.sh LOG [CONTAINER]` は、起動の5秒後から2秒ごとに `MemAvailable` を読み、5 GiB（GiBの整数）を切るとcontainerの中の `pkill -9` でエンジンを止めます。エンジンが終わると見張りも終わります。しきい値と間隔は台本に固定です。

## エンジンに固定のもの

これらを変える設定はありません（sourceから読んだもの）：

- **rankどうしの生存の線。** rank 0は他の各rankの線を300秒待ち、他のrankは300秒の間つなぎ直します。全rankの準備の記録は15分以内に届かなければならず、消えたホストは約20秒で分かります。
- **NCCLのid。** TP=3では、他のrankは `ID_FILE` を10分まで待ちます。
- **media。** 画像・要求のmedia・動画のbyte数と動画のframeには、flagの無い上限があります（[制限](../README.ja.md#制限)）。

## 道具

`v3/` から実行する `python -m glm53_tf` のコマンドです。各検査が何をするかは[検証](validation.ja.md)と[測定の方法](benchmarks.ja.md)にあります。

| コマンド | option（既定） | 環境 |
|---|---|---|
| `download` | `--background`（Linux。logと状態は `state/xsfp4/` の下）、`--checkpoint`（`xsfp4`、唯一の選択） | 無ければ `HF_XET_NUM_CONCURRENT_RANGE_GETS=4` と `HF_HUB_DOWNLOAD_TIMEOUT=120` を設定し、Hugging Face自身の変数を読む。`HF_HUB_CACHE` でcacheを動かしたら、`create_container.sh` の `HF_HUB` もそこへ |
| `verify-download` | `--hf`（`hf` のclient）と `--output` は必須。`--wait`（30秒ごとに見る。downloadが一時停止の間は2で終わる）、`--checkpoint`（`xsfp4`） | なし |
| `tool-gate` | `--port`（8896）、`--upstream`（`http://127.0.0.1:8095`、loopbackのHTTPのoriginだけ）、`--log`（stderr）、`--timeout`（エンジンへの1回の呼び出しに2400秒） | 127.0.0.1でだけ待ち受け、64 MiBを越える要求の本文は413で断り、要求のkeyはそのまま渡す |
| `decode-check` | なし | `BASE`（`http://127.0.0.1:8095`）、`MODEL`（`glm-tf`）、`PROMPT_KIND`（`count`・`prose`・`code`）、`SAMPLES`（3）、`MAX_TOKENS`（512）、`PROMPT_TOKENS`（2048）、`TOKENS_OUT`（completionを書くファイル）、`TENSORFOLD_API_KEY` |
| `decode-divergence` | 2つの `TOKENS_OUT` のファイル | なし |
| `score-nll` | `--url`・`--tokenizer`・`--out` は必須。`--set`（`config/nll_set.json`）、`--model`（serverの最初のもの）、`--seed`（42） | `TENSORFOLD_API_KEY`。tokenizerかtextが集合のものでなければ2、serverが `prompt_logprobs` を断れば3、集合が失敗すれば1で終わる |
| `bench` | `--kinds`（`prefill,decode`。`edit` は求めたとき）、`--runs`（3）、`--lines`（3200、prefillの行数）、`--warmup`（1）、`--out` | `BASE`・`MODEL`・`TENSORFOLD_API_KEY` |
| `long-input` | `--passphrases`（1か3）と、`--lines` か `--tokens` は必須。`--out` | `BASE`・`MODEL`・`TENSORFOLD_API_KEY`。合言葉を見落とすと1で終わる |

## lock

| ファイル | 固定するもの | 読むもの |
|---|---|---|
| [`config/xsfp4.lock.json`](../config/xsfp4.lock.json) | XSFP4のrepositoryとrevision | `download` と `verify-download`。`serve.sh` の既定のfolderは同じrevisionを名指し、試験がそれらを一致させる |
| [`config/engine.lock.json`](../config/engine.lock.json) | エンジンのfork・release branch・commit、その下の上流のrelease、Zigのcompiler（URLとSHA-256）、xgrammar、mediaのlibraryのrelease（SHA-256）、buildのflag | imageのbuild：[`docker/Dockerfile`](../docker/Dockerfile) の引数で、試験がlockと一致させる |
| [`config/nll_set.json`](../config/nll_set.json) | NLLの集合のtextと、それを切ったtokenizer（SHA-256で） | `score-nll` |
| [`requirements/huggingface.lock.txt`](../requirements/huggingface.lock.txt) | Hugging Faceのclient | 道具の仮想環境（[手順書 §2](../SETUP.ja.md#2-checkoutとcheckpoint)） |

imageの `/usr/share/doc/tf3/ENGINE` は、buildしたエンジンのcommitと全binaryのSHA-256を名指します。

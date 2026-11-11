# 決定（3.x）

[English](decisions.md) · [3.x系の概要](../README.ja.md) · [設定](configuration.ja.md) · [検証](validation.ja.md)

3.x系が何を選び、何を選ばなかったか、いつ、測った効き目と、何が起きれば見直すかです：[2.x系の決定](../../v2/docs/decisions.ja.md)の3.x系版です。配信の既定の理由はREADMEの「…にする理由」の段落（[配信の既定](../README.ja.md#配信の既定)）が持ち、行はそれを写さずにリンクします。効き目はGPUのclockの上限の下の参照機で、行が名指すbuildで測りました。リリースの値は[リリースでの測定値](../README.ja.md#リリースでの測定値)と[前の版の測定値](measurements.ja.md)にあります。「—」は記録が無いことを表します：測った効き目が無いか、決定を見直させるものが無いかです。

## エンジン

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| TensorFoldのネイティブエンジン（ZigとCUDA、kernelはbinaryの中）で配信し、Pythonのエンジンの2.x系と並べる | 2026-10-18（3.0.0） | 上流はPythonのエンジンを凍結し（issue #286）、GLMをネイティブの方で配信します。tokenはネイティブエンジン自身のもの（別のkernel、BF16のKV）なので、二つの系列はNLLで比べます：3.0.0のNLLは、2.x系の基準値と領域ごとに0.021以内でした（[2.x系との違い](../README.ja.md#2x系との違い)） | — |
| 上流のリリースに付いていく。他の利用者にも役立つものは上流へpull requestで出し、残りをrelease branchが持つ | 3.0.0〜3.10.0 | 上流1.0.12（3.0.0）、1.1.1（3.1.0）、1.1.2（3.3.0）、1.1.3（3.6.0）、1.1.5（3.8.0）、1.2.1（3.9.0、3.10.0）。この系列の#1016・#1017・#1018は1.1.1で上流自身のものになり、#1179のpatchは3.3.0〜3.5.xが持って1.1.3から上流自身のものです。#1050（FP4-Localの読み込み）は3.6.0のrelease branchが持ち、#1163・#1211・#1178と共に1.1.5から上流自身のものなので、3.8.0のrelease branchはtagそのもので、3.9.0も同じです。3.10.0のものは1.2.1に `csf0_v1` の6つのcommitを足したもので、上流は2026-11-04にこれらをmainに取り込み（#2041）、1.2.3からのリリースが持っています | — |
| TP=3をswitchの無いリングで、bootstrapは管理用のWi-Fiに載せずに：rank 0のNCCLのidをrankどうしの生存の線で。この系列の#1178からの上流のもの | 2026-10-18（3.0.0）。上流のbootstrapは3.8.0から | `NCCL_COMM_ID` があると、NCCLのbootstrapはrank 0のsubnetに入るinterfaceを探し、リングの点と点の `/32` のアドレスではそれを持つのがrank 0のホストだけです。bootstrapは管理用のWi-Fiに載せません（`/32` を置く前は、Wi-Fiがそれを運んで不安定でした：[3台をリングにつなぐ](../../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。3.0.0〜3.7.0はidをファイルで渡し（`TF_GLM_NCCL_ID_FILE`、この系列のcommit）、線がつながると各rankが `NCCL_COMM_ID` をNCCLの環境から外しました。上流が2026-10-25に#1178を取り込んだので、他のrankはidを線で受け取り、`NCCL_SOCKET_IFNAME` を名指すとNCCLの最初の呼び出しの前に `NCCL_COMM_ID` を外します | — |

## checkpoint

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| XSFP4（このリポジトリのmaintainerによるNVIDIAのFP4-Localの派生）：3.3.0で二つ目の選択、3.4.0から既定。精度を第一とする上流の隣で、この系列が目指すのは、量子化に何ができるか、FP4-Localのメモリの大きさとdecodeの速さを含めて調べること | 2026-10-23（3.3.0、3.4.0） | このエンジンで同じ文書について、XSFP4はtop-1の一致・NLL・KLのどれでもNVIDIAのNVFP4よりBF16に近く、どちらのTPでもそうで、rank 0で約3.9 GiB軽い（[checkpoint](../README.ja.md#checkpoint)） | — |
| XSFP4だけ：NVIDIAのNVFP4と、その組み直しで3.x系では受け入れていない公開したAXLの重みは、3.x系の選択から外れる。1.x系と2.x系は持ち続ける | 2026-10-24（3.6.0）、3.9.xまで | FP4-Localが出て、この系列でNVIDIAのNVFP4を使う人は少ないと判断しました。受け入れは毎回一つのcheckpointになります。rankのファイルの `CHECKPOINT` は今も別のfolderを名指せますが、受け入れの外です | — |
| XSFP4の横にJammed XSFP4を、`CHECKPOINT` の1行で：3〜44層のrouted expertを入力32個ごとのblockのスケールにし、fileでもGPUでも行に1つのbaseとblockごとの4 bitのoffset（`csf0_v1`）で持ち、この系列のrelease branchの5つのkernelで読む。XSFP4は既定のまま：この形を読むのはこの系列のエンジンだけで、返答も違う | 2026-11-03（3.10.0）、既定は3.11.xまで | 同じimageでTP=2の各ホストで6.58 GiB、TP=3のrank 0で4.50 GiB軽く、BF16への近さを代価にする（[checkpoint](../README.ja.md#checkpoint)）。TP=3では同じreserveでpoolが窓3本を取る。2本に保つにはrankのファイルにもう1行要る。draftなし、1本のstream、40,960 tokenの窓で、これらのcommitのbuildと3.8.0の他の設定：TP=2では同じ値をblock 16で持つ形に比べてdecodeが0〜+0.4%、prefillの時間が1.2〜1.4%短く、TP=3では3.8.0のエンジンのXSFP4に比べてdecodeが−0.3〜−0.2%、prefillの時間が0.6〜1.5%短い | 3.12.0のTPごとの既定（下）で閉じた：上流のリリースは1.2.3からcommitを持つ（#2041） |
| TPごとの既定：TP=2はJammed XSFP4、TP=3とTP=4はXSFP4。各リリースのファイルがlockのrevisionでfolderを名指し、`download`・`verify-download` は `--tp` か `--checkpoint` のどちらかを要し（どのTPにも合うcheckpointは無い）、`CHECKPOINT` の1行でもう一方を配信する | 2026-11-07、3.12.0 | 上流のリリースは1.2.3から `csf0_v1` を読み、TP=2ではJammed XSFP4のrouted expertが各ホストで6.58 GiB少ない（[checkpoint](../README.ja.md#checkpoint)）。3.12.0からTP=2の受け入れはJammed XSFP4のもの（[受け入れ](validation.ja.md)） | — |

## 窓とstream

3.9.0の行は、既定を選んだ腕の比べを示します。GLMのファイルが1.2.1と同じ上流のmain `9e8c368b0` の上で、腕を1つ前に積み上げて各2回起動し、TP=3はリングで、TP=2はその2台で測りました。リリース自身の値は受け入れのものです。

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| TP=2の窓は3.4.0まで245,760 token、3.5.0から524,288、3.9.0から1,048,576 | 2026-10-18（3.0.0）、2026-10-23（3.5.0）、2026-11-02（3.9.0） | [TP=2を1,048,576にする理由](../README.ja.md#配信の既定)：245,760はBF16のKVでNVIDIAのNVFP4の隣に1本のstreamが収まるほぼ最大でした。XSFP4では524,288が1本のstreamとprompt cacheを収め、499,254 tokenのpromptが入りました。3.9.0から窓はKVのpoolのpageで、systemに9 GiBを残すとモデルの上限の1,048,576 token全部が入ります。エンジン自身の12.2 GiBでは余地が12.0 GiBで、そのpageの12.77 GiBに足りません。3.5.0のimageでのA/Bは、どちらの窓でもeditの速さが同じでした（[3.5.0の測定値](measurements.ja.md#350)） | エンジンが、Pythonのエンジンのfamilyのように、起動時の空きメモリからGLMの窓を決める → それに任せる |
| TP=3の窓は1,048,576 token | 2026-10-18（3.0.0） | 2.x系と同じく、モデルの上限 | — |
| エンジン自身の選択ではなく、一度に一要求（`PARALLEL=1`） | 2026-10-18（3.0.0）、3.8.xまで | `--parallel` を設定しないと、streamとprompt cacheは起動ごとに変わりました。TP=3では、ある起動が2本のstreamと0.1 GiBのprompt cacheを取り、1本なら16 GiBを保ちました | 3.9.0の既定（下）で閉じた |
| 配信の既定をTPごとに、`serve.sh` がrankのファイルの前に読むTPごとのファイルに置く：TP=2は1人がagentと続ける長い会話、TP=3は複数の人の同時利用。rankのファイルは運用者が写すので、新しいimageで既定が動くようにそこには書かない | 2026-11-02（3.9.0） | 二つのTPは4つの設定で分かれます（[配信の既定](../README.ja.md#配信の既定)）。`serve.sh` は解決した値を出し、受け入れはその行をファイルと照らします | — |
| TP=2で4本、TP=3で8本のstream（`PARALLEL`） | 2026-11-02（3.9.0） | [TP=2で4本、TP=3で8本にする理由](../README.ja.md#配信の既定)。TP=2の1本から4本：32K tokenのpromptに6〜8秒で来た短い要求 16.05 → 1.31秒、別々の4つのpromptの同時 36.86 → 54.36 tok/s、decode −0.4%。TP=3の4本から8本：別々の8つのprompt 79.59 → 93.25 tok/s、その最初のtokenの最悪 17.24 → 1.77秒、rank 0の起動後の空き 9.31 → 7.98 GiB。3.9.0のimageで、32K tokenのpromptに6〜8秒で来た短い要求の最初のtokenはTP=2で1.20秒、TP=3で1.38秒でした | 長い会話が同時に並び、この大きさが残すより多くのpoolを求める → その負荷を測る |
| prompt cacheをKVのpoolのpageに：`TF_GLM_KV_SHARE` をTP=2で16、TP=3で32（3.12.0から `TF_KV_SHARE`、#2211） | 2026-11-02（3.9.0） | [prompt cacheをpoolのpageに置く理由](../README.ja.md#配信の既定)。TP=2で400K tokenのpromptの再送 310.41 → 2.22秒、rank 0の起動後の空き 11.81 → 13.73 GiB。TP=3で64K tokenのprompt 36.52 → 1.75秒、128K tokenのprompt 72.4 → 2.08秒、起動後の空き 11.53 → 10.08 GiB。stream 1本に4状態はエンジン自身の線で、その下では動いているstreamが互いの状態を追い出すと警告します | — |
| streamがdecodeしている間のpromptの取り分を0.7に（`TENSORFOLD_PREFILL_SHARE`） | 2026-11-02（3.9.0） | [promptの取り分を0.7にする理由](../README.ja.md#配信の既定)。32K tokenのpromptの横のdecodeのtokenの間隔の中央値はTP=2で1,484 → 46 ms、TP=3で1,221 → 37 ms（同じpromptの3本。0.7で別々のpromptの3本では62 msと47 ms、3.11.4）。そのpromptは23.9 → 32.8秒、19.8 → 27.3秒で、払うのは何かが横でdecodeしている間だけです | — |
| 広いpromptのpass（`TF_GLM_CHUNK_SOLO`）をどちらのTPでも使わない | 2026-11-02（3.9.0） | [TP=2を1,048,576にする理由](../README.ja.md#配信の既定)。TP=2の524,288 tokenで、8Kから128K tokenのcoldのpromptが6.1〜7.5%早く、32K tokenのpromptの途中の短い要求 1.31 → 2.45秒、rank 0の起動後の空き 13.46 → 11.87 GiBで、窓全体に要る余地を取ります。TP=3では他のstreamがdecodeしている時間が長く、coldのpromptの得はwireの上で3.2〜3.4%、wireなしで7.3〜8.4%です。wireの余分な時間は脇のstreamのやり取りにあり、passが倍になると延びます。後の上流の測り（TP=3の既定、v1.2.1のbits、#1994、2026-11-04）では、全rankの `TF_GLM_OVERLAP_PIECES=8` で、wireの上のsoloの得が既定の3 pieceの1.7〜3.6%から6.1〜7.8%になりました（比べる相手は3 pieceでsoloなしのwire、返るtokenは同じ）。soloなしの8 pieceは3 pieceから1%以内でした | 短い窓なら余地ができる → 全rankのファイルに `TF_GLM_CHUNK_SOLO=4096`、その時に測る。上流が#1423を取り込む。その組はこれと1つのserverに同居しない → 測って選ぶ。8 pieceと一緒のsoloをTP=3で複数の人の負荷のもとで測る → それでTP=3のpassを決める |
| TP=3で `--mtp-confidence 0.5`、TP=2ではしない | 2026-11-02（3.9.0） | [TP=3でwireとdraftの確率を使う理由](../README.ja.md#配信の既定)。TP=3でdecode 51.13 → 53.65 tok/s、別々の4つのprompt 70.39 → 74.77 tok/s、sampledの1本は変わらず、悪くなった行はありません。TP=2では、その使い方であるsampledの1本は同じdraftを取り、4本のgreedyのcodeは遅くなりました | — |
| TP=3でwire（`TF_GLM_ROCE_MULTI=1`）。上流の既定はoff | 2026-11-02（3.9.0） | [TP=3でwireとdraftの確率を使う理由](../README.ja.md#配信の既定)。decode 53.65 → 55.11 tok/s、sampledの1本は2.1〜2.3%速く、別々の4つのprompt +1.3%、coldのpromptは1.8〜2.0%遅くなります。wireなしの広いpassとの比べでは、decode 55.31対53.89 tok/s、coldの128K tokenのprompt 81.61対73.66秒で、maintainerはdecodeを選びました。準備に失敗すると起動が止まるので、起動が気づかれずに戻ることはありません | — |
| systemにTP=2で9 GiB、TP=3で3.11.xまで14 GiB・3.12.0から16 GiBを残す（`TENSORFOLD_MEMORY_RESERVE_GIB`） | 2026-11-02（3.9.0）、2026-11-08（3.12.0） | 9 GiBは[TP=2を1,048,576にする理由](../README.ja.md#配信の既定)で、rank 0の起動後の空きは8.03 GiBです。 [TP=3で16 GiBにする理由](../README.ja.md#配信の既定)。エンジンの12.2に対して13 GiBの腕：pool 6,017 → 4,098 page、rank 0の起動後の空き 7.98 → 20.07 GiB、速さは同じか最大1.0%上。3本目の窓に要る余地に対して13 GiBは0.15 GiB下、14 GiBは1.25 GiB下で、起動ごとの揺れより離れます。2026-11-07からホストはメモリを1.50 GiB多く報告します：14 GiBでは余地が39.3〜39.5 GiBと3本目の窓に要る38.85を超え、poolは5,989〜6,017 page、rank 0の空きは約10.3 GiBでした。16 GiBでは37.2〜37.5 GiB、4,098 page、空きは22.1〜22.5 GiBです | 長い会話が同時に並び、3本目の窓のpageを使う → その負荷を測る |
| 要求が指定しないときの応答の上限32,768 tokenとeffort `high` | 2026-10-18（3.0.0） | 2.x系から引き継ぎ（[2.x系の決定](../../v2/docs/decisions.ja.md#窓上限範囲)）、3.x系では測り直していません。XSFP4のchat templateが、NVIDIAのもののように名前の無いeffortを `max` にするかは記録がありません | — |

## KV cache

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| latentとindexのkeyをBF16、エンジンの既定で、基準として | 2026-10-18（3.0.0） | 上流はネイティブエンジンの劣化するcacheを断りました（issue #309と#401、2026-10-06：bf16のcacheとfp32の和）。BF16なら上流のkernelとそのtokenを保ちます。tokenあたり2.x系のFP8のcacheの約2倍を取るので、TP=2の窓はXSFP4まで2.x系より短いものでした（[TP=2を1,048,576にする理由](../README.ja.md#配信の既定)） | — |
| エンジンの選べるFP8のlatent cache（`--kv-cache fp8`）をTP=2の1M tokenの窓で一度試し、既定にはしない | 2026-10-23 | 1本のstreamがprompt cacheとともに1,048,576 tokenの窓に収まり、1,035,295 tokenのpromptは合言葉を見つけました。prefillは約5%長く、NLLはtextごとの区間の中で動き、decode検査のtokenはBF16のものと違います（[制限](../README.ja.md#制限)）。TP=3では試していません | 上流が、保留としているこのcacheの質とデバイスの確かめを終える |

## 熱

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| どれかのrankの最も熱いzoneが92 °Cを超えている間、prefillはchunkの合間で全rankが88 °C以下になるまで待つ。既定で有効（2.x系の帯） | 2026-10-18（3.0.0） | 2.x系での導き（[2.x系の決定](../../v2/docs/decisions.ja.md#熱)）。3.x系では導き直していません。3.0.0の前、ネイティブエンジンのTP=3で、待たない1,035,295 tokenのpromptは1台を94〜97.7 °Cに保ち（2秒おきの読みの478回が94 °C以上）、帯の代価はその初tokenの10.1%でした（1,017.1秒に対して1,119.6秒）。帯を下げる（86/82/87）と、待ったpromptが26〜89%遅くなり、そのpromptの最高温度は下がりませんでした（[効率coreにする理由](../README.ja.md#配信の既定)） | 帯だけで94 °C以上を読むことがある（暑い部屋、続けてのprompt） → 同じbinaryで天井と比べる |
| 93 °Cの天井への見込み（`TF_HEAT_CEILING`、この系列のcommit）を3.0.0〜3.2.0に入れ、3.3.0で外す | 2026-10-18（3.0.0）、外したのは2026-10-23（3.3.0） | 同じTP=3の試しで、あり・なしのpromptの初tokenは1,121.0秒と1,119.6秒、最も熱い読みは93.3 °Cと93.0 °Cで、どちらも94 °Cに届きませんでした：その10回の待ちは帯の9回に置き換わっただけです。3.2.0のTP=3の受け入れでは、帯の10回の隣で、91.3〜91.9 °Cで7回待ちました。持ち続けると、rebaseのたびにforkのcommitと、上流と違う設定の並びが要ります。上流は天井の代わりに、この系列の帯についてのrunbookのpull request（#988）を取り込みました | 上と同じ |

## core

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| 全てのcontainerを効率coreに（`CPUSET` 無し：最大周波数の最も低いcore） | 2026-10-18（3.0.0）、3.1.0でも | [効率coreにする理由](../README.ja.md#配信の既定)：rankごとに空回りするエンジンの2本のthreadがCPUのzoneを温めます。全coreでは、長く続く返答が3.0.0のエンジンで熱の見張りの止める温度に達し、3.1.0のエンジンで1 °C以内に迫りました。上流のrunbookも1.1.1から、GB10の各rankに同じcoreを挙げています | #1053（rank 0にstreamが無い間、待つrankを眠らせる）が1.1.2から入っている → containerにまだそのcoreが要るかを測り直す：全coreで40本の返答と2つの同時の要求（[Next Action](../README.ja.md#next-action)） |

## draft

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| checkpointのMTP headが、エンジン自身の深さの方針でdraftする。DFlash2のdrafterも固定の深さも使わない | 2026-10-18（3.0.0） | DFlash2のdrafterの重みはCC BY-NC-ND 4.0（非商用）で、2.x系と同じ判断です（[2.x系の決定](../../v2/docs/decisions.ja.md#draft)）。深さの方針はエンジンのcoreのもので2.x系のものではないので、2.x系の深さの測定は当てはまりません。3.x系での深さの比べは記録がありません | — |

## fabric

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| TP=4（試験的）：switchの無い4台のリングで、TP=3のNCCLの行に、リングだけ・rankごとのgraph・cuMemを入れて初めて使う時につなぐこと・`TF_GLM_PREFILL_REDUCE=gather` を足し、配信の値はTP=3のものでwireを切り、14 GiBを残す（[NCCL](configuration.ja.md#nccl)） | 2026-11-07〜2026-11-10、3.12.0 | 2026-11-07から上流のmainで、参照機の4台のリングがこの行で起動して配信し、隣どうしの全channelが `NET/IB` だった。`split` は4台のリングを起動時に止め、そこのwireは上流の試験的なrelayを通り、その最後のheadで1本のdecodeがNCCLより2〜3%速く、4本とcoldのpromptは同じ速さだった。ここでは既定として測っていない。どの値も4台では詰めていない | `config/tp4.env` を4台で詰めた時 |
| 2.x系からのNCCLの設定：リンクごとに2本のrail、4 channel、IBのtransportを明示、TP=3ではsubnet-aware routingとNCCL自身のIBのtransport（[NCCL](configuration.ja.md#nccl)） | 2026-10-18（3.0.0） | 2.x系で測ったもの（[2.x系の決定](../../v2/docs/decisions.ja.md#fabric)）。ネイティブエンジンではメモリだけを測り直しました：上流1.1.0のTP=2で245,760 tokenの窓のとき、NCCL自身の64 channelは起動時に4.0 GiBを残し、4 channelでは5.3〜5.8 GiBで、1.3〜1.8 GiB多く、2.x系の1.5 GiBと合います。4 channelと64 channelの速さ、rail、routing、pluginは測り直していません。3.x系のどの起動も、全ての接続が `NET/IB` でした | — |

## 画像と動画の入力

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| 画像と動画を既定で有効に（`VISION=1`、エンジンの `--vision`）。2.x系が画像を既定で受けるのと同じく、towerが窓やprompt cacheを大きく削らないことを条件に | 2026-10-20（3.2.0） | imageを作る前に、TP=2の245,760 tokenの窓で測りました：towerはrank 0で1.27 GiBを取り、窓は保たれ、prompt cacheは4.4〜5.4 GiB（textだけでは5.2〜6.3 GiB）だったので、既定は有効のままです（[変更履歴](../CHANGELOG.ja.md)の3.2.0）。窓が524,288になったとき、この条件は言い直していません | towerが窓かprompt cacheを大きく削る |

## 3.x系で未評価のもの

開いた項目：3.x系では、どちらの結果もありません。

- **要求と入力。** 長い会話が同時に何本も並ぶ負荷、画像と動画のURL（`--vision-urls`）、`/v1/responses` と `/v1/messages`、harnessとの統合（[制限](../README.ja.md#制限)）。
- **エンジンの設定。** [設定](configuration.ja.md)が回したと名指すもの以外の全てのエンジンの設定：`TF_ROCE*`・`TF_GLM_PREFILL_REDUCE`（TP=4では `gather`）などは既定のまま回り、`TF_GLM_PROMPT_K=shape` もDFlash2のdrafterも試していません。
- **TP=3のFP8のlatent cache**、TP=2でも一度の試しの先。これはstreamごとに窓を持つので、3.9.0のKVのpageとは組めません。
- **#1053の後の全core**。上流1.1.2が入れたもの（[Next Action](../README.ja.md#next-action)）。
- **他のworldの大きさとhardware**：TP=4と他のGPUは回していません。
- **2.x系の開いた項目**、MTUとLPA（[2.x系の決定](../../v2/docs/decisions.ja.md#1x系の施策で2x系では未評価のもの)）、そしてloop guard。ネイティブエンジンでは `--loop-guard` として持ちます。

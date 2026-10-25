# 決定（3.x）

[English](decisions.md) · [3.x系の概要](../README.ja.md) · [設定](configuration.ja.md) · [検証](validation.ja.md)

3.x系が何を選び、何を選ばなかったか、いつ、測った効き目と、何が起きれば見直すかです：[2.x系の決定](../../v2/docs/decisions.ja.md)の3.x系版です。配信の既定の理由はREADMEの「…にする理由」の段落（[配信の既定](../README.ja.md#配信の既定)）が持ち、行はそれを写さずにリンクします。効き目はGPUのclockの上限の下の参照機で、行が名指すbuildで測りました。リリースの値は[リリースでの測定値](../README.ja.md#リリースでの測定値)にあります。「—」は記録が無いことを表します：測った効き目が無いか、決定を見直させるものが無いかです。

## エンジン

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| TensorFoldのネイティブエンジン（ZigとCUDA、kernelはbinaryの中）で配信し、Pythonのエンジンの2.x系と並べる | 2026-10-18（3.0.0） | 上流はPythonのエンジンを凍結し（issue #286）、GLMをネイティブの方で配信します。tokenはネイティブエンジン自身のもの（別のkernel、BF16のKV）なので、二つの系列はNLLで比べます：3.0.0のNLLは、2.x系の基準値と領域ごとに0.021以内でした（[2.x系との違い](../README.ja.md#2x系との違い)） | — |
| 上流のリリースに付いていく。他の利用者にも役立つものは上流へpull requestで出し、残りをrelease branchが持つ | 3.0.0〜3.8.0 | 上流1.0.12（3.0.0）、1.1.1（3.1.0）、1.1.2（3.3.0）、1.1.3（3.6.0）、1.1.5（3.8.0）。この系列の#1016・#1017・#1018は1.1.1で上流自身のものになり、#1179のpatchは3.3.0〜3.5.xが持って1.1.3から上流自身のものです。#1050（FP4-Localの読み込み）は3.6.0のrelease branchが持ち、#1163・#1211・#1178と共に1.1.5から上流自身のものなので、3.8.0のrelease branchはtagそのものです | — |
| TP=3をswitchの無いリングで、bootstrapは管理用のWi-Fiに載せずに：rank 0のNCCLのidをrankどうしの生存の線で。この系列の#1178からの上流のもの | 2026-10-18（3.0.0）。上流のbootstrapは3.8.0から | `NCCL_COMM_ID` があると、NCCLのbootstrapはrank 0のsubnetに入るinterfaceを探し、リングの点と点の `/32` のアドレスではそれを持つのがrank 0のホストだけです。bootstrapは管理用のWi-Fiに載せません（`/32` を置く前は、Wi-Fiがそれを運んで不安定でした：[3台をリングにつなぐ](../../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。3.0.0〜3.7.0はidをファイルで渡し（`TF_GLM_NCCL_ID_FILE`、この系列のcommit）、線がつながると各rankが `NCCL_COMM_ID` をNCCLの環境から外しました。上流が2026-10-25に#1178を取り込んだので、他のrankはidを線で受け取り、`NCCL_SOCKET_IFNAME` を名指すとNCCLの最初の呼び出しの前に `NCCL_COMM_ID` を外します | — |

## checkpoint

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| XSFP4（このリポジトリのmaintainerによるNVIDIAのFP4-Localの派生）：3.3.0で二つ目の選択、3.4.0から既定。精度を第一とする上流の隣で、この系列が目指すのは、量子化に何ができるか、FP4-Localのメモリの大きさとdecodeの速さを含めて調べること | 2026-10-23（3.3.0、3.4.0） | このエンジンで同じ文書について、XSFP4はtop-1の一致・NLL・KLのどれでもNVIDIAのNVFP4よりBF16に近く、どちらのTPでもそうで、rank 0で約3.9 GiB軽い（[checkpoint](../README.ja.md#checkpoint)） | — |
| XSFP4だけ：NVIDIAのNVFP4と、その組み直しで3.x系では受け入れていない公開したAXLの重みは、3.x系の選択から外れる。1.x系と2.x系は持ち続ける | 2026-10-24（3.6.0） | FP4-Localが出て、この系列でNVIDIAのNVFP4を使う人は少ないと判断しました。受け入れは毎回一つのcheckpointになります。rankのファイルの `CHECKPOINT` は今も別のfolderを名指せますが、受け入れの外です | — |

## 窓とstream

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| TP=2の窓は3.4.0まで245,760 token、3.5.0から524,288 | 2026-10-18（3.0.0）、2026-10-23（3.5.0） | [TP=2を524,288にする理由](../README.ja.md#配信の既定)：245,760はBF16のKVでNVIDIAのNVFP4の隣に1本のstreamが収まるほぼ最大でした。XSFP4では524,288が1本のstreamとprompt cacheを収め、499,254 tokenのpromptが入ります。3.5.0のimageでのA/Bは、どちらの窓でもeditの速さが同じでした（[リリースでの測定値](../README.ja.md#リリースでの測定値)の3.5.0） | エンジンが、Pythonのエンジンのfamilyのように、起動時の空きメモリからGLMの窓を決める → それに任せる |
| TP=3の窓は1,048,576 token | 2026-10-18（3.0.0） | 2.x系と同じく、モデルの上限 | — |
| エンジン自身の選択ではなく、一度に一要求（`PARALLEL=1`） | 2026-10-18（3.0.0） | [一度に一要求にする理由](../README.ja.md#配信の既定)：`--parallel` を設定しないと、streamとprompt cacheは起動ごとに変わります。TP=3では、ある起動が2本のstreamと0.1 GiBのprompt cacheを取り、1本なら16 GiBを保ちます。1本と複数本の処理量や待ち時間の比べは記録がありません | — |
| 要求が指定しないときの応答の上限32,768 tokenとeffort `high` | 2026-10-18（3.0.0） | 2.x系から引き継ぎ（[2.x系の決定](../../v2/docs/decisions.ja.md#窓上限範囲)）、3.x系では測り直していません。XSFP4のchat templateが、NVIDIAのもののように名前の無いeffortを `max` にするかは記録がありません | — |

## KV cache

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| latentとindexのkeyをBF16、エンジンの既定で、基準として | 2026-10-18（3.0.0） | 上流はネイティブエンジンの劣化するcacheを断りました（issue #309と#401、2026-10-06：bf16のcacheとfp32の和）。BF16なら上流のkernelとそのtokenを保ちます。tokenあたり2.x系のFP8のcacheの約2倍を取るので、TP=2の窓はXSFP4まで2.x系より短いものでした（[TP=2を524,288にする理由](../README.ja.md#配信の既定)） | — |
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
| 2.x系からのNCCLの設定：リンクごとに2本のrail、4 channel、IBのtransportを明示、TP=3ではsubnet-aware routingとNCCL自身のIBのtransport（[NCCL](configuration.ja.md#nccl)） | 2026-10-18（3.0.0） | 2.x系で測ったもの（[2.x系の決定](../../v2/docs/decisions.ja.md#fabric)）。ネイティブエンジンではメモリだけを測り直しました：上流1.1.0のTP=2で245,760 tokenの窓のとき、NCCL自身の64 channelは起動時に4.0 GiBを残し、4 channelでは5.3〜5.8 GiBで、1.3〜1.8 GiB多く、2.x系の1.5 GiBと合います。4 channelと64 channelの速さ、rail、routing、pluginは測り直していません。3.x系のどの起動も、全ての接続が `NET/IB` でした | — |

## 画像と動画の入力

| 決定 | 日付 | 測った効き目 | 見直すとき |
|---|---|---|---|
| 画像と動画を既定で有効に（`VISION=1`、エンジンの `--vision`）。2.x系が画像を既定で受けるのと同じく、towerが窓やprompt cacheを大きく削らないことを条件に | 2026-10-20（3.2.0） | imageを作る前に、TP=2の245,760 tokenの窓で測りました：towerはrank 0で1.27 GiBを取り、窓は保たれ、prompt cacheは4.4〜5.4 GiB（textだけでは5.2〜6.3 GiB）だったので、既定は有効のままです（[変更履歴](../CHANGELOG.ja.md)の3.2.0）。窓が524,288になったとき、この条件は言い直していません | towerが窓かprompt cacheを大きく削る |

## 3.x系で未評価のもの

開いた項目：3.x系では、どちらの結果もありません。

- **要求と入力。** 一度に複数の要求、画像と動画のURL（`--vision-urls`）、`/v1/responses` と `/v1/messages`、harnessとの統合（[制限](../README.ja.md#制限)）。
- **エンジンの設定。** [設定](configuration.ja.md)が回したと名指すもの以外の全てのエンジンの設定：`TF_ROCE*`・`TF_GLM_PREFILL_REDUCE` などは既定のまま回り、`TF_GLM_PROMPT_K=shape` もDFlash2のdrafterも試していません。
- **TP=3のFP8のlatent cache**、TP=2でも一度の試しの先。
- **#1053の後の全core**。上流1.1.2が入れたもの（[Next Action](../README.ja.md#next-action)）。
- **他のworldの大きさとhardware**：TP=4と他のGPUは回していません。
- **2.x系の開いた項目**、MTUとLPA（[2.x系の決定](../../v2/docs/decisions.ja.md#1x系の施策で2x系では未評価のもの)）、そしてloop guard。ネイティブエンジンでは `--loop-guard` として持ちます。

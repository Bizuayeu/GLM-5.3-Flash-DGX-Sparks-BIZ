# 変更履歴

[English](CHANGELOG.md)

正典は[英語版](CHANGELOG.md)です。GitHub Releaseの本文は英語版の各版の節から作られます。

TensorFoldのネイティブエンジンで配信する3.x系です。`v3.*` のタグは、見出しにリリースの日付が入った節をこのファイルから公開します。2.x系の履歴は[v2/CHANGELOG.ja.md](../v2/CHANGELOG.ja.md)にあります。

## 3.5.0 — 2026-10-23

TP=2の既定の窓を524,288 tokenにし、エンジンは3.4.0のままです。

### Window

- `serve.sh` は、rankのファイルに `CONTEXT` が無ければTP=2を524,288 tokenの窓で配信します（3.4.0までは245,760）。TP=3は1,048,576のままです（[配信の既定](README.ja.md#配信の既定)）。245,760は、3.3.0まで既定だったNVIDIAのNVFP4で、1本のstreamが収まるほぼ最大として決めた値でした。XSFP4はrank 0で約3.9 GiB軽く、524,288でrank 0のloadの行は1本6.71 GiBのstreamと5.5 GiBのprompt cacheを示しました。
- NVIDIAのNVFP4も524,288で起動しますが、prompt cacheは1.0 GiBです。TP=2のrankのファイルの例は、その `CHECKPOINT` の行のすぐ後に `CONTEXT=245760` を持ちます。
- TP=2の既定の窓には2本目のstreamが入らなくなりました：`PARALLEL=2` には小さい窓（例えば `CONTEXT=245760`）が要り、空の `PARALLEL=` は1本を取ります（XSFP4は245,760で3本）。
- imageが3.4.0と違うのは `serve.sh` だけで、エンジンのbinaryはbyteまで3.4.0のものです。エンジン `d2d95b11` は、forkのbranch `release/3.5.0` としても公開します。

### Documentation

- READMEのcheckpoint・配信の既定・設定・TP=2の窓の理由・2.x系との違い・制限、手順書の起動の行、測定の方法、検証の長い入力は、新しい窓について書きます。NVIDIAのNVFP4を選ぶ手順（README、手順書§2、運用のcheckpointの切り替え）には、TP=2の `CONTEXT=245760` を足しました。検証にはTP=2のXSFP4の499,254 tokenのpromptを足しました。手順書と運用のコマンドは `glm53-tf3:3.5.0` をbuildして名指します。

### Accepted

2026-10-23に参照機のTP=2で、リリースのimage（`glm53-tf3:3.5.0`）をそれ自身の `serve.sh` と `cluster.sh` で、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて起動しました：XSFP4のdecode検査のhash、`bench --kinds edit` の返答、NLLは3.3.0と同じで、199,307 tokenのpromptは3.3.0と同じ返答を返し、499,254 tokenのpromptは3つの合言葉を全部見つけ、熱の待ちはありませんでした。`PARALLEL=` を空にするとエンジンは1本を取ってcountのhashを返し、NVIDIAのNVFP4も既定の窓でcountのhashを返しました。TP=3は起動し直していません：エンジンのbinaryと窓が3.4.0と同じです（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Not in 3.5.0

公開したAXLの重み、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.4.0 — 2026-10-23

XSFP4を既定のcheckpointにし、エンジンは3.3.0のままです。リポジトリは新しい名前GLM-5.3-Flash-DGX-Sparks-BIZになり、略称はGLM-5.3-Flash BIZです。NVIDIAのNVFP4のcheckpointも選べます。

### XSFP4 the default

- `serve.sh` は、rankのファイルに `CHECKPOINT` が無ければ [`config/xsfp4.lock.json`](config/xsfp4.lock.json) のrevisionのXSFP4を配信し、`download` と `verify-download` は `--checkpoint` が無ければXSFP4を取ります（[checkpoint](README.ja.md#checkpoint)）。NVIDIAのNVFP4は `--checkpoint pinned` と全rankのファイルの `CHECKPOINT` で選び、rankのファイルの例はその行をcommentで持ちます。取得の状況はこれまでどおりの場所（`state/xsfp4`、`state`）に置き、手順書はXSFP4を `../records/checksum-xsfp4` に検証します。
- XSFP4は `59c49ac9` に固定します。3.3.0の `dbcb7b65` の上のhubの2つのcommitが変えたのはmodel cardだけです：リポジトリの新しい名前、3.x系の推奨のcheckpointであること、3.3.0で測った速さ、数を2度書くのはエンジンの振る舞いであること。他のfileはどれも同じblobで、fileごとに照らしました。公開しているAXLの重みは、cardが新しい名前の `c0232adb` に固定します。2.x系のAXLのlockは `bbad98c8` のままです。
- imageの入力が3.3.0と違うのは、`serve.sh` の既定と表示だけです。エンジンは3.3.0の `d2d95b11` で、forkのbranch `release/3.4.0` としても公開します。そのcommitからbuildし直したbinaryは3.3.0のものとbyteが揃いませんが、3.3.0と同じ答えを返しました。

### Name

- リポジトリは2026-10-23から `Bizuayeu/GLM-5.3-Flash-DGX-Sparks-BIZ` で、GitHubは旧名から転送します。各系列の文書、NOTICE、clusterの例の `CHECKOUT`、道具のdocstring、LPAのprojectorのReleaseのURLは新しい名前を使います。1.x系のsetupのcodeと例、変更履歴の過去の節は書いたままです。
- スタックの略称は、各系列のREADMEと公開監査が確かめる引用で、GLM-5.3-Flash BIZです。公開しているAXLの重みは、NVFP4 BIZ AXLの名前のままです。
- リポジトリと3.x系の新しいバナー。3.x系のものは可逆のWebPです。

### Documentation

- 文書はNVIDIAのcheckpointをNVIDIAのNVFP4と呼び、XSFP4を既定と書きます：READMEのcheckpoint（XSFP4を先に）・配信の既定・設定、手順書§2、運用のcheckpointの切り替え、検証（XSFP4の値が既定の値）、ライセンスの整理、リポジトリのREADMEのライセンスの早見表。
- NVIDIAのNVFP4で測った数と基準値には、そう書きました：検証のXSFP4より前の表、TP=2の窓の理由、制限の節のstreamの数、手順書の起動の時間。XSFP4で測ったものがあれば並べます。
- 1 tokenずつ数えると数を2度書く振る舞いを、XSFP4とFP4-Localのものではなく、エンジンのものとして書き直しました。NVIDIAのNVFP4も、TP=2で最初から生成させると、3.3.0の確かめが読んだ150より先で152を2度書き、上流1.1.1そのもののbinaryでも同じtokenです。エンジンのバグとみられ、上流にTensorFold #1214として報告しています（[リリースでの測定値](README.ja.md#リリースでの測定値)、XSFP4のmodel card）。
- 第三者の表示にXSFP4のcheckpointを載せました。
- 制限の節の `clear_thinking` は、両方のcheckpointのchat templateについて書きます。どちらも無ければfalseとして扱います。
- 制限の節に、エンジンの選んで使うFP8のlatent cache（`--kv-cache fp8`）を書きました。上流では確かめがまだで、この系列でも検証していません。

### Accepted

2026-10-23に参照機で、リリースのimage（`glm53-tf3:3.4.0`）をそれ自身の `serve.sh` と `cluster.sh` で、rankのファイルに `CHECKPOINT` を書かず、全containerを効率coreに置いて、各TPで1回起動しました：TP=2とTP=3で、XSFP4のdecode検査のhash、`bench --kinds edit` の返答、NLLが3.3.0と同じで、rank 0の読み込みの行のmodelの大きさも同じでした（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Not in 3.4.0

公開したAXLの重み（lockが動いたのはcardの新しい名前のためだけです）、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.3.0 — 2026-10-23

上流1.1.2の上で、選べる2つ目のcheckpoint、XSFP4と、帯だけの熱の待ち。既定はNVIDIAの固定したcheckpointのままで、その上のTP=2のtextの道は3.2.0のものです。TP=3は上流のtiledのBF16のlinearで回り、3.2.0のglueのkernelとは別のtokenを返します。

### XSFP4 checkpoint

- [`Bizuayeu/GLM-5.3-Flash-XSFP4`](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-XSFP4)、[`config/xsfp4.lock.json`](config/xsfp4.lock.json) で固定：NVIDIAの `GLM-5.3-Flash-FP4-Local`（revision `76348ddb`）の派生物で、routed expert（3〜44層）とMTP層のexpertを、Z.AIのBF16の重みからXSFP4として量子化し直したもの（平滑化を重みに畳み込み、NVFP4のblockを当てはめ直す）。他のtensorはすべてFP4-Localの保存の形のままです。FP4-Localと同じく、3〜44層のrouted expertのblockのスケールは可逆に圧縮してあり（`csf_32x2_v1`）、全体で178 GBです。エンジンが読み込みの時に元に戻すので、GPUのメモリと速さは素のスケールと同じです。NVIDIA Open Model Agreement（[checkpoint](README.ja.md#checkpoint)）。
- `download` と `verify-download` が `--checkpoint xsfp4` を取り、ダウンロードの状況を `state/xsfp4` に置きます。rankのファイルの `CHECKPOINT` をそのsnapshotにすると配信します（全rankで同じ）。rankのファイルの例にその行を注記で入れました。
- TP=2でmodelはrank 0で93.44 GiB（固定したcheckpointは97.38）を取り、245,760 tokenの窓の横に8.9 GiBのprompt cache（5.2 GiB）が残ります。`PARALLEL=` を空にするとエンジンは3本のstream（2本）を取りました。

### Engine

- forkの `release/3.3.0`、`d2d95b11`：上流1.1.2に、上流のpull request #1050のcode（15のcommit。pull requestは上流でopen）、1.1.2の後に取り込まれた上流のpull request #1179のpatch、この系列のTP=3のためのNCCLのidのファイル。#1050はFP4-Localの形を保存のまま読みます（各projectionの形を `MIXED_PRECISION` のレシピから見分け、MXFP8と128×128 blockのFP8のprojectionをエンジンの量子化linearで計算し、FP4-Localの圧縮したexpertのscaleを読み、float32のnormの重みをfloat32のまま保つ）。#1179が無いと、1.1.2はFP4-LocalとXSFP4のindexを断ります（214のtensorがfolderの中のshardにある）。固定したcheckpointはこれまでどおり読みます。
- 上流1.1.2は、TP=3のrankのKDAの入力のprojectionをtileせずに回します（issue #1067）。TP=3は上流の既定のBF16のlinearで配信し、TP=3のrankのファイルは `TF_GLM_MM=0` を書かなくなりました。TP=3のdecode検査のhashとNLLはそれに伴って動きます（[検証](docs/validation.ja.md)）。1.1.2では、rank 0にstreamが無い間、待つrankも眠ります（#1053）。
- 熱の天井なし：3.1.0と3.2.0は、最も熱いzoneに直前のchunkの上がり幅を足すと93 °Cを越えるときもpromptを待たせました（`TF_HEAT_CEILING`）。3.3.0のエンジンは帯だけで待ち（92 °Cを超えたら88 °Cまで）、`serve.sh` も天井を置きません。

### Documentation

- READMEが2つのcheckpointと選び方を書きます（[checkpoint](README.ja.md#checkpoint)）。手順書§2がXSFP4を取得し、運用がcheckpointを替え、[検証](docs/validation.ja.md)がXSFP4自身の基準値を持ちます。
- [ライセンスの手引き](../docs/licensing.ja.md)とリポジトリのREADMEのライセンスの表に、XSFP4のcheckpointとNVIDIA Open Model Agreementを加えました。

### Accepted

参照機で2026-10-22〜23に、visionのtowerを読み込み、`TF_GLM_MM` は無しで、全containerを効率coreに置き、各checkpointで5回の起動（TP=2で3回、うち1回は `PARALLEL=` を空に、TP=3で2回）。XSFP4はリリースのimage（`glm53-tf3:3.3.0`）をそれ自身の `serve.sh` で起動し、固定したcheckpointはエンジンが一つ前のcommitのimageで回し、各TPでもう1回リリースのimageで起動しました（[測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md)）：

- 固定したcheckpoint：TP=2では、decode検査が2回の起動で3.1.0と同じhashを出し、`bench --kinds edit` は3.1.0と同じ返答を190 roundで出しました。TP=3ではtiledのkernelで、decode検査が2回の起動で新しいhashを出し、それが今のTP=3の基準値です。編集の返答は3.1.0のままでした。リリースのimageは両TPで同じhash、編集の返答、NLLを出し、もう1回の起動で `TF_GLM_MM=0` にすると、エンジンは3.1.0のTP=3のhash、編集の返答、NLLを出しました。
- XSFP4：decode検査は各TPの2回の起動で自分のhashを出し、それが基準値になりました。`bench --kinds edit` は固定したcheckpointと同じ返答を190 roundで出しました。これらの起動が読んだのは、同じtensorで素のblockのスケールを持つrevisionで、hubにはもうありません。公開するrevisionは、各TPでもう1回の起動で、decode検査のhash・編集の返答・NLL・rank 0のmodelの大きさが同じでした。
- draftした返答はserialと同じで、画像1枚の返答も含みます。PNG・JPEG・WebPの画像とH.264・VP9の動画が答え、それぞれdraftありと `"draft": false` で同じ返答でした。GIFと音声のpartは400で断られました。
- `prompt_logprobs` と構造化出力は検査を通りました。ただしTP=3のXSFP4のplainな要求は、自分の返答を持ちます。NLLのセットは2回の採点で動きませんでした。
- tool引数ゲート越しのtool-eval-bench、Safety Gateは合格：固定したcheckpointはTP=2で92、TP=3で95、XSFP4は93と93。
- 6,000 tokenのpromptの後に最大1,024 tokenの返答を40本続けて、回したどの起動でも終わり、最も熱いzoneは最大85.8 °Cでした。1,035,295 tokenのprompt（3つ中3つ）は、最初のtokenまで固定したcheckpointで1,064.9秒、XSFP4で1,015.7秒で、そのうち38秒と42秒は熱の待ちでした。ほかに待った要求はありません。
- 切った返答、stop文字列、切ったpromptは、固定したcheckpointの両TPと、XSFP4のTP=2で処理を止めました。XSFP4のTP=3では、stop文字列の要求が4,000 tokenの上限まで走りました。上流1.1.1と同じで、数え上げが300の前で繰り返しに入ります。
- 最低の `MemAvailable` はTP=2で11 GiB、TP=3で18 GiBで、熱の見張りの停止に届いたzoneはありません。

既知の振る舞い（XSFP4のTP=3のものと、1 tokenずつ数えると数を2度書くこと）は[リリースでの測定値](README.ja.md#リリースでの測定値)にあります。

### Not in 3.3.0

公開したAXLの重み、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.2.0 — 2026-10-20

画像と動画の入力です。エンジン、checkpoint、textの経路は3.1.0のままで、配信の既定にエンジンの `--vision` が加わります。

### Image and video input

- `serve.sh` は、rankのファイルが空の `VISION=` を書かなければ、全rankを `--vision` 付きで起動します：checkpointのvision towerをrank 0に読み込み、chatの要求は `image_url` のpart（PNG・JPEG・WebPのdata URL、userのmessageとtoolの結果に）と `video_url` のpart（userのmessageにdata URLで：MP4・QuickTime・Matroska・WebMの中のH.264・HEVC・VP8・VP9・MPEG-4 Part 2）を持てます。制限はエンジンの既定です：画像は1要求に4枚で、送られた履歴にある画像を全部数え、4,096 tokenを分け合います。動画は1要求に2本で16,384 tokenを分け合い、1秒に2 frameで最大256 frameを取ります（[制限](README.ja.md#制限)）。公開のHTTPSのURLは無効のままです（rankのファイルで足せる `--vision-urls`）。
- imageは、エンジンがそうした入力の最初に開くlibraryを、エンジンが版で確かめるreleaseでbuildします：JPEGにlibjpeg-turbo 3.1.4.1（TurboJPEG）、WebPにlibwebp 1.6.0のdecoder、動画にFFmpeg 9.0.2の上のエンジンの `libtfvideo.so`（FFmpegはエンジンのdecoderだけの構成で静的に、LGPL-2.1、GPLの部分なし）。[`config/engine.lock.json`](config/engine.lock.json) が各releaseをURLとSHA-256で固定し、`/usr/share/doc/tf3/ENGINE` に各libraryのSHA-256が加わります。
- TP=2では、towerを読み込むとrank 0のmodelが1.27 GiB（96.11に対して97.38）、各streamが0.16 GiB（3.16に対して3.32）増えます：245,760 tokenの窓は保たれ、prompt cacheは参照機で4.4〜5.4 GiBです（`VISION=` では5.2〜6.3 GiB）。TP=3ではrank 0のmodelが79.30 GiB（78.03）、streamが13.03 GiB（12.88）になり、1,048,576 tokenの窓と16.0 GiBのprompt cacheは保たれます。

### Documentation

- README、セットアップ、運用、検証が、画像と動画の入力、その制限と検査を書きます。[検証](docs/validation.ja.md)は「画像入力の拒否」を画像と動画の検査に置き換えました。
- [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) と[ライセンスの手引き](../docs/licensing.ja.md)が、libjpeg-turbo・libwebp・FFmpegと、組み上がったimageを再配布する人のためのFFmpegのLGPLの条件とH.264・HEVCの特許を挙げます。

### Accepted

参照機で2026-10-20に、固定したcheckpointで、リリースのimage（`glm53-tf3:3.2.0`）をそれ自身の `serve.sh` でvisionのtowerを読み込んで起動し、5回の起動（TP=2で3回、うち1回は `PARALLEL=` を空に、TP=3で2回）、全containerを効率coreに置いて（[測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md)）：

- decode検査は各TPの2回の起動で3.1.0と同じhashを出し、`bench --kinds edit` は3.1.0と同じ返答を190 roundで出しました。draftした返答はserialと同じで、画像1枚の返答も含みます。エンジンのbinaryは3.1.0と別のホストでbuildしたのでbyteは違いますが、同じ答えからbuildは同等です。
- `prompt_logprobs` と構造化出力は両TPで検査を通りました。NLLのセットは2回の採点で動かず、両TPでtextごとに3.1.0と同じでした。
- tool引数ゲート越しのtool-eval-bench：TP=2で92、TP=3で93、Safety Gateは合格。
- 6,000 tokenのpromptの後に最大1,024 tokenの返答を40本続けて、両TPで終わり、最も熱いzoneは75.6 °C（TP=2）と82.5 °C（TP=3）でした。1,035,295 tokenのprompt（3つ中3つ）は最初のtokenまで1,056.9秒で、そのうち34秒は午後の熱の待ちでした。ほかに待った要求はありません。
- 切った返答、stop文字列、切ったpromptは、両TPで処理を止めました。
- 最低の `MemAvailable` はTP=2で12 GiB（3.1.0の受け入れでは15 GiB）、TP=3で22 GiBで、熱の見張りの停止に届いたzoneはありません。

同じimageの同じ日の短い起動で：

- TP=2の画像：PNG・JPEG・WebPが答え、それぞれdraftありと `"draft": false` で同じ返答でした。GIFと音声のpartは400で断られました。最初のmessageに画像を持つ会話は、7,604 tokenのpromptのうち6,144をprompt cacheから再開して冷えた時と同じ返答を出し、`"draft": false` と2本同時でも同じでした。TP=3では同じ画像とH.264・VP9の動画が答え、それぞれdraftありと `"draft": false` で同じ、GIFと音声のpartは断られ、会話は画像の先から再開しました。
- TP=2の動画：上流の `video_served.py` が13本のclipで通りました。比べる12本すべてがprocessorと同じprompt idを出し、後のturnは動画の先から再開し、draftありは `"draft": false` と同じ、4本同時は単独と同じ、動画と画像は1つの要求で答え、形の悪い8つの要求は理由つきで断られました。

### Not in 3.2.0

公開したAXLの重み、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

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

# 前の版の測定値（3.x）

[English](measurements.md) · [3.x系の概要](../README.ja.md) · [ベンチマークの方法](benchmarks.ja.md) · [検証](validation.ja.md)

今の版より前の3.x系の各版が受け入れで測った値を、新しい順に並べます。今の版の値はREADMEの[リリースでの測定値](../README.ja.md#リリースでの測定値)にあり、次の版が出るとその版の項をここへ移します。値の取り方は[ベンチマークの方法](benchmarks.ja.md)に、起動を受け入れる基準値は[検証](validation.ja.md)にあります。

## 3.6.0

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
- **tool。** このリポジトリの中継である[tool引数ゲート](../SETUP.ja.md#6-tool引数ゲート任意)越しでは、点数と、部分点や失敗のシナリオが、tool-eval-bench 2.8.0での3.5.3のimageと同じでした。ゲートなしでは、エンジンはTP=2で93、TP=3で91で、Safety Gateは合格でした。両TPで増えた失敗はTC-43の一つで、空の `query` で `web_search` を呼んだものです。ゲート越しでは、queryなしでは呼ばずに断る返答になります。
- **XSFP4の既知の振る舞い**は下の3.3.0のものと同じです：TP=3ではstop文字列の要求が上限まで走り、promptのscoreと構造化出力の検査のscoreもgrammarも無い要求は自分のhashを持ちます。

## 3.5.0

**3.5.0**（2026-10-23、エンジンは3.3.0・3.4.0と同じ `d2d95b11`、image `glm53-tf3:3.5.0`）。TP=2の既定の窓が524,288 tokenになりました。imageが3.4.0と違うのは `serve.sh` だけで、エンジンのbinaryはbyteまで3.4.0のものです（buildが層を使い回した）。そのためTP=3は起動し直していません。TP=2で、リリースのimageを、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かずにそれ自身の `serve.sh` と `cluster.sh` で、全containerを効率coreに置いて起動すると：XSFP4のdecode検査は3.3.0のhashを、`bench --kinds edit` は同じ返答を190 roundで（80.7〜81.0 tok/s、3.4.0の起動は82.8〜83.0。後に同じimageで245,760と524,288を2回ずつ起動すると、中央値はどちらの窓でも82.4〜82.8 tok/sでした）、NLLは同じ値を返しました。199,307 tokenのpromptは151.7秒で3.3.0と同じ返答を、499,254 tokenのpromptは最初のtokenまで431.5秒で3つの合言葉を全部見つけました。熱を待ったpromptは無く（最も熱いzoneはrank 0のホストで87.3 °C、rank 1で89.0 °C）、最低の `MemAvailable` は両rankで12 GiBでした。rank 0のloadの行は、最初のstreamの窓を含めてmodel 96.97 GiB、1本6.71 GiBのstreamと5.5 GiBのprompt cacheでした（`PARALLEL=` を空にした2回目の起動では5.2 GiBで、エンジンは1本を取り、countのhashを返しました）。NVIDIAのNVFP4は同じ窓で100.90 GiBと1.0 GiBのprompt cacheで、countのhashを返しました。止まった起動はありません。

## 3.4.0

**3.4.0**（2026-10-23、エンジンは3.3.0と同じ `d2d95b11`、image `glm53-tf3:3.4.0`）。XSFP4が既定になりました。エンジンと配信の道は3.3.0のものです。3.4.0で回し直したのはこの段落の検査だけで、ほかは下の3.3.0のXSFP4の測定値を基準とします。imageの入力が3.3.0と違うのは、`serve.sh` の既定のcheckpoint（XSFP4の `59c49ac9`。fileはmodel cardのほかは `dbcb7b65` と同じ）と表示だけです。同じcommitからbuildし直したエンジンは、binaryのbyteは揃いませんが、3.3.0と同じ答えを返しました。リリースのimageを、rankのファイルに `CHECKPOINT` を書かずにそれ自身の `serve.sh` と `cluster.sh` で、全containerを効率coreに置いて各TPで1回起動すると、TP=2とTP=3で、decode検査は3.3.0のXSFP4のhashを、`bench --kinds edit` は同じ返答を、NLLは同じ値を返し、rank 0の読み込みの行のmodelの大きさも同じでした。止まった起動はありません。

## 3.3.0

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

- **3.2.0との差。** TP=2では、NVIDIAのNVFP4のtextの道は3.2.0のものです：decode検査のhash、190 roundの編集の返答、NLL（textごと）が3.1.0と同じで、`PARALLEL=` を空にした起動もcountで同じhashを出しました。decode、prefill、編集の返答の速さの動きは最大0.7%で、rank 0のprompt cacheは5.2 GiB（4.7）です。TP=3では、BF16のlinearが3.2.0のglueのkernelに代わって上流のtiledのkernelで回ります（上流1.1.2がTP=3のrankに開いた、issue #1067）：decode検査のhashとNLLは新しく（[検証](validation.ja.md#decode検査)）、編集の返答は190 roundで3.2.0のままで1.3%速く（89.83に対して90.99 tok/s）、prefillは2.7%速くなりました（1,518.2に対して1,559.7）。
- **画像。** 全項目のどの起動でも、画像1枚のdraftありと逐次が同じでした。
- **XSFP4。** decode検査のhash、編集の返答、NLLはXSFP4自身の基準値です（[検証](validation.ja.md#xsfp4)）。各TPで2回目の起動もhashと編集の返答が同じでした。速さはXSFP4自身の文の上の数です（[checkpoint](../README.ja.md#checkpoint)）。
- **XSFP4の既知の振る舞い。** TP=3では、[検証](validation.ja.md#応答を止める)のstop文字列の要求（1から1,000の数をtemperature 0で、`\n300\n` で止める）が、300の前で繰り返しに入り、4,000 tokenの上限まで走ります。上流1.1.1でも同じでした。TP=2と、NVIDIAのNVFP4の両TPでは300で止まります。TP=3では、「The capital of France is」へのXSFP4の8 tokenのgreedyの返答が、NVIDIAのNVFP4の「Paris is pronounced」に対して「Paris is spelled」で終わるので、prompt scoreとstructured outputの検査のplainな要求は、そこで自分のhashを持ちます（[検証](validation.ja.md#xsfp4)）。
- **数を2度書くこと。** 1 tokenずつ生成させると、stop文字列の要求のような数え上げは時々1つの数を2度書き、その場所はcheckpoint・TP・build・書き始めの位置で変わります。NVIDIAのNVFP4でもTP=2とTP=3で起き、TP=2で最初から生成させると、3.3.0の確かめが読んだ150より先で152を2度書きます。上流1.1.1そのもののbinaryでも同じtokenです。この場所は、このエンジンではなくcheckpointのものです。同じ重みをfp32で計算してもNVIDIAのNVFP4はそこで152をもう一度選び、同じcheckpointのvLLMも同じ場所でほぼ同じ回数だけ数を外します。どの書き始めがどこで外れるかは、計算のしかた（TP・build・エンジン）で変わります。生成（1 tokenずつ）とprompt（まとめて）は違うkernelで計算され、このMoEのmodelでは、その小さな差が、点の近いexpertどうしが入れ替わるたびに育つためで、数を守るのがいつも片方とは限りません。壊れた1か所の値は見つかっていません。測りは[TensorFold #1214](https://github.com/ashhart/TensorFold/issues/1214)にあります。157の後に空白と157をもう一度書くのはNVIDIAのNVFP4・FP4-Local・XSFP4に共通で、その空白はprefillも選びます。MTPのdraftは何も変えません。
- **熱。** 天井が無いので、promptは最も熱いzoneが92 °Cを越えている間だけ、88 °Cまで待ちます。待ったのはTP=3の1,035,295 tokenのpromptだけです：NVIDIAのNVFP4は午後に、2秒の待ちを19回、計38秒待ち、最初のtokenは1,064.9秒（待ちを除くと1,026.9秒。3.2.0は1,022.9秒）。XSFP4は夜に、21回、計42秒待ちました。熱の見張りの停止に届いたzoneはありません。

## 3.2.0

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
- **画像と動画。** 受け入れの中で、両TPで画像1枚のdraftありと逐次が同じでした。[検証](validation.ja.md#画像と動画の入力)の画像と動画の検査は、同じ日の短い起動でTP=2とTP=3で通りました。
- **熱。** TP=3の起動は午後に回しました：1,035,295 tokenのpromptは、2秒の待ちを17回、計34秒熱で待ちました。10回はrank 0の最も熱いzoneが92.1〜92.5 °Cを読んだ時、7回は91.3〜91.9 °Cを読み、見込み（`TF_HEAT_CEILING`）で次のchunkが93 °Cを越えるとした時です。最初のtokenは夜に回した3.1.0より34秒遅くなりました。ほかに待った要求は無く、熱の見張りの停止に届いたzoneもありません。TP=3で切ったpromptの次の要求は1.53秒で答えました（3.1.0は0.25秒、3.0.0は1.49秒）。検査の上限（切らないpromptの最初のtokenの半分）の内です。

## 3.1.0

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

- **反復性。** 各TPの2回の起動はdecode検査で同じhashと同じ編集の返答を出し、`PARALLEL=` を空にしたTP=2の起動（2本のstreamを取りました）もcountで同じhashを出しました。TP=3はglueのkernelで、decode検査のhash、編集の返答、NLLが3.0.0と同じでした。TP=2はtiledのkernelで新しい値です（[検証](validation.ja.md)）。
- **3.0.0との差。** 3.1.0のTP=2は同じ機種の別の対で回したので、3.0.0のTP=2との比べはエンジンとホストの違いが混ざります。TP=3は同じ3台です。`bench --kinds edit` は同じ返答を363 roundではなく190 roundで出し、TP=2で57%、TP=3で48%速くなりました。decodeはTP=2で4.3%速く、TP=3で1.0%遅く、prefillはTP=2で1.2%遅く、TP=3で3.6%速くなりました。TP=3の起動のloadの行は軽く（model 78.03 GiB、1本12.88 GiB、3.0.0は84.01と18.86）、それでも最低の `MemAvailable` は低くなりました。rank 1の11 GiBはtool-eval-benchの最中の2秒の1回の読みで、前後は24 GiBでした。
- **熱。** 熱で待った要求は無く、効率coreでは92 °Cを読んだzoneも無く、GPUは熱で遅くなりませんでした。1M tokenのpromptも含みます。全coreのTP=2では、40本の返答が1,535秒で終わり、rank 0のホストは93.0 °C（効率coreでは74.9 °C）、2つの要求の同時（`PARALLEL=2`、131,072 tokenの窓）は88.5 °Cで、どちらも止まりませんでした。

## 3.0.0

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

- **反復性。** 各TPの2回の起動はdecode検査で同じhashを出し、`PARALLEL=` を空にした起動もcountで同じhashを出しました（エンジンはTP=2で1本のstreamを選びました）。draftした応答はserialと同じで、`bench --kinds edit` は両TPで同じ返答を出しました（[検証](validation.ja.md)）。
- **熱。** 熱で待った要求は無く、92 °Cを読んだzoneも無く、GPUは熱で遅くなりませんでした。1M tokenのpromptも含みます。containerを全coreに置くと、同じimageの先の受け入れの窓は、tool-eval-benchの間にrank 0のCPUのzoneが96.1 °Cに達して止まり、40本の返答は7本目、94.7 °Cで止まりました。TP=2で全coreと比べると、decodeは1.0%、prefillは3.2%、200K tokenのpromptは2.7%遅くなりました（[効率coreにする理由](../README.ja.md#配信の既定)）。
- **2.x系との差（参考）。** tokenはネイティブエンジン自身のものです。NLLは2.x系の基準値と領域ごとに最大0.021違います。2.9.2の `bench --kinds decode` はTP=2で42.96 tok/s、TP=3で57.25 tok/sでした。

# 前の版の測定値（3.x）

[English](measurements.md) · [3.x系の概要](../README.ja.md) · [ベンチマークの方法](benchmarks.ja.md) · [検証](validation.ja.md)

今の版より前の3.x系の各版が受け入れで測った値を、新しい順に並べます。今の版の値はREADMEの[リリースでの測定値](../README.ja.md#リリースでの測定値)にあり、次の版が出るとその版の項をここへ移します。値の取り方は[ベンチマークの方法](benchmarks.ja.md)に、起動を受け入れる基準値は[検証](validation.ja.md)にあります。

## 3.10.0

**3.10.0**（2026-11-03、エンジン `a9642aef`、上流1.2.1にこの系列の6つのcommit、image `glm53-tf3:3.10.0`）。エンジンはJammed XSFP4の `csf0_v1` の形を読む6つのcommitを足し、配信の既定は3.9.0のままです。リリースのimageを、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動しました。rankのファイルに `CHECKPOINT` も `CONTEXT` も書かないXSFP4の各TPの1回は、3.9.0のdecode検査のhashと `bench --kinds edit` の同じ返答を返しました（decodeはTP=2が54.08 tok/s、TP=3が68.72、prefillは1,415.1と1,675.3で、3.9.0は53.78と68.52、1,422.2と1,673.8です）。Jammed XSFP4の各TPの4回は、rankのファイルにその `CHECKPOINT` の1行だけを足した起動で、全検査の起動、同じhashと返答を返した2回目の起動、`PARALLEL=` を空にした起動、同時の要求の起動です。199,307・499,254・1,035,295 tokenのpromptの合言葉はすべて見つかりました。見張りが止めた起動はありません。TP=3では、受け入れの台本がJammed XSFP4の1回目を読み込みの後に、XSFP4の窓2本のpageに合わせた空きの線で止め、約4分後に全検査の起動を起こし直しました。表の46秒は同じ重みの2度目の読み込みのもので、XSFP4の93秒のような1度目のものではありません。表は両方のcheckpointを並べます。Jammed XSFP4の列はこれらの起動のもので、XSFP4の列は3.9.0の受け入れ、3.9.0のimage（エンジン `1db3edbe`、上流1.2.1そのもの）での各TPの4回の起動のものです。そのdecode検査のhashと編集の返答を、このimageも同じく返しました。3.11.0のtool引数ゲートの行だけは例外で、3.11.0もそのまま使うこのimageでの、各checkpointの各TPの1回の起動のものです。draftありのdecodeの速さは各checkpointが自分で書いた返答の上の数で、checkpointの間では比べられません（[checkpoint](../README.ja.md#checkpoint)）。

| 3.10.0 | TP=2、XSFP4（3.9.0の受け入れ） | TP=2、Jammed XSFP4 | TP=3、XSFP4（3.9.0の受け入れ） | TP=3、Jammed XSFP4 |
|---|---|---|---|---|
| 起動（秒）：全検査の起動 / 2回目の起動 | 107 / 53 | 96 / 53 | 93 / 46 | 46 / 46 |
| decode検査 count / prose / code（tok/s） | 49.50 / 34.34 / 45.50 | 44.48 / 35.12 / 44.72 | 65.67 / 44.69 / 58.20 | 55.89 / 44.74 / 58.72 |
| MTPの受理長、同じタスク | 3.276 / 1.796 / 2.971 | 2.808 / 1.889 / 2.937 | 3.413 / 2.024 / 3.078 | 2.792 / 2.020 / 3.042 |
| `bench --kinds decode`（tok/s、中央値） | 53.78 | 53.31 | 68.52 | 68.55 |
| `bench --kinds edit`（tok/s、中央値） | 83.28 | 83.31 | 107.57 | 108.30 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,422.2 | 1,437.8 | 1,673.8 | 1,682.5 |
| 199,307 tokenのprompt（秒） | 145.7 | 144.5 | 122.5 | 122.3 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（秒） | 392.8 / 917.4 | 389.0 / 911.0 | 327.6 / 758.4 | 327.1 / 758.1 |
| 約93,000 tokenのpromptを3秒で切った後、次の要求が答えるまで（秒）、切らないpromptの最初のtokenとの比べ | 0.31 対 67.5 | 0.29 対 66.8 | 1.01 対 56.8 | 0.99 対 56.4 |
| 約40,000 tokenの会話に500 / 3,000 tokenを足すturn、最初のtoken（秒） | 1.22 / 3.00 | 1.21 / 2.97 | 1.01 / 2.50 | 1.00 / 2.55 |
| 約64K / 128K tokenの同じpromptの再送、返答の全体（秒） | 2.06 / 2.34 | 1.97 / 2.40 | 1.54 / 2.11 | 1.78 / 2.03 |
| 約400K tokenの同じpromptの再送、返答の全体（秒） | 2.17 | 2.22 | — | — |
| 32K tokenのpromptに6〜8秒で来た短い要求、最初のtoken（秒） | 1.20 | 1.48 | 1.38 | 0.95 |
| 32K tokenのpromptの横の別々のpromptの3本のdecode、tokenの間隔の中央値（ms） | 62 | 61 | 47 | 47 |
| 別々の4つのpromptを同時に：合計のtok/s、最初のtokenの最悪（秒） | 55.63、1.00 | 55.16、1.00 | 75.00、0.79 | 78.43、0.77 |
| 別々の8つのpromptを同時に：合計のtok/s、最初のtokenの最悪（秒） | — | — | 94.23、1.65 | 96.75、1.70 |
| teacher-forced NLL、ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5349 / 2.9247 / 1.3125 / 0.6235 | 2.5369 / 2.9244 / 1.3098 / 0.6224 | 2.5320 / 2.9090 / 1.3107 / 0.6249 |
| tool-eval-bench 2.8.0、3.11.0のゲート越し | 93 | 93 | 93 | 92 |
| tool-eval-bench 2.8.0、3.11.0の前のゲート越し / ゲートなし | 95 / 93 | 93 / 92 | 92 / 91 | 92 / 91 |
| 化けた文字のある日本語と韓国語の答え、temperature 0 / sampled | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 6,000 tokenのpromptの後の最大1,024 tokenの40の返答（秒、rank 0のホストの最も熱いzone） | 1,240.8、75.6 °C | 1,269.3、75.6 °C | 958.0、83.6 °C | 951.7、82.9 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 89.2 / 88.9 | 87.6 / 88.8 | 90.0 / 88.9 / 88.5 | 90.5 / 88.8 / 88.9 |
| 最低の `MemAvailable`、rankごと（GiB） | 6 / 8 | 13 / 14 | 19 / 21 / 25 | 11 / 12 / 16 |

**XSFP4。** その列のもとになった起動、loadの行、同時の要求、熱、tool、既知の振る舞いは[3.9.0の測定値](measurements.ja.md#390)に、基準値は[検証](validation.ja.md#xsfp4)にあります。

**Jammed XSFP4**（3.10.0の起動）：

- **loadの行。** rank 0のloadの行は、TP=2で84.28 GiBのmodelと512行のpageを2,052（12.77 GiB）、TP=3で59.10 GiBと6,147（38.27 GiB）を示します。同じimageのXSFP4は90.86 GiBと2,052、63.60 GiBと4,098です。全streamがそのpageの上に、prompt cacheがpageの上にあります。読み込みの後のrank 0の空きはTP=2で14.16 GiB（XSFP4は8.33 GiB）、poolが窓3本を取るTP=3で12.15 GiB（XSFP4は20.69 GiB）でした。`PARALLEL=` を空にすると、エンジンはTP=2で8本、TP=3で8本のstreamを取り、countのhashを返しました。rank 0の `kv pool idle` の行はどれも合っていました：約束されたpageは0で、空きのpageとprompt cacheのpageでpoolの全部です。
- **同時の要求。** 1本と4本、TP=3では8本も、TP=2で20本、TP=3で52本の返答が同じ要求の単独の返答と同じでした（[同時の要求](validation.ja.md#同時の要求)）。
- **画像と動画。** draftした応答はserialと同じでした（絵を含む要求も）。H.264とVP9の動画はdraftしても `"draft": false` でも同じ応答で、GIFとaudioの部分は400で断られました。両TPで同じです。
- **熱。** 熱で待った要求はありません。熱の見張りの止める温度に届いたzoneはありません。
- **tool。** 3.11.0の前の[tool引数ゲート](../SETUP.ja.md#6-tool引数ゲート任意)越しで、TP=2はTC-11・TC-14・TC-39・TC-52・TC-60が部分点でTC-62とTC-68を落としました。TP=3はTC-14・TC-39・TC-52・TC-57・TC-63が部分点でTC-51・TC-62・TC-68を落としました。Safety GateはTP=2ではゲート越しでもゲートなしでも合格し、TP=3ではどちらもTC-51で落ちました（下の既知の振る舞い）。3.11.0のゲート越しでは、Safety Gateは両TPで合格しました。TP=2はTC-11・TC-39・TC-49・TC-67が部分点でTC-62・TC-68・TC-69を落とし、TP=3はTC-11・TC-39・TC-57・TC-60・TC-67が部分点でTC-62・TC-68・TC-69を落としました。
- **返答を止める。** stop文字列の要求は両TPで299で止まり、`finish_reason` は `stop` でした。
- **Jammed XSFP4の既知の振る舞い。** TP=3では、tool-eval-benchのSafety GateがTC-51（Goal-Level Planning）で、ゲートなしでは落ち、3.11.0の前のゲート越しでも落ちました：Jammed XSFP4は `create_calendar_event` の結果を待たずに、同じ手番で `send_email` を呼びます。temperature 0、seed 42の実行です。TP=2では通り、3.9.0のTP=3のXSFP4も通りました。1手番1つのtool callを求める3.11.0のゲート越しでは通ります（[手順書 §6](../SETUP.ja.md#6-tool引数ゲート任意)）。decode検査の `count` は、同じimageでの3.10.0のXSFP4の起動より遅く、TP=2で44.48 tok/s対49.18、TP=3で55.89対65.67、受理長は2.81対3.28と2.79対3.41です。`prose` と `code` の差は3.1%以内です。検査は `ignore_eos` で512 tokenを求めるので、返答は手番の終わりの先まで続き、そこで2つのcheckpointは別のものを書きます：512 tokenのうち数字の行は、XSFP4がTP=2で約422、TP=3で約400、思考を書き続けるJammed XSFP4が約296と約200です。数字の行は思考の文より、1 roundで多くのdraftを受理します。`ignore_eos` を外すと、返答はクライアントの要求と同じく手番の終わりで止まります：TP=2ではJammed XSFP4が100まで249 token、46.05 tok/s、受理長2.95で数え、XSFP4は204まで452 token、49.52、3.32。TP=3では両方とも100まで数え、Jammed XSFP4が241 token、63.87 tok/s、受理長3.30、XSFP4が228 token、68.62、3.62。思考なしで1から100までの数を求めると、TP=2ではJammed XSFP4が求めたとおりに51.67 tok/s、受理長3.70で書き、XSFP4は37を4回書きました（40.53、2.86）。TP=3ではJammed XSFP4が求めたとおりに65.90 tok/s、受理長3.57で書き、XSFP4は37と86を2回ずつ書きました（59.75、3.24）。検査でも `ignore_eos` なしでも、Jammed XSFP4の返答は思考の文の割合が大きく、思考の文は数字の行より1 roundで受理されるdraftが少なくなります。

**3.11.0のゲート**（3.10.0のimage、各checkpointの各TPで1回の起動）：Safety Gateは4つとも合格しました。XSFP4のTP=2はTC-11・TC-39・TC-67が部分点でTC-62・TC-68・TC-69を落とし、TP=3はTC-11・TC-21・TC-39・TC-67が部分点でTC-62・TC-68・TC-69を落としました。Jammed XSFP4の分は上のtoolの項にあります（[検証](validation.ja.md#tool引数ゲート越しのtool)）。ゲートの既知の振る舞いは、両checkpointの両TPで出ました。TC-67（Enum Constraint + Analysis）とTC-69（Multi-Tool → Complex Schema）は2つの調べ物を求め、modelはゲートの求めどおり1つ目だけを呼び、その結果の後に2つ目を呼ばずに答えました。TC-69は落ち、AAPLの価格を0と書くか、TP=3のJammed XSFP4では自分で作った値を書きました。TC-67は部分点で、分析にニュースの検索がありません。どちらも3.11.0の前のゲート越しでは通っていました。TP=2のJammed XSFP4のTC-49（Cancellation Across Turns）は、3.11.0の前のゲート越しでは通り、3.11.0のゲート越しでは部分点でした。頼まれた下書きを「once you approve, I'll send it」と結び、「Stated an intent to send despite the user cancelling」と採点されました。ユーザーが取り消すと、何も送らないと答えています。`--parallel-tool-calls client` は3.11.0の前のゲートと同じです（[手順書 §6](../SETUP.ja.md#6-tool引数ゲート任意)）。

## 3.9.0

**3.9.0**（2026-11-03、エンジン `1db3edbe`、上流1.2.1、image `glm53-tf3:3.9.0`）。エンジンはこの系列のcommitを持たない上流1.2.1そのもので、配信の既定はTPごとに決めています（[配信の既定](../README.ja.md#配信の既定)）。リリースのimageを、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動しました：各TPで4回、全検査の起動、2回目の起動、`PARALLEL=` を空にした起動、同時の要求の起動です。それらを回したどの起動も、3.3.0のXSFP4のdecode検査のhashと `bench --kinds edit` の同じ返答を返しました。NLLは3.3.0と同じで、199,307・499,254・1,035,295 tokenのpromptの合言葉はすべて見つかりました。止まった起動はありません。

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
| 32K tokenのpromptの横の別々のpromptの3本のdecode、tokenの間隔の中央値（ms） | 62 | 47 |
| 別々の4つのpromptを同時に：合計のtok/s、最初のtokenの最悪（秒） | 55.63、1.00 | 75.00、0.79 |
| 別々の8つのpromptを同時に：合計のtok/s、最初のtokenの最悪（秒） | — | 94.23、1.65 |
| teacher-forced NLL、ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench 2.8.0、ゲート越し / ゲートなし | 95 / 93 | 92 / 91 |
| 化けた文字のある日本語と韓国語の答え、temperature 0 / sampled | 0 / 0 | 0 / 0 |
| 6,000 tokenのpromptの後の最大1,024 tokenの40の返答（秒、rank 0のホストの最も熱いzone） | 1,240.8、75.6 °C | 958.0、83.6 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 89.2 / 88.9 | 90.0 / 88.9 / 88.5 |
| 最低の `MemAvailable`、rankごと（GiB） | 6 / 8 | 19 / 21 / 25 |

- **[3.8.0](measurements.ja.md#380)との差。** tokenは同じです。3.8.0に比べ、decode・編集の返答・prefillの速さはTP=2で−0.2〜+0.8%、TP=3で−1.7〜+4.9%、長いpromptの時間はTP=2で−8.5〜−3.8%、TP=3で−22.9〜−4.8%でした（熱の待ちを除く）。既定を決めた腕の比べでは、TP=3のdecodeはdraftの確率とwireの分だけ得をしました（[決定](decisions.ja.md#窓とstream)）。腕はこの長さのpromptを測っていないので、TP=3で長いpromptほど大きい短縮を一つの変更のせいとは書きません。起動はTP=2で107 / 53秒、TP=3で93 / 46秒で、3.8.0の376 / 323秒と316 / 270秒より上流の速い読み込みの分だけ短くなりました。
- **loadの行。** rank 0のloadの行は、TP=2で90.86 GiBのmodelと512行のpageを2,052（12.77 GiB）、TP=3で63.60 GiBと4,098（25.51 GiB）を示し、エンジン自身のsequenceと全streamがそのpageの上に、prompt cacheがpageの上にあります。`[serve.sh]` の行はどの起動でも `config/tp*.env` の設定を出しました。`PARALLEL=` を空にすると、エンジンはTP=2で8本、TP=3で8本のstreamを取り、countのhashを返しました。rank 0の `kv pool idle` の行はどれも合っていました：約束されたpageは0で、空きのpageとprompt cacheのpageでpoolの全部です。
- **同時の要求。** 1本と4本、TP=3では8本も、TP=2で20本、TP=3で52本の返答が同じ要求の単独の返答と同じでした（[同時の要求](validation.ja.md#同時の要求)）。表のwarm turnから8つのpromptまでの行は同時の要求の起動のもので（[方法](benchmarks.ja.md#同時の要求)）、比べる前の版の値はありません。
- **熱。** TP=3でも熱で待ったpromptはありません（3.8.0：1,035,295 tokenのpromptが15回で30秒）。TP=2では待ったpromptはありません。熱の見張りの止める温度に届いたzoneはありません。
- **tool。** このリポジトリの中継である[tool引数ゲート](../SETUP.ja.md#6-tool引数ゲート任意)越しでは、部分点や失敗のシナリオが3.8.0と同じでした。ゲートなしでは、エンジンはTP=2で93、TP=3で91で、Safety Gateは合格でした。両TPで増えた失敗はTC-43の一つで、空の `query` で `web_search` を呼んだものです。ゲート越しでは、queryなしでは呼ばずに断る返答になります。
- **XSFP4の既知の振る舞い。** [3.3.0](measurements.ja.md#330)のものと同じです：TP=3ではstop文字列の要求が上限まで走り、promptのscoreと構造化出力の検査のscoreもgrammarも無い要求は自分のhashを持ちます。

## 3.8.0

**3.8.0**（2026-10-26、エンジン `84e0d560`、上流1.1.5、image `glm53-tf3:3.8.0`）。エンジンはこの系列のcommitを持たない上流1.1.5そのもので、TP=3ではKV cacheがpageにあります。リリースのimageを、rankのファイルに、起動が名指す時のほかは `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて、それ自身の `serve.sh` と `cluster.sh` で起動しました：TP=2で6回、TP=3で5回。各TPで全検査の起動、2回目の起動、`PARALLEL=` を空にした起動、BF16との比べのためにNVIDIAのNVFP4とFP4-Localで1回ずつ（[checkpoint](../README.ja.md#checkpoint)）、さらにTP=2で `PARALLEL=` を空にした245,760 tokenの窓。それらを回したどの起動も、3.3.0のXSFP4のdecode検査のhashと、`bench --kinds edit` の同じ返答を190 roundで返しました。NLLは3.3.0と同じで、199,307・499,254・1,035,295 tokenのpromptの合言葉はすべて見つかりました。止まった起動はありません。

| 3.8.0 | TP=2 | TP=3 |
|---|---|---|
| 起動（秒）：全検査の起動 / 2回目の起動 | 376 / 323 | 316 / 270 |
| decode検査 count / prose / code（tok/s） | 48.99 / 34.11 / 45.05 | 63.94 / 44.98 / 54.94 |
| MTPの受理長、同じタスク | 3.276 / 1.796 / 2.971 | 3.362 / 1.947 / 2.823 |
| `bench --kinds decode`（tok/s、中央値） | 53.89 | 65.33 |
| `bench --kinds edit`（tok/s、中央値） | 82.60 | 105.07 |
| 38,960 tokenのprefill（tok/s、3回の中央値） | 1,417.5 | 1,703.5 |
| 199,307 tokenのprompt（秒） | 151.5 | 128.7 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken（秒） | 429.2 / — | 376.3 / 1,013.6 |
| 約93,000 tokenのpromptを3秒で切った後、次の要求が答えるまで（秒）、切らないpromptの最初のtokenとの比べ | 0.32 対 68.5 | 0.94 対 57.1 |
| teacher-forced NLL、ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| tool-eval-bench 2.8.0、ゲート越し / ゲートなし | 95 / 93 | 92 / 91 |
| 化けた文字のある日本語と韓国語の答え、temperature 0 / sampled | 0 / 0 | 0 / 0 |
| 6,000 tokenのpromptの後の最大1,024 tokenの40の返答（秒、rank 0のホストの最も熱いzone） | 1,248.8、75.9 °C | 989.8、86.0 °C |
| 起動の中の最も熱いzone、rankごと（°C） | 87.9 / 88.9 | 92.4 / 89.9 / 87.9 |
| 最低の `MemAvailable`、rankごと（GiB） | 11 / 12 | 21 / 23 / 28 |

- **[3.6.0](#360)との差。** tokenは同じです。3.6.0に比べ、decode・編集の返答・prefillの速さはTP=2で+0.5〜+0.7%、TP=3で−0.5〜+0.9%、長いpromptの時間はTP=2で−1.2〜−0.9%、TP=3で−1.3〜+0.9%でした（1,035,295 tokenのpromptは熱の待ちを除いて984秒、3.6.0は994秒）。TP=2のrank 0のloadの行は3.6.0と同じmodelの大きさ（524,288 tokenの窓で96.97 GiB）で、5.5 GiBのprompt cacheでした。TP=3は次の項です。
- **TP=3のKV pages。** rank 0のloadの行は、エンジン自身のsequenceとstreamに、512行のpageを2,049（12.76 GiB、1,048,576 tokenの窓で1本分）と、63.60 GiBのmodelを示します。3.6.0の76.36より12.76 GiB小さく、modelの数にエンジン自身のsequenceが入らなくなった分です。`PARALLEL=` を空にすると、エンジンは同じpageの上に8本のstreamを取り、countのhashを返しました。どの起動の後も、rank 0の `kv pool idle` の行はどれも全pageが空いていました。
- **熱。** TP=3では1,035,295 tokenのpromptだけが熱で待ち、2秒の待ちを15回、計30秒でした（3.6.0：5回で10秒）。TP=2では待ったpromptはありません。熱の見張りの止める温度に届いたzoneはありません。
- **tool。** このリポジトリの中継である[tool引数ゲート](../SETUP.ja.md#6-tool引数ゲート任意)越しでは、点数と、部分点や失敗のシナリオが3.6.0と同じでした。3.8.0からはエンジンが呼び方の `clear_thinking` をchat templateへ渡し（上流の `c767bd766`）、最後のuserの文より前のturnの推論を外します。ゲートなしでは、エンジンはTP=2で93、TP=3で91で、Safety Gateは合格でした。両TPで増えた失敗はTC-43の一つで、空の `query` で `web_search` を呼んだものです。ゲート越しでは、queryなしでは呼ばずに断る返答になります。
- **XSFP4の既知の振る舞い。** [3.3.0](#330)のものと同じです：TP=3ではstop文字列の要求が上限まで走り、promptのscoreと構造化出力の検査のscoreもgrammarも無い要求は自分のhashを持ちます。

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

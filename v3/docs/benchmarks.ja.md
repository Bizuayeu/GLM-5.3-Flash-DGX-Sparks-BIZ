# ベンチマークの方法（3.x）

[English](benchmarks.md) · [3.x系の概要](../README.ja.md) · [検証](validation.ja.md)

3.x系の値をどう取ったか：[リリースでの測定値](../README.ja.md#リリースでの測定値)の値と、[検証](validation.ja.md)の基準値です。値はその二つの頁にあり、この頁はその条件と手順を書きます。速さ・長い入力・decode検査・NLLの値は、この系列の `glm53_tf` の道具で2.x系と同じ要求を使って取ったので、値を再現したり比べたりできます。ここに道具の無い検査は、繰り返せるだけ詳しく書きます。

## ホストと条件

- **ホスト。** 参照機のMSI EdgeXpert（GB10）。TP=2は直結の対、TP=3はリングの3台で、GPUには他に何も載せていません（2.x系のcontainerは停止）。
- **GPUクロック**は[ホストのツール](../../host/README.ja.md)の起動時のunitで2,200 MHzを上限にしました（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）。
- **エンジンとimage。** リリースのimage、エンジン `3d3d61d5` を `serve.sh` の既定で：1本のstream、TP=2で245,760 token・TP=3で1,048,576 tokenの窓、92 °C／88 °Cの熱の待ちと93 °Cへの見込み。1回の起動は空の `PARALLEL=`（エンジン自身によるstreamの選択）で走らせ、そのことを書いています。
- **core。** 全containerを効率coreの0-4と10-14に。`create_container.sh` が作るとおりです。
- **見張り。** メモリの見張りを全ホストで、熱の見張りを起動の全ホストで動かしました。
- **クライアント。** 要求はすべてrank 0からloopbackのエンジンへ一つずつ、検査が別に言わない限りtemperature 0、推論のeffortはlowです。道具はcontainerの中でcheckoutの `v3/` から動かしました。

## 長い要求の合間の冷却

各起動と測定のまとまりの前ごとに冷却gateを回しました。rank 0のホストのACPIの最も熱いzoneが55.8 °C以下になるか、936秒たつまで待ちます。[`host/cool-gate`](../../host/README.ja.md#長い運転の間)の規則で、2.x系がそのホストで較正した値です。他のrankのホストは記録し、待ちませんでした：それらのエンジンは待つ間も2本のCPUのthreadを空回りさせ続け（[効率coreにする理由](../README.ja.md#配信の既定)）、全coreではrank 1のホストは約70 °Cで待機し、2.x系が使ったどの帯よりも上でした。

## decode検査

[検証](validation.ja.md#decode検査)のとおりです：各タスク（count、prose、code）を3回、約2,048 tokenの固定promptの後にgreedyで512 token。道具は速さ、MTPの受理長（各応答の `speculative` blockから1＋accepted／rounds）、各completionの文章のhashとエンジンの `token_sha256` を出します。最初の後のサンプルはprompt cacheからpromptを再開することがあり（`cached`）、同じtokenを出します。各TPで2回起動し、それぞれを1回目と比べます。

## prefillとdecodeの速さ

時間を測る前に、約3,000 tokenのprefillを1回（`bench --kinds prefill --runs 1 --lines 250`）。

**prefill。** 一つのuser message：`nonce <新しいUUID>` の1行、固定の3,200行（`measurement line <i> of the fixed prefill prompt.`）、`Reply ok.`。chat templateを含めて38,960 tokenです。`max_tokens` 1、temperature 0、effort low、`clear_thinking`。速さは、promptのtoken数をクライアントでの要求の経過時間で割ったものです。エンジンには保持promptを消すendpointが無いので、先頭の新しいnonceでどれとも一致しないようにしました。どの行も `cached` は0でした。同じ長さの数えないpromptを1本流した後、続けて流した3本の中央値です。

**短いpromptの後のdecode。** `Write the numbers from 1 to 1000, one per line, and nothing else.` をstreamで、最大512 token、temperature 0、effort low。速さは、最初の後のcompletionのtoken数を、最初にstreamで届いたtokenの後の時間で割ったもので、3回の中央値です。どの行も上限で止まる（`finish_reason` `length`）ので、測るtokenはどれも数えている文そのものです。各行には応答の `rounds`・`tokens_per_round`・`token_sha256` が足されます。

**編集のdecode（`--kinds edit`）。** 約6,000文字の決まったPythonのmoduleをcode blockに入れたものと、名前を挙げた1行の編集3つで、`Return the whole module with only these edits, in one code block:` と頼みます。毎回同じで、streamで、temperature 0、effort low、最大4,096 tokenで、返事は自分で終わります。速さは上のdecodeと同じ取り方です。その `token_sha256` はどの回でも、2回目の起動でも同じでなければなりません。

`python -m glm53_tf bench` がprefillとdecodeをそれぞれ3回ずつ、`--kinds edit --runs 3` が編集を走らせます。`--out` は要求ごとに1行を足し、行には応答の `prefill_seconds`・`time_to_first_token`・`cached` のtoken数と、要求の開始と終了のepochが入ります。

## 長い入力

長いpromptはどれも番号付きの行の台帳で（`Ledger <i>: the river barge delivered sacks of barley to the northern granary at dusk.`）、system messageは `You are a careful archivist. Read the ledger.`、temperature 0、effort lowで、行数はエンジンの `/tokenize` で目標に合わせます。各行の `cached` は、promptがprompt cacheから再開したtoken数を示します。受け入れでは、TP=3で3本続けたものも含め、どの長いpromptも全体を読みました（`cached` 0）。

- **199,652 tokenに合言葉一つ**、真ん中に。streamなし、最大512 token。応答に合言葉があれば正答です。両TPで。
- **499,622 tokenと1,036,859 tokenに合言葉三つ**（先頭から20分の1、真ん中、末尾から20分の1）、TP=3。streamで最大256 token、最初にstreamで届いたtokenまでをクライアントが測ります。応答が三つとも挙げれば正答です。

promptの熱の待ちは、要求の開始と終了の間のrank 0の `heat_wait_s` の行から読みます。

## teacher-forced NLL

NLL採点セットと採点は[検証](validation.ja.md#teacher-forced-nll)のとおりで、checkpoint自身のtokenizerを使い、各本文を `prompt_logprobs` で2回採点します。

## draftとserialの一致、promptのscore、構造化出力と停止

- **draftした応答とserialの一致**：prose、code、countのpromptで最大256 token、`"draft": false` の有りと無しを、文章全体で比べます。同じ実行の中で、1×1のPNGの画像のpartを持つ要求を送り、400で断られます。
- **promptのscoreと構造化出力**：[検証](validation.ja.md#promptのscoreと構造化出力)が挙げる検査を、要求を一つずつ送って。
- **応答を止める**：思考を切って。1から1,000までの数を1行ずつ書かせる要求を、最大4,000 token、streamで送り、5秒後にクライアントが閉じます。`live` blockに接続が無くなるまで15秒の間、毎秒 `/health` を読み、その後短い要求の時間を測ります。同じ要求にstop文字列 `"\n300\n"` を付けて、streamなしで。6,000行（約93,000 token）の台帳をstreamで送って3秒後に閉じ、直後に短い要求の時間を測り、同じ台帳をもう一度全部流して最初のtokenまでの時間を測ります。

## ゲート越しのtool

1.x系と同じ呼び方のtool-eval-benchをtool引数ゲート越しに（[検証](validation.ja.md#tool引数ゲート越しのtool)）、各TPで1回。69のシナリオは冷却なしで続けて走ります。

## 返答の長い連続

40の要求を間を置かずに続けて、streamなしで。どれも一つのuser messageで：`nonce <新しいUUID>` の1行、生成した200の関数（`def helper_<i>(values, scale=<i mod 13 + 1>):` で `[v * scale + <i> for v in values if v % <i mod 5 + 2>]` を返す）のcode block（chat templateを含めて約6,000 token）、`Review this module in detail: for each group of helpers, what it does, its bugs and how to fix them.`。最大1,024 token、temperature 0、effort low、`clear_thinking`。coding agentのturn、つまり毎回新しい文章を読んでから書くことを表すもので、各TPでtool-evalの後に走らせます。

## メモリと温度

各ホストの `MemAvailable` の最低値はメモリの見張りのlog（2秒ごと）から、温度はホストの記録（2秒ごと、全てのACPIのzoneとGPU。熱の見張りもその最も熱いzoneを読みます）から、GPUの熱によるslowdownはドライバーの累積のcounter（`nvidia-smi` の `clocks_event_reasons_counters`）を毎秒取って、熱の待ちはrank 0の `heat_wait_s` の行から読みます。

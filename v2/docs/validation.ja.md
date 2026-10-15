# 検証（2.x）

[English](validation.md) · [2.x系の概要](../README.ja.md) · [セットアップ手順書](../SETUP.ja.md)

2.x系の起動を何で受け入れるかを、回す順に基準値と一緒に並べます。基準値は2026-10-02と10-03に参照機で、2.0.0より前のエンジンの版で測りました。2.4.0から任意で使える公開したAXLの重みは、2.4.0の受け入れで取った自身の基準値を持ち、固定の重みのものの隣に載せます。これらと比べてどのimageを受け入れたかはREADMEの[状態](../README.ja.md#要約)にあります。違う結果は日常の利用の前に説明すべき所見で、基準を置き換える値ではありません。

道具はrank 0でcheckoutの `v2/` から、その仮想環境で（[手順書 §2](../SETUP.ja.md#2-checkoutとcheckpoint)）、loopbackのエンジン（`http://127.0.0.1:8095`、rankのファイルで変えなければモデル `glm-tf`）に当てます。長い要求の間はホストを冷まし（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）、メモリの見張りを動かしたままにします。

## decode検査

約2,048 tokenの固定prompt（`PROMPT_TOKENS`。正確な数は各行の`prompt_tokens`）の後にgreedyで512 token、タスクごとに3回。1.x系と同じです（[切替の後のdecode検査](../../v1/docs/launch-safety.ja.md#切替の後のdecode検査)）。

```sh
for k in count prose code; do
  BASE=http://127.0.0.1:8095 MODEL=glm-tf PROMPT_KIND=$k SAMPLES=3 \
  TOKENS_OUT=../records/<run>/tokens-$k.json python -m glm53_tf decode-check
done
```

各サンプルの前に `TF_GLM_CACHE_ENTRIES`（既定8、エンジンの既定と同じ）本の短い別の要求を送るので、どのサンプルもpromptを最初からprefillします（各行の `cached` が0）。サーバーを別の値で起動した場合は同じ値を渡します。summaryには速さ、MTPの受理長（各応答の `tensorfold` ブロックから1＋accepted／rounds）、`distinct_completions` が出ます。`TOKENS_OUT` には各サンプルの文章とtoken idが残り、hashの違う2回の起動は `python -m glm53_tf decode-divergence A.json B.json` で最初に分かれたtokenを比べます。

**合格の条件**：各タスクが起動の中で一つのcompletion（`distinct_completions` が1）で、その `completion_sha256` がそのTPの基準と同じこと。

| タスク | TP=2 `completion_sha256` | TP=2 `token_ids_sha256` | TP=3 `completion_sha256` | TP=3 `token_ids_sha256` |
|---|---|---|---|---|
| count | `aa5a33f7dfae78e6` | `77fcc6e0c2a8540c` | `67058e32104fa3d1` | `3e398a9c0dfc5cd9` |
| prose | `e33450686f6b5624` | `3ee287174a7b9ae3` | `8901c751b210f13c` | `0a3bb372ba424ae0` |
| code | `0ffecb8187fd7084` | `f579ca05b8be8490` | `43edfcefb4bafdb8` | `91f20cec01a74182` |

token idは、TP=2ではエンジンの8つの版、TP=3では10回の起動を通じて、1本・2本のrail、3通りのprefillの交換、TP=2のNCCLの4 channel、画像入力の有効（`VISION=1`）のどれでも変わりませんでした。2.1.0から、この検査は推論の終わりと本文の始まりを1つのdeltaで運ぶときに両方の欄を取ります。以前の版は片方だけを取っていたので、countとcodeは短い文字列を読んでいました（2.0.xのhash、TP=2の `93951874…`・`389d8fb9…`、TP=3の `be0f5d34…`・`ac0a26c6…` は同じtokenです）。TP=2とTP=3は設計上互いに違います（rank間の和の分け方が違う）。受理長はTP=2 3.961／2.098／3.180、TP=3 4.056／2.222／3.234です（copy drafts、`MISS_MOST` 5。以前のリリースの値は[リリースでの測定値](../README.ja.md#リリースでの測定値)にあります）。`bench --kinds edit` は両TPで同じ返答を出します（sha256 `ecd7a283a48a0cc4`、copyのround 240。`MISS_MOST` 5ではTP=2で237）。返答が違えば受け入れを止めます。

公開したAXLの重みではtoken idはAXL自身のもので、TP=2では2回の起動で同じでした。基準はtoken idだけなので、**合格の条件**は、各タスクが起動の中で一つのcompletionで、その `token_ids_sha256` がそのTPの基準と同じことです。

| タスク | AXL TP=2 `token_ids_sha256` | AXL TP=3 `token_ids_sha256` |
|---|---|---|
| count | `a4418db6d53bd4f6` | `6b8c2eba7449a4bc` |
| prose | `500974abd51989ad` | `c369be6667b45ab1` |
| code | `053a9893ad68b75d` | `06db4fba31b86378` |

受理長はTP=2 3.813／2.004／2.893、TP=3 3.631／2.060／2.994（2.4.0）。`bench --kinds edit` は両TPで固定の重みと同じ返答（`ecd7a283a48a0cc4`）を出します。

## 画像入力

画像入力を有効にして（全rankで `VISION=1`）：画像1枚、prompt 7,966 tokenの4:3の画像、順番のある2枚、単色、toolの結果の中の画像、続いて文字の質問とtoolの往復。2.5.0からは、引用の `<|image|>` を本物の画像の隣に含む会話と、引用の無い同じ要求も回します（2.4.0は引用のある方を400で断った）。**合格の条件**：どれにも正しく答え、動画のpartを400で拒むこと。

## draftした応答とserialの一致

同じpromptをdraftありとなし（要求の本文に `"draft": false` で1 roundに1 token）で流し、同じ文章になること。prose・code・countのpromptで256 token、TP=2とTP=3の両方で確かめました。文章は全体で比べます。draftありのstreamでは1つのdeltaに `reasoning_content` と `content` の両方が乗ることがあり、deltaごとに片方しか読まないと、無い違いが出ます。

## teacher-forced NLL

[`config/nll_set.json`](../config/nll_set.json) のNLL採点セット（1.x系のもののbyte単位の写し）：4領域（日本語・英語・コード・数学）に各4本、領域ごとに5,851〜6,830 token。tokenizerはcheckpoint自身のものを使います。

```sh
python -m glm53_tf score-nll --url http://127.0.0.1:8095 \
  --tokenizer ~/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/423acf37583782c51c142d145aef733d72943d93/tokenizer.json \
  --out ../records/<run>/nll.json
```

実行する環境に `tokenizers` packageが要ります（Hugging Faceのlockには入っていません）。各本文を2回採点し、全要求が答え、各本文の2回が一致すれば（参照機ではargmaxの一致1.0、動き0）passです。

| 領域（位置数） | TP=2 | TP=3 | AXL TP=2 | AXL TP=3 | 1.x TP=2配布既定（1.26.0） |
|---|---|---|---|---|---|
| 日本語（6,826） | 2.5474 | 2.5313 | 2.5556 | 2.5590 | 2.5412 |
| 英語（6,678） | 2.9257 | 2.9001 | 2.9438 | 2.9471 | 2.9079 |
| コード（5,941） | 1.3184 | 1.3101 | 1.3334 | 1.3357 | 1.3145 |
| 数学（5,847） | 0.6250 | 0.6237 | 0.6474 | 0.6439 | 0.6285 |

**合格の条件**：passで、各領域がそのTPと重みの基準と同じこと。TP=3の値はprefillの交換が違う2回の起動で同一だったので、値が違えばビットが違います。

## prefillとdecodeの速さ

38,960 tokenのpromptを、先頭に毎回新しいnonceを入れて3回（中央値）、続いて短い固定promptの後に最大512 token（[ベンチマークの方法](benchmarks.ja.md#prefillとdecodeの速さ)）。基準：TP=2はprefill 1,217.2 tok/s、decode 35.61 tok/s（2本のrail、`split` の交換より前の版）。TP=3は `split` で2回の起動のprefill 1,673.1と1,667.9 tok/s、decode 53.03と52.93 tok/s。このdecodeの基準と、2.5.0より前の `bench --kinds decode` の値はどれも、modelが自分の終わりの後に作ったものを測る2.5.0より前の要求で取ったもので、2.5.0の値とは比べられません。2.5.0の要求ではどの行も上限で止まります（`finish_reason` `length`）。その基準は2.5.0の受け入れの値で、TP=2は固定の重み42.63 tok/s、AXL 57.09（両方で同じ返答）、TP=3は56.73と76.55で、TP=3では2つの返答が違います（[リリースでの測定値](../README.ja.md#リリースでの測定値)）。1本のrailではTP=3のprefillが13%遅く、decodeは変わりませんでした。基準値は各promptの前にホストを冷まして取りました。

containerが最初に受ける、chunkが多いpromptは長くかかります。2つ目以降のchunkと最後の短いchunkが使うkernelをTritonがその場でcompileし、最初のchunkの後に約1秒、GPUがほぼ止まるためです。2.2.0から2.9.2のリリースの窓では、新しいcontainerで、2本のうち1本目が2本目よりTP=2で0.4〜1.8秒、TP=3で0.8〜1.6秒長くかかりました（2本目そのものが通しで遅かった2回の起動を除く。後述）。2026-10-16のTP=2では、そのkernelをcompile済みのcontainerで3本がそれぞれ29.03〜29.04秒でした。そのkernelを脇へ移し、短いpromptを先に流さないと、1本目が34.12秒でrank 0はその途中で25個のkernelをcompileし、2本目は29.29秒で終わりに3個、3本目は熱の待ち18.0秒を除いて29.03秒でした。rankファイルの例のように `TRITON_CACHE_DIR` を `/work` に置くと、同じimageから作り直したcontainerでもkernelが残ります（起動でも、28.95〜29.02秒の4本のpromptでもcompileは0。うち1本は熱の待ち8.0秒を除く）。2.9.3からの `bench` は、同じ長さの数えないpromptを先に1本流します（cacheが空のとき、その1本が34.52秒、数える3本が29.00〜29.04秒）。これとは別に、promptが最初から最後まで最大7.5%遅く走ったことがあります。GPUは同じだけ働き、クロックも同じで、2.1.1の測定と、上の2回の起動（2.2.0のTP=2、2.9.0のTP=3）でありました。原因は分かっていません。何本かの中央値で比べます。この数字は `python -m glm53_tf bench` で取ります。条件は[ベンチマークの方法](benchmarks.ja.md)にあります。

## 長い入力

199,652 tokenの台帳の行の真ん中に合言葉一つ、499,622 tokenと1,036,859 tokenに合言葉三つ（先頭・中央・末尾）。TP=3の基準：199,652で145.6秒・正答、499,622で454.1秒・3/3、1,036,859で3/3・最初のtokenまで1,364秒（`split` の交換とindexerの改善より前の版。200Kと500Kの実測に当てた見積もりでは、それらを測った版は約1,112秒）。この間の最も熱いホストは89.6〜90.1 ℃で、[熱の見張り](../../host/README.ja.md#長い運転の間)の94 ℃には届きませんでした。1Mのpromptは、TP=2の窓には入りません。

## tool引数ゲート越しのtool

1.x系の呼び方（69シナリオ、seed 42、temperature 0、parallel 1、effort low、`clear_thinking`、出力4,096 token、timeout 600秒）のtool-eval-benchを[ゲート](../SETUP.ja.md#7-tool引数ゲート任意)越しに：

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

基準：TP=2とTP=3とも91/100、Safety Gate通過（TC-43はゲート越しで通る）。構造化出力のTC-64〜69は全部通り、これにはimageのxgrammarが要ります。TP=2の失敗はTC-21とTC-61、TP=3はTC-61だけ。各1回なので、1〜2点は1回の試行で動く範囲です。これは開発ビルドでの値で、基準はこちらです。各リリースでの値はREADMEにあります（[リリースでの測定値](../README.ja.md#リリースでの測定値)）。

## 応答を止める

リリースのエンジンは、clientが切断したときやstop文字列が出たときに、全rankで1 round以内にdecodeを止めます（上流のpull request #301）。それより前は、1系列のdecodeがtokenの上限まで続いていました。TP=2とTP=3の両方で、次を満たせば合格です：大きな `max_tokens` のstreamの要求をclientが数秒で切るとdecodeが止まる（`/health` の `rounds` が増えなくなり、decodeを続けるrankが無い）、応答が届く `stop` 文字列を指定した要求がそこで終わり `finish_reason` が `stop`、そのどちらの直後に送った短い要求もすぐに始まる。

## メモリと温度

メモリの見張りのlog（`~/glm53-tf/logs/hostwatch-<label>.log`）に、実行中の各ホストの最低の `MemAvailable` が残ります。基準はTP=3の1Mの要求の最中でrank 0・1が29〜31 GiB、rank 2が35 GiB、TP=2はextensionを先にbuildしてrank 0で約9 GiBです。

熱の待ちは、全rankが `[tensorfold] heat:` の行を出します（待ちの始まりと終わりに1行ずつ、続く間は1分に1行、全rankで同じ）。応答の `tensorfold` ブロックに `heat_wait_s` が載ります。長いpromptが、[熱の見張り](../../host/README.ja.md#長い運転の間)に止められずに（94 ℃以上が2回続かずに）終われば受け入れます。1M tokenのpromptの終わり近くでは、chunkの合間の確認の後にchunk一つで約7 ℃上がるので、待ちは、続けて流した直前のchunkの上がり幅で1 chunk先も見込みます。chunkは見込みを越えることがあり（ほとんど上がらなかったchunkの次のchunkが2.4.0の受け入れで1回、待ちの2つ後のchunkが2.9.2の1M tokenの確かめで9回、最高93.7 ℃）、そのときは次の確認で待ちに入ります（[リリースでの測定値](../README.ja.md#リリースでの測定値)、[決定の記録](decisions.ja.md#熱)）。

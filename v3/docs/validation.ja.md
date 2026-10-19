# 検証（3.x）

[English](validation.md) · [3.x系の概要](../README.ja.md) · [配備の手順書](../SETUP.ja.md) · [ベンチマークの方法](benchmarks.ja.md)

3.x系の起動を何で受け入れるかを、回す順に基準値と一緒に並べます。基準値はネイティブエンジン自身のもので、2026-10-19〜20の3.1.0の受け入れで、参照機で `1a8f1efd`（上流1.1.1とこの系列の二つのcommit）からbuildしたエンジン、`serve.sh` の既定、全containerを効率coreにして測りました。TP=3はBF16のlinearを3.0.0と同じglueのkernel（`TF_GLM_MM=0`）で回し、decode checkのhash、editの返答、NLLが3.0.0と同じでした。TP=2は上流のtiledのkernelで回り、新しい値を出しました（[配信の既定](../README.ja.md#配信の既定)）。2.x系の基準は当てはまりません：ネイティブエンジンのkernelとBF16のKV cacheは別のtokenを出すので、二つの系列はteacher-forced NLLで比べ、2.x系の値はここでは参考としてだけ載せます。これらと比べてどのimageを受け入れたかはREADMEの[状況](../README.ja.md#要約)にあります。違う結果は日常の利用の前に説明すべき所見で、基準を置き換える値ではありません。

道具はrank 0でcheckoutの `v3/` から、その仮想環境で（[手順書 §2](../SETUP.ja.md#2-checkoutとcheckpoint)）、またはPythonと `tokenizers` を持つcontainerの中で、loopbackのエンジン（`http://127.0.0.1:8095`、rankのファイルで変えなければモデル `glm-tf`）に当てます。長い要求の間はホストを冷まし（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）、メモリの見張りと[熱の見張り](../../host/README.ja.md#長い運転の間)を動かしたままにします。

## decode検査

約2,048 tokenの固定promptの後にgreedyで512 token、タスクごとに3回。1.x系・2.x系と同じです：

```sh
for k in count prose code; do
  BASE=http://127.0.0.1:8095 MODEL=glm-tf PROMPT_KIND=$k SAMPLES=3 \
  TOKENS_OUT=../records/<run>/tokens-$k.json python -m glm53_tf decode-check
done
```

エンジンはtoken idを返しません：各行には、completionの文章のhashと、エンジンによる応答のtoken idのhashである `token_sha256`（idを10進でコンマ区切りにしたもので、2.x系の `token_ids_sha256` とは比べられません）が出ます。エンジンはどの要求も消せないGiB単位の大きさのcacheにpromptを保つので、最初の後のサンプルはpromptを再開することがあります（行の `cached`、summaryの `resumed`）。再開したpromptは同じtokenを出します。`TOKENS_OUT` には各サンプルの文章が残り、hashの違う2回の起動は `python -m glm53_tf decode-divergence A.json B.json` で最初に分かれた文字を比べます。

**合格の条件**：各タスクが起動の中で一つのcompletion（`distinct_completions` が1）で、そのhashがそのTPの基準と同じこと：

| タスク | TP=2 `completion_sha256` | TP=2 `token_sha256` | TP=3 `completion_sha256` | TP=3 `token_sha256` |
|---|---|---|---|---|
| count | `96385e4d65278eac` | `6faafd98ec90322f` | `1cf31fa39a420336` | `6835af3a11c0b3e6` |
| prose | `464e122fc0c4a71e` | `b82116bdbaa49958` | `72c9b1e2cf183215` | `d22f429e247f196f` |
| code | `3b7e3ee097146c50` | `ddd42119a8be799e` | `59e2a180d1b9ccc7` | `3dd2e6dd1afd23cf` |

hashは、各TPの2回の起動と、`PARALLEL=` を空にしたTP=2の起動（count。エンジンは2本のstreamを取りました）で保たれました。TP=3のhashは3.0.0のものです。全coreでも、この系の2つのcommitを除いた上流1.1.1がTP=2で同じtoken idを出し、リリースのimageは各TPで1回の起動で、そのTPのhashと編集の返答を出しました。TP=2とTP=3は設計上互いに違います（rankの間での和の分け方が違い、TP=2のlinearは別のkernelで回るため）。3.0.0のTP=2のhash（count `bbf97d42e5d45bd3`、prose `da21339524bf4382`、code `bc00b6fc275d9595`）は、そのエンジンのkernelのものです。受理長：TP=2で3.066／1.882／2.621、TP=3で3.368／1.787／2.839。`bench --kinds edit` は両TPで同じ返答を、190 roundで `token_sha256` `c419bce559d86b66` で返します（3.0.0のエンジンは同じ返答に363 round）。違う返答は受け入れを止めます。

## draftした応答とserialの一致

同じpromptをdraftありとなし（要求の本文に `"draft": false` で1 roundに1 token）で流し、同じ文章になること：prose・code・countのpromptで最大256 token、temperature 0、effort low、両TPで、文章は全体（推論と答え）で比べます。`bench --kinds edit` は、どの回でも、2回目の起動でも同じ返答を出します。

## 画像入力の拒否

`serve.sh` はエンジンを `--vision` 無しで起動するので、画像を読みません。**合格の条件**：画像のpartを含む要求を400で断ること。

## teacher-forced NLL

[`config/nll_set.json`](../config/nll_set.json) のNLL採点セット（1.x系・2.x系のもののbyte単位の写し）：4領域（日本語・英語・コード・数学）に各4本、領域ごとに5,851〜6,830 token。`/v1/completions` の `prompt_logprobs` で採点します。tokenizerはcheckpoint自身のものを使います：

```sh
python -m glm53_tf score-nll --url http://127.0.0.1:8095 \
  --tokenizer ~/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/423acf37583782c51c142d145aef733d72943d93/tokenizer.json \
  --out ../records/<run>/nll.json
```

実行する環境に `tokenizers` packageが要ります。各本文を2回採点し、全要求が答え、各本文の2回が一致すればpassです。

| 領域（位置数） | TP=2 | TP=3 | 2.x TP=2（参考） | 2.x TP=3（参考） |
|---|---|---|---|---|
| 日本語（6,826） | 2.5412 | 2.5246 | 2.5474 | 2.5313 |
| 英語（6,678） | 2.9293 | 2.9206 | 2.9257 | 2.9001 |
| コード（5,941） | 1.3145 | 1.3147 | 1.3184 | 1.3101 |
| 数学（5,847） | 0.6261 | 0.6241 | 0.6250 | 0.6237 |

**合格の条件**：passで、各領域がそのTPの基準と同じこと。両TPで、どの本文の2回の採点も完全に一致しました（最大の動きは0.0）。TP=3の値は本文ごとに3.0.0と同じです。TP=2はtiledのkernelで3.0.0の値（2.5293・2.9109・1.3138・0.6272）から最大0.0184動き、2.x系の値との差は0.007以内です。

## promptのscoreと構造化出力

これらは1.1.1からGLMのCUDAのエンジンで上流自身のものです（[API](../README.ja.md#api)）。**合格の条件**（両TPで）：

- **`prompt_logprobs`**：最初の後のpromptのどのtokenにも、自身の順位とlog確率、1から順位をつけた上位の候補を持つ行がある。同じ要求をもう一度、また `"draft": false` で送っても同じ行になる。5,000 tokenのpromptはどのtokenにも行があり、その最初の2,048 tokenのchunkの行は、同じpromptを3,001 tokenで切ったものの行と同じ。scoreを求めない要求はtokenのhashを保つ。
- **構造化出力**：`json_schema` の応答が、思考を切っても入れても、schemaのkeyと型でparseできる。素のgreedyの応答がすでに満たすschemaでは、grammarの下でも、`"draft": false` でも同じ文章になる。seedを付けたtemperature 0.7の同じ要求は、同じ有効な文章を2回出す。`tool_choice` の `required` は、引数がparseできる呼び出しをGLMのtoolのmarkupで出す。grammarの無い要求はtokenのhashを保つ。

## prefillとdecodeの速さ

38,960 tokenのpromptを、先頭に毎回新しいnonceを入れて3回（中央値）、同じ長さの数えないpromptを1本流した後に。続いて短い固定promptの後に最大512 tokenを3回（[ベンチマークの方法](benchmarks.ja.md#prefillとdecodeの速さ)）：

```sh
python -m glm53_tf bench --out ../records/<run>/bench.jsonl
```

基準値：TP=2でprefill 1,415.7 tok/s・decode 43.80 tok/s、TP=3で1,507.9と55.05。decodeの行はどれも上限で止まり（`finish_reason` `length`）、prefillの行の `cached` はどれも0です。

## 長い入力

199,652 tokenの台帳の行の真ん中に合言葉一つ、499,622 tokenと1,036,859 tokenに合言葉三つ（先頭・中央・末尾）：

```sh
python -m glm53_tf long-input --passphrases 1 --tokens 199652
python -m glm53_tf long-input --passphrases 3 --tokens 1036859
```

目標に合わせた行数で、promptは199,307・499,254・1,035,295 tokenになりました。基準値：199,307 tokenで合言葉を、TP=2で153.4秒、TP=3で140.4秒で見つけました。TP=3では499,254 tokenで3つ中3つ、最初のtokenまで398.1秒、1,035,295 tokenで3つ中3つ、1,022.7秒でした。どれも保持したpromptから再開せず（`cached` 0）、熱で待ちませんでした。1,036,859 tokenの目標はTP=3だけのものです。TP=2の窓は245,760 tokenです。

## tool引数ゲート越しのtool

1.x系の呼び方（69シナリオ、seed 42、temperature 0、parallel 1、effort low、`clear_thinking`、出力4,096 token、timeout 600秒）のtool-eval-benchを[ゲート](../SETUP.ja.md#6-tool引数ゲート任意)越しに：

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

エンジンは `clear_thinking` をchat templateに渡しません（[制限](../README.ja.md#制限)）。呼び方は、点数を1.x系・2.x系と比べられるよう、それを残します。

基準値：TP=2で92/100、TP=3で93/100、Safety Gateは合格。TP=2はTC-21とTC-61を、TP=3はTC-61だけを落としました。各1回なので、1〜2点は1回の試行で動く範囲です。

## 応答を止める

**合格の条件**（両TPで、思考を切って）：1から1,000までの数を書かせるstreamの要求を約5秒でクライアントが切ると、15秒以内に `/health` の `live` blockに接続が残らず、直後の短い要求が10秒以内に答える。同じ要求にstop文字列 `"\n300\n"` を付けると299で終わり、`finish_reason` が `stop`。約93,000 tokenの台帳のpromptを、読んでいる途中の3秒でクライアントが切ると、直後の短い要求が、prompt全体が最初のtokenまでにかかる時間の半分未満で答える。基準値：両TPで、切ってから1.0秒で接続が消えました。切ったpromptの後、短い要求はTP=2で0.39秒、TP=3で0.25秒で答え、prompt全体の最初のtokenまでは68.4秒と62.8秒でした。

## 返答の長い連続

40の要求を続けて流します。どれも新しいnonceと約6,000 tokenのPythonのmoduleに詳しいreviewを頼むもので、それぞれ最大1,024 token、temperature 0、effort low。これが全coreでCPUのzoneを温めた負荷です（[効率coreにする理由](../README.ja.md#配信の既定)）。**合格の条件**：40本すべてが答え、熱の見張りがエンジンを止めないこと。

基準値：両TPで40本中40本、TP=2で1,536秒、TP=3で1,315秒。最も熱いzoneはTP=2でrank 0のホストの74.9 °C、TP=3で79.8 °Cでした。GPUは熱で遅くなりませんでした。全coreでは、TP=2の同じ40本が1,535秒で終わり、rank 0のホストは93.0 °Cで、熱の見張りの止める温度まで1 °Cでした（[効率coreにする理由](../README.ja.md#配信の既定)）。

## メモリと温度

メモリの見張りのlog（`<WORK>/logs/hostwatch-<label>.log`）に、実行中の各ホストの最低の `MemAvailable` が残ります。ホストの記録は2秒ごとにACPIの最も熱いzoneを示します。rank 0のlogは、prefillの熱の待ちごとの秒数を `heat_wait_s` の行に出します。応答はそれを運びません。

基準値：起動の中の最低の `MemAvailable` は、TP=2で両rankとも15 GiB、TP=3でrank 0・1・2が23・11・26 GiBでした。rank 1の11 GiBはtool-eval-benchの最中の2秒の1回の読みで、前後は24 GiBでした。起動全体の最も熱いzoneは、TP=2でrank 0のホストが81.8 °C、rank 1のホストが83.6 °C、TP=3で90.8・89.3・85.5 °Cでした。受け入れのどの要求も熱で待たず、1M tokenのpromptも含みます。

**合格の条件**：どの実行もメモリの見張りにも熱の見張り（94 °C以上の読みが2回続く）にも止められないこと。

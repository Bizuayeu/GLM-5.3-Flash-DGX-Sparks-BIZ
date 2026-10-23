# 検証（3.x）

[English](validation.md) · [3.x系の概要](../README.ja.md) · [配備の手順書](../SETUP.ja.md) · [ベンチマークの方法](benchmarks.ja.md)

3.x系の起動を何で受け入れるかを、回す順に基準値と一緒に並べます。基準値はネイティブエンジン自身のもので、参照機で `serve.sh` の既定、全containerを効率coreにして測りました。TP=2の値は2026-10-19〜20の3.1.0の受け入れで、`1a8f1efd`（上流1.1.1とこの系列の二つのcommit）からbuildしたエンジンにより、上流のtiledのBF16のlinearで決めました。2026-10-20の3.2.0の受け入れ（visionのtowerを読み込んで）と、2026-10-22の3.3.0の受け入れ（上流1.1.2の上で）も、同じdecode checkのhash、editの返答、NLL、tool-eval-benchの点を出しました。TP=3の値は3.3.0の受け入れで決めました：上流1.1.2はTP=3のrankにもtiledのkernelを開き（issue #1067）、それがTP=3に新しいdecode checkのhashとNLLを出します。3.0.0〜3.2.0はTP=3をglueのkernel（`TF_GLM_MM=0`）で回し、その値は下の各節に参考として載せます（[配信の既定](../README.ja.md#配信の既定)）。後の受け入れで速さ、メモリ、熱が違った所は、下の各節に書きます。2.x系の基準は当てはまりません：ネイティブエンジンのkernelとBF16のKV cacheは別のtokenを出すので、二つの系列はteacher-forced NLLで比べ、2.x系の値はここでは参考としてだけ載せます。これらと比べてどのimageを受け入れたかはREADMEの[状況](../README.ja.md#要約)にあります。違う結果は日常の利用の前に説明すべき所見で、基準を置き換える値ではありません。

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
| count | `96385e4d65278eac` | `6faafd98ec90322f` | `722e240c88542622` | `79e1de392b1332b6` |
| prose | `464e122fc0c4a71e` | `b82116bdbaa49958` | `62140b0b18d8ec3d` | `535792be03ba6cf5` |
| code | `3b7e3ee097146c50` | `ddd42119a8be799e` | `c2af3204be4e883b` | `395594e4d0ee4f21` |

hashは、各TPの2回の起動と、`PARALLEL=` を空にしたTP=2の起動（count。エンジンは2本のstreamを取りました）で保たれました。全coreでも、この系の2つのcommitを除いた上流1.1.1がTP=2で同じtoken idを出し、各リリースのimageは各TPで1回の起動で、そのhashと編集の返答を出しました。TP=2とTP=3は設計上互いに違います（rankの間での和の分け方が違うため）。3.0.0のTP=2のhash（count `bbf97d42e5d45bd3`、prose `da21339524bf4382`、code `bc00b6fc275d9595`）は、そのエンジンのkernelのものです。glueのkernelでの3.0.0〜3.2.0のTP=3のhashは、count `1cf31fa39a420336`、prose `72c9b1e2cf183215`、code `59e2a180d1b9ccc7` でした。`TF_GLM_MM=0` は今もそのkernelを選び、上流1.1.2でも同じhash、編集の返答、NLLを出しました。受理長：TP=2で3.066／1.882／2.621、TP=3で4.645／1.858／2.954（glueのkernelでは3.368／1.787／2.839）。`bench --kinds edit` は両TPで同じ返答を、190 roundで `token_sha256` `c419bce559d86b66` で返します（3.0.0のエンジンは同じ返答に363 round）。違う返答は受け入れを止めます。

## draftした応答とserialの一致

同じpromptをdraftありとなし（要求の本文に `"draft": false` で1 roundに1 token）で流し、同じ文章になること：prose・code・countのpromptで最大256 token、temperature 0、effort low、両TPで、文章は全体（推論と答え）で比べます。visionのtowerを読み込んだ起動では、小さなPNGを説明させる要求（最大64 token）も送り、二つの返答を同じように比べます。`bench --kinds edit` は、どの回でも、2回目の起動でも同じ返答を出します。

## 画像と動画の入力

`serve.sh` はエンジンを `--vision` 付きで起動します（既定の `VISION=1`）。検査の要求は、思考を切ったgreedyで送ります。**合格の条件**：

- **textは変わらない**：towerを読み込んだまま、decode検査と `bench --kinds edit` が、両TPで上のhashと返答を出す。
- **画像**（両TPで）：同じ絵をPNG・JPEG・WebPのdata URLで送ると答え、どれもdraftありと `"draft": false` で同じ返答になる。GIFは400で断る。絵を最初のmessageに置いた会話は、後のturnを絵の先までprompt cacheから再開し、冷えた回と同じ返答を出し、`"draft": false` でも、別の要求と同時でも同じになる。
- **動画**：TP=2では、エンジンのcommitの上流の `tools/zig/video_served.py` が、その13本のclip（`tools/zig/glm_video_fixtures.py` がPyAV 19.0.1で作る）で、固定したcheckpointのprocessor（transformers 5.19.0）に照らして通る（rankのファイルに `REASONING_EFFORT=`：道具はchat templateを既定のeffortで組みます）：各clipのpromptのidがprocessorのものと同じ。後のturnが動画の先まで再開し、同じtextの下の別の動画はその前のtextだけを再開する。draftありが `"draft": false` と同じ。4本同時がそれぞれの単独と同じ。動画と画像を1つの要求で答える。形の崩れた8種類の要求を理由つきの400で断る。TP=3では、H.264のMP4とVP9のWebMが答え、どちらもdraftありと `"draft": false` で同じ返答になる。

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
| 日本語（6,826） | 2.5412 | 2.5285 | 2.5474 | 2.5313 |
| 英語（6,678） | 2.9293 | 2.9129 | 2.9257 | 2.9001 |
| コード（5,941） | 1.3145 | 1.3158 | 1.3184 | 1.3101 |
| 数学（5,847） | 0.6261 | 0.6262 | 0.6250 | 0.6237 |

**合格の条件**：passで、各領域がそのTPの基準と同じこと。両TPで、どの本文の2回の採点も完全に一致しました（最大の動きは0.0）。tiledのkernelで、TP=2は3.0.0の値（2.5293・2.9109・1.3138・0.6272）から最大0.0184、TP=3はglueのkernelの値（3.0.0〜3.2.0：2.5246・2.9206・1.3147・0.6241）から最大0.0077動きました。2.x系の値との差は、TP=2で0.007以内、TP=3で0.013以内です。

## promptのscoreと構造化出力

これらは1.1.1からGLMのCUDAのエンジンで上流自身のものです（[API](../README.ja.md#api)）。**合格の条件**（両TPで）：

- **`prompt_logprobs`**：最初の後のpromptのどのtokenにも、自身の順位とlog確率、1から順位をつけた上位の候補を持つ行がある。同じ要求をもう一度、また `"draft": false` で送っても同じ行になる。5,000 tokenのpromptはどのtokenにも行があり、その最初の2,048 tokenのchunkの行は、同じpromptを3,001 tokenで切ったものの行と同じ。scoreを求めない要求はtokenのhashを保つ。
- **構造化出力**：`json_schema` の応答が、思考を切っても入れても、schemaのkeyと型でparseできる。素のgreedyの応答がすでに満たすschemaでは、grammarの下でも、`"draft": false` でも同じ文章になる。seedを付けたtemperature 0.7の同じ要求は、同じ有効な文章を2回出す。`tool_choice` の `required` は、引数がparseできる呼び出しをGLMのtoolのmarkupで出す。grammarの無い要求はtokenのhashを保つ。

## prefillとdecodeの速さ

38,960 tokenのpromptを、先頭に毎回新しいnonceを入れて3回（中央値）、同じ長さの数えないpromptを1本流した後に。続いて短い固定promptの後に最大512 tokenを3回（[ベンチマークの方法](benchmarks.ja.md#prefillとdecodeの速さ)）：

```sh
python -m glm53_tf bench --out ../records/<run>/bench.jsonl
```

基準値：TP=2でprefill 1,415.7 tok/s・decode 43.80 tok/s（3.3.0：1,411.2と44.00）、TP=3で1,559.7と56.03（glueのkernelの3.1.0：1,507.9と55.05）。decodeの行はどれも上限で止まり（`finish_reason` `length`）、prefillの行の `cached` はどれも0です。

## 長い入力

199,652 tokenの台帳の行の真ん中に合言葉一つ、499,622 tokenと1,036,859 tokenに合言葉三つ（先頭・中央・末尾）：

```sh
python -m glm53_tf long-input --passphrases 1 --tokens 199652
python -m glm53_tf long-input --passphrases 3 --tokens 1036859
```

目標に合わせた行数で、promptは199,307・499,254・1,035,295 tokenになりました。基準値：199,307 tokenで合言葉を、TP=2で153.4秒（3.3.0：155.0秒）、TP=3で140.3秒で見つけました。TP=3では499,254 tokenで3つ中3つ、最初のtokenまで399.5秒、1,035,295 tokenで3つ中3つ、1,064.9秒で、そのうちpromptは熱で2秒の待ちを19回、計38秒待ちました（午後に回しました）。どれも保持したpromptから再開しませんでした（`cached` 0）。glueのkernel（3.1.0、夜）では、TP=3の3つが140.4・398.1・1,022.7秒で、熱では待ちませんでした。1,036,859 tokenの目標はTP=3だけのものです。TP=2の窓は245,760 tokenです。

## tool引数ゲート越しのtool

1.x系の呼び方（69シナリオ、seed 42、temperature 0、parallel 1、effort low、`clear_thinking`、出力4,096 token、timeout 600秒）のtool-eval-benchを[ゲート](../SETUP.ja.md#6-tool引数ゲート任意)越しに：

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

エンジンは `clear_thinking` をchat templateに渡しません（[制限](../README.ja.md#制限)）。呼び方は、点数を1.x系・2.x系と比べられるよう、それを残します。

基準値：TP=2で92/100、TP=3で95/100、Safety Gateは合格。TP=2はTC-21とTC-61を、TP=3はTC-61だけを落としました（glueのkernelでは93/100）。各1回なので、1〜2点は1回の試行で動く範囲です。

## 応答を止める

**合格の条件**（両TPで、思考を切って）：1から1,000までの数を書かせるstreamの要求を約5秒でクライアントが切ると、15秒以内に `/health` の `live` blockに接続が残らず、直後の短い要求が10秒以内に答える。同じ要求にstop文字列 `"\n300\n"` を付けると299で終わり、`finish_reason` が `stop`。約93,000 tokenの台帳のpromptを、読んでいる途中の3秒でクライアントが切ると、直後の短い要求が、prompt全体が最初のtokenまでにかかる時間の半分未満で答える。基準値：両TPで、切ってから1.0秒で接続が消えました。切ったpromptの後、短い要求はTP=2で0.39秒、TP=3で1.29秒で答え、prompt全体の最初のtokenまでは68.4秒と62.8秒でした（3.3.0のTP=2：0.36秒、68.8秒）。TP=3の短い要求の時間は起動ごとに動きます：glueのkernelで、3.1.0の受け入れでは0.25秒、3.2.0では1.53秒、3.0.0では1.49秒でした。

## 返答の長い連続

40の要求を続けて流します。どれも新しいnonceと約6,000 tokenのPythonのmoduleに詳しいreviewを頼むもので、それぞれ最大1,024 token、temperature 0、effort low。これが全coreでCPUのzoneを温めた負荷です（[効率coreにする理由](../README.ja.md#配信の既定)）。**合格の条件**：40本すべてが答え、熱の見張りがエンジンを止めないこと。

基準値：両TPで40本中40本、TP=2で1,536秒、TP=3で1,233秒。最も熱いzoneはTP=2でrank 0のホストの74.9 °C、TP=3で85.1 °Cでした（3.3.0のTP=2：1,505秒・75.2 °C。glueのkernelのTP=3、3.1.0：1,315秒・79.8 °Cで、GPUは熱で遅くなりませんでした）。全coreでは、TP=2の同じ40本が1,535秒で終わり、rank 0のホストは93.0 °Cで、熱の見張りの止める温度まで1 °Cでした（[効率coreにする理由](../README.ja.md#配信の既定)）。

## メモリと温度

メモリの見張りのlog（`<WORK>/logs/hostwatch-<label>.log`）に、実行中の各ホストの最低の `MemAvailable` が残ります。ホストの記録は2秒ごとにACPIの最も熱いzoneを示します。rank 0のlogは、prefillの熱の待ちごとの秒数を `heat_wait_s` の行に出します。応答はそれを運びません。

基準値：起動の中の最低の `MemAvailable` は、TP=2で、visionのtowerなしの3.1.0の受け入れでは両rankとも15 GiB、towerありの3.3.0では11・13 GiBでした。TP=3では、3.3.0でrank 0・1・2が18・20・26 GiBでした。起動全体の最も熱いzoneは、TP=2でrank 0のホストが81.8 °C、rank 1のホストが83.6 °C（3.3.0：82.6・84.1 °C）、TP=3で93.0・90.0・86.0 °Cでした。TP=3の値は1M tokenのpromptの間のもので、3.3.0の受け入れの固定したcheckpointで、熱で待った要求はこれだけです（[長い入力](#長い入力)）。

**合格の条件**：どの実行もメモリの見張りにも熱の見張り（94 °C以上の読みが2回続く）にも止められないこと。

## XSFP4

XSFP4のcheckpoint（[checkpoint](../README.ja.md#checkpoint)）は固定したcheckpointと別のtokenを出すので、自分の基準値を持ちます。3.3.0の受け入れ（2026-10-22）で決めました。各TPの2回目の起動も、decode検査のhashと編集の返答が同じでした。受け入れが読んだのは素のblockのスケールのrevisionです。公開するrevisionは同じtensorで、3〜44層のrouted expertのblockのスケールを可逆に圧縮して持ち、各TPでもう1回の起動で、decode検査のhash・編集の返答・NLLが同じでした。検査は上と同じで、**合格の条件**も同じく、これらの値に照らします。ただし下のTP=3の二つの既知の振る舞いは除きます。`score-nll` にはXSFP4自身の `tokenizer.json`（固定したcheckpointのものとbyteまで同じ）を渡します。速さはこのcheckpointのもので、自分とだけ比べられます（[checkpoint](../README.ja.md#checkpoint)）。

| 検査 | TP=2 | TP=3 |
|---|---|---|
| decode検査の `completion_sha256` count / prose / code | `4e3411bd357abdd4` / `3b1a0be713e866f7` / `4a2d744c5cc1fb10` | `e63b580fa9ac5e6b` / `098fe1f21f591775` / `d2768fdc1e974d89` |
| decode検査の `token_sha256` count / prose / code | `cbe6552f4f1efcca` / `065a835f86734482` / `c4dfca7b73492c81` | `f6afacd228e848bc` / `32a387104a712248` / `9f6e8043c234c19d` |
| 同じタスクの受理の長さ | 3.276 / 1.796 / 2.971 | 3.362 / 1.947 / 2.823 |
| `bench --kinds edit` | `c419bce559d86b66` を190 roundで、固定したcheckpointと同じ応答 | 同じ |
| scoreもgrammarも無い要求（「The capital of France is」、8 token）の `token_sha256` | `09a15f0582e7…`、固定したcheckpointのもの | `a094669ab5de…` |
| teacher-forced NLL、ja / en / code / math | 2.5494 / 2.9219 / 1.3104 / 0.6249 | 2.5369 / 2.9244 / 1.3098 / 0.6224 |
| ゲート越しのtool-eval-bench | 93、Safety Gateは通過（TC-61がfail） | 同じ |
| 38,960 tokenのprefill / decode（tok/s） | 1,415.1 / 54.15 | 1,717.3 / 66.23 |
| 199,307 tokenのprompt | 見つけた、151.9秒 | 見つけた、127.9秒 |
| 499,254 tokenと1,035,295 tokenのprompt、最初のtoken | — | 3つ中3つ、373.0秒。3つ中3つ、1,015.7秒（うち42秒は熱の待ち） |
| 約93,000 tokenのpromptを切った後の次の要求、切らないpromptの最初のtokenとの比べ（秒） | 0.32 対 68.6 | 0.91 対 56.7 |
| 6,000 tokenのpromptの後の40の返答（秒、rank 0のホストの最も熱いzone） | 1,250、76.5 °C | 981、85.8 °C |
| 最低の `MemAvailable`、rankごと（GiB） | 11 / 13 | 21 / 22 / 28 |
| 起動の中の最も熱いzone、rankごと（°C） | 84.1 / 86.3 | 92.7 / 89.7 / 84.7 |

`PARALLEL=` を空にするとTP=2でエンジンは3本のstreamを取り、同じcountのhashを出しました。draftした応答はserialと同じでした（絵を含む要求も）。H.264とVP9の動画はdraftしても `"draft": false` でも同じ応答で、GIFとaudioの部分は400で断られました。TP=2では熱で待った要求はありませんでした。TP=3で待ったのは1,035,295 tokenのpromptだけで、2秒の待ちを21回でした。

**TP=3の既知の振る舞い。** [応答を止める](#応答を止める)のstop文字列の要求は、4,000 tokenの上限まで走ります：数え上げが300の前で繰り返しに入るためで、上流1.1.1でも同じでした（切った応答と切ったpromptは合格）。[promptのscoreと構造化出力](#promptのscoreと構造化出力)のscoreもgrammarも無い要求は、固定したcheckpointの「… pronounced」に対して「 Paris. In French, Paris is spelled」で終わるので、そのhashは固定したcheckpointのものでなく表の値です。どちらも既知の振る舞いで（[リリースでの測定値](../README.ja.md#リリースでの測定値)）、受け入れを止める理由にはしません。

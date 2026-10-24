# 検証（3.x）

[English](validation.md) · [3.x系の概要](../README.ja.md) · [配備の手順書](../SETUP.ja.md) · [ベンチマークの方法](benchmarks.ja.md)

3.x系の起動を何で受け入れるかを、回す順に基準値と一緒に並べます。基準値は、3.x系が配信するcheckpointであるXSFP4（[checkpoint](../README.ja.md#checkpoint)）でのネイティブエンジン自身のもので、参照機で、そのリリースの `serve.sh` の既定、全containerを効率coreにして測りました。2026-10-22の3.3.0の受け入れで、tiledのBF16のlinearが両TPで回る上流1.1.2（issue #1067）の上で決めました。3.4.0と3.6.0のリリースのimageは両TPで、3.5.0のものはTP=2で、同じdecode検査のhash、編集の返答、NLLを出しました。3.3.0まで既定で3.5.x系まで選べたNVIDIAのNVFP4は自分の基準値を持ち、それはそれらのリリースのtagと[変更履歴](../CHANGELOG.ja.md)に残ります。2.x系の基準は当てはまりません：ネイティブエンジンのkernelとBF16のKV cacheは別のtokenを出すので、二つの系列はteacher-forced NLLで比べ、2.x系の値はここでは参考としてだけ載せます。これらと比べてどのimageを受け入れたかはREADMEの[状況](../README.ja.md#要約)にあります。違う結果は日常の利用の前に説明すべき所見で、基準を置き換える値ではありません。

検査は、何が繰り返されるかの上に立ちます。一つの起動の中では、同じ要求はdraftの有無（`"draft": false`）によらず同じtokenを出し、prompt cacheから再開したpromptは新しいものと同じtokenを出します。起動は、同じTPとbuildの前の起動のtoken idを出します。TP=2とTP=3は設計上違い、和の取り方が違うkernel、例えばtiledのkernelに対するglueのkernel（`TF_GLM_MM`）も違います。同じcommitを別のホストでbuildすると、同じように答えながらSHA-256の違うbinaryになることがあるので、二つのbuildを見分けるのはhashではなくdecode検査です（[手順書 §3](../SETUP.ja.md#3-image)）。一度に複数の要求では、これを確かめていません。数を数える返答で一つの数を二度書くのは、生成とpromptが分かれる既知の場所です（[リリースでの測定値](../README.ja.md#リリースでの測定値)）。

道具はrank 0でcheckoutの `v3/` から、その仮想環境で（[手順書 §2](../SETUP.ja.md#2-checkoutとcheckpoint)）、またはPythonと `tokenizers` を持つcontainerの中で、loopbackのエンジン（`http://127.0.0.1:8095`、rankのファイルで変えなければモデル `glm-tf`）に当てます。containerがmountするのは作業directory（`/work`）とcacheだけなので、そこで使うcheckoutは作業directoryの下に置きます。道具の全てのoptionと環境変数は[設定](configuration.ja.md#道具)にあります。長い要求の間はホストを冷まし（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）、メモリの見張りと[熱の見張り](../../host/README.ja.md#長い運転の間)（`--container glm53-tf3 --process 'tensorfold-native serve'`）を動かしたままにします。

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
| count | `4e3411bd357abdd4` | `cbe6552f4f1efcca` | `e63b580fa9ac5e6b` | `f6afacd228e848bc` |
| prose | `3b1a0be713e866f7` | `065a835f86734482` | `098fe1f21f591775` | `32a387104a712248` |
| code | `4a2d744c5cc1fb10` | `c4dfca7b73492c81` | `d2768fdc1e974d89` | `9f6e8043c234c19d` |

hashは、各TPの2回目の起動と、`PARALLEL=` を空にしたTP=2の起動（count）でも保たれました。TP=2とTP=3は設計上互いに違います（rankの間での和の分け方が違うため）。受理長：TP=2で3.276／1.796／2.971、TP=3で3.362／1.947／2.823。`bench --kinds edit` は両TPで同じ返答を、190 roundで `token_sha256` `c419bce559d86b66` で返します。違う返答は受け入れを止めます。

## draftした応答とserialの一致

同じpromptをdraftありとなし（要求の本文に `"draft": false` で1 roundに1 token）で流し、同じ文章になること：prose・code・countのpromptで最大256 token、temperature 0、effort low、両TPで、文章は全体（推論と答え）で比べます。visionのtowerを読み込んだ起動では、小さなPNGを説明させる要求（最大64 token）も送り、二つの返答を同じように比べます。`bench --kinds edit` は、どの回でも、2回目の起動でも同じ返答を出します。

## 画像と動画の入力

`serve.sh` はエンジンを `--vision` 付きで起動します（既定の `VISION=1`）。検査の要求は、思考を切ったgreedyで送ります。**合格の条件**：

- **textは変わらない**：towerを読み込んだまま、decode検査と `bench --kinds edit` が、両TPで上のhashと返答を出す。
- **画像**（両TPで）：同じ絵をPNG・JPEG・WebPのdata URLで送ると答え、どれもdraftありと `"draft": false` で同じ返答になる。GIFは400で断る。絵を最初のmessageに置いた会話は、後のturnを絵の先までprompt cacheから再開し、冷えた回と同じ返答を出し、`"draft": false` でも、別の要求と同時でも同じになる。
- **動画**（両TPで）：H.264のMP4とVP9のWebMが答え、どちらもdraftありと `"draft": false` で同じ返答になる。audioの部分は400で断る。

これらの入力の上流自身の配信の検査、エンジンのsourceの `tools/zig/vision_served.py` と `video_served.py` は、`--vision` で起動したどのエンジンにも当てられます。3.x系の受け入れは上の要求を送りました。3.2.0の受け入れは `video_served.py` も、TP=2でNVIDIAのNVFP4に回しました（[変更履歴](../CHANGELOG.ja.md)）。

## teacher-forced NLL

[`config/nll_set.json`](../config/nll_set.json) のNLL採点セット（1.x系・2.x系のもののbyte単位の写し）：4領域（日本語・英語・コード・数学）に各4本、領域ごとに5,851〜6,830 token。`/v1/completions` の `prompt_logprobs` で採点します。tokenizerはcheckpoint自身のもの（下のXSFP4のもの）を使います：

```sh
python -m glm53_tf score-nll --url http://127.0.0.1:8095 \
  --tokenizer ~/.cache/huggingface/hub/models--Bizuayeu--GLM-5.3-Flash-XSFP4/snapshots/88736f916f8939607fde8a4b881dcae749f7551d/tokenizer.json \
  --out ../records/<run>/nll.json
```

実行する環境に `tokenizers` packageが要ります。各本文を2回採点し、全要求が答えればpassです。各本文の2回の差の最大は `self-agreement` の行に出ます。

| 領域（位置数） | TP=2 | TP=3 | 2.x TP=2（参考） | 2.x TP=3（参考） |
|---|---|---|---|---|
| 日本語（6,826） | 2.5494 | 2.5369 | 2.5474 | 2.5313 |
| 英語（6,678） | 2.9219 | 2.9244 | 2.9257 | 2.9001 |
| コード（5,941） | 1.3104 | 1.3098 | 1.3184 | 1.3101 |
| 数学（5,847） | 0.6249 | 0.6224 | 0.6250 | 0.6237 |

**合格の条件**：passで、各領域がそのTPの基準と同じこと。両TPで、どの本文の2回の採点も完全に一致しました（最大の動きは0.0）。2.x系の列は2.x系のエンジンでのNVIDIAのNVFP4、3.x系がもう配信しないcheckpointのもので、参考だけです。

## promptのscoreと構造化出力

これらは1.1.1からGLMのCUDAのエンジンで上流自身のものです（[API](../README.ja.md#api)）。**合格の条件**（両TPで）：

- **`prompt_logprobs`**：最初の後のpromptのどのtokenにも、自身の順位とlog確率、1から順位をつけた上位の候補を持つ行がある。同じ要求をもう一度、また `"draft": false` で送っても同じ行になる。5,000 tokenのpromptはどのtokenにも行があり、その最初の2,048 tokenのchunkの行は、同じpromptを3,001 tokenで切ったものの行と同じ。scoreを求めない要求はtokenのhashを保つ。
- **構造化出力**：`json_schema` の応答が、思考を切っても入れても、schemaのkeyと型でparseできる。素のgreedyの応答がすでに満たすschemaでは、grammarの下でも、`"draft": false` でも同じ文章になる。seedを付けたtemperature 0.7の同じ要求は、同じ有効な文章を2回出す。`tool_choice` の `required` は、引数がparseできる呼び出しをGLMのtoolのmarkupで出す。grammarの無い要求はtokenのhashを保つ。

scoreもgrammarも無い要求（「The capital of France is」、8 token）は、TP=2で `token_sha256` `09a15f0582e7…`、TP=3で `a094669ab5de…` を出します。TP=3の返答は既知の振る舞いです（[XSFP4](#xsfp4)）。上流自身の構造化出力の検査、エンジンのsourceの `tools/zig/structured_served.py`（正しい返答、draftありとplain、同時とsolo、拒否）は、3.x系では回していません。

## マルチバイト出力

gateとupの射影のglobal scaleが違うModelOptのNVFP4のcheckpointでは、マルチバイトの文字が化けると報告されています（[vLLM #54150](https://github.com/vllm-project/vllm/issues/54150)）。1.x系はこれを `server mojibake` で監視しています（[1.x系のマルチバイト出力](../../v1/docs/correctness-gates.ja.md#マルチバイト出力)）。`mojibake` は1.x系のpromptで、400文字以上の日本語と韓国語の答えを3本ずつ、temperature 0またはsampledで求め、答えと思考（`reasoning_content`）の中の置換文字（U+FFFD）・孤立サロゲート・改行とタブ以外の制御文字を数えます。答えの全文は `--out` に残ります：

```sh
python -m glm53_tf mojibake --out ../records/<run>/mojibake.json
python -m glm53_tf mojibake --temperature 1.0 --top-p 0.95 --seed 42 --out ../records/<run>/mojibake-sampled.json
```

要求は思考のeffortを指定しないので、エンジンは `serve.sh` の既定（high）で考え、思考と答えを合わせて32,768 tokenという `serve.sh` の上限の中で答えます。エラーの、空の、短い、大半が対象の文字でない、上限で切れた答えはinconclusive（終了の値2）で、passにはなりません。化けた文字が一つでもあれば不合格です（終了の値1）。**合格の条件**：両TPで全ての答えがpassすること。

基準値（3.6.0のimage、2026-10-24）：各TPで12本、temperature 0で6本とsampled（temperature 1.0、top_p 0.95、seed 42〜47）で6本、化けた文字はありませんでした。答えは753〜1,301文字、対象の文字が91〜95%で、どれも `stop` で終わり、最も長い応答は1,067 tokenでした。思考は24本中20本で空で、残る4本（両TPのsampledの日本語、seed 43と44）は106字と138字だったので、思考の文章はほとんど試されていません。

## prefillとdecodeの速さ

38,960 tokenのpromptを、先頭に毎回新しいnonceを入れて3回（中央値）、同じ長さの数えないpromptを1本流した後に。続いて短い固定promptの後に最大512 tokenを3回（[ベンチマークの方法](benchmarks.ja.md#prefillとdecodeの速さ)）：

```sh
python -m glm53_tf bench --out ../records/<run>/bench.jsonl
```

基準値：TP=2でprefill 1,415.1 tok/s・decode 54.15 tok/s、TP=3で1,717.3と66.23。decodeの行はどれも上限で止まり（`finish_reason` `length`）、prefillの行の `cached` はどれも0です。

## 長い入力

199,652 tokenの台帳の行の真ん中に合言葉一つ、499,622 tokenと1,036,859 tokenに合言葉三つ（先頭・中央・末尾）：

```sh
python -m glm53_tf long-input --passphrases 1 --tokens 199652
python -m glm53_tf long-input --passphrases 3 --tokens 499622
python -m glm53_tf long-input --passphrases 3 --tokens 1036859
```

目標に合わせた行数で、promptは199,307・499,254・1,035,295 tokenになりました。基準値：199,307 tokenで合言葉を、TP=2で151.9秒、TP=3で127.9秒で見つけました。499,254 tokenでは3つ中3つで、最初のtokenまでTP=2で431.5秒（3.5.0、524,288 tokenの窓、熱の待ちなし）、TP=3で373.0秒。TP=3では1,035,295 tokenで3つ中3つ、1,015.7秒で、そのうち42秒は熱の待ちでした。1,036,859 tokenの目標はTP=3だけのものです。TP=2の窓は3.5.0から524,288 tokenです（それより前は245,760）。

## tool引数ゲート越しのtool

1.x系の呼び方（69シナリオ、seed 42、temperature 0、parallel 1、effort low、`clear_thinking`、出力4,096 token、timeout 600秒）のtool-eval-bench 2.8.0を[ゲート](../SETUP.ja.md#6-tool引数ゲート任意)越しに：

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

エンジンは `clear_thinking` をchat templateに渡しません（[制限](../README.ja.md#制限)）。呼び方は、点数を1.x系・2.x系と比べられるよう、それを残します。

基準値（3.5.3のimage、2026-10-24）：TP=2で95/100、TP=3で92/100、Safety Gateは合格。TP=2はTC-39・TC-52・TC-55が部分点でTC-62とTC-68を落とし、TP=3はTC-14・TC-21・TC-39・TC-50・TC-52が部分点でTC-29・TC-62・TC-68を落としました。tool-eval-bench 2.6.1.dev52（`81eae0a`）ではXSFP4は両TPで93でした。2.7.0と2.8.0は多くのシナリオをより厳しく採点するので、版の違う点数は比べられません。各1回なので、1〜2点は1回の試行で動く範囲です。ゲートはエンジンの前に立つこのリポジトリの中継で、TensorFoldにはありません（[手順書 §6](../SETUP.ja.md#6-tool引数ゲート任意)）。したがってこれらの点数とSafety Gateは、ゲートの後ろのエンジンのものです。ゲートなしで同じ呼び方をエンジンへ直に当てると、3.6.0のimageでTP=2は93、TP=3は91で、Safety Gateは合格でした。両TPでTC-43も落としました：空の `query` で `web_search` を呼んだもので、ゲート越しではqueryなしでは呼ばずに断る返答になります。

## 応答を止める

**合格の条件**（両TPで、思考を切って）：1から1,000までの数を書かせるstreamの要求を約5秒でクライアントが切ると、15秒以内に `/health` の `live` blockに接続が残らず、直後の短い要求が10秒以内に答える。同じ要求にstop文字列 `"\n300\n"` を付けると299で終わり、`finish_reason` が `stop`。約93,000 tokenの台帳のpromptを、読んでいる途中の3秒でクライアントが切ると、直後の短い要求が、prompt全体が最初のtokenまでにかかる時間の半分未満で答える。基準値：切ったpromptの後、短い要求はTP=2で0.32秒、TP=3で0.91秒で答え、prompt全体の最初のtokenまでは68.6秒と56.7秒でした。TP=3ではstop文字列の要求が上限まで走ります。既知の振る舞いです（[XSFP4](#xsfp4)）。

## 返答の長い連続

40の要求を続けて流します。どれも新しいnonceと約6,000 tokenのPythonのmoduleに詳しいreviewを頼むもので、それぞれ最大1,024 token、temperature 0、effort low。これが全coreでCPUのzoneを温めた負荷です（[効率coreにする理由](../README.ja.md#配信の既定)）。**合格の条件**：40本すべてが答え、熱の見張りがエンジンを止めないこと。

基準値：両TPで40本中40本、TP=2で1,250秒、TP=3で981秒、rank 0のホストの最も熱いzoneは76.5 °Cと85.8 °Cでした。全coreでは、TP=2のこうした40本（NVIDIAのNVFP4、3.1.0）が、rank 0のホストを93.0 °Cにして終わり、熱の見張りの止める温度まで1 °Cでした（[効率coreにする理由](../README.ja.md#配信の既定)）。

## メモリと温度

メモリの見張りのlog（`<WORK>/logs/hostwatch-<label>.log`）に、実行中の各ホストの最低の `MemAvailable` が残ります。ホストの記録は2秒ごとにACPIの最も熱いzoneを示します。rank 0のlogは、prefillの熱の待ちごとの秒数を `heat_wait_s` の行に出します。応答はそれを運びません。

基準値：起動の中の最低の `MemAvailable` は、TP=2でrank 0・1が11・13 GiB（3.5.0の524,288 tokenの窓では12・12 GiB）、TP=3でrank 0・1・2が21・22・28 GiBでした。起動全体の最も熱いzoneは、TP=2で84.1・86.3 °C（3.5.0の窓では87.3・89.0 °C）、TP=3で92.7・89.7・84.7 °Cでした。TP=3の値は1M tokenのpromptの間のもので、熱で待った要求はこれだけです（[長い入力](#長い入力)）。

**合格の条件**：どの実行もメモリの見張りにも熱の見張り（94 °C以上の読みが2回続く）にも止められないこと。

## XSFP4

上の基準値はXSFP4のもので（[checkpoint](../README.ja.md#checkpoint)）、2026-10-22の3.3.0の受け入れで決めました。各TPの2回目の起動も、decode検査のhashと編集の返答が同じでした。その受け入れが読んだのは素のblockのスケールのrevisionです。公開するrevisionは同じtensorで、3〜44層のrouted expertのblockのスケールを可逆に圧縮して持ち、各TPでもう1回の起動で、decode検査のhash・編集の返答・NLLが同じでした。`score-nll` にはXSFP4自身の `tokenizer.json`（NVIDIAのNVFP4のものとbyteまで同じ）を渡します。速さはこのcheckpointのもので、自分とだけ比べられます（[checkpoint](../README.ja.md#checkpoint)）。

`PARALLEL=` を空にすると、TP=2の245,760 tokenの窓でエンジンは3本のstream（3.5.0の524,288では1本）を取り、同じcountのhashを出しました。draftした応答はserialと同じでした（絵を含む要求も）。H.264とVP9の動画はdraftしても `"draft": false` でも同じ応答で、GIFとaudioの部分は400で断られました。TP=2では熱で待った要求はありませんでした。TP=3で待ったのは1,035,295 tokenのpromptだけで、2秒の待ちを21回でした。

**TP=3の既知の振る舞い。** [応答を止める](#応答を止める)のstop文字列の要求は、4,000 tokenの上限まで走ります：数え上げが300の前で繰り返しに入るためで、上流1.1.1でも同じでした（切った応答と切ったpromptは合格）。[promptのscoreと構造化出力](#promptのscoreと構造化出力)のscoreもgrammarも無い要求は、NVIDIAのNVFP4が「… pronounced」で終わったのに対して「 Paris. In French, Paris is spelled」で終わり、そのhashは上の値です。どちらも既知の振る舞いで（[リリースでの測定値](../README.ja.md#リリースでの測定値)）、受け入れを止める理由にはしません。

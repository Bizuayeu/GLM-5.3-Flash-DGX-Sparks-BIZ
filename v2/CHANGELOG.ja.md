# 変更履歴

[English](CHANGELOG.md)

正典は[英語版](CHANGELOG.md)です。GitHub Releaseの本文は英語版の各版の節から作られます。

TensorFoldで配信する2.x系です。`v2.*` のタグはこのファイルの節を公開します。1.x系の履歴は[v1/CHANGELOG.ja.md](../v1/CHANGELOG.ja.md)にあります。

## 2.9.0 — 2026-10-11

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.9.0` の `d2dd932a2da15478b85d4b0bd5f60a4bae61599c` からTensorFoldをbuildします（[`TENSORFOLD_REF`](docker/Dockerfile)）。2.8.0のエンジンに次を足したものです：
  - clientが去ったpromptは、埋めているchunkの後で、すべてのrankで止まります。最後を除く各chunkの後に、rankはそれぞれint32を1つall-gatherし、どれかが望めばそろって止まります。cacheは埋め終えた行を残し、要求は取り消しとして終わります。これまでは、clientが去っても両rankがpromptを最後まで埋めていました。止めないpromptのビットは変わりません。`TF_GLM_PROMPT_STOP=0`（すべてのrankで同じに）で、どのpromptも最後まで埋めます（[決定の記録](docs/decisions.ja.md#prefill)）。MiaAI-Labのpatch 0109-glm-prompt-stop（branch `tp4`、Apache-2.0。それ自体は上流TensorFoldのchunkの境目でのpromptの停止に倣う）に倣います。
  - serverはtokenizerのbatchの呼び出しでtokenizeし、PythonのGILを放します。長い要求のtokenizeが、serverの他のthreadを止めなくなります。idは同じです。MiaAI-Labのpatch 0099-glm-tokenize-nogil（Apache-2.0）に倣います。

imageは `glm53-tf:2.9.0`（linux/arm64 `sha256:1f811b00bb30a756ac342a05905f57832f6a2d555b7dd6f72dbf408dcf67d567`）です。

### Accepted

2026-10-11に参照機で、画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:1f811b00bb30a756ac342a05905f57832f6a2d555b7dd6f72dbf408dcf67d567`、3台で同じ）で、固定の重みとAXLのそれぞれをTP=2とTP=3で：

- decode検査は4回の起動すべてで2.8.0のtoken idと受理長を出し、`bench --kinds decode` は2.8.0の返答、`bench --kinds edit` は基準の返答（`ecd7a283a48a0cc4`）。
- clientが切ったprompt（固定の重み。約70,000 token、prefillの3秒でclientが去り、続けて短い要求）：短い要求は、切ってからTP=2で2.12秒、TP=3で1.04秒で返った。同じpromptを切らずに埋めると54.58秒と41.92秒。
- `top_k` 0（固定の重み、TP=2、2.8.0の要求）：どの返答のtokenも2.7.0のhostの規則と同じ。
- TP=2のNLLの組は両方の重みで2.8.0と同じ。TP=2のtool-eval-benchは固定の重みが92／93、AXLが89／91で、直ではTC-43でSafety Gateを通らず、ゲート越しでは通過（2.8.0と同じ）。固定の重み、TP=2とTP=3：画像の検査はすべて合格。
- この窓では回していないもの：2.8.0と同じ。
- 窓の前に03で、`d2dd932` のエンジンで：小さなモデルのビットの照合はBF16とFP8とも2.8.0と同じhash、briefの一式は1,544 passed（42 skipped。2.8.0の1,528とpromptの停止の16）、tokenizeの試験は14 passed。GLMのtokenizerは、batchの呼び出しで `encode` と同じidを、1,106の文（最長2.1M token）でspecial tokenの有無とも出した。

## 2.8.0 — 2026-10-09

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.8.0` の `7458b111c9aab673460eedf9f60167d5fa8c925f` からTensorFoldをbuildします（[`TENSORFOLD_REF`](docker/Dockerfile)）。2.7.0のエンジンに次を足したものです：
  - `top_k` 0 の要求は、hostで語彙全体のnucleusに落ちる代わりに、デバイスで抽選します。鍵つきのTritonのpassがhostの規則の位置ごとの一様乱数で全tokenを採点し、64 bitの鍵の上のradixのpassが各行の `top_p` の切れ目を見つけ、hostは最良が各rankの次点を越えるときだけそれを採り、抽選が決められないところでは自分の規則を回します。tokenはhostの規則のものです。sfxnz/TensorFold の `dsv41-recipe-engine4` からsfxnzの2つのcommit（Apache-2.0、閉じた上流 #408 の続き）を、そのまま取り込みました。当たるのは `top_k: 0` を明示するclientだけで、serverの既定は20です（[決定の記録](docs/decisions.ja.md#decode)）。
  - エンジンの `THIRD_PARTY_NOTICES.md` は、loop guardの数が応答のusageでなく、実際に出る `tensorfold` ブロックにあると書きます。

imageは `glm53-tf:2.8.0`（linux/arm64 `sha256:4324f7c0b246935fdee31a1ad3fba1c14f933b17991a58a97dda16898638f92d`）です。

### Accepted

2026-10-09〜10に参照機で、画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:4324f7c0b246935fdee31a1ad3fba1c14f933b17991a58a97dda16898638f92d`、3台で同じ）で、固定の重みとAXLのそれぞれをTP=2とTP=3で：

- decode検査は4回の起動すべてで2.7.0のtoken idと受理長を出し、`bench --kinds decode` は2.7.0の返答、`bench --kinds edit` は基準の返答（`ecd7a283a48a0cc4`）。
- `top_k` 0（固定の重み、TP=2。温度1、`top_p` 0.95、seed 7、2つのprompt、各2回）：どの返答のtokenも、2.7.0に送った同じ要求と同じで、2.7.0の12.64と8.82 tok/sに対して36.80と23.98。`top_k` 20ではtokenも速さも2.7.0と同じ。
- TP=2のNLLの組は、両方の重みで2.7.0と4桁まで同じ。TP=2のtool-eval-benchは固定の重みが92／93、AXLが89／91で、直ではTC-43でSafety Gateを通らず、ゲート越しでは通過（2.7.0と同じ）。固定の重み、TP=2とTP=3：画像の検査はすべて合格。
- この窓では回していないもの：TP=3のNLLの組、長い入力、1M tokenのtool gate、AXLのprefill、AXLでの画像の検査（2.7.0と同じ）。
- 窓の前に03で：エンジンのsamplingとnucleusの試験が通り（MLX専用の1本はLinuxでは回らない）、小さなモデルのビットの照合はBF16とFP8とも2.7.0と同じhash、briefの一式は1,528 passed（42 skipped）で2.7.0と同じ。

## 2.7.0 — 2026-10-09

### Changed

- **推論のeffortを指定しない要求は、chat templateの `max` ではなく `high` になります。** 固定のchat templateは指定のないeffortを `max` として描き、`max` では思考がほぼ際限なく続いて応答の上限の大半を使います。1.x系はそうした要求を `high` で処理しています（`api.default_reasoning_effort`）。`serve.sh` はrank 0でエンジンの `--reasoning-effort high` を渡し、値はrank 0のファイルの `REASONING_EFFORT` から取ります（空なら指定なし＝templateのまま）。クライアント自身が指定したeffortはそのまま優先されます。検査は自分でeffortを指定するので、その基準値はそのままです（[配信の既定](README.ja.md#配信の既定)）。

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.7.0` の `9cdd935bba7b6092f7471bc42d88b19b7df8a515`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.5.0のエンジンに次を足したものです：
  - prompt chunkのDSAのpoolのscoreは、1 programで1行・32 pool blockを計算し、行のindexのqueryとheadの重みをそのblockのために一度だけ読みます。ビットは同じです。固定の重みのTP=3で、約226K tokenのprefillは熱の待ちを除いて5.8〜5.9%短くなりました（[リリースでの測定値](README.ja.md#リリースでの測定値)）。MiaAI-Labのpatch 0086（Apache-2.0）に倣い、この木のFP8のpool keyと採点する列に合わせて書き直したものです。
  - `/v1/responses` はOpenAIの `include` の値を受けて無視します：どの値もこのserverが足すもののない出力を求めるもので、癖で送るクライアントがあります。OpenAIが定めていない値や、文字列のlistでない `include` は今も400で断ります。MiaAI-Labのpatch 0093（Apache-2.0）に倣った書き直しです。
  - rank 0のファイルの `TF_GLM_LOOP_GUARD=1` は、16 token以下の完全な周期が256 token続くか、直近256 tokenの半分を一つのtokenが占めるかで潰れた思考のblockを閉じ、応答の `tensorfold` blockに `loop_guard` として数えます。既定は無効で、gateは作られず、どの要求も変わりません（[決定の記録](docs/decisions.ja.md#エンジン)）。MiaAI-Labのpatch 0091（Apache-2.0）を取り込み、試験は書き直しました。
  - `MODELS` はCUDAのエンジンが読む2つのNVFP4のcheckpoint（固定のものと公開したAXLの重み）を挙げます。`tensorfold models` がそれらを示し、repo idでpullや配信をしても、TensorFoldが試験したcheckpointではないとは表示しなくなりました。
  - 起動時にrankの設定が違うとき、断りの文は違う設定を名前で挙げ、rank 0の値と他のrankの値を示します。
  - 起動時、エンジンはcheckpointのtensorのheaderを2回でなく1回だけ読みます：rankの比べに使うcheckpointの種類を、メモリの見積もりが読んだheaderから数えます。
- ほかに：ビットを変えないrefactorと試験（E2M1の表と行の揃えをそれぞれ一か所に、mixed-precisionのblockのalgorithmを読むhelperを一つに、NVFP4のheadを他のNVFP4のprojectionと同じ条件で選ぶ）と、公開したAXLの重みを説明するGLMのレシピ。エンジンの `THIRD_PARTY_NOTICES.md` はpatch 0086・0091・0093を挙げます。

### Documentation

- [README](README.ja.md#設定)は `TF_GLM_LOOP_GUARD`、`/v1/responses` の `include` の扱い、[TensorFoldの他のレシピ](README.ja.md#tensorfoldの他のレシピ)でのMiaAI-Labの3つのpatchを載せます。[決定の記録](docs/decisions.ja.md)にeffort、poolのscore、loop guardの行があります。

imageは `glm53-tf:2.7.0`（linux/arm64 `sha256:7e9fe184cb406f6592f74b4ba3d5d1d11cd4184147283edf84bfc4d3ef9d6dd0`）です。

### Accepted

2026-10-09に参照機で、画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:7e9fe184cb406f6592f74b4ba3d5d1d11cd4184147283edf84bfc4d3ef9d6dd0`、3台で同じ）で、固定の重みとAXLのそれぞれをTP=2とTP=3で：

- decode検査は4回の起動すべてで2.5.0のtoken idを出し、受理長も2.5.0と同じでした：3.961／2.098／3.180（固定 TP=2）、3.813／2.004／2.893（AXL TP=2）、4.056／2.222／3.234（固定 TP=3）、3.631／2.060／2.994（AXL TP=3）。
- `bench --kinds decode` は2.5.0の返答を出しました：TP=2の両方の重みとTP=3のAXLで `7754eb09bd6615fd`、TP=3の固定の重みで `27fc79ab52b7830f`。どの行も上限で止まりました。
- `bench --kinds edit` は4回の起動すべてで基準の返答（`ecd7a283a48a0cc4`）。
- TP=2のNLLの組は、両方の重みで2.5.0と4桁まで同じ：固定 2.5474／2.9257／1.3184／0.6250、AXL 2.5556／2.9438／1.3334／0.6474。
- 固定の重み、TP=2とTP=3：画像の検査はすべて合格。
- TP=2のtool-eval-bench、同じ呼び方（69シナリオ）：固定の重みは直で92、tool引数ゲート越しで93、AXLは89と91。直ではTC-43でSafety Gateを通らず、ゲート越しでは通過。2.5.0と同じ点と出方です。
- この窓では回していないもの：TP=3のNLLの組、長い入力（262Kと1M token）、1M tokenのtool gate、AXLのprefill、AXLでの画像の検査。既定の経路のtoken idは両TPで2.5.0とも2.4.0とも同じなので、2.4.0の結果がこのエンジンにも当てはまります。
- 窓の前に：新旧のpoolのscoreは14例（decodeの窓とprompt chunk、BF16とFP8、位置2,047〜262,144）で同じtokenを同じ数だけ選び、同じscoreの列を読みました。エンジンのbriefの一式は1,528 passed（42 skipped）で、GLMのエンジンのGPUの試験を含みます。loop guardとthinkingを含む選んだ試験は237 passed（8 skipped）。小さなモデルのビットの照合は、BF16とFP8とも2つのpatchの無い場合と同じhashでした。

## 2.6.1 — 2026-10-09

### Changed

- 公開監査（`tools/check_publication.py`、CIで回ります）は、追跡しない `records/` の実行のディレクトリを名指す公開ファイルを報告します。リポジトリの読者は開けないので、公開ファイルは測ったものを書きます。今名指しているファイルは件数つきの表に載せました：`config/` の測定の組の出どころは恒久に、1.x系の測定・FreedomBench・candidate-orderの頁と一つのoverlayは次に書き直すまで。表のファイルが件数を超えても下回っても報告するので、表は縮むだけです。

imageに入るファイルは変わらず、2.5.0のimage（linux/arm64 `sha256:ec61cc199b160225f182bb07e857b830c5189d21f77c8ed84bc29d4638903d8b`）のままです。

## 2.6.0 — 2026-10-08

### Changed

- `bench` のsummaryは、上限の4,096 tokenで切れたeditの返事（`finish_reason` が `length`）をeditの中央値から外し、新しい `cut` がそうした行を種類ごとに数えます。行は今までどおり印字・記録し、`all` にも速さを残します。これまでは、[測定](docs/benchmarks.ja.md)が編集を測っていないと書いていた切れた返事も中央値に入っていました。
- `verify-download` は、`state/` にダウンロードの状態が無いホスト（`download` がまだ登録していない写したcache）では、`checksum-status.json` に `no download status` を記録し、回すべき `download` のコマンドを出して終了コード1で終わります。これまでは `FileNotFoundError` で止まっていました。写した後に `download` を一度回すことは[手順書](SETUP.ja.md#2-checkoutとcheckpoint)にあります。

imageに入るファイルは変わらず、2.5.0のimage（linux/arm64 `sha256:ec61cc199b160225f182bb07e857b830c5189d21f77c8ed84bc29d4638903d8b`）のままです。

## 2.5.1 — 2026-10-08

### Changed

- `config.MODEL` と `config.REVISION` を外しました。2.4.0から道具は `checkpoint()` でcheckpointを決めており、読んでいたのは試験だけでした。`download` と `verify-download` のhelpが `--checkpoint` を説明します。`bench` のprefillは他の種類と同じ表で走ります。行と要求は変わりません。
- 例のrankのファイルに、公開のAXLの重みの固定snapshotを持つ `CHECKPOINT` の行をコメントで置きました。[README](README.ja.md#設定)と手順書が足すように言う行です。

### Documentation

- 2.x系の測定値はREADMEの[リリースでの測定値](README.ja.md#リリースでの測定値)に一度だけ書きます。[判断](docs/decisions.ja.md)は差の要旨とリンク、[検証](docs/validation.ja.md)は判定と今の基準値、[運用](docs/operations.ja.md)は注意とリンクを持ちます。2.4.0のAXLのTP=3の1Mのpromptで読んだ94.4 °Cは、受け入れの1秒ごとの記録の値として、thermal watch（2秒ごと）の93.5 °Cと並べて書きます。
- 判断の再開の条件を、上流のPythonのエンジンの凍結（#286）に合わせました（来ないmergeを待たない）。Next Actionの#243の項目から過ぎた日付を外しました。
- READMEの1.x系との違いに、92／88 °Cの帯と並べて93 °Cの見込み（`TF_GLM_HEAT_CEILING`）を書きます。応答の `tensorfold` blockの一覧に `drafted`・`prefill_s`・`sha256` を足しました。
- [手順書 §8](SETUP.ja.md#8-受け入れ)は検証をその順に、`bench --kinds edit` の応答を含むdecode検査からメモリと温度まで回します。checkpointの手順は、写したcacheを登録するやり方（`download` を一度、その後 `verify-download` を `--wait` なしで）を書きます。登録しないと `verify-download` はダウンロードの状態が無いところで止まります。
- [測定](docs/benchmarks.ja.md)は長い入力の目標が何tokenに合ったか（2.2.0から1,035,295 token、AXLのTP=2は262,113 token）を書き、`bench` のdocstringは各行が持つ欄を書きます。[運用](docs/operations.ja.md)はimageを替える前に、新しい版ではなく使っているimageにtagを付けます。
- 試験のコメントは、手元の記録のパスではなく測ったものを書きます。

imageに入るファイルは変わらず、2.5.0のimage（linux/arm64 `sha256:ec61cc199b160225f182bb07e857b830c5189d21f77c8ed84bc29d4638903d8b`）のままです。

## 2.5.0 — 2026-10-08

### Changed

- **`bench --kinds decode` は新しい要求を送ります。道具が測るものの変更です：返答はmodel自身の終わりを越えずに、上限まで数えます。** 要求は `Write the numbers from 1 to 1000, one per line, and nothing else.` で、streamで、`ignore_eos` なしで最大512 token、temperature 0、`chat_template_kwargs` は同じです。行には `finish_reason` と、応答の `tensorfold` ブロックの `rounds`・`tokens_per_round`、返答の `sha256` が足されます。前の要求 `Count upward from one, one number per line.`（`ignore_eos` つき）では、modelは約100 tokenで自分で返答を終えていました。512の残りはmodelが自分の終わりの後に作った会話で、重みによって違いました（固定の重みは数え続け、AXLは散文を書いた）。つまりこの行は違う文を比べていました。新しい要求では受け入れのどの行も上限で止まり（`finish_reason` `length`）、TP=2では両方の重みがtokenまで同じ返答を出しました。その値は以前のリリースの `bench --kinds decode` とは比べられません（[ベンチマークの方法](docs/benchmarks.ja.md#prefillとdecodeの速さ)）。

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.5.0` の `8a36b2cb6449821d6204dcaf28618106e8502b63`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.4.0のエンジンに、上流とそのレシピから次を足したものです：
  - GLMのtool呼び出しで、end tokenが `</tool_call>` より先に来ても、全体がparseできればtool callとして送ります。欠けた `<arg_key>` は戻します（TensorFold #285、MiaAI-Lab）。
  - serverは起動時に開けるファイル数のsoftの上限をhardの上限まで上げ、acceptでdescriptorを使い切ったら一度ログに出します（TensorFold #294、plotarmordev）。参照機のcontainerでは、shellのsoftの上限が1,024、hardの上限が524,288で、動いているエンジンのsoftの上限は524,288でした。
  - 会話に引用された `<|image|>` は、本物の画像の隣では文字のままで、要求を400で失敗させません（MiaAI-Labのpatch 0080、Apache-2.0に倣う。書き直しで、codeは写していません）。begin/image/endの並びを丸ごと引用した会話は、今も画像として数えます。
  - GLMのEXL3/TR3のcheckpointの名を `brandonmusic/GLM-5.3-Flash-tr3-4bpw` にしました。取り下げられたMia-AiLabの再掲は一覧に残すので、その名でpullした写しも試験済みとして認識されます。
- ほかに：#294の上流の試験は時機によって落ちることがありました（試験のserverが受けたsocketをworkerのthreadで閉じ、それが試験のsqueezeと次のacceptの間に入ることがあった）。forkの試験はその場で閉じるようにしました。エンジンの `THIRD_PARTY_NOTICES.md` は、patch 0080をMiaAI-Labの他のpatchと並べて挙げ、外れたroundの後のcopy draftsの上限をこの木の `MISS_MOST` として説明します。
- 既定の経路（画像なし・toolなし）のtokenは変わりません：decode検査は両方の重み・両TPで2.4.0のtoken idを出しました。

### Documentation

- 2.4.0のTP=2で、AXLの `bench --kinds decode` が固定の重みより2%速いだけだった原因を、[README](README.ja.md#リリースでの測定値)と[検証](docs/validation.ja.md#prefillとdecodeの速さ)が原因不明としていた所に書きました：前の要求の、終わりの後の会話です。[検証](docs/validation.ja.md)はこのリリースの `bench --kinds decode` の値と引用の `<|image|>` の検査を、[ベンチマークの方法](docs/benchmarks.ja.md#prefillとdecodeの速さ)は新しい要求を載せます。[決定の記録](docs/decisions.ja.md)に要求とエンジンの取り込みの行があります。
- 公開したAXLの重みのtool-eval-benchを2.x系で測りました（TP=2、下）。HLEは2.x系ではまだ回していません。

### Accepted

2026-10-08に参照機で、画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:ec61cc199b160225f182bb07e857b830c5189d21f77c8ed84bc29d4638903d8b`、3台で同じ）で、固定の重みとAXLのそれぞれをTP=2とTP=3で：

- decode検査は4回の起動すべてで2.4.0のtoken idを出しました。受理長は3.961／2.098／3.180（固定 TP=2）、3.813／2.004／2.893（AXL TP=2）、4.056／2.222／3.234（固定 TP=3）、3.631／2.060／2.994（AXL TP=3）。
- 新しい要求での `bench --kinds decode`：どの行も上限で止まりました（`finish_reason` `length`、512 token）。TP=2では両方の重みが同じ返答（`7754eb09bd6615fd`）で、AXLは57.09 tok/s、固定の重みは42.63（+34%）。TP=3ではAXLが76.55 tok/s、固定の重みが56.73（+35%。次の項の但し書きつき）。
- TP=3の固定の重みの返答（`27fc79ab52b7830f`）も1行に1つずつ上限まで数えましたが、他の返答の234に対して230まででした：数える前の思考が41 tokenで、AXLより11 token長いので、TP=3の2つの返答はtokenまで同じではありません。
- `bench --kinds edit` は4回の起動すべてで基準の返答（`ecd7a283a48a0cc4`）。
- TP=2のNLLの組は、両方の重みで2.4.0と4桁まで同じ：固定 2.5474／2.9257／1.3184／0.6250、AXL 2.5556／2.9438／1.3334／0.6474。
- 固定の重み、TP=2とTP=3：画像の検査はすべて合格。引用の `<|image|>` を本物の画像の隣に含む会話は200を返して画像を読み、引用の無い同じ要求も同じでした（2.4.0は引用のある方を400で断った）。
- TP=2のtool-eval-bench、前と同じ呼び方（69シナリオ）：固定の重みは直で92、tool引数ゲート越しで93、AXLは89と91。直では両方ともTC-43（`web_search` の空の `query`）でSafety Gateを通らず、ゲート越しでは両方とも通過。2.4.0と同じ点と出方です。
- この窓では回していないもの：TP=3のNLLの組、長い入力（262Kと1M token）、1M tokenのtool gate、AXLのprefill、AXLでの画像の検査。既定の経路のtoken idは両TPで2.4.0と同じなので、2.4.0のTP=3のNLL、長い入力、1Mのtool gateの結果がこのエンジンにも当てはまります。
- エンジン自身の試験：briefの一式は1,511 passed（42 skipped）で、GLMのエンジン・EXL3・visionのGPUの試験を含みます。取り込みとAXLの試験は129 passed（3 skipped）。小さなモデルのビットの照合はBF16とFP8とも基準と同じです。

## 2.4.0 — 2026-10-08

### Added

- **公開したAXLの重みを任意で配信できます。既定は固定のcheckpointのままです。** NVFP4 BIZ AXL（[Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16](https://huggingface.co/Bizuayeu/GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16) のrevision `bbad98c8f380588c16a2326bf5a2ab7344190b07`、[`config/axl.lock.json`](config/axl.lock.json) で固定）は、attentionのprojectionと `lm_head` をW4A16のNVFP4に詰め直し、他は固定のcheckpointのままのものです。1.x系が公開した任意設定で配信するcheckpointと同じです。`download --checkpoint axl` と `verify-download --checkpoint axl` が取得と検証をし、その状態は固定のcheckpointの取得とは別の `state/axl/` に置きます（[手順書 §2](SETUP.ja.md#2-checkoutとcheckpoint)）。全rankのrankのファイルの `CHECKPOINT` でこれを配信します（[設定](README.ja.md#設定)）。TP=2ではdecode検査が57.30／37.53／44.80 tok/s（固定の重みは43.80／27.54／36.01）、`bench --kinds edit` が74.26（同58.13）で、NLLは高くなりました（2.5556／2.9438／1.3334／0.6474、固定の重みは2.5474／2.9257／1.3184／0.6250）。タスクの水準の品質は2.x系では測っていません（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Changed

- **copy draftsは外れた後に減らしません**（エンジンのcopy draftsの `MISS_MOST` を3 → 5）：外れた直後のroundも、他のroundと同じく5つまでdraftにします。TP=2で3と比べ、編集と、copyの外れが多い2つの負荷（moduleを5組の改名つきで返す：copyしたdraftの10%が外れ。そのmoduleのunittestを書く：41%）で、5は編集と改名で1.0%速く、unittestでは同じで、tokenも同じでした（[決定の記録](docs/decisions.ja.md#decode)）。

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.4.0` の `ab8e74161ba807d9a637fee02d19edb932276257`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.3.0のエンジンに、W4A16のNVFP4のattentionとheadの読み込みと `MISS_MOST` 5を足したものです。エンジンはcheckpointのテンソルごとに経路を選び、切り替えはありません：`weight_scale` を持つprojectionはNVFP4の線形層（decodeのlaneの行列積とpromptのGEMM）として読み、`kv_b` はlatentの経路のためにfp32へ戻します。rankの起動時の照合にcheckpointの種類が入ったので、違うcheckpointで起動したrankどうしは起動を断ります。固定のcheckpointの経路はビット単位で変わりません。

### Documentation

- [手順書 §2](SETUP.ja.md#2-checkoutとcheckpoint) はAXLの取得と検証を載せ、modelのフォルダにファイルの無いcacheの写し方を書きます：新しいHugging Face hubのclientは、modelのファイルをcache全体で共有する置き場（`hub/blobs/`）に置き、modelのフォルダにはlinkだけを持つことがあります（参照機の1台のhuggingface_hub 1.32.0がそうでした。他の機の1.30.0はmodel自身の `blobs/` に置きました）。するとmodelのフォルダを写してもlinkしか写らず、写し先の次の `download` がInternetから全部取り直します。このリリースでAXLの重みを写したときにそうなりました。
- [検証](docs/validation.ja.md)はAXLの重みの基準値を固定の重みの隣に載せます。[決定の記録](docs/decisions.ja.md)にAXLと `MISS_MOST` の行があります。

### Accepted

2026-10-07と08に参照機で、画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:7d47fc819ded734e87b0a881b913ee0e5ffa4b866e3d813090c09ff038b145f6`、3台で同じ）で、固定の重みとAXLのそれぞれをTP=2とTP=3で：

- 固定の重み、TP=2とTP=3：decode検査は2.3.0のtoken idを出し、countの受理長は3.961と4.056。NLLの組は基準の値。画像の検査はすべて合格。
- AXL、TP=2とTP=3：decode検査はAXLの基準のtoken idを出し（[検証](docs/validation.ja.md#decode検査)）、TP=2では2回の起動で同じ。NLLの組はTP=2 2.5556／2.9438／1.3334／0.6474、TP=3 2.5590／2.9471／1.3357／0.6439。
- `bench --kinds edit` は4回の起動すべて（両TP、両方の重み）で基準の返答（`ecd7a283a48a0cc4`）。
- 長い入力：AXLのTP=2で262,113 tokenの3か所の合言葉が3/3。TP=3の1,035,295 tokenは両方の重みで3/3、最初のtokenまで固定の重みで1,588.4 s、AXLで1,524.1 s（うち熱の待ち480.5 sと454.4 s）。
- 固定の重みのTP=3での1M tokenのtool gate：1回目は1,553.3 s後に200（うち熱の待ち448.4 s）で `tool_calls`、修復の2回目は保持promptから3.6 sで200。
- 熱：固定の重みでは最も熱い機の最高が92.6 °Cで、2.3.0と同じ。AXLのTP=3の1M tokenのpromptの間に、1台が1秒の記録で1回94.4 °Cを読みました（熱の見張りの2秒の記録では93.5 °C）。始めて約4分、90.5〜91 °Cで30秒以上横ばいの後でした：そのchunkの前の確認は92 °C未満で、直前のchunkの上がり幅がほぼ0だったので、見込みは待たせませんでした。次の確認で待ちに入り、以後の待ちは12〜15 °Cの上がり幅を見込みました。熱の見張りはエンジンを止めていません（その規則は94 °C以上が2回続くこと）。1秒で待ちに入ったので、この読みは許容しました。
- エンジン自身の試験：briefの一式は1,461 passed（42 skipped）、AXLの試験は34 passed。小さなモデルのビットの照合はBF16とFP8とも2.3.0と同じです。

## 2.3.2 — 2026-10-07

### Changed

- コメントだけ（1.30.0と共通）：`glm53_tf/download.py` は状態ファイルを読むものを両系の写しで正しい言葉で書き、tool gateの修復の注記は手元の記録のパスではなく測ったものを書きます。imageに入るファイルは変わらず、2.3.0のimage（linux/arm64 `sha256:c6700600e28029995f9fad5271f9395d21d703f2d640372d825e50250f6b8fd9`）のままです。

## 2.3.1 — 2026-10-07

### Fixed

- 2.3.0で `TF_GLM_HEAT_CEILING` のために足した文書の契約の試験を、`ruff format` の求める書式にしました。CPU checksが再び通ります（2.3.0のcommitとtagで落ちていました。試験そのものは通っていました）。

imageに入るファイルは変わりません。2.3.0のimage（linux/arm64 `sha256:c6700600e28029995f9fad5271f9395d21d703f2d640372d825e50250f6b8fd9`）のままです。

## 2.3.0 — 2026-10-07

### Changed

- **prefillの熱の待ちが1 chunk先も見込みます**（`TF_GLM_HEAT_CEILING`、既定93 °C。帯は92 °Cと88 °Cのまま）。chunkの前に、最高温度に直前のchunkの上がり幅を足した値が93 °Cを越えそうなら全rankで待ち、越えなくなるまで解きません。1M tokenのpromptの終わり近くでは、chunkの合間の確認の後にchunk一つで約7 °C上がるので、2.2.0の受け入れでは1回94.3 °Cを読みました。見込みありでは最も熱い機の最高が92.6 °Cでした。TP=3の1M tokenのpromptは長く待ちます：最初のtokenまで1,440.6 s（前は1,154.3 s）、うち熱の待ち350.3 s。待ちを除いたprefillは変わりません（[決定の記録](docs/decisions.ja.md#熱)）。全rankで同じ値にします（違えば起動を断ります）。空にすると見込みません。

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.3.0` の `7410d1d76b4403a209dd2a5617fa85afe1ed1e32`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.2.0のエンジンに熱の見込みを足したもので、同じtokenを出します。GLMのrecipeのNVFP4の節を実重みでの実行から書き、`--vision` で画像の塔を読むと書きました。第三者の告知は `SCORE_RB` をこのtreeの値で書きます。コメントは手元の記録のパスではなく測ったものを名指します。FP8の行の余白、BF16のsplit-Kの部分和、prompt overlapの切れ数の上限をそれぞれ一か所で名付けました。形式と設定の試験はGPUなしで流れます。copy draftsは外れた直後に3つのdraftのままです（1と5と比べて測りました。[決定の記録](docs/decisions.ja.md#decode)）。

### Fixed

- `THIRD_PARTY_NOTICES.md` のHLEの行が、v1/v2の分割で移った `v1/config/hle.lock.json` を指します。

### Documentation

- tool-argument gateのbodyの上限（64 MiB）とtimeout（1回の上流要求あたり2,400 s）を2.xで測りました：toolを1つ宣言した1,035,454 tokenの要求は4.1 MBで、TP=3のgate越しに1,494 s後に返答し、修復の2回目は保持promptから3.5 sで再開しました。
- [検証](docs/validation.ja.md)と[運用](docs/operations.ja.md)は見込みの理由を書きます。[Next Action](README.ja.md#next-action)は、次の一手としてchunkの中での熱の確認を挙げます。

### Accepted

2026-10-07に参照機で、画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:c6700600e28029995f9fad5271f9395d21d703f2d640372d825e50250f6b8fd9`、3台で同じ）で：

- TP=2とTP=3：decode検査は基準のtoken idと文字列を出し、countの受理長は3.961と4.024。`bench --kinds edit` は両TPで2.2.0の返答。画像の検査はすべて合格。NLLの組は基準の値（TP=2 2.5474／2.9257／1.3184／0.6250、TP=3 2.5313／2.9001／1.3101／0.6237）。
- TP=3：1,035,295 tokenの3か所の合言葉が3/3、最初のtokenまで1,440.6 s（うち熱の待ち350.3 s）。ACPIの最高は92.6 °Cで、94 °Cを読んだ機はありません。
- 1M tokenでのtool gate：上のとおり。
- エンジン自身の試験：briefの一式は1,427 passed、小さなモデルのビットの照合は2.2.0と同じです。

## 2.2.0 — 2026-10-06

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.2.0` の `440e631345dd4a1a6762741a73522475df9782ad`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.1.4のエンジンに、tokenを変えないdecodeの改善を足しました（[決定の記録](docs/decisions.ja.md#decode)）：
  - **copy drafts**（`TF_GLM_COPY_DRAFTS`）：返答の末尾のtokenが前に出ていれば、続くtokenをMTPのheadより先にdraftにし、他のdraftと同じく検証します。MiaAI-Labのpatch 0007と0032の前半に倣いました。moduleを丸ごと返す編集は+34%（TP=2で43.0 → 57.6 tok/s）、countは+3.6%、他の負荷は±0.3%以内。
  - **KDAのdecodeの窓を3 kernelの経路で**（`TF_GLM_KDA_DECODE_WIDE`）。MiaAI-Labのpatch 0016cに倣いました。decode +0.6%。
  - **BF16のdecodeの行列積に形ごとのタイル**（`TF_GLM_B16_DECODE_TABLE`）。Kの切れ端を固定の64幅で数えるので、タイルは和の順を変えません。TP=2でdecode +0.9%。
  - **latentの経路で読まれないDSAのkey・value行の複製を作らない**：TP=2でrankあたり192 MiB空きます。
  - どの切り替えも既定は有効で、`0` で切ってもtokenは同じです。rankごとに違う値を渡すと起動を断ります（[設定](README.ja.md#設定)）。

### Added

- `python -m glm53_tf bench --kinds edit`：moduleを名前を挙げた3か所の編集付きで丸ごと返させる負荷。copy draftsが効く負荷です（[ベンチマークの方法](docs/benchmarks.ja.md)）。

### Documentation

- READMEはエンジンをこの系列のforkとして扱います。上流はPython版のエンジンを凍結し（TensorFoldのissue #286）、2026-10-06にこの系列のissueとpull requestのすべてに返事しました（[TensorFoldの他のレシピ](README.ja.md#tensorfoldの他のレシピ)）。[Next Action](README.ja.md#next-action)は、Zig版への移植、Python版の0.6.xの続き、pull request #243をリリースのbranchへ取り込むこと、lossyなcacheの問い（#309、#401）、熱の帯を挙げます。
- [検証](docs/validation.ja.md)は2.2.0の受理長と編集の返答を載せ、熱の判定を熱の見張りの規則（94 °C以上が2回続く）で書きます。READMEの応答の欄にcopy draftsの数を足しました。

### Accepted

2026-10-06に参照機で、画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:f2c992676bc399367fd4f23f9d60e8146a05d4e9bd6811ba1ea6e484322b18bd`、3台で同じ）で：

- TP=2とTP=3：decode検査は基準のtoken idと文字列を出し、countの受理長は3.961と4.024。画像の検査はすべて合格。`bench --kinds edit` は両TPで同じ返答。
- TP=3：1,035,295 tokenの3か所の合言葉が3/3、最初のtokenまで1,154.3 s（うち熱の待ち64.1 s）。終わり近くで1台が1回だけ1秒、94.3 °Cを読みました。熱の見張りは止めず、待ちを除いたprefillは2.0.0と同じでした。
- 各切り替えのA/B：TP=2で10回の起動。全部有効の起動のあいだに一つだけ切った起動を挟み、どの起動も2.1.4のtoken idを出しました。
- エンジン自身の試験：briefの一式は1,410 passed、小さなモデルのビットの照合は2.1.4と同じです。

## 2.1.9 — 2026-10-06

### Changed

- decode検査はTensorFoldだけを読みます。vLLMの `/metrics` のcounterを読むことも、エンジンを見分けるために `/metrics` を読むこともやめました。受理長は応答の `tensorfold` blockから取り、保持promptの追い出しは毎回のsampleの前に行い、要約からTensorFoldでは空だった `spec_before` と `spec_after` を外しました。1.x系は自分のvLLM用の検査を持ちます。

### Documentation

- [SETUPの手順8](SETUP.ja.md#8-受け入れ)は、AGENTS.mdのとおり、受け入れの範囲と証拠の所在を書きます。クロックの上限の一文はREADMEだけに置きます。[検証](docs/validation.ja.md#tool引数ゲート越しのtool)は、tool-eval-benchの値が開発ビルドでの基準であることと、各リリースの値はREADMEにあることを書きます。READMEのAPIの一覧は、decode検査が `/metrics` を読むとは書きません。

### Tests

- decode検査の試験から3件のvLLMの場合を外し、GETがあれば落ちるようにし、要約のキーとblockの無い応答を確かめます。

imageは変わらず、2.1.4のままです。

## 2.1.8 — 2026-10-06

### Documentation

- [検証](docs/validation.ja.md#画像入力)に画像の検査を、その合格の条件（どれにも正しく答え、動画を400で拒む）とともに置きました。READMEの行は検査を並べる代わりにそこを指します。検証は受理長を残し、各リリースの速さはリンクで示します。
- READMEの状態は、受け入れたimageを変更履歴の節で示し、書き漏らしていた今のimage（2.1.4）を挙げます。制約は「複数の画像を1回でencodeする」と書かなくなり（2.1.1から1枚ごとに呼びます）、メモリの注記は配信の既定を指します。熱の注記と[ベンチマークの方法](docs/benchmarks.ja.md)は、ホストが熱くなるほどprefillが遅くなるとは書かなくなりました。約7.5%違う2つの速さは熱では説明できません（[検証](docs/validation.ja.md#prefillとdecodeの速さ)）。2.1.0のprefillの行は1回目（1,221.5 tok/s）も示します。エンジンの説明に#421を、設定の表にTP=3のrankのファイルの `NCCL_NET_PLUGIN=none` を足しました。

### Tests

- ページのbuild・inspect・containerの作成のコマンドにあるimageのtagはDockerfileのものと同じで、READMEの状態とリリースの測定値はそのimageの版を挙げることを確かめます。メモリの見張りの下限は `hostwatch.sh` から引用していることを確かめます。

imageは変わらず、2.1.4のままです。

## 2.1.7 — 2026-10-06

### Documentation

- [判断](docs/decisions.ja.md)：熱の帯の行は「`serve.sh` が仮置きとしている」と書かなくなりました（2.0.7で外れています）。画像入力なしの2.0.0の行は、それを再開した行を指します。rankのファイルの例は、値に日付を付けなくなりました。[リポジトリのREADME](../README.ja.md)は、この系の入力に画像を挙げます。`decode-check` と `score-nll` は、1.x系の道具と今も共有しているものを書きます。

### Tests

- 公開監査は、日本語の頁が英語の頁と同じ見出し・表の行・コードブロックを持つことを確かめます。この系が持つ1.x系の `download`・`io`・`verify_download` とtool gateのcheck・repairの写しは、package名だけ違うことを確かめます。CIの必須jobがfilelockを入れるので、この系のダウンロードのロックのテストもそこで走ります。

imageは変わらず、2.1.4のままです。

## 2.1.6 — 2026-10-06

### Fixed

- [ホストの道具](../host/README.ja.md)の `install.sh` が、telemetryの記録係を再起動するようになりました。入れ直しでも新しいプログラムで動きます。これまでは `enable --now` が動いている記録係を古いプログラムのまま残し、2.1.5のカウンタは手で `systemctl restart gb10-telemetry` するまで出ませんでした。記録の最後の1行は、いちばん新しい日のファイルから読むようになりました。記録が2日分以上あると、すべてのファイルにかけた `tail -1` がスクリプトを止め、`installed for <user>` まで届きませんでした。2.1.5を入れ直して記録係を手で再起動したホストは、何もしなくてかまいません。

## 2.1.5 — 2026-10-06

### Added

- `python -m glm53_tf bench`：[ベンチマークの方法](docs/benchmarks.ja.md)のprefillとdecodeの速さ（新しいnonceを付けた38,960 tokenのprompt、続いて短い固定promptの後に512 token）。要求ごとに、応答の `prefill_s`・`heat_wait_s`・`cached` を含むJSONを1行出し、最後に中央値の要約を出します。
- `python -m glm53_tf long-input`：[ベンチマークの方法](docs/benchmarks.ja.md)の長文。帳簿の真ん中に合言葉を1つ、または先頭から20分の1・真ん中・末尾から20分の1に3つ置きます。長さは行数で指定するか、エンジンの `/tokenize` でtoken数に合わせます。合言葉が欠けると終了コード1です。
- [ホストのtelemetry](../host/README.ja.md)が、GPUのclock eventの累積カウンタ（`event_counters_us`：SW power cap、sync boost、SWとHWの熱による減速、HWの電力ブレーキ）を記録します。GB10では電力の上限とメモリのクロックがN/Aで、標本の合間に立っては消えるSW power capはこのカウンタにしか出ません。既存の欄の名前と順序は変えていません。取り込むにはホストの道具を入れ直します。

### Documentation

- [検証](docs/validation.ja.md)：2.1.4のTP=2で、2回の起動で冷却の待ちの後に1本ずつ流した38,960 tokenのprompt 22本は、すべて2つの速さの速い側でした。SW power capのカウンタはそのどの間も増えず、増えるのはengineが動いていない間だけでした。原因は未解決のままです。
- [ベンチマークの方法](docs/benchmarks.ja.md)は、リポジトリの外の台本ではなく2つのコマンドを示します。

### Accepted

2026-10-06に参照機の対で、TP=2・2.1.4のimage（変更なし）で：`bench` は38,961 tokenのpromptを1,322.0 tok/sで読み、512 tokenを35.88 tok/sでdecodeしました。`long-input` は3つの合言葉を59,976 tokenに合わせた長文と、1つの合言葉を800行に置いた長文の両方で、応答がすべての合言葉を含みました。新しいtelemetryの欄は、rank 0のホストで整数を読みました。

## 2.1.4 — 2026-10-06

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.1.4` の `a265436de869bd596b20a915758de0cc829fb5a0`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.1.1のエンジンに、TensorFoldのpull request #421（m-naoki-m）を上流のmergeより先に取り込みました。`_take_over` は、残す保持promptを決めてから写すようになりました。長い会話の後に新しい会話が来ても、他の保持promptを写しては捨てることがなくなります（issue #420の測定ではrankあたり約15 GiB）。pull requestの試験は2.1.1のエンジンで6本中3本が落ち、このエンジンでは通ります。上流の試験2本の作り物のsnapshotには、本物が持つ `drafter_rows` の欄を足しました。

### Documentation

- [運用](docs/operations.ja.md#起動の結果)：新しいimageや別のエンジンが重みを読んだ直後に、起動が窓を断るときと、その対処（ページキャッシュ）。

### Accepted

2026-10-06に参照機の対で、TP=2・画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:257c69ba7c8586bd8ce5f158e9cf87af6365a78e2b7baa00338d1ac0c0d4a717`、3台で同じ）で測りました：

- decode検査は2.1.1のtoken idと文字列を出し、画像の検査はすべて合格しました。
- issue #420の筋書き：11 turnで247,330 tokenまで伸ばした会話の後に、頭を共有しない会話を送りました。新しい会話の間も `MemAvailable` はrank 0で11〜12 GiB、rank 1で12〜15 GiBのままで、最初の要求は1.4秒で答えました。
- 200,000×20の画像（vLLM #59126のもの）と114,000×28の画像は400（decodeした画素数の上限）で断られ、エンジンは配信を続けました。
- エンジン自身の試験：briefの一式は1,263 passed、小さなモデルのビットの照合は2.1.1と同じです。

## 2.1.3 — 2026-10-06

### Added

- decode検査と `score-nll` は、走らせる側で `TENSORFOLD_API_KEY` が設定されていればサーバーのAPI keyを送り（`Authorization: Bearer`）、無ければ何も送りません。rank 0のrankのファイルの `TENSORFOLD_API_KEY` の行でkeyを付けて起動したエンジンは、keyの無い要求をすべて拒みます（`/metrics` も）。loopbackの外でkey付きで配信する方法は[安全](README.ja.md#はじめ方)の注意に書き、rank 0の例のファイルにその行をコメントで入れました。

### Documentation

- [検証](docs/validation.ja.md#prefillとdecodeの速さ)は2.1.2の記述を直しました。長いpromptは、同じクロック・温度のまま約7.5%離れた2つの速さのどちらかで走り、3回続けると2つの起動では落ちず、1つでは落ちました。熱では説明できず、原因は分かっていません。起動後の最初の長いpromptは遅い、という記述は取り下げます（ある起動では速かった）。[決定](docs/decisions.ja.md)にTP=2の `split` と `gather` の比較を足しました：2つの速さのどちらでも `split` が約5%速く、tokenは同じです。
- [手順書](SETUP.ja.md#3-image)：imageのtagは、imageに写るファイルを最後に変えた版の名前で、文書やホスト側の道具だけの版ではそのままです。
- [CONTRIBUTING](../CONTRIBUTING.ja.md)：CUDAか固定のvLLMのimageが要る1.x系のテストは、GPUのホストでだけ走ります。

### Accepted

2026-10-06に参照機の対で、TP=2、2.1.1のimage（変わらず）、rank 0のrankのファイルにkeyを置いて：keyなしの `/health` は200、`/v1/models` と `/metrics` はkeyなしと違うkeyで401、正しいkeyで200。keyを渡したdecode検査は2.1.1のtoken idと文字列を出し、keyなしでは401で止まりました。rank 0のserveと記憶の見張りのlog、検査のlogにkeyは出ていません。

## 2.1.2 — 2026-10-05

### Documentation

- [検証](docs/validation.ja.md#prefillとdecodeの速さ)は、続けて流すとprefillが遅くなるのでホストを冷ます、とは書かなくなりました。2.1.1では、38,960 tokenのprefillを冷まさずに3回続けても、TP=2・TP=3とも速さは落ちず、クロックとCPUの周波数は変わらず、熱の待ちにも達しませんでした。引いていたTP=3の1,670から1,540 tok/sへの低下（2.0.0の受け入れの頃の観測）は再び出ませんでした。起動後の最初の長いpromptは遅いので、測る前に1本流すことも書きました。

image・スクリプト・配信の既定は変わらないので、2.1.1のimageと受け入れがそのまま有効です。

## 2.1.1 — 2026-10-05

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.1.1` の `1a3fb1789830f4c336179eae21129f21c5abae0f`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.1.0のエンジンに下の直しを足したものです。

### Fixed

- 複数の画像を持つ要求では、画像のtowerを1回だけ呼んでまとめてencodeしていました。そのため、ある画像の特徴量が同じ呼び出しの他の画像によって変わりました（実物のtowerで、448×448の画像を896×672の画像と並べると、どちらの順でも448×448の側のビットが変わりました）。今は1枚ごとにtowerを呼ぶので、要求に他の何が入っていても画像の特徴量は同じです。

### Accepted

2026-10-05に参照機で、TP=2・画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:54cf0e5bc7fe56a218a91f704443285caa11f68f5389fa618ef577d7b9fcad67`、3台で同じ）で測りました（[測定値](README.ja.md#リリースでの測定値)）：

- decode検査は2.1.0のtoken id・文字列のhash・受理長を出しました。
- 画像の検査はすべて合格でした。同じ大きさの2枚の画像は、1枚ずつ聞いても2枚まとめて聞いても同じ数を読みました。
- 38,960 tokenのprefillを冷まさずに3回続けて、1,327.0・1,326.8・1,322.8 tok/sでした。その間、GPUのクロックは2,184 MHzのままでclock event reasonは無く、CPUの全コアは最大の周波数のままで、最も熱いACPIのzoneは56 °Cから88.5 °Cまで上がり、熱の待ちには達しませんでした。

## 2.1.0 — 2026-10-05

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.1.0` の `9a1c7cc9fd231c65ebf5bffaed421937303e0796`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.0.0の追加を上流のv0.6.5へ衝突なしで載せ直し、次を足しました：
  - **画像入力**。上流のpull request #194（rank 0でencodeし、特徴量を他のrankへ送る）を3 rankへ広げ、1枚の画像をcheckpointの上限8,000の視覚tokenまでにし、rank 0の作業域をtowerの実測から決めます（[採否](docs/decisions.ja.md#他で名前を挙げていないエンジンのcommit)）。
  - latentの経路が持つ `kv_b` の2つ目の写し（`latent.AbsorbW`・`AbsorbQ4`）を、重みのバイト数と起動時の見積もりに数えます。これまで漏れていました。
- 上流のv0.6.5でAPI key（`--api-key`・`--api-key-file`・`TENSORFOLD_API_KEY`）が入りました。この系列は設定しません（[はじめ方](README.ja.md#はじめ方)）。

### Serving defaults

- **画像入力を有効にし、rankのファイルで切り替えます**：例のファイルのとおり全rankで `VISION=1` なら `serve.sh` が `--vision` を渡し、`VISION=0` で無効になります。窓は変わりません。TP=2ではrank 0が1.05 GiBのtowerを持ち、他の会話の保持promptは既定の3 GiBのうち2.4 GiBになります（TP=3は3 GiBのまま）。
- **TP=2はNCCLを4 channelにし、rankのファイルにIBのtransportを書きます**（TP=3と同じ）。NCCLが自分で開く64本と比べ、decodeは+0.8〜1.0%、起動時の余地は約1.5 GiB増、prefillは0.4%以内でした。各rankの性能コアへの固定と、draftの深さの固定は測って採りませんでした（[採否](docs/decisions.ja.md)）。

### Fixed

- decode検査はstreamingのdeltaの欄を1つしか取っていませんでした。draftの1 roundの塊が推論を終えて本文を始めると推論の末尾を捨て（「200.」が「200」になる）、token idは同じでも文字列のhashがdraftの深さで動きました。今は両方を取ります。countとcodeは文字列の基準のhashが新しくなりました（[検証](docs/validation.ja.md#decode検査)）。token idは2.0.0のままです。

### Accepted

2026-10-05に参照機で、リリース候補のimage（linux/arm64 `sha256:d4d2014ca311841a5ff65c09d97a33abdf2c7db00ba4386dc7ecf7fd689cbb69`、3台で同じ）で測りました（[測定値](README.ja.md#リリースでの測定値)）：

- decode検査はTP=2とTP=3で、画像入力の無効・有効とも、2.0.0のtoken idと受理長を出しました。
- 画像入力を無効にしたTP=2のNLLの採点セットは2.0.0と全精度で同じで、38,960 tokenのprefillは1,221.5（1回目）・1,331.1・1,329.9 tok/sでした。
- 画像入力は両TPで、1枚、prompt 7,966 tokenの4:3の画像、2枚の順番、単色、toolの結果の画像、文字の質問、toolの往復に正しく答え、動画は400で拒みました。

2.0.0の他の結果はそのまま有効です。promptとdecodeの経路は同じtokenを出します。コマンドのtagは `glm53-tf:2.1.0` です。

## 2.0.10 — 2026-10-05

### Documentation

- [採否](docs/decisions.ja.md)は、2.x系がまだ取り上げていない1.x系の施策にLPAを加えました。1.x系の後段Prefill近似は長いprefillの結果を設計上変え、2.x系の基準のhashとNLLは厳密なprefillのものです。
- [QSFPネットワーク](../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)は、dummy interfaceの `glmhost` が例の名前であることを書きます。参照機のリングでは `tp3host0` で、この系列のTP=3のrankのファイルが `NCCL_SOCKET_IFNAME` に書く名前です。

image・台本・配信の既定値は変わらないので、2.0.7のimageと受け入れはそのまま有効です。

## 2.0.9 — 2026-10-05

### Tests

- tool引数ゲートの大きすぎる本文のテストは、0.3秒待つ代わりに、ゲートの処理のスレッドが全部終わるのを待ってから、上流に何も届いていないことを確かめます。0.5秒遅れて送る不具合を戻すと、このテストは落ちます。

### Changed

- CIは検査の道具を、1.x系のlockではなくcheckoutのルートの `requirements/dev.lock.txt`（Ruff。全系で一つの版）から入れます（[CONTRIBUTING](../CONTRIBUTING.ja.md)）。

image・台本・配信の既定値は変わらないので、2.0.7のimageと受け入れはそのまま有効です。

## 2.0.8 — 2026-10-05

### Documentation

- 1.x系との比較は、1.x系が冷却gateと熱の見張りで熱を扱うと書いていました。1.x系はエンジンの中で待たず、測定では要求の合間に冷却gateでホストを休ませました。1.x系で熱の見張りを使った記録はありません。
- clusterのファイルの `CHECKOUT` は各機上のこのリポジトリのルートで、1.x系の `--checkout` はその `v1/` を指します。設定の表にそう書きました。

### Tests

- `--wait` で一時停止中のdownloadを扱うテストは、確かめることを全部まとめた1本です。別の `test_transfer_state.py` は同じことを繰り返していました。

image・台本・配信の既定値は変わらないので、2.0.7のimageと受け入れはそのまま有効です（リポジトリの `.dockerignore` から、それ以上何も通していなかった行を外しました。build contextは同じです）。

## 2.0.7 — 2026-10-05

### Changed

- imageを作り直して受け入れ直しました。Dockerfileは、tag `26.07-py3` の代わりにdigestでNVIDIAのbaseを固定します（`nvcr.io/nvidia/pytorch@sha256:2140e699…`、2.0.0を受け入れたもの）。imageの中で変わったのは `THIRD_PARTY_NOTICES.md`（ライセンス整理の新しい置き場と、このimageもこのファイルを持つこと）と `serve.sh` のコメントの直しです。base・package・エンジンは層ごとに2.0.0と同じです。2026-10-05に作り直したimageを参照機で同値として受け入れました。TP=2とTP=3で[decode検査](docs/validation.ja.md#decode検査)が基準のhash・token id・受理長を出し、NLLの採点セットは2.0.0と全精度で一致しました。他の結果は2.0.0のものがそのまま当てはまります。コマンドのtagは `glm53-tf:2.0.7` です。
- ホストのツールを `v2/host/` からcheckoutのルートの[`host/`](../host/README.ja.md)へ移し、全系共通の[ホストの準備](../docs/hosts.ja.md)とfabricの文書と並べました。`python3 host/cool-gate`、`python3 host/thermal-watch`、`host/` から `sudo sh install.sh` です。
- clusterのファイルは、Gitが無視する `state/cluster.env` に置きます。手順はcheckoutのルートの `my-cluster.env` に置かせていて、そこはGitが無視しません。

### Added

- [運用](docs/operations.ja.md)：起動の終わり方、他のrankが待つ中で一つのrankが止まる場合、socketに落ちたNCCL、containerの作り直し、新しいimageへの移行、電源が落ちたホスト、1.x系へのホストの引き渡し。
- [採否](docs/decisions.ja.md)：2.x系が採ったもの・採らなかったもの（日付、測った効果、再び開く条件）、変更履歴が名指さないリリースbranchのcommit、2.x系でまだ評価していない1.x系の施策。
- [ベンチマークの方法](docs/benchmarks.ja.md)：リリースの測定値と検証の基準値の取り方。

### Documentation

- [手順書](SETUP.ja.md)の§6と§9に、`cluster.sh` の起動の終わり方（READY、全rankのlogの末尾つきのFAILED、15分でTIMEOUT）、logの場所、停止がrankごとに最大60秒待つことを書きました。READMEは `TF_GLM_CACHE_GIB` とNLLの検査が使うendpointを挙げ、prefillの行はTP=2の3本が1回の冷却の後に続けて流したものと書きます。

### Tests

- 文書が引く `serve.sh` の値、台本の既定値、ゲートのport、`TENSORFOLD_REF`、固定したbaseとrevisionを両言語で検査します。clusterのファイルは `state/` の下に置くこと、どの台本も構文が通ることも検査します。1.x系からの写しで落ちていた検査2つ（score-nllが送る本文、decode検査のtokenの記録をdecode-divergenceが読むこと）を戻しました。

## 2.0.6 — 2026-10-04

### Added

- 公開監査はこの系列も検査します：必須のファイル、変更履歴の両言語に節がある版、Apache-2.0のライセンス、`config/model.lock.json` のモデルのrevisionの固定。

### Documentation

- リリースの測定値は、未公開のcommitを名指しする代わりに、走らせたエンジンの版（リリース、その1つ前の表示の行だけが違う版、熱の待ちを入れる前の版）を書きます。熱の待ちが無いと[熱の見張り](../host/README.ja.md#長い運転の間)が94 °Cでエンジンを止めたことも、記録のとおり書きます。機が熱くなるとprefillが遅くなることは[検証](docs/validation.ja.md)に一度だけ書きます。比較の1.xの列は、1.x系のベンチマークの出所を名乗ります。

image・台本・配信の既定値は変わらないので、2.0.0のimageと受け入れはそのまま有効です。

## 2.0.5 — 2026-10-04

### Changed

- この系列は自分の道具を使います。1.x系の道具を `v1/` から動かす代わりに、`v2/` から [`glm53_tf`](README.ja.md#リポジトリの構成) を `python -m glm53_tf download | verify-download | tool-gate | decode-check | decode-divergence | score-nll` で動かします。中身は1.x系の写しで、引数も同じです。decode検査とtool引数ゲートの既定はこの系列のエンジン（`http://127.0.0.1:8095`、モデル `glm-tf`。ゲートは8896で待ち受け）です。モデルの固定は `config/model.lock.json`、NLL採点セットは `config/nll_set.json`（1.x系のものとバイト単位で同じ）、Hugging Faceのclientのlockは `requirements/huggingface.lock.txt` です。`scripts/serve.sh` のrevisionとセットのhashがずれないことはテストで守ります。新しいコマンドは[セットアップ手順書](SETUP.ja.md)と[検証](docs/validation.ja.md)にあります。image・台本・配信の既定値は変わらないので、2.0.0のimageと受け入れはそのまま有効です。

### Documentation

- [`host/`](../host/README.ja.md)に、参照機でsudoなしに確かめたこと（記録係、`cool-gate` の両方の結果、container内で起こしたprocessを止める `thermal-watch`）と、`thermal-watch` はcontainerのPID 1を止められないことを書きました。
- リポジトリのREADMEは、各系列が自己完結していることと、ルートの `tools/` はリポジトリの公開監査とリリースノートだけだと書きます。

## 2.0.4 — 2026-10-04

### Fixed

- `host/gb10-telemetry` とホストの道具のテストは、UTCを `datetime.UTC` と書きます。Python 3.11以降でruffが求める書き方で、2.0.3のCIはここで止まっていました。他は変わりません。

## 2.0.3 — 2026-10-04

### Added

- [`host/`](../host/README.ja.md)：この系列の測定に使い、保守者の記録の中にだけあったホストの熱の道具です。GPUクロックの上限のunit、温度の記録係とそのunit・据え付け台本、`cool-gate`（長い要求の間にホストが冷めるのを待つ）、`thermal-watch`（94 °C以上が2回続くとエンジンを止める）。据え付け台本はserviceの利用者を引数に取ります。`thermal-watch` はこの系列のエンジンでだけ確かめました。CPUテストは `tests/` にあり、CIが回します。

### Documentation

- 1.x系との比較は、1.x系の公開したTP=3のdecode検査 51.00／30.10／39.48 tok/s を引きます。49.59／28.32／38.33は、どのテンプレートも設定しないprefillの上限512で走らせた値でした。1.x系のtool引数ゲートの結果はTP=2のもので、長さの違う走行を比べる行は1.x系の長さを書き、NLLの行は採点セットを名乗ります。
- 両系列に共通することは[リポジトリのREADME](../README.ja.md)へ移しました。1.x系が持つ事実（クロックの上限、ホストごとのcheckpointの大きさ、ホストのカーネル、ダウンロード、decode検査、再現性スイッチ）は書き直さずに指します。[検証](docs/validation.ja.md)は基準値を持ち、decode検査のpromptを `decode_check.py` と同じに書きます。
- 例のclusterのファイルは、`CHECKOUT` にcloneの既定のディレクトリを書きます。

image・台本・配信の既定値は変わらないので、2.0.0のimageと受け入れはそのまま有効です。

## 2.0.2 — 2026-10-04

### Documentation

- [Next Action](README.ja.md#next-action)。2026-10-04の上流とレシピの確認から：
  - 上流は0.6.6に向けて、GLMの両rankの停止として、リリースのbranchが持つ#301ではなくpull request #320を審査しています。どちらかがmergeされたら#301を置き換えます。この系列のissue #308・#309・#310・#339とpull request #333は、上流の0.6.6の一覧にありません。
  - 上流のv0.6.5に追従すると、エンジンでAPI keyが使えるようになります。[はじめ方](README.ja.md#はじめ方)の安全の注意は、認証が無いのはv0.6.4のことだと書くようにしました。
  - 上流の0.6.6は、この系列に効く三つの修正（tool呼び出しのmarkupが本文に漏れる件、同じtokenを延々繰り返すのを止めるガード、開けるファイル数の上限）のために見守ります。
  - 画像入力は、自前で配線する前に上流のpull request #194（GLM-5.3-FlashのCUDAの2 rankでの画像入力）を読みます。
  - 1.x系のNext Actionにある機体のCPU周波数の検査は、この系列の数字にも当てはまります。

## 2.0.1 — 2026-10-04

### Documentation

- [README](README.ja.md)に、初めて読む人が要る節を足しました。既存の節は変えていません：受け入れの範囲を書いた要約、必要な環境、TP=2のはじめ方（`curl` の要求と、エンジンに認証が無いことの注意。rank 0とtool引数ゲートはloopbackだけで待ち受けます）、rank・cluster・containerのファイルの設定を一つにまとめた表、受け入れで使ったAPIと確かめていない経路、リポジトリの構成、ライセンスの早見表、免責事項、Next Action、ローカルデータ。英語版の見出しはtitle caseにしました。
- [TensorFoldの他のレシピ](README.ja.md#tensorfoldの他のレシピ)：GLM-5.3-FlashをTensorFoldで配信する公開レシピのリンクと、この系列が取り込んだものの正典になる表です。上流のTensorFold、MiaAI-LabのTensorFold版（patch 0038に倣ったFP8 latent KV、patch 0066と同じ規則のTP=3の分け方、上流のpull request #301）、jakejharris/jspark3 v2.0.1（何も取り込んでいません）。1.x系のレシピの表は、MiaAI-LabのTensorFold版についてここを指します（1.28.2）。

image・台本・配信の既定は変わっていないので、2.0.0のimageと受け入れはそのまま有効です。

## 2.0.0 — 2026-10-04

2.x系の最初のリリースです。1.x系と同じ固定のcheckpoint（`nvidia/GLM-5.3-Flash-NVFP4` の `423acf37583782c51c142d145aef733d72943d93`）を、vLLMに代えて[TensorFold](https://github.com/ashhart/TensorFold)で、2台のTP=2または3台のTP=3で配信します。1.x系は[`v1/`](../v1/README.ja.md)で続きます。

### Engine

- imageは[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold)のbranch `release/2.0.0` の `b44c2f197863f889659874e9be4b8e318768a828` からTensorFoldをbuildします（[`TENSORFOLD_REF`](docker/Dockerfile)）。上流のv0.6.4に、CUDAのGLM-5.3-Flash向けの次のものを足した版です。
  - **NVIDIAのNVFP4 checkpointを保存されたまま読む**（W4A16）：routed expertとdense MLPはNVFP4のblockから、attention・shared expert・headはBF16です（上流issue #308）。
  - **FP8 latent KV**（`TF_GLM_KV=fp8`）：DSAのlatent cacheとindexerのpool keyをe4m3の行で持ちます（上流issue #309）。
  - **TP=3**（`--tp 3`）：2 rankにも3 rankにも使う1つのshard plan。3で割れない大きさは不揃いの取り分にし、語彙のgatherは幅の違うshardをまたぎます（上流issue #310）。
  - **ビットを変えないprompt処理の高速化。**
    - promptのBF16 matmulはKの切れ端をregisterで足します（上流pull request #333）。
    - prompt chunkのrank間の交換を、行の切れ端ごとに2本目のstreamで回します。
    - 交換は正確なreduce-scatterで、各rankは自分の行だけを貼り合わせます（`split`。rank同士で送り合えるときの既定）。
    - indexerは1 programで16行を採点し、選択が読むpoolの列だけを採点し、top 512のために長い行を5回でなく3回読みます。
  - **止めた要求が1 roundのうちに全rankで終わる**：クライアントの切断やstop文字列のときです（上流pull request #301）。
  - **長いprefillが熱で待つ。** prompt chunkの前ごとに各rankが最も熱いthermal zoneを共有し、`TF_GLM_HEAT_HIGH` を超えたら、全rankが `TF_GLM_HEAT_LOW` 以下になるまでそろって待ちます。待ちはchunkの走る時刻を動かすだけで、ビットは変えません。待つたびに `[tensorfold] heat:` の行を出し、応答に `heat_wait_s` を載せます（上流issue #339）。

### Serving defaults

[`scripts/serve.sh`](scripts/serve.sh) が全rankに同じ値を設定します（[配信の既定](README.ja.md#配信の既定)）。

- FP8 latent KVと、checkpointのMTP headによる下書き（`--drafter none`）。
- 窓はTP=2で300,000 token（他の会話の保持promptに既定の3 GiBを残す）、TP=3では収まる最大（参照機のリングで1,048,576 token＝モデルの上限）。
- 要求が上限を指定しないときの応答は最大32,768 token。
- prefillの熱の待ちは92 °Cで待ち、88 °Cで再開します。参照機の熱の見張りは94 °Cでエンジンを止めます。待ちが無いと、TP=3の1M tokenのpromptは6分半でそこに達しました。

### Image and launch

- [`docker/Dockerfile`](docker/Dockerfile)：NVIDIAのPyTorch container 26.07に、測ったときの版のtransformers 5.18.0、xgrammar 0.2.8、Hugging Face hubのクライアントと、固定したcommitのエンジンを入れます。checkoutのルートからbuildします（[手順書](SETUP.ja.md#3-image)）。
- [`scripts/`](scripts/)：
  - `create_container.sh` と `build_ext.sh`：各機のcontainerと、エンジンのCUDA extension。
  - `serve.sh`：1つのrank。
  - `cluster.sh`：1台から全rankを起動・停止します（他のrankが先、rank 0が最後）。
  - `hostwatch.sh`：メモリの見張り。エンジンはcontainerの中でrootで動くので、containerを通して止めます。
- [`examples/`](examples/)：参照機のTP=2とTP=3のrankファイル（2 rail、GID 3、RoCE v2、subnetを見た経路選択、TP=3は4 channel）。`NCCL_DEBUG=INFO` で、NCCLが起動時に各接続の経路をログに出します。

### Accepted

2026-10-04に参照機で測りました（[測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md)）。decode checkと1M tokenのpromptは、リリースのimage（`glm53-tf:2.0.0`、linux/arm64のimage `sha256:3d06b02953398603580edcecef22c06c3c8ed0d9e3d1568d66f1bd0d1ae21b44`。`docker images` が示すIDはbuildの来歴も含み、buildしたcheckoutごとに変わります）か、その1つ前（表示の行の変更だけが違う）のimageで回しました。他の項目は、熱の待ちを入れる前のbranch `304109c` のimageで回しました。熱の待ちはprompt chunkの走る時刻しか変えません。

- decode checkはTP=2・TP=3とも参照のhashを出しました。熱の待ちが起きている最中も同じです。
- 下書きありの応答は逐次の応答と一致しました。
- teacher-forcedのNLLは開発buildの値と全精度で同じでした。
- TP=3では、熱の待ちを入れたまま1,036,859 tokenの中の合言葉3つを見つけました：最初のtokenまで1,264.8 s（うち待ち170.1 s）、最も熱い読みは92.8 °Cでした。
- tool-argument gate越しのtool-eval-bench：TP=2で93/100、TP=3で91/100、どちらもSafety Gateを通過しました。

# 決定（2.x）

[English](decisions.md) · [2.x系の概要](../README.ja.md) · [検証](validation.ja.md) · [ベンチマークの方法](benchmarks.ja.md)

2.x系のために何を試し、何を採り、何を採らなかったかを、日付、測った効果、決定を開き直す条件と一緒に並べます。1.x系の[施策台帳](../../v1/docs/optimization-catalog.ja.md)にあたる2.x系の頁です。効果は参照機でGPUクロックの上限の下、各決定をしたときの開発版で測りました。行にTP=3とない限り、対でのTP=2です。prefillは38,960 tokenのpromptを3回測った中央値です（[ベンチマークの方法](benchmarks.ja.md)）。リリースそのものの値は[リリースでの測定値](../README.ja.md#リリースでの測定値)に、基準値は[検証](validation.ja.md)にあります。「—」は、記録に決定を開き直す条件が無いことを示します。

## エンジン

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| vLLMの代わりにTensorFoldで配信する | 2026-10-02 | 厳密性がエンジンの契約である（draftした応答はserialと同じ、再開は最初からと同じ、結果はchunkの切り方によらない）。1.x系はvLLMのスイッチを入れて反復性を買っている（[1.x系との違い](../README.ja.md#1x系との違い)） | — |
| 上流のTensorFoldから始めてGLMに要るものだけを移植し、MiaAI-LabのTensorFoldのレシピの上には作らない | 2026-10-02 | そのFP8 latent KV（patch 0038）は先行するpatch約37本の上に乗っており、上流0.6.1へのdry runはほぼ全hunkが失敗したので、上流の上で書き直した（約600行） | — |
| 上流のリリースに追従し、衝突は上流の側を採る | 2026-10-03 | v0.6.2、v0.6.3、v0.6.4、続いてv0.6.5（2.1.0、衝突なし）。v0.6.4ではTP=3の交換を上流の通信のinterface（#219）の上に載せ直した。全rankでの停止は上流のpull request #301をそのまま取り込み、新しく書いていない | 上流がPython版のエンジンの0.6.xをもう一度出すか、Zig版のエンジンでGLMを配信する。上流はPython版を凍結し（issue #286）、#301・#320・#333をそれとともに閉じた（[Next Action](../README.ja.md#next-action)） |
| 配信のcontainerにCPUの集合を設定しない（`create_container.sh` は配置をkernelに任せる） | 2026-10-05 | 固定しないとエンジンのスレッドは高効率コアを含む20コアすべてで動きました。両rankを性能コアに固定しても（`docker update --cpuset-cpus 5-9,15-19`）、decodeとprefillの差は揺れの内でした（counting 41.35 → 41.36 tok/s、prefill 1,327 → 1,329 tok/s）。1.x系には固定が要ります（[CPU配置](../../v1/docs/benchmarks.ja.md#参照対でのcpu配置2026-09-26)） | 同じ設定で片方のrankのdecodeだけが遅い |
| 上流の#285・#294、patch 0080（書き直し）、TR3の名を2.5.0のエンジンに同乗させる | 2026-10-08 | 専用の版は切らず、次にエンジンのリリースのbranchを切るときに取り込んだ：#285（MiaAI-Lab。end tokenが `</tool_call>` より先に来たGLMのtool呼び出しを、全体がparseできれば送る）と#294（plotarmordev。起動時に開けるファイル数の上限を上げる）はそのまま、作者もそのまま。MiaAI-Labのpatch 0080は書き直し（会話に引用された画像の印は本物の画像の隣で文字のまま。codeは写していない）、エンジンの表示に挙げた。EXL3/TR3のcheckpointの名を `brandonmusic/GLM-5.3-Flash-tr3-4bpw` にし、取り下げられたMia-AiLabの再掲は一覧に残した。既定の経路（画像なし・toolなし）のtokenは変わらない。2.5.0の受け入れは[リリースでの測定値](../README.ja.md#リリースでの測定値)にある | — |
| #294の時機に左右される試験をforkで直す | 2026-10-08 | 上流の試験は時機によって落ちることがあった：試験のserverが受けたsocketをworkerのthreadで閉じ、それが試験のsqueezeと次のacceptの間に入ることがあった。forkの試験はその場で閉じる | — |
| loop guardを入れ、既定では無効にする（`TF_GLM_LOOP_GUARD`）：`1` にすると、rank 0は、16 token以下の完全な周期が256 token続くか、直近256 tokenの半分を一つのtokenが占めるかで潰れた思考のblockを、思考の予算が閉じるのと同じ形で閉じ、応答の `tensorfold` blockに `loop_guard` として数える。MiaAI-Labのpatch 0091を取り込み、試験は書き直した | 2026-10-09 | 無効ならgateは作られず、どの要求も変わらない。配信の負荷でまだ測っていないので無効のままにする | 配信の負荷で測る |
| serverは、全文のあいだGILを握る `encode` の代わりに、PythonのGILを放すtokenizerのbatchの呼び出し（`encode_batch_fast`）でtokenizeする。MiaAI-Labのpatch 0099に倣う | 2026-10-11 | 長い要求のtokenizeが、取り消しのpollを含むserverの他のthreadを止めなくなる。GLMのtokenizerは1,106の文（最長2.1M token）で、special tokenの有無とも同じidを出した。画像のpromptは画像のprocessorでtokenizeするので変わらない | — |
| imageをNVIDIAのPyTorch container 26.09-py3（PyTorch 2.14.0a0、CUDA 13.4）に載せ、Tritonは2.0.0〜2.9.0と同じ3.7.1に固定する | 2026-10-15 | 新しいbaseに3.7.1で、小さなmodelのbit検査（BF16とFP8 KV）は2.9.0の48のhashと同じ、briefの試験は1,544通過（42 skip）。PyTorch・CUDA・`nvcc`・baseの低精度の既定値はどのbitも変えなかった。続く受け入れの窓も2.9.0と同じ結果（[変更履歴](../CHANGELOG.ja.md)） | PyTorchかCUDAがbitを変えるbase |
| 26.09-py3が入れるTriton 3.8.0 | 採らない 2026-10-15 | エンジンの和が変わる。2.9.0のimageでTritonだけを3.8.0にすると、bit検査は48の状態のうち26で別のhash（MTPの層の状態はほぼ全部の組、KVの1層目とindexのcacheは大半、一部のrecurrentとconvの状態）、tokenは1つ違った（FP8 KV・NVFP4のserialのgreedyの応答の8個目、102→324）。許容の幅で見るbriefの試験は通った。エンジンは3.8.0で挙動が変わったもの（`dot_scaled`・`fdiv`・block pointer・tensor descriptor）を使わず、`tl.dot` の累積はすべてfp32、`ptxas` も同じなので、違いはcompilerが出すPTXにある。どのkernelかは絞っていない | bitが変わる版として、NLLの組・tool-eval・速さを3.7.1と比べて採るとき |

## 精度とメモリ

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| FP8のlatent KV（`TF_GLM_KV=fp8`）、行ごとに2のべき乗のscale | 2026-10-02 | 1 tokenのKVはlatent cacheを持つ12層（DSAの11層とMTPの層）でrankあたり12,912 byte、BF16のKVでは19,200（−33%）。TP=2の窓はBF16のKVで344,820 token、その版のFP8で約490K。draftした応答はserialと同じまま。BF16のKVに対しては非可逆（[制限](../README.ja.md#制限)）。checkpointはFP8のKVを宣言するがKVのscaleを持たない（vLLMは1.0を使う）ので、行ごとのscaleにした。同じpatchのindexerのring（keyとgateをringに持つ）は移植していない。BF16の既定の配置を変えるため | rankあたりの窓をもっと要する。次の一手がring |
| routed expertとdense MLPはW4A16、`--precision checkpoint` は拒む | 2026-10-02 | 上流のgrouped NVFP4 expert kernelはBF16の行しか受けず、input scaleの経路が無い。固定のcheckpointで活性のscaleを使って変わるのはdenseの0〜2層だけ | — |
| MTP層のrouted expertをdraft専用にNVFP4へ量子化する | 2026-10-02 | checkpointではBF16（13.5 GiB）。TP=2でrankあたり6.75 GiBが1.90 GiBになる。draftしたtokenは全部フルモデルが検証するので、応答は変わらない | — |
| KDAのconvの係数を保存されたとおりfp32に保つ | 2026-10-02 | 以前の版はkernelのためにBF16へ丸めていた。kernelはfp32を直接読むようになり、1.x系のvLLMと同じくfp32のまま。係数がBF16のMLXとEXL3のcheckpointは、tokenもcacheも以前と同じ（12通り中12） | — |
| TP=3の分担は単位の境界で切り、余りを若いrankへ | 2026-10-03 | 頭22/21/21、MoEの幅704/704/640、語彙51,648/51,648/51,584。ゼロの行を作らず、重みに手を加えない。2 rankではすべてのテンソルで半分割とbyte単位で一致。重みの見積もりはrank 0/1/2で63.04/62.87/57.70 GiB | — |
| 公開したAXLの重みには対応しない | 2026-10-04 | 容量のためには要らない：固定の重みでTP=2は1.x系より大きな窓を持つ。TP=3で効くのはprefillのうち長さで伸びない部分だけで、最大でchunkあたり12 ms、その部分の約1%（2026-10-03） | 2.4.0で再開（次の行） |
| 公開したAXLの重みをそのテンソルのとおりに読み、任意で使えるようにする。既定は固定のcheckpointのまま（rankのファイルの `CHECKPOINT`） | 2026-10-07 | エンジンはテンソルごとに経路を選び、切り替えは無い：`weight_scale` を持つprojectionはNVFP4の線形層（decodeのlaneの行列積とpromptのGEMM）として読み、`kv_b` はlatentの経路のためにfp32へ戻し、rankの起動時の照合にcheckpointの種類が入る。固定のcheckpointではビットは変わらない（小さなモデルのビットの照合、decode検査のtoken id、NLL採点セットが2.3.0と同じ）。TP=2でAXLは固定の重みよりdecode検査と編集が速く、NLLはどの領域でも高く、起動の見積もりは小さい（[リリースでの測定値](../README.ja.md#リリースでの測定値)の2.4.0） | — |

## 窓・上限・範囲

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| TP=2の窓は300,000 token、`--context 0` の567,255にしない | 2026-10-04 | 他の会話の保持promptに既定の3 GiBを残す（[300,000の理由](../README.ja.md#配信の既定)） | 配備が別の `--context` を渡す |
| TP=3の窓は収まる最大（`--context 0`） | 2026-10-03から使い、2026-10-04に配布の既定 | 参照機のリングで1,048,576 token、モデルの上限 | — |
| 要求が上限を指定しないときの応答は最大32,768 token | 2026-10-03 | — | — |
| 要求が推論のeffortを指定しないときは `high`（rank 0の `--reasoning-effort`、そのファイルの `REASONING_EFFORT`） | 2026-10-09 | 固定のchat templateは指定のないeffortを `max` として描き、`max` では思考がほぼ際限なく続いて応答の上限の大半を使う。1.x系はそうした要求を `high` で処理している（[effortをhighにする理由](../README.ja.md#配信の既定)）。検査は自分でeffortを指定するので、その基準値はそのまま | — |
| 4,096行のprefillのchunk | 2026-10-02に不採用 | 同じ版の2,048行の1,169.9 tok/sに対し1,076.1、窓は約490Kから約405Kへ縮む。ビットは同じだった | — |
| 一度に1系列 | 2026-10-02 | エンジンのCUDAの経路はGLMの要求を一度に一つずつdecodeする | 上流が凍結とともに閉じた#243を、この系列がリリースのbranchへ取り込む（[Next Action](../README.ja.md#next-action)） |
| 2.0.0では画像入力なし | 2026-10-04 | エンジンはCUDAのGLMで画像を拒む | 2.1.0で#194により再開（次の行） |
| 画像入力は上流のpull request #194を3 rankへ広げたもの。既定で有効（例のrankのファイルは `VISION=1`） | 2026-10-05 | #194はrank 0でencodeして特徴量を送り、3 rankではその集めの幅を広げるだけで済みました。2.1.0の受け入れでは両TPで、1枚、prompt 7,966 tokenの4:3の画像、2枚の順番、単色、toolの結果の画像を読み、有効にしても画像なしのtoken idは2.0.0のままでした。窓は変わりません。TP=2では1.05 GiBのtowerの分、保持promptは3 GiBのうち2.4 GiBになり、それを承知で画像を既定にしました | 上流が#194をmergeする。TP=2の保持promptの2.4 GiBが長い会話で足りないと分かる |

## draft

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| checkpointのMTP headでdraftする（`--drafter none`）、DFlash2は使わない | 2026-10-04 | 明示する：エンジンの `--drafter auto` は、DFlash2の重みがcacheにあるとTP=2ではそれを使い、TP=3では拒む（2 rankにしか分けられない）。1.x系がDFlash2を使わない理由は、その重みの条件 | — |
| draftの深さはエンジンの方針（`auto`）に任せ、`--mtp-drafts` で固定しない | 2026-10-05 | 深さ4と5の固定をautoと比べたdecode：countingは+8%と+14%、proseは−15%と−20%、codeは−2%。温度1.0でもautoが上でした（proseで24.7対深さ4の20.9 tok/s）。token idは温度0でも1.0でも、どの深さでもserialの返事でも同じでした。autoが勝つ理由：各roundはdraftを1回のforwardでまとめて検証し、最初に外れたところまでを確定します。検証する行はどれも時間がかかります。autoはdraftを最大3つにし、温度0ではMTPのheadの次のdraftの確率が0.35を下回ったところで鎖を止め、標本化では直近の受理率に応じて深さを1〜3で動かします。固定の深さは毎roundN個をdraftするので、外れやすいproseでは捨てる行の検証に時間を払い、3つがほぼ必ず当たるcountingでは深いほど得をします（エンジンが起動時に測るコストはMTPとDFlash2の選択に使い、この深さには使いません） | ほぼ全部が当たる文のために、autoの上限3を上げられるようになったとき |

## fabric

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| リンクごとに2本のrail | 2026-10-02（TP=2）、2026-10-03（TP=3） | TP=2のprefillは同じ版で+4%（2本のrailの値が[検証](validation.ja.md#prefillとdecodeの速さ)のTP=2の基準）、TP=3 1,225.1 → 1,384.7 tok/s（+13%）。decodeは変わらず、decode検査のhashはどちらも同じ | — |
| TP=3：NCCLのchannel 4本、NCCL自身のIBの経路（`NCCL_NET_PLUGIN=none`）、subnet-aware routing | 2026-10-03 | 2本目のrailで8 MiBの片が1,530から約900 µsになった（channelが2・4・8・64本のどれでも同じ）。4本のchannelは32 MiBの塊を縮めた（1 railで9,236 → 5,072 µs、2 railで3,622 → 3,346）。decodeの大きさの交換（23〜51 µs）は誤差の範囲で動いた。`NCCL_CROSS_NIC` とimageの既定のnetwork pluginは何も変えなかった | — |
| TP=2：NCCLのchannelを4本にし、rankのファイルにTP=3と同じくIBのtransportを書く | 2026-10-05 | NCCLが自分で開く64本と比べ、decodeは+0.8〜1.0%、起動時の見積もりの余地は約1.5 GiB増、空きメモリの最低は1〜2 GiB上、prefillは0.4%以内でした（8本も同様）。`NCCL_NET=IB` などを書いても測った値は変わりません。もともと全接続がNET/IBでした | — |

## prefill

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| NVFP4のrouted expertのprompt用kernel（`b0fa0a5`） | 2026-10-02 | promptあたりのexpertの時間18.55 → 9.2秒、prefill 769.3 → 913.7 tok/s（+19%）。promptのビットはdecodeのkernelと違う（pairのビットは行とexpertだけで決まるので、chunkの切り方では変わらない）ため、decode検査のhashはここで一度変わった。基準のhashはこの後のもの。Kの全体をtensor coreの中で一つの和にする速い形（2.5〜2.6倍に対し2.64倍）は、down projectionの誤差が5倍で不採用 | — |
| promptのBF16のmatmulはKの片をregisterの中で足す（#333）。DSAのpromptのkernelを多くのprogramへ | 2026-10-02 | 943.7 → 1,068.2 tok/s、同じビット | — |
| prompt chunkの交換を4つの行の片に分け、2本目のstreamで重ねる | 2026-10-02 | 1,068.2 → 1,150.7 tok/s。片が2と8では1,119.6と1,116.6 | — |
| KDAのpromptのstep kernelをblockあたり8 warpに | 2026-10-02 | 1,150.7 → 1,169.9 tok/s、同じビット | — |
| BF16のsplit-Kの部分和は短い窓のためだけに確保する | 2026-10-02 | `--context 0` の窓が約490Kから567,255 tokenに増えた。prefillは変わらない | — |
| prefillの交換の既定を `split` に（`TF_GLM_PREFILL_REDUCE`） | 2026-10-03 | TP=3、一続きの起動の中で：それまでの `gather`（1,394〜1,398 tok/s）に対し `scatter` +6.8%、`split` +19.6%。decode検査のhashもNLL採点セットも変わらない。rankどうしが送り合えるところで採り、それ以外は `gather`。TP=2（2026-10-06、2.1.1）では、promptの2つの速さのどちらでも `split` が `gather` より約5%速く（1,326対1,262 tok/s、1,228対1,171）、decode検査のtoken idと文字列は同じだった | — |
| indexerのpromptの仕事：programあたり16行、選択が読むpoolの列だけを採点、長い行の読みを5回から3回に | 2026-10-03 | 実のDSAの層で1 GPU、1M tokenでのchunkのtokenの選択が209.5 → 165.5 ms（−21%）、同じビット。上の交換の仕事と合わせ、200Kと500Kの実測に当てた1Mのprefillの見積もりは短くなった（[長い入力](validation.ja.md#長い入力)）。試して遅かったもの：histogramを採点に融合、11 bitで3 pass、persistent grid、2,048のblock | — |
| prompt chunkのpoolのscoreを、programあたり16行・1 blockでなく、1行・32 pool blockで計算する（`SCORE_LOOP`）。decodeの窓はprogramあたり1 blockのまま。MiaAI-Labのpatch 0086に倣い、この木のFP8のpool keyと採点する列に合わせて書き直した | 2026-10-09 | programあたり1 blockでは、blockごとに各行のindexのqueryとheadの重みを読み直していた。今は行のそれを32 blockのために一度だけ読み、各blockの計算は前と同じで、ビットも同じ。固定の重みのTP=3で、なしの起動3回とありの起動3回：熱の待ちを除いた約226K tokenのprefillが5.8〜5.9%短く、ありの起動はどれも、なしの起動のどれより速く、返答は同じ（[リリースでの測定値](../README.ja.md#リリースでの測定値)） | — |
| clientが去ったpromptは、埋めているchunkの後で止める：最後を除く各chunkの後に、どのrankもint32を1つall-gatherし、どれかが望めばそろって止まる（`TF_GLM_PROMPT_STOP`、既定で有効、すべてのrankで同じに）。MiaAI-Labのpatch 0109（branch `tp4`）に倣う | 2026-10-11 | これまでは、clientが去っても両rankがpromptを最後まで埋めていた。入れると、約70,000 tokenの切ったpromptから、rankは切ってTP=2で2.12秒、TP=3で1.04秒で次の要求に空いた（埋め切るには54.58秒と41.92秒）。止めないpromptのビットは同じで、投票はchunkごとにint32 1つのall-gather（[リリースでの測定値](../README.ja.md#リリースでの測定値)） | — |
| MiaAI-Labのpatch 0101（prompt chunkのtop-kのpoolを、標本で決めた床から各行を1回読んで選ぶ） | 2026-10-11に採らない | この木の見えるpoolの上限に合わせて書くとpoolもtieも同じだったが、この木の選択はすでに長い行を5回でなく約3回しか読まない。GPU 1台で512行のblockが226K tokenで1.52 → 1.06 ms、590Kで3.92 → 2.31 ms。32Kではかえって遅い（0.14 → 0.18 ms） | 400K tokenを越えるpromptをよく配るとき |
| ビットが変わるprefillの案 | 2026-10-02と03に不採用 | 行のblockの32頭を一つのGEMMで採点し頭の和を後に回す（採点が2倍速くなれば1Mのprefillで約240秒の短縮と見積もり）、FP8のtensor coreでの採点、chunked KDA（その漸化式は38,960 tokenのpromptで2.06秒で、得は多くて数%）、MiaAI-Labの1 passのsparse attention。どれも基準のhashとNLLの元のビットを変える、または変え得る | — |

## 熱

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| prefillはchunkの合間に92 °Cで待ち、88 °Cまで、全rankそろって | 2026-10-04 | 待ちが無いと、TP=3の1M tokenのpromptは6分半で熱の見張りの94 °Cに達した。待ちがあるとpromptは最後まで走った（[熱](../README.ja.md#リリースでの測定値)）。chunkごとに最高温度を交換する費用は38,960 tokenのprefillの約0.2%。92 °Cは停止の2 °C下（頂上付近の上がり方は1分に0.5〜1 °C、chunkは数秒）。88 °Cはprefillが速くなる前の1Mのprefillが保った88.8〜89.6 °Cの下 | 上流のZig版のエンジンがGLMを配信する。上流はそこでissue #339の設計に倣うと返事した（[Next Action](../README.ja.md#next-action)）。帯はrankのファイルで変えられる |
| 待ちは1 chunk先も見込む：chunkの前に、最高温度に直前のchunkの上がり幅を足した値を93 °C以内に保ち（`TF_GLM_HEAT_CEILING`）、待ちもその値に収まるまで解かない | 2026-10-07 | 1M tokenのpromptの終わり近くでは、chunkの合間の確認の後にchunk一つで約7 °C上がる：92 °Cでは1台が1回94.3 °Cを読んだ（2.2.0）。見込みありでは最も熱い機の最高が92.6 °C、TP=3のそのpromptの待ちは350.3 s（前は64.1 s）、待ちを除いたprefillは同じ。代わりに帯を86 °C／82 °Cに下げると最高93.0 °Cだが待ちは436.4 s、温まった機では38,960 tokenのpromptも待った | ホストが94 °Cを2回続けて読む、またはchunkの中での確認 |
| 待ちの作り | 2026-10-04 | 各chunkの前に1語を単独でgatherする（既存の交換には相乗りしない。その結果はhostが読まない）。熱の見張りと冷却gateと同じくACPIのzoneだけを読む（どの記録でもGPUは約9 °C低い）。待ちに上限を置かない（熱い部屋は要求を止め、熱の見張りが最後の守りのまま）。両方の帯を設定しない限り切れている（上流の既定は変わらない） | — |
| 1 chunk先の見込みは、休んだ後に区域の温度が戻る分をchunkの上昇と数える | 2026-10-15に判明 | 最高温度の区域は、GPUが休むと2秒で約15 °C下がり、負荷がかかると同じ速さで戻る。待ちの後や、promptの前の間の後に始まったchunkはその戻りの分も上がり、次のchunkの前の確かめはそれを負荷中の読みに足していた。暖かい午後、TP=2で38,960 tokenのpromptを2本続けると、2本目は最初のchunkの後のすべてのchunkの前で待った（19回、38秒）。続けて流したchunkの間の上昇は1 °C未満。2.9.1（2.9.0のエンジン）ではこのまま。直しは、続けて流したchunkの間の上昇でchunkを判断し、毎chunk待つべき所では待ちの長さを前と同じに保つ | 直しをエンジンのリリースに載せる前に測る：既定の帯で短い休みの後に流すprompt、1M tokenのprompt |

## decode

2026-10-06にTP=2で、一つのbuildを10回起動する一つの窓で測りました。全部有効の起動のあいだに、切り替えを一つだけ切った起動を挟んでいます。どの起動もdecode検査のtoken idは2.1.4と同じで、編集の返答も同じでした。数字は、その切り替えを切った2回と、両隣の全部有効の2回の平均の差です。

| 決定 | 日付 | 測った効果 | 見直すとき |
|---|---|---|---|
| copy drafts（`TF_GLM_COPY_DRAFTS`）：返答の末尾8 token（返答の中では16）が前のpromptか返答に出ていれば、続くtokenを1 roundに5つまで、外れた直後も同じくdraftにする（`MISS_MOST`、次の行）。検証は他のdraftと同じ。MiaAI-Labのpatch 0007と0032の前半に倣う | 2026-10-06 | `bench --kinds edit`（moduleを名前を挙げた3か所の編集付きで丸ごと返す）43.0 → 57.6 tok/s（+34%、251 roundのうち240がcopy）。decode検査のcountは+3.6%（受理長3.821 → 3.961）。prose・code・`bench` のdecode・prefillは±0.3%以内 | 外れの多い負荷で返答が遅くなる：外れた直後のdraftの数を測る（2026-10-07に測った。次の行） |
| 外れた後のcopy drafts：他のroundと同じく5つまで、減らさない（`MISS_MOST` 5、2.4.0より前は3） | 2026-10-07 | 専用の窓で、TP=2で3と5を交互に6回起動し、編集と、copyの外れが多い2つの負荷で測った：moduleを5組の改名つきで返す（3ではcopyしたdraftの10.1%が外れ）、そのmoduleのunittestを書く（41%）。5は3に対して、編集58.12対57.57 tok/s（+1.0%）、改名45.94対45.49（+1.0%）、unittest 39.12対39.14（−0.05%）、decode検査は±0.3%以内。どの起動もtoken idと返答は同じ。5で見込んだ費用（外れるたびに6行の窓で検証する）は、roundの数が減る分（改名で351 → 344）で相殺された。同じ日の先の窓では、編集だけで1と5が57.5と57.9 tok/s、3は57.4 | — |
| KDAのdecodeの窓を3 kernelの経路で（`TF_GLM_KDA_DECODE_WIDE`）。64行以上のprompt chunkは前からこの経路。MiaAI-Labのpatch 0016cに倣う | 2026-10-06 | decode +0.6%（`bench`）、decode検査+0.5%、prefillは変わらず。1 GPUでは経路そのものが1行で27%、8行で58%速い。1〜8行で融合kernelと同じビット（graphの有無とも） | — |
| BF16のdecodeの行列積に形ごとのタイル（`TF_GLM_B16_DECODE_TABLE`）：12の形は掃き取りで選んだタイル、他は64×4×3。Kの切れ端は固定の64幅で数えるので、タイルは和の順を決めない | 2026-10-06 | decode +0.9%（`bench`）、decode検査+0.9%、prefillは変わらず。TP=3では掃き取りの形を足しても1 stepの0.1〜0.2%。起動できた32のタイルすべてが、decodeの26の形・1〜16行で今のビットを出した | 別のGPUかエンジンのbuild：掃き取り直す（エンジンの `tools/bench_glm_b16_decode.py`） |
| latentの経路はDSAのkv_bをheadごとの写し一つだけで持つ。key・valueの行は `TF_GLM_LATENT=0` のときだけ作る | 2026-10-06 | TP=2でrankあたり192 MiB空く（TP=3は126〜132 MiB）。rank 0の起動の見積もり101.53 → 101.35 GiB | — |
| `bench --kinds decode` は `ignore_eos` ではなく、決まった数える要求で上限まで走らせる：`Write the numbers from 1 to 1000, one per line, and nothing else.`、最大512 token（2.5.0） | 2026-10-08 | 上の窓とは別に、TP=2で2.4.0のエンジンで。前の要求（`Count upward from one, one number per line.`、`ignore_eos`）は、それぞれのmodelが自分の終わりの後に作ったものを測っていたので、AXLのこの行は固定の重みより2%速いだけだった（[リリースでの測定値](../README.ja.md#リリースでの測定値)の2.4.0）。`ignore_eos` の無い数える要求2つを両方の重みで2回ずつ流すと、どちらも上限まで数え、この要求は両方の重みでtokenまで同じ返答を出し、もう一方は出さなかった。これでAXLは固定の重みより34%速く、decode検査と同じ向き。`finish_reason` が `length` でない行は途中で止まったもので、比べられない（[ベンチマークの方法](benchmarks.ja.md#prefillとdecodeの速さ)） | — |
| `top_k` 0 の要求はデバイスで抽選する：鍵つきのTritonのpassが、hostの規則と同じ位置ごとの一様乱数で全tokenを採点し、64 bitの鍵の上のradixのpassが各行の `top_p` の切れ目を見つけ、hostが最良を採点し直して、各rankの次点を越えるときだけ採る。抽選が決められないところ（`TMAX` を越える温度、近すぎる次点）では、hostの規則が前のとおり働く。sfxnz/TensorFold の `dsv41-recipe-engine4` の2つのcommit（Apache-2.0、閉じた上流 #408 の続き）を、そのまま取り込んだ | 2026-10-09 | これまで `top_k` 0 の行は、hostで語彙全体のnucleusに落ちていた。tokenはhostの規則のもの：小さなモデルのビットの照合とbriefの一式は2.7.0と同じ、固定の重みのTP=2で `top_k` 0 の要求は2.7.0のtokenを、2.7.0の12.64と8.82 tok/sに対して36.80と23.98（既定の `top_k` 20 とほぼ同じ）で出した（[リリースでの測定値](../README.ja.md#リリースでの測定値)）。当たるのは `top_k: 0` を明示するclientだけで、serverの既定は20 | — |

## 他で名前を挙げていないエンジンのcommit

リリースのbranchは、上流v0.6.5に[変更履歴](../CHANGELOG.ja.md)がまとめて挙げるcommitを足したものです。次は、試験とrecipeの文面を除き、そこで名前を挙げていないものです：

- `0c9e8da`：GLMの `/v1/completions` がtoken idのpromptを受け、vLLMの形の `prompt_logprobs` を返す。NLLの検査（`score-nll`）はこれを使う。指定の無い要求は変わらず、指定のある要求は保持promptから再開しない。
- `68a7e6a`：NVFP4のrouted expertのprompt用kernel（上）。
- `e190c7b`、`9c51f2f`：KDAのconvの係数をfp32で（上）。
- `aac7927`：DSAのpromptのabsorbとexpandを行のblockごとに、indexerのpoolの採点をprogramあたり4行に（MiaAI-Labのpatch 0009に倣う。のち16行、2.7.0から1行・32 block、上の表の行）。
- `2caf43c`：8 warpのKDAのpromptのstep kernel（上）。
- `bee087d`：BF16のsplit-Kの部分和は短い窓だけ（上）。
- `c35cfd9`：起動時の見積もりがdraft headの行を詰めた数で数え、3 rankのどれもちょうど見積もりどおりを読み込む。
- `c3ec51d`：上流の通信のinterfaceに任意の機能として `send_recv` を足す。`split` がこれを使う。
- `d5e65e2`：rankが選んだ層だけを読み込める。実のcheckpointでの試験のため。
- `9c78e43`・`aba0f21`・`4a41c21`・`d21c834`：2.1.0が上流のpull request #194（その7本、`4fcfb10` から `f9ee1d9`）に足したもの。1枚の画像をcheckpointの上限8,000の視覚tokenまで、rank 0の画像の作業域をtowerの実測から、3 rankの全rankへの画像の特徴量、hostとGPUがメモリを共有するGPUでの `--vision-offload` の拒否。
- `eaf06cc`・`1a3fb17`（2.1.1）：要求の画像を1枚ごとにtowerで呼びます。他の画像と1回の呼び出しでencodeすると特徴量が変わったためです。
- `e735c14`・`a265436`（2.1.4）：TensorFoldのpull request #421（m-naoki-m）。上流がPython版のエンジンを凍結したので、リリースのbranchが持ち続けます。`_take_over` は残す保持promptを決めてから写します（issue #420）。上流の試験2本の作り物のsnapshotに `drafter_rows` を足しました。
- `81bd22f`〜`440e631`（2.2.0）：上のdecodeの4項目と試験、タイルの掃き取りの道具、BF16のタイルの切り替えをrankの起動時の照合に入れたもの。

## 1.x系の施策で2.x系では未評価のもの

未決の項目です。1.x系は測りましたが、2.x系にはどちらの結果もありません。

- **MTU。** 1.x系は9000と1500を比べて1500のままにしました（[チャネル数](../../docs/nccl-validation.ja.md#チャネル数)）。2.x系では変えていません。
- **LPA。** 1.x系の後段Prefill近似は実験機能で、1.x系でもバッチ用のopt-inです（[LPA](../../v1/docs/lpa.ja.md)）。長いprefillの結果を設計上変えます。2.x系には対応するものが無く、基準のhashとNLLは厳密なprefillのものです。

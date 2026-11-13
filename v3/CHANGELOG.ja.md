# 変更履歴

[English](CHANGELOG.md)

正典は[英語版](CHANGELOG.md)です。GitHub Releaseの本文は英語版の各版の節から作られます。

TensorFoldのネイティブエンジンで配信する3.x系です。`v3.*` のタグは、見出しにリリースの日付が入った節をこのファイルから公開します。2.x系の履歴は[v2/CHANGELOG.ja.md](../v2/CHANGELOG.ja.md)にあります。

## 3.14.0 — 2026-11-13

imageの外の道具とその試験と文書の版です。imageのファイルは変わらず、3.12.0のままです（`glm53-tf3:3.12.0`、`sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`）。

### Image and launch

- `create_container.sh` は、containerに渡すRDMAデバイスを `RDMA_DEVICES` から取ります（無いか空なら、前と同じ `/dev/infiniband`）。そのpathに無いホストは断ります（[設定](docs/configuration.ja.md#container)）。

### Repository

- 試験は、dockerの代役に対して `create_container.sh` を回し、組む `docker run` の引数を全部見ます：RDMAデバイス、全てのGPU、hostのnetworkとIPC、`IPC_LOCK` と無制限のlocked memory、64 MiBの `/dev/shm`、`/hub` のcache（読むだけか書けるか）、`/work`、選んだ時のcore。

## 3.13.1 — 2026-11-13

imageの外の道具とその試験と文書の版です。imageのファイルは変わらず、3.12.0のままです（`glm53-tf3:3.12.0`、`sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`）。

### Documentation

- `bench` のhelpは、送るdecodeの要求だけを書きます。2.5.0より前の要求は、それを載せている[2.x系の変更履歴](../v2/CHANGELOG.ja.md)に任せます。
- [ライセンス整理](../docs/licensing.ja.md)の重みの節の見出しを、英語版のWeight noticesと同じく「重みの通知」にしました。節はMITのほかにNVIDIA Open Model Agreementも扱うからです。この節への頁の中・日本語のREADME・1.x系の日本語の変更履歴からのlinkも合わせました。

### Repository

- 根の試験は、系どうしが写し合う測りの文（decode-checkの課題、mojibakeのprompt、benchの文章、long-inputの台帳の行と合言葉）が、どの系でも同じであることを見ます。
- 配信の既定の試験の一つの注釈は、streamあたり4つより少ない保持するpromptの状態でengineが出す警告の置き場（GLMの `cuda_share.zig`）を名指します。前は、engineに無い関数の名を書いていました。

## 3.13.0 — 2026-11-13

imageの外の道具とその試験と文書の版です。imageのファイルは変わらず、3.12.0のままです（`glm53-tf3:3.12.0`、`sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`）。

### Fixes

- `cluster.sh` は、数えられなかった数をエンジン無しと読みません。ホストへのSSHかそのDockerが失敗したとき、`start` はどのrankも起動する前に止まり（`rank R HOST: its engines cannot be counted (ssh or docker failed)`、exit 1）、`status` と `stop` はそのホストのエンジンの数を `?` と出します。止まったcontainerは、メモリの見張りと同じくエンジンを動かしていないと数え、無いcontainerも同じです。Dockerは無いcontainerを「No such object」か「No such container」と言い、docker 29.6.2は小文字で言います。daemonに届かないDocker（「… no such file or directory」）は失敗と読みます。3.12.xまでは、Dockerの失敗をエンジン無しと、SSHの失敗をエンジンがもう動いていると読んでいました。
- メモリの見張り（`hostwatch.sh`）は、参照機のdocker 29.6.2のように、containerが無いと小文字で言われたときも終わり、Dockerがdaemonに届かないときは見張りを続けます。3.12.xまでは、そうしたDockerの上で見張りの間にcontainerを消すと、見張りはkillされるまで続きました。
- `cluster.sh` は、labelの後のserveの引数を、空白やquoteを含むものも一つずつそのまま `serve.sh` に渡します（[エンジンのflag](docs/configuration.ja.md#エンジンのflag)）。3.12.xまでは、SSHと `bash -c` にquoteせずに渡したので、そうした引数は一つのまま届きませんでした。
- `long-input` は、`--tokens` が台帳の行の無いpromptより小さいとき、そのpromptの大きさを示してexit 2で止まります。3.12.xまでは、台帳の長さを終わりなく探していました。
- `decode-check` と `bench` は、streamの返答に文かusageが無いとき、どちらが無いかを示してexit 1で止まります。`decode-check` は、`PROMPT_KIND` が `count`・`prose`・`code` のどれでもないとき、その3つを挙げてexit 2で止まります。3.12.xまでは、どれもPythonのtracebackで終わっていました。

### Documentation

- [手順書](SETUP.ja.md)の最初の段は、1.x系か2.x系のserverと2.x系のcontainerを先に止めます（全ホストで `docker stop glm53-tf`）。そのcontainerが全GPUを取るからです。4台のringのaddressは[TP=4のexamples](examples/tp4-rank0.env)を指します。runtimeのimageの一覧は、`serve.sh` のほかに `tokenizers` 入りの `python3`、TPの大きさごとの既定、wireのkernelを挙げます。前は `serve.sh` だけを挙げていました。
- 手順書は、Hugging Faceのcacheの写しを受け取ったホストが、同じ `--tp` で `download` を一度回してから `verify-download` することと、`docker stop glm53-tf3` の後は次の `cluster.sh start` の前にcontainerを起こし直すことを書きます。起動の秒数が何を含むかを書き、リリースの起動の時間は[リリースでの測定値](README.ja.md#リリースでの測定値)に任せます。前は3.9.0の数を挙げていました。TC-67とTC-69の既知の振る舞いは[3.10.0の測定値](docs/measurements.ja.md#3100)へつなぎます。4台のホストのTP=2の組は、もう「まだ」と書きません。
- [README](README.ja.md)の配信の既定は、TP=2で主streamの小さなall-gatherが、rankあたり `TF_ROCE_MAX_KB`（4 MiB）まではengineの2 rankのRoCEの道を、それを超えるとNCCLを通ると書きます。前はNCCLと書いていました。READMEと[設定](docs/configuration.ja.md)は、4台のringでは、split自身の確かめがその組を名指す前にNCCLがpeerのwarm-upで失敗するので、`split` は起動しないと書きます。前は、splitの確かめが断ると書いていました。[2.x系との違い](README.ja.md#2x系との違い)はTP=4を他の大きさと一緒に数え、回り続けるcoreの限りの文は要点を述べて数へつなぎ、上流のrunbookへのlinkはengineの版の1.2.7を名指します。前は1.2.4でした。
- [運用](docs/operations.ja.md)は、一つのrankが止まると、他のrankもliveness lineがホストの不在に気づいて約20秒のうちに止まると書きます。前は、2.x系と同じく集団通信で待つと書いていました。節は[一つのrankが止まったとき](docs/operations.ja.md#一つのrankが止まったとき)になり、[ホストの道具のREADME](../host/README.ja.md)もそこへつなぎます。TPの大きさの既定のcheckpointを替えるimageへ移るときの段を、独りの段にしました。起動の結果に、どのrankも起動する前の `cluster.sh` の断りを挙げます。数えられない時の断りもその一つで、`stop` の最後の行の `?` と0の意味も書きます。
- [設定](docs/configuration.ja.md)は、3.xのdeploymentが設定するものと、この系が名指すか測ったengineの設定を挙げると書き、engineはもっと読み、それは固定したcommitのsourceにあると書きます。前は、deploymentが読む全ての設定と書いていました。`cluster.sh` がserveの引数を一つずつquoteすると書きます。前は、quoteせずに渡すと書いていました。
- [cheatsheet](docs/cheatsheet.ja.md)は、`csf0_v1` を読むengine（3.10.0からのこの系のものと、1.2.3からの上流のリリース）と、3.11.0からのtool引数ゲートが、`--parallel-tool-calls client` でなければ1ターンに1つのtool呼び出しもengineに頼むことを書きます。`VISION=0` で空くrank 0のメモリは、他のrankの余地の許す限りKVのpoolに入り、その後でprompt cacheに入ると書きます。前はprompt cacheと書いていました。100万tokenのpromptの最初のtokenは分で示し、秒はREADMEに任せます。TP=2の組は、どれが配信したかを手順書へつなぎます。`score-nll` の行は、検証の頁と同じくcontainerの中で回します。
- [判断](docs/decisions.ja.md)は、大きさで分かれる設定を数える代わりに配信の既定の表を指し、[ベンチマークの方法](docs/benchmarks.ja.md)は、ホストと既定にTP=4の4台のringを挙げます。
- READMEの[免責事項](README.ja.md#免責事項)は、上流が取り込んだpull requestの一覧を[判断](docs/decisions.ja.md#エンジン)に任せます。判断の行は全部を、上流のCHANGELOGがそれを挙げるリリースごとに持ちます。前は2つの一覧が食い違っていました。
- [検証](docs/validation.ja.md)は、基準値ごとに出所を示します。3.12.0の受け入れの受理長とTP=2でのXSFP4の編集の返答の64回、TP=2は3.9.0のimageから・TP=3は3.9.0の答えを一字一句同じに出した3.12.0のimageからの多バイトの答え、toolsの数ごとのtool-eval-benchの版、3.12.0からのTP=3のtoolsの数（3.11.0のgateの前のgateを通して93、3.9.0では92。gateなしで91）、XSFP4の節のTP=2のdecode検査と `bench` は3.12.0から、balancedなidle poolの行の数は1つのリリースのものだけ、です。TP=4の基準値はこの頁に無いと書き、`score-nll` の例は、`tokenizers` のあるcontainerの中で、cacheを `/hub`、revisionをlockから取って回します。前はhostで固定のsnapshotを使っていました。頁の冒頭は、それぞれがどの受け入れのものかをXSFP4の節へつなぎ、その節が上流の版を挙げます。メモリと温度の基準値は、1M tokenのpromptの間のものはrank 0の最も熱いzoneだと、両TPについて書きます。
- [文書の地図](../docs/README.ja.md)は、[Contributing](../CONTRIBUTING.ja.md)のとおり、利用者に見える内容を変えるときに英日の対を両方更新すると書きます。前は手順と書いていました。文書の地図と[AGENTS.md](../AGENTS.md)は、保守する人が非公開の計画をどう持つかを、もう書きません。

### Repository

- 道具は、要求の送りと、streamの返答とcacheされたtokenの読みを、1つのmodule `glm53_tf/client.py` で行います。`bench` はdecodeとeditの行を1か所で組み、`verify-download` のmainは段ごとに読め、`download` はstateのfolderのlockを1か所で取り、tool引数ゲートの要求のhandlerはmoduleの階のclassになり、`--tp` のhelpはTPとcheckpointの表から組みます。この組み替えで、出す物と送る物は変わりません。
- `verify-download` は、downloadの状態を、platformの符号化でなく、`download` が書くとおりUTF-8で読みます。
- 試験は、`ssh` と `docker` の代役に対して `cluster.sh` を回し、tool引数ゲートの `main()` と、`serve.sh` の名・address・返答の上限・追加の引数を回します。`bench` の行の試験は行のkeyの順を、tool引数ゲートのstreamの試験はstreamごとの記録を確かめます。道具の試験は返答の代役を1つのmoduleで共有し、`serve.sh` の文字の試験は回す試験の隣に置き、TPの大きさは `config.TP_CHECKPOINTS` から取ります。
- hostの道具の仮の値の注釈は、`cc-defer` の印を外し、言っていることは残します。

### Accepted

2026-11-13に2台の参照機で、TP=2のJammed XSFP4を3.12.0のimage（`glm53-tf3:3x-54ccb94`、`glm53-tf3:3.12.0` と同じimage）とexamplesのrankのファイルで起こし、このリリースの `cluster.sh` の小文字を読む前の形で、`status`、空白入りのserveの引数を1つ付けた `start`（`--alias "GLM e15 check"`）、`stop` を回しました。引数は一つのまま届き、エンジンは `GLM e15 check` を1つのmodelのidとして挙げました。`status` は、containerが動いてエンジンが無いときに0、配信中はrankごとに1、`stop` の後と `docker stop` の後は0と数えました。`stop` は各ホストの `MemAvailable` を出し、両方のメモリの見張りは `done` で終わりました。containerを消すとDockerは「error: no such object」と答え、その `cluster.sh` は `?` と読みました。大文字と小文字の両方を読む写しは0と数え、1つのrankに届かないときはそのrankを名指してstartを断りました。消したcontainerに当てた3.12.0のメモリの見張りは10秒のtimeoutまで終わらず、両方を読む写しはすぐに終わりました。daemonに届かないときのdocker 29.6.2の答えは「no such file or directory」を含み、リリースの形の数えはそれを失敗と読みます（試験で固定）。quoteを含む引数はホストで回しておらず、リリースの形の `cluster.sh` ではホストでエンジンを起動していません。

## 3.12.1 — 2026-11-12

文書とexamplesの注釈と試験だけの版です。imageのファイルは変わらず、3.12.0のままです（`glm53-tf3:3.12.0`、`sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`）。

### Documentation

- 既定のcheckpointは、3.12.0が決めたとおりTPの大きさで決まります。[リポジトリのREADME](../README.ja.md)、[ライセンスの整理](../docs/licensing.ja.md)、このREADMEの[何であるか](README.ja.md#何であるか)と[2.x系との違い](README.ja.md#2x系との違い)は、TP=2でJammed XSFP4、TP=3とTP=4でXSFP4と書きます。前は、XSFP4を既定、Jammed XSFP4を選べるものと書いていました。imageに入る `THIRD_PARTY_NOTICES.md` は、次のimageまで前の言い方のままです。
- [ホストの準備](../docs/hosts.ja.md)とREADMEの必要な環境は、2026-11-07からの参照機の状態（kernel `7.0.0-1025-nvidia`、displayのmemoryはAuto）で測ったのは3.12.0が最初のリリースで、前の版から引き継いだ数はその前の状態で測ったと書きます。前は、この状態ではまだ何も測っていないと書いていました。
- READMEの[免責事項](README.ja.md#免責事項)と[判断](docs/decisions.ja.md#エンジン)は、3.12.0のengineが上流1.2.7そのものだと書きます。前は、READMEが1.2.4と書き、判断の版は1.2.1で止まっていました。
- TP=4は回りました。判断はもう、回していないとは書きません。[設定](docs/configuration.ja.md)は、TP=4のexamplesがengineのNCCLの接続の設定2つを1にすることと、`cluster.sh` がTP=4のrankもTP=2と同じく3秒おきに起動することを書きます。
- rankのファイルの空の値は、ほとんどの設定でunsetと読まれます。READMEの[設定](README.ja.md#設定)と、設定の頁のheatの行は、空の値が設定を切る、`serve.sh` がunsetする、とはもう書きません。imageに入る `serve.sh` と `config/tp*.env` の注釈は、次のimageまで前の言い方のままです。
- [手順書](SETUP.ja.md#5-起動)と[cheatsheet](docs/cheatsheet.ja.md)は、cluster fileを写す前に `state/` を作ります（READMEのはじめ方と同じ）。cheatsheetは、tool引数ゲートを `v3/` で回します。
- [文書の地図](../docs/README.ja.md)は、releaseの確かめを `release.yml` と同じ `release_notes.py X.Y.Z --match-project` と書き、ホストの準備の「ホストの更新」の節を挙げます。[AGENTS.md](../AGENTS.md)は、根の文書の地図とCIのfileがcheckoutのルートにあると書きます。日本語の[NCCLの診断](../docs/nccl-validation.ja.md)はcontainerの命令の行継ぎを保ち、日本語の判断は2.x系が画像を受けると「既定で」なしに書き、examplesのrankのファイルの `CONTEXT` の注釈は `config/tpN.env` を挙げます。

### Repository

- `serve.sh` の試験は、空の値が空のままengineに届くことを固定します。keyそのものを読むようにし、前はkeyが無くても通っていました。試験の名の1つはどのTPの大きさとも言い、`.gitignore` は `docs/plans` を一度だけ挙げます。

## 3.12.0 — 2026-11-12

エンジンを、この系列のcommitを持たない上流のTensorFold v1.2.7そのもの（`93a2e93e`）へ移します。Jammed XSFP4の `csf0_v1` のcommitは、上流が1.2.3から持っています。既定のcheckpointはTPで決まります：TP=2はJammed XSFP4、TP=3はこれまでどおりXSFP4、新しく試験的なTP=4はXSFP4です。imageは `glm53-tf3:3.12.0`（`sha256:103b79933cfca32e14ce1ef0809b82ea16882b42d518dd55de212e8358be1e67`）です。

### Engine

- forkのbranch `release/3.12.0` は上流のv1.2.7（`93a2e93e`）そのものです。`config/engine.lock.json` とDockerfileの `ENGINE_REF` がそのcommitに固定します。3.10.0のbranch（上流1.2.1にこの系列の6つのcommit）は退きます：上流のリリースが1.2.3からその6つを持っています（[TensorFold #2041](https://github.com/ashhart/TensorFold/pull/2041)）。
- rankのファイルの空の値（`NAME=`）は、上流1.2.6からほとんどの設定でunsetと読まれ、`serve.sh` は空の値をそのまま渡します（3.11.xはそのうち6つを自分でunsetしていました）。空の値を今も断るのは `TF_ROCE_MAX_KB` と `TF_NVFP4_DECODE_WARPS` の2つで、空の `TF_HEAT_HIGH` と `TF_HEAT_LOW` を両方そろえると熱の待ちは無くなります（[設定](docs/configuration.ja.md#rank-0のserver)）。
- `TF_GLM_PDL`・`TF_GLM_PROMPT_STEPS`・`TF_GLM_SHARED`・`TF_GLM_LINK_WAIT`・`TF_GLM_PROF` は `0` か `1` だけ、`TF_GLM_DRAFT_CONFIDENCE` は0から1の数を取ります（[TensorFold #2578](https://github.com/ashhart/TensorFold/pull/2578)、上流1.2.6）。**どれかを語（`off`・`yes`）にしたrankのファイル**は、名を挙げて起動を止めます。`0` か `1` を書きます。
- 保持するpromptの状態は起動の計画のslotに1つずつ入り、prompt cacheの残りはpoolのpageになります（上流1.2.5、#2358）：TP=3でsystemに16 GiBを残すと、poolは窓2本とその残りを取ります（[TP=3で16 GiBにする理由](README.ja.md#配信の既定)）。TP=3のJammed XSFP4では余地に窓3本目が入り、計画はそれをslotより先に置くので、`TF_KV_SHARE=32` のうち保持されるstateは8で、エンジンが警告します。`cluster.sh` のlabelの後に `--prompt-cache-gib 6` を足すと、32全部と窓2本が入ります（[エンジンのflag](docs/configuration.ja.md#エンジンのflag)）。64を越える `TF_KV_SHARE` は起動を止めます（[設定](docs/configuration.ja.md#rankのファイル)）。
- TP=3のdraftありのdecodeは、tokenは同じまま3.10.0より遅くなります：decode検査の `count` は57.94 tok/s（3.10.0の表は65.67）、`bench --kinds decode` は63.23（68.52）です。`--mtp-confidence` の下では、temperature 0のstreamが毎roundで鎖の上限までdraftを作り、窓は確率がconfidenceの床より上の頭だけを検証します。上流の直し（[TensorFold #2864](https://github.com/ashhart/TensorFold/pull/2864)）は、それを持つ最初のリリースで入ります。

### Serving defaults

- TP=4（試験的）：switchの無いリングの4台がTP=4で配信します。`serve.sh` はTP 4とrank 0〜3を受け、imageは他の2つの隣に [`config/tp4.env`](config/tp4.env) を持ちます：TP=3の値でwireを切り、システムに14 GiBを残すもので、2026-11-07から上流のmainで参照機の4台のリングを配信した設定です。どれも4台では詰めていません。exampleはそのリングのrankのファイル、rankごとのNCCLのgraph、`cluster.tp4.env` を持ちます。各rankのファイルはリングのNCCLの行と `TF_GLM_PREFILL_REDUCE=gather` を足します。エンジンの `split` は全rankへ送るので、4台のリングでは起動しないからです：peer warm-upがNCCLの `ncclGroupEnd: unhandled system error` で止まり、届かない組を名指すsplitの確かめまで進みません（[配信の既定](README.ja.md#配信の既定)、[cheatsheet](docs/cheatsheet.ja.md)）。他のexampleは同じ4台を、2組の対としてTP=2で配信します：04-05と06-07（それぞれTP=2で配信した）、または04-06と05-07（まだ起動していない）。2組を同時に配信したことはまだありません。
- 既定のcheckpointはTPで決まります：TP=2はJammed XSFP4、TP=3とTP=4はこれまでどおりXSFP4です。各リリースのファイルがlockのrevisionでそのfolderを名指し、rankのファイルの `CHECKPOINT` の行でもう一方を配信し、空の行はTPの既定のままです。`serve.sh` の起動の行は、配信するfolderで終わります。ホストに無いfolderは、名を挙げて起動を止めます。**XSFP4だけを持つ対**は、Jammed XSFP4を取得するか（`download --tp 2`、`verify-download --tp 2`）、全rankのファイルにXSFP4の `CHECKPOINT` の行を足します（[手順2](SETUP.ja.md#2-checkoutとcheckpoint)）。

### Image and launch

- メモリの見張り（`cluster.sh` が各ホストで起こす `hostwatch.sh`）は、確かめが失敗しても返らなくても見張りを続けます。dockerの呼びはどれも1回の間隔の2秒で切り、失敗するか止まった確かめは `check-failed` と書いて続け、見張りが終わるのは、エンジンが居なくなった時か、`docker inspect` でcontainerが止まった・無いと分かった時だけです。止めに失敗すると `KILL-FAILED` と書き、メモリが足りないままなら次の回にもう一度止めます。`KILLED` は止めが効いた後にだけ書きます（[設定](docs/configuration.ja.md#メモリの見張り)）。3.11.xまでは、失敗した `docker exec` をエンジンが居ないと読み、見張りを終えていました。

### Tools

- `download` と `verify-download` は、そのTPが配信するcheckpointを選ぶ `--tp 2`・`3`・`4` か `--checkpoint` を要し、どちらも無ければ使い方を示して止まります。3.11.xまでは、どちらも無ければXSFP4を取得・検証しました。**どちらも付けずに回す台本**は `--tp` か `--checkpoint xsfp4` を足します（[手順2](SETUP.ja.md#2-checkoutとcheckpoint)）。

### Documentation

- READMEの[状況](README.ja.md#要約)・[checkpoint](README.ja.md#checkpoint)・[配信の既定](README.ja.md#配信の既定)・[リリースでの測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md)、[設定](docs/configuration.ja.md)（空の値、厳しくなったGLMのflag、`TF_KV_PAGES`、`TF_QMMF_HALF_BELOW`、保持する状態のslot）、[決定](docs/decisions.ja.md)、[cheatsheet](docs/cheatsheet.ja.md)は、3.12.0のエンジンと既定を名指します。数でない `TF_QMMF_HALF_BELOW` は読み込みを止め、空の `TF_KV_PAGES` は `auto` です（設定は別のことを書いていました）。3.10.0の表は[前の版の測定値](docs/measurements.ja.md#3100)へ移り、XSFP4が繰り返した数は返答のとおりに直しました：TP=2で37を4回、TP=3で37と86を2回ずつです。
- README・手順書・運用のコマンドは `glm53-tf3:3.12.0` をbuildして名指します。

### Accepted

2026-11-12に参照機で、リリースのimage（`glm53-tf3:3x-54ccb94`、`glm53-tf3:3.12.0` と同じimage）をそれ自身の `serve.sh` と `cluster.sh` で、全containerを効率coreに置いて起動しました。既定のTP=3のXSFP4とTP=2のJammed XSFP4では、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かない各TPの2回の起動が、TP=3で3.9.0の、TP=2で3.10.0の、decode検査のhash・`bench --kinds edit` の返答・NLLを返し、1回目は199,307・499,254・1,035,295 tokenのpromptの合言葉をすべて見つけ、`mojibake` は化けた文字を見つけませんでした。rankのファイルに `CHECKPOINT` の行を書いたTP=2のXSFP4では、1回の起動が3.9.0のdecode検査のhashと `bench --kinds edit` の返答を返しました。3.11.0のtool引数ゲート越しのtool-eval-benchは、TP=2のJammed XSFP4とTP=3のXSFP4で93、Safety Gateは合格でした。TP=3のJammed XSFP4では、`CHECKPOINT` の行を足した起動が3.10.0のdecode検査のhashと `bench --kinds edit` の返答を返し、`--prompt-cache-gib 6` を足した起動も同じhashを返しました。これらとTP=2のXSFP4の起動では、memory guard（このリリースの `hostwatch.sh`）が2〜3秒ごとに行を書き、最後に `done` で終わりました。TP=4では別の4台で、2回の起動がdecode検査のhashと編集の返答を同じく返し、合言葉をすべて見つけました。`TF_KV_SHARE`・`TENSORFOLD_PREFILL_SHARE`・`TF_HEAT_HIGH`・`TF_HEAT_LOW` を空にしたrankのファイルは、prompt cacheを写しで持ち熱の待ちの無い形で、`TENSORFOLD_MEMORY_RESERVE_GIB` を空にしたものはエンジン自身の12.3 GiBのreserveで起動しました。見張りが止めた起動はありません（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Not in 3.12.0

TP=3のdraftありのdecodeの上流の直し（#2864）は、それを持つ最初のリリースで入ります。prompt chunkの索引器を既定で自前のkernelに載せること（`TF_GLM_INDEX_CUDA=1`、上流の#1449）：各TPでエンジン自身の道と並べて測り、tokenは同じで長いpromptの最初のtokenは早まりましたが、メモリを測り直してから次の版で入れます。

## 3.11.7 — 2026-11-07

文書だけの版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Documentation

- 上流のリリースは1.2.3（2026-11-05、[TensorFold #2041](https://github.com/ashhart/TensorFold/pull/2041)）から `csf0_v1` のcommitを持ちます。READMEのJammed XSFP4の[制限](README.ja.md#制限)、エンジンについての免責事項、[Next Action](README.ja.md#next-action)、[決定](docs/decisions.ja.md#エンジン)はそう書きます。3.11.3では、それを持つ上流のリリースはまだ無いと書いていました。この系列のリリースのbranchは、上流のリリースへ戻るまで3.10.0のエンジンのままです。

## 3.11.6 — 2026-11-07

文書と道具のhelpと試験だけの版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Documentation

- [検証](docs/validation.ja.md)は、先に回の記録のfolderを作るように書きます（`mkdir -p ../records/<run>`）。どの道具もそのfolderを作らないので、新しいcheckoutでは最初の検査のfileが失われていました。
- [検証](docs/validation.ja.md)は、containerでは道具を `python3 -m glm53_tf` で回すこと（imageには `python` がありません）と、`score-nll` に要る `tokenizers` は仮想環境ではなくcontainerにあることを書きます。
- 検証は、エンジンがpromptを、GiB単位の大きさのcacheではなく、3.9.0からのとおりKV poolのpageの上の状態（`TF_GLM_KV_SHARE`）として保つと書きます。
- 英語の[測り方](docs/benchmarks.md#requests-at-once)は、promptの横の3本のdecodeが3.11.3までは一つのpromptを分けていたと書き、英語の[README](README.md#requirements)は参照機の起動の設定に `initcall_blacklist` の名を出します。日本語のcheatsheetと測り方は、tool引数ゲートが確かめることと、TP=2の対の冷却gateについて、英語と同じことを書くようになりました。

### Tools

- `decode-check --help` と `long-input --help` も保ったpromptについて同じことを書き、`tool-gate --help` は中継するのが `GET`・`POST`・`DELETE` だと書きます（他のmethodには前と同じく501を返します）。

### Repository

- 新しい試験は、二つのfileがそれぞれ書く事実を結びます：`serve.sh` の名前・host・port・応答の上限と、道具の既定と `tool-gate` の `--upstream`。`Dockerfile.build` の基礎とNCCL・tokenizersの版と、`Dockerfile` のもの。`cluster.sh` と `serve.sh` がimageの中で使うpathと、`Dockerfile` のもの。scriptとexamplesのcontainerの名前。
- `mojibake` と `decode-check` の試験は、回す所に `TENSORFOLD_API_KEY` や `PROMPT_KIND` が立っていても通り、`decode-divergence` の試験からは落ちようのないassertを外しました。

## 3.11.5 — 2026-11-07

文書だけの版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Documentation

- 参照機は 2026-11-07 に、カーネル `7.0.0-1025-nvidia`（`kho=off` と、`initcall_blacklist` の `power_wrap_init` つきで起動）、ConnectX-7 ファームウェア 28.50.1002、表示用のメモリを Auto にした MSI の UEFI 5.36_1.9.0 へ移りました。Auto で OS が使えるメモリは 1.5 GiB 増えます。[ホストの準備](../docs/hosts.ja.md#ホストカーネルと複数ノードroce)は、この状態と、3.11.4 までの 3.x系の数をすべて測った状態（`7.0.0-1019-nvidia`、ConnectX-7 28.45.4028、表示用の既定の 2 GiB）を分けて書きます。新しい状態では、3.x系の数はまだ測っていません。
- 新しい節[ホストの更新](../docs/hosts.ja.md#ホストの更新)は、参照機がたどった手順と、それぞれの確かめ方を並べます。DGX OS 7.6 では、再起動の前に `nvidia-spark-mlnx-firmware-manager` の ConnectX-7 ファームウェアの書き込みが終わるのを待つこと（書き込みの途中の再起動で止まり、止まった試みが 3 回になると、参照機の 2 台で自分を無効にして古いファームウェアを残しました）、`/proc/cmdline` の 2 つの起動の設定、`lvfs-testing` から入れた基板のファームウェアと表示用のメモリの設定、4 組で通った NCCL 検証です。
- [NCCL 診断](../docs/nccl-validation.ja.md)：`docker save | docker load` で基礎の image を受け取ったホストは、image を ID で指します。
- [必要な環境](README.ja.md#必要な環境)と[手順 1](SETUP.ja.md#1-機体とfabric)から新しい節へリンクします。

## 3.11.4 — 2026-11-05

文書だけの版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Documentation

- 32K tokenのpromptの横の3本のdecodeのtokenの間隔は、別々のpromptの3本で取った値になりました：XSFP4ではTP=2で62 ms、TP=3で47 ms、Jammed XSFP4では61 msと47 msです。これまでは3本が `bench` の同じ数え上げのpromptで、同じtokenを書くのでroundが軽く出ていました（45・46・37・36 msで、同じimageで測り直すと1 ms以内で同じでした）。[README](README.ja.md#配信の既定)の測定値とpromptの取り分を0.7にする理由、[測定値](docs/measurements.ja.md)、[測り方](docs/benchmarks.ja.md#同時の要求)、[判断](docs/decisions.ja.md)がそう書きます。取り分は0.7のままです：エンジンの `1` では間隔はTP=2で1,484 ms、TP=3で1,221 msでした。

## 3.11.3 — 2026-11-04

文書だけの版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Documentation

- 上流は2026-11-04に `csf0_v1` のcommitをmainに取り込みました（[TensorFold #2041](https://github.com/ashhart/TensorFold/pull/2041)）。それを持つ上流のリリースはまだありません。[README](README.ja.md#制限)と[判断](docs/decisions.ja.md#エンジン)は、commitを次に上流へ出すと書いていた所でそう書き、READMEのJammed XSFP4の制限は、リリースされたエンジンでそれを読むのはこの系列のものだけと書きます。リリースのbranchを上流のリリースへ戻し、[Jammed XSFP4の行](docs/decisions.ja.md#checkpoint)を開き直すのは、commitを持つ上流のリリースが出た時になります（[Next Action](README.ja.md#next-action)）。

### Not in 3.11.3

上流のリリースへ戻したリリースのbranch（commitを持つ上流のリリースを待ちます）と、XSFP4から何も借りずBF16の重みから作ったJammed XSFP4（[Next Action](README.ja.md#next-action)）。

## 3.11.2 — 2026-11-04

文書だけの版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Documentation

- [判断](docs/decisions.ja.md#窓とstream)の広いpromptのpassの行に、後の上流の測り（TP=3の既定、wireの上、[TensorFold #1994](https://github.com/ashhart/TensorFold/issues/1994)）を足します：全rankの `TF_GLM_OVERLAP_PIECES=8` で、soloの得が既定の3 pieceの1.7〜3.6%から6.1〜7.8%になり、返るtokenは同じでした。soloなしの8 pieceは3 pieceから1%以内でした。TP=3では他のstreamがほとんどの時間decodeしているのでsoloは使わないままで、行には開き直す条件として、8 pieceと一緒のsoloを複数の人の負荷のもとで測ることを書きます。
- [ベンチマークの方法](docs/benchmarks.ja.md#decode検査)に、READMEのJammed XSFP4の既知の振る舞いにある残り2つのcountの取り方を書きます：`ignore_eos` をfalseにしたdecode検査の写しと、思考なしで1から100の数を求めた写しです。
- 日本語の[判断](docs/decisions.ja.md)と、日本語の変更履歴の3.9.0の節は、TP=2の用途を3.10.1からのREADMEと同じく「1人がagentと続ける長い会話」と書きます。

### Not in 3.11.2

6つのcommitの上流への取り込みと、XSFP4から何も借りずBF16の重みから作ったJammed XSFP4（[Next Action](README.ja.md#next-action)）。

## 3.11.1 — 2026-11-04

`download --background` と公開監査の直し2つです。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Tools

- `download --background` は戻る前にjobの状態を書くので、[手順書](SETUP.ja.md#2-checkoutとcheckpoint)がすぐ後に走らせる `verify-download --wait` はこのjobを追います。前は、まだ状態が無くて1で終わる（「run download first」）か、前のjobの状態を見てそこで終わることがありました。別のdownloadがcheckpointのフォルダを持つ間の開始は、前景の実行と同じく断り、`download.log` の中で落ちるjobを起こしません。起こせなかったjobは失敗の状態を残します（[道具](docs/configuration.ja.md#道具)）。

### Repository

- 公開監査（`tools/check_publication.py`）は、XSFP4のlockの横にJammed XSFP4のlockも求め、modelと完全なrevisionを固定しているかを確かめます。固定していないlockは名前で挙げます。

### Not in 3.11.1

6つのcommitの上流への取り込みと、XSFP4から何も借りずBF16の重みから作ったJammed XSFP4（[Next Action](README.ja.md#next-action)）。

## 3.11.0 — 2026-11-04

tool引数ゲートと文書の版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Tools

- [tool引数ゲート](SETUP.ja.md#6-tool引数ゲート任意)は、エンジンに1手番1つのtool callを求め、modelにもそう伝えます。toolを宣言した要求は、clientが何を送っても `parallel_tool_calls` をfalseにし、最初のsystem messageの末尾に「Make one tool call a turn, and the next one after its result has come back.」の1文を足して渡します。TP=3ではJammed XSFP4が、tool-eval-benchのTC-51で `create_calendar_event` と同じ手番に `send_email` を呼び、Safety Gateがそこで落ちていました。`--parallel-tool-calls client` は、これまでどおり要求をclientが書いたとおりに送ります（[設定](docs/configuration.ja.md#道具)）。

### Accepted

- 3.10.0のimageでゲート越しのtool-eval-bench 2.8.0、各checkpointの各TPで1回の起動：XSFP4はTP=2で93、TP=3で93、Jammed XSFP4は93と92で、Safety Gateは4つとも合格（[検証](docs/validation.ja.md#tool引数ゲート越しのtool)）。その前のゲート越しでは4つは95・92・93・92で、Jammed XSFP4のSafety GateはTP=3で落ちていました。TC-69は4つとも落ち、TC-67は4つとも部分点です。どちらも2つの調べ物を求め、modelは1つ目の結果の後に2つ目を呼ばずに答えました。TP=2のJammed XSFP4はTC-49も部分点でした。これらは既知の振る舞いです（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Documentation

- READMEの[リリースでの測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md)のtoolとJammed XSFP4の基準値、[手順書](SETUP.ja.md)§6、[設定](docs/configuration.ja.md#道具)の道具は、3.11.0のゲートとその点数、既知の振る舞いを書きます。ゲートなしでは、TP=3のJammed XSFP4のTC-51は既知の振る舞いのままです。
- READMEの[Next Action](README.ja.md#next-action)は、`csf0_v1` のcommitの上流へのpull request、[TensorFold #2041](https://github.com/ashhart/TensorFold/pull/2041)を名指します。

### Not in 3.11.0

6つのcommitの上流への取り込みと、XSFP4から何も借りずBF16の重みから作ったJammed XSFP4（[Next Action](README.ja.md#next-action)）。

## 3.10.2 — 2026-11-03

文書だけの版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Documentation

- READMEの[リリースでの測定値](README.ja.md#リリースでの測定値)は、表のTP=3のJammed XSFP4の起動の時間が何かを書きます：受け入れの台本が1回目を読み込みの後に、XSFP4の窓2本のpageに合わせた空きの線で止めたので、46秒は同じ重みの2度目の読み込みのもので、XSFP4の93秒のような1度目のものではありません。見張りが止めた起動はありません。
- Jammed XSFP4の遅い `count` は、何と比べたかを名指します。同じimageでの3.10.0のXSFP4の起動で、3.9.0の受け入れである表のXSFP4の列ではありません。

### Not in 3.10.2

6つのcommitの上流への取り込みと、XSFP4から何も借りずBF16の重みから作ったJammed XSFP4（[Next Action](README.ja.md#next-action)）。

## 3.10.1 — 2026-11-03

文書だけの版です。imageのファイルは変わらず、3.10.0のままです（`glm53-tf3:3.10.0`、`sha256:948af28e09e6c539f0cc5671d0fc34bbd850bc7ff8b29c86287df98cdc297995`）。

### Documentation

- READMEの[リリースでの測定値](README.ja.md#リリースでの測定値)は、XSFP4とJammed XSFP4を各TPで1枚の表に並べます。Jammed XSFP4の列は3.10.0の起動、XSFP4の列は3.9.0の受け入れのもので、列の見出しにそう書きました。READMEは今の版の項だけを持つので、3.9.0の項は[前の版の測定値](docs/measurements.ja.md#390)へ一字一句そのまま移しました。
- [設定](docs/configuration.ja.md)を3.10.0のエンジンと既定に合わせました：CUDAのGLMは `--mtp-confidence` を受け、`--mtp-drafts` と、`--drafter` と一緒の `--mtp-confidence` を断ります。`TF_KV_PAGES=off` には空の `TF_GLM_KV_SHARE=` が要ります。TP=3のprompt cacheはpoolのpageの上にあります。TP=3のreserveの窓2本はXSFP4のものです。lockの表に `config/jammed.lock.json` を足しました。TP=3のexampleのKVのpageのコメント行も空の `TF_GLM_KV_SHARE=` を示し、[手順書](SETUP.ja.md)§4がそれを挙げます。
- [ベンチマークの方法](docs/benchmarks.ja.md)は3.10.0の起動の取り方を書き、[チートシート](docs/cheatsheet.ja.md)は1,035,295 tokenのpromptの最初のtokenを、3.9.0と3.10.0の両TPの値で書きます。
- [ライセンスの整理](../docs/licensing.ja.md)とリポジトリのREADMEは、XSFP4の横にJammed XSFP4を名指します。READMEの日本語の頁は、TP=2の長い会話を1人がagentと続けるものと書き、はじめ方はcheckoutの根でimageをbuildします。

### Not in 3.10.1

6つのcommitの上流への取り込みと、XSFP4から何も借りずBF16の重みから作ったJammed XSFP4（[Next Action](README.ja.md#next-action)）。

## 3.10.0 — 2026-11-03

Jammed XSFP4を足します。routed expertがTP=2の各ホストで6.58 GiB、TP=3のrank 0で4.50 GiB少ないcheckpointで、rankのファイルの `CHECKPOINT` の1行で配信します。TP=3ではKVのpoolが窓3本分のpageを取ります。XSFP4は既定のままで、tokenは3.9.0と同じです。エンジンのrelease branchは、新しい形を読む6つのcommitを足します。

### Checkpoint

- [Jammed XSFP4](README.ja.md#checkpoint)、`Bizuayeu/GLM-5.3-Flash-Jammed-XSFP4` を [`config/jammed.lock.json`](config/jammed.lock.json) のrevisionで：3〜44層のrouted expertを、XSFP4の平滑化のまま入力32個ごとのblockのスケールで合わせ直し、そのスケールを行に1つのbaseとblockごとの4 bitのoffset（`csf0_v1`）で、fileでもGPUでも同じ形で持ちます。MTP層のexpertはFP4-Localのものです。
- `download` と `verify-download` は `--checkpoint jammed` を受け、状況を `state/jammed` に置きます。`serve.sh` は `CHECKPOINT` が名指すfolderを配信します。他は変わりません（[手順2](SETUP.ja.md#2-checkoutとcheckpoint)）。
- TP=2では空いた分が空いたまま残ります：読み込みの後のrank 0の空きは14.16 GiBで、XSFP4は8.33 GiBです。TP=3では同じ14 GiBのreserveの下で窓3本分のpage、6,147（38.27 GiB、XSFP4は4,098）を取り、rank 0の空きは12.15 GiB、XSFP4は20.69 GiBです。
- 返答はこのcheckpointのものなので、自分の基準値を持ちます（[検証](docs/validation.ja.md#jammed-xsfp4)）。TP=3でtool-eval-benchのSafety GateがTC-51で落ちることと、decode検査の `count` がXSFP4より遅いことは既知の振る舞いです（[リリースでの測定値](README.ja.md#リリースでの測定値)）。この形を読むのはこの系列のエンジンだけです（[制限](README.ja.md#制限)）。

### Engine

- forkのbranch `release/3.10.0`（`a9642aef`）は、上流v1.2.1（`1db3edbe`）にこの系列の6つのcommitを足したものです：形、そのpacker、5つのkernel、loaderからの道です。`csf0_v1` を持たないcheckpointは上流の道をそのまま通ります。GB10で5つのkernelは上流のkernel contractの4つのgateを全部通り、これらのcommitは次に上流へ出します。
- `config/engine.lock.json` とDockerfileの `ENGINE_REF` はそのcommitを固定します。

### Documentation

- READMEの[checkpoint](README.ja.md#checkpoint)・[制限](README.ja.md#制限)・[リリースでの測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md#jammed-xsfp4)、[決定](docs/decisions.ja.md#checkpoint)、[設定](docs/configuration.ja.md)、[チートシート](docs/cheatsheet.ja.md)、手順書がJammed XSFP4を挙げます。XSFP4の基準値は3.9.0のままです。
- README・手順書・運用のコマンドは `glm53-tf3:3.10.0` をbuildして名指します。

### Accepted

2026-11-03に参照機で、リリースのimage（`glm53-tf3:3.10.0`）をそれ自身の `serve.sh` と `cluster.sh` で、全containerを効率coreに置いて起動しました：rankのファイルに `CHECKPOINT` も `CONTEXT` も書かない各TPの1回の起動は、3.9.0のXSFP4のdecode検査のhashと `bench --kinds edit` の返答を返しました。Jammed XSFP4の `CHECKPOINT` の1行だけを足すと、各TPの2回の起動はhashと返答を繰り返し、1回目は199,307・499,254・1,035,295 tokenのpromptの合言葉を全部見つけました。`PARALLEL=` を空にすると、エンジンはTP=2で8本、TP=3で8本のstreamを取り、どれもcountのhashを返しました。1本と4本、TP=3では8本も、TP=2で20本、TP=3で52本の返答が同じ要求の単独の返答と同じでした。tool-eval-bench 2.8.0は、ゲート越しでTP=2が93・TP=3が92、ゲートなしで92と91で、Safety GateはTP=2で合格し、TP=3でTC-51で落ちました（既知の振る舞い）。`mojibake` は化けた文字を見つけませんでした（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Not in 3.10.0

6つのcommitの上流への取り込みと、XSFP4から何も借りずBF16の重みから作ったJammed XSFP4（[Next Action](README.ja.md#next-action)）。配信の既定は3.9.0のままです。

## 3.9.0 — 2026-11-03

エンジンを上流のTensorFold 1.2.1そのものの上へ移し、TP=2もTP=3と同じくモデルの上限の1,048,576 tokenの窓を開き、配信の既定をTPごとに決めます：TP=2は1人がagentと続ける長い会話のため、TP=3は複数の人の同時利用のためです。TP=2で4本、TP=3で8本のstreamがKVのpoolを分け合い、保持するpromptはpoolのpageに残ります。文書の測定値は3.9.0の受け入れのものです。

### Engine

- forkのbranch `release/3.9.0` は上流v1.2.1（`1db3edbe`）そのもので、commitを足していません。上流は1.1.5の後に、この系列の#1352・#1404・#1424（1.1.9）、#1516・#1524・#1616・#1636（1.2.0）、#1823（1.2.1）を取り込みました。
- TP=2のKV cacheがpageに移ります。上流の1.1.6からの2 rankの既定です（#1322）：全streamのcacheとエンジン自身のsequenceが一つのpoolのpageを取ります。FP8のlatent cacheはstreamごとに窓を持つので、`--kv-cache fp8` には空の `TF_GLM_KV_SHARE=` と1本のstreamが要ります（[チートシート](docs/cheatsheet.ja.md#tp2のfp8のlatent-cache)）。
- 起動が短くなります：#1616と#1636は重みを複数のthreadで読んで詰めます（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Serving defaults

- TPで分かれるものは [`config/tp2.env`](config/tp2.env) と [`config/tp3.env`](config/tp3.env) が持ちます。`serve.sh` はimageの中のそのTPのファイルをrankのファイルの前に読むので、新しいimageで既定が動き、rankのファイルの行は今までどおり強く、空の値はその設定を切ります。
- TP=2：`CONTEXT=1048576`（モデルの上限、3.8.xまでは524,288）、`PARALLEL=4`、`TF_GLM_KV_SHARE=16`、`TENSORFOLD_PREFILL_SHARE=0.7`、`TENSORFOLD_MEMORY_RESERVE_GIB=9`。
- TP=3：`PARALLEL=8`、`TF_GLM_KV_SHARE=32`、`TENSORFOLD_PREFILL_SHARE=0.7`、`MTP_CONFIDENCE=0.5`（`--mtp-confidence`）、`TF_GLM_ROCE_MULTI=1`（wire）、`TENSORFOLD_MEMORY_RESERVE_GIB=14`。
- 理由はREADMEの[配信の既定](README.ja.md#配信の既定)と[決定](docs/decisions.ja.md#窓とstream)にあり、`PARALLEL=1` の行はそこで閉じます。

### Image and launch

- imageは `serve.sh` の横に `tp2.env`、`tp3.env`、wireのkernelである `tp_mailbox.fatbin` を持ち、`/usr/share/doc/tf3/ENGINE` はそのkernelのSHA-256を名指します。
- `TF_GLM_ROCE_MULTI` がonの間、`serve.sh` はwireに、`MASTER` からの `TF_TP_MASTER`、`TF_TP_PORT`、`TF_TP_PLAN_TIMEOUT`、`TF_TP_KERNEL_IMAGE`、`TF_TP_ROCE_FALLBACK=error` を渡すので、準備に失敗すると起動が止まります（[運用](docs/operations.ja.md)）。
- `[serve.sh]` の行は解決した `kept`・`prefill-share`・`solo`・`mtp-confidence`・`wire`・`reserve` を出し、受け入れはそれをファイルと照らします。
- `config/engine.lock.json` とDockerfileの `ENGINE_REF` は `release/3.9.0` の `1db3edbe`（上流1.2.1）を固定します。

### Documentation

- 文書の測定値は3.9.0の受け入れのものです：[検証](docs/validation.ja.md)の基準値（decode検査のhash・編集の返答・NLLは3.3.0の受け入れのまま）と、READMEのcheckpoint・配信の既定・制限・[リリースでの測定値](README.ja.md#リリースでの測定値)。3.8.0の項はそのまま[前の版の測定値](docs/measurements.ja.md#380)へ移ります。
- [検証](docs/validation.ja.md#同時の要求)に同時の要求（上流の `bench_concurrent.py` で同じ要求の単独の返答と比べる）を、[ベンチマーク](docs/benchmarks.ja.md#同時の要求)にその行の取り方を足しました。
- [設定](docs/configuration.ja.md)は `config/tp*.env` の設定とwireの設定を挙げ、手順書と運用は4本・8本のstreamとwireを書き、[チートシート](docs/cheatsheet.ja.md)にエンジンが要求のmodelの名をどう扱うかを足しました。
- README・手順書・運用のコマンドは `glm53-tf3:3.9.0` をbuildして名指します。

### Accepted

2026-11-03に参照機で、リリースのimage（`glm53-tf3:3.9.0`）をそれ自身の `serve.sh` と `cluster.sh` で、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて起動しました：各TPの2回の起動で、XSFP4のdecode検査のhashと `bench --kinds edit` の返答は3.3.0と同じで、1回目ではNLLと199,307 tokenのpromptへの返答も3.3.0と同じで、499,254 tokenと1,035,295 tokenのpromptの3つの合言葉を全部見つけました。`PARALLEL=` を空にすると、エンジンはTP=2で8本、TP=3で8本のstreamを取り、どれもcountのhashを返しました。1本と4本、TP=3では8本も、TP=2で20本、TP=3で52本の返答が同じ要求の単独の返答と同じでした。tool-eval-bench 2.8.0は、ゲート越しでTP=2が95・TP=3が92、ゲートなしで93と91で、3.8.0と同じ点と、同じ部分点・失敗のシナリオでした。Safety Gateは合格で、`mojibake` は化けた文字を見つけませんでした。128本の文書に対するXSFP4の次tokenの数は、両TPで3.8.0とbyteまで同じでした（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Not in 3.9.0

上流で開いている#1423と#1580（[Next Action](README.ja.md#next-action)）、3.x系でのNVIDIAのNVFP4と公開したAXLの重み（1.x系と2.x系が配信します）、生成したtokenのlog確率（[制限](README.ja.md#制限)）。

## 3.8.1 — 2026-10-26

文書だけの版です。imageのファイルは変わらず、3.8.0のままです（`glm53-tf3:3.8.0`、`sha256:1055b9feee2ef704c8dd736495bfc8d231df5a59406b17eb0655eefdd830b7a2`）。

### Documentation

- READMEは今の版の[リリースでの測定値](README.ja.md#リリースでの測定値)、3.8.0のものだけを持ちます。3.6.0から3.0.0までは、新しい頁の[前の版の測定値](docs/measurements.ja.md)へ一字一句そのまま、版ごとの見出しの下に移しました。次の版が出ると、その版の項がそこへ移ります。移した版を指していた頁はそこへリンクし、文書の地図とREADMEの構成にその頁を足しました。READMEの冒頭の段落は各版で何が変わったかを並べず、この変更履歴へリンクします。
- 3.8.0のエンジンに合わせた直しで、そのsourceと3.8.0の受け入れで確かめました：[手順書](SETUP.ja.md)§5は、各rankの `NCCL_COMM_ID … leaves NCCL's environment` を読ませなくなりました。これは3.7.0までのリリースのbranchが持ったidのファイルのcommitの行で、1.1.5は出しません。rank 0のloadの行は、TP=3ではKVのpageで書きます。READMEの免責事項は、3.8.0のリリースのbranchがこの系列のcommitを持たない上流v1.1.5そのものだと書きます。[ベンチマークの方法](docs/benchmarks.ja.md)は、TP=2の各checkpointで1回の起動を `PARALLEL=` を空にして走らせたとは書かなくなり、冷却の上限を3.8.0のものでもあると書きます。[運用](docs/operations.ja.md)は、測定値を載せたどの版の受け入れでも（3.8.0を含めて）見張りがエンジンを止めなかったと書き、どの停止もエンジンを残さなかった受け入れに3.8.0を数えます。

### Not in 3.8.1

3.x系でのNVIDIAのNVFP4と公開したAXLの重み（1.x系と2.x系が配信します）、生成したtokenのlog確率（[制限](README.ja.md#制限)）。

## 3.8.0 — 2026-10-26

エンジンを上流のTensorFold 1.1.5そのものの上へ移します。この系列のpull requestを持つ上流の最初のリリースなので、リリースのbranchにこの系列のcommitはありません。TP=3ではKV cacheがpageに移り、rank 0のNCCLのidはrankどうしの線で他のrankへ届き、`clear_thinking` がchat templateに届きます。文書の測定値は3.8.0の受け入れのものです。

### Engine

- forkのbranch `release/3.8.0` は上流v1.1.5（`84e0d560`）そのもので、commitを足していません。上流は2026-10-25に、この系列のpull requestをmainへ取り込みました：#1050（NVIDIAのGLM-5.3-Flash-FP4-LocalとXSFP4の読み込み。3.6.0のリリースのbranchが持っていたもの）、#1163と#1211（GLMのKVのpage）、#1178（rank 0のNCCLのidをrankの生存の線で送る。上流はTPのbootstrap #636を閉じていました）。Zig・xgrammar・mediaのlibraryは3.6.0の版のままで、1.1.5もその版を固定しています。
- TP=3では、全streamのKV cacheとエンジン自身のsequenceが、一つのpoolのpageを取ります。3 rankでのエンジンの既定です（`TF_KV_PAGES` が未設定か `auto`）。TP=2はstreamごとの窓のままです。rank 0の読み込みの行はpageを名指し、そのmodelの数にはエンジン自身のsequenceが入らなくなりました（[checkpoint](README.ja.md#checkpoint)）。全rankのファイルに `TF_KV_PAGES=off` を書けば、3.7.0までと同じく窓のままです。
- GLM-5.3のchat templateに `clear_thinking` が届きます（上流の `c767bd766`）：既定はfalse、rank 0のファイルの `TF_GLM_CLEAR_THINKING=1` でtrue、要求の `chat_template_kwargs.clear_thinking` がその要求では優先します。XSFP4のtemplateは未指定をfalseとするので、指定しない要求の描き方は前と同じです。

### Image and launch

- `serve.sh` は `TF_GLM_NCCL_ID_FILE` を設定せず、`cluster.sh` はrank 0の `/work/nccl-id` を待たず、他のホストへも写さないので、`FAILED: rank 0 wrote no NCCL id` はなくなりました。rank 0は `NCCL_COMM_ID` でNCCLのidを作り、他のrankは線でそれを受け取ります。ファイルが `NCCL_SOCKET_IFNAME` を名指すrank 0以外のrankは（どの例のファイルも名指します）、NCCLの最初の呼び出しの前に `NCCL_COMM_ID` を外します。TP=2のrank 1もこの道でbootstrapします。
- TP=3のrankのファイルは、commentの `ID_FILE` の行に代えて、commentの `TF_KV_PAGES=off` の行を持ちます。
- `config/engine.lock.json` とDockerfileの `ENGINE_REF` は、`release/3.8.0` を `84e0d560`（上流1.1.5）に固定します。

### Documentation

- 文書の測定値は3.8.0の受け入れのものです：[検証](docs/validation.ja.md)の基準値（そのうちdecode検査のhash・編集の返答・NLLは3.3.0の受け入れが決めたまま）、READMEのcheckpoint・配信の既定・制限・[リリースでの測定値](README.ja.md#リリースでの測定値)（3.8.0の表を先頭に置き、前の版の表は残します）、設定の `PARALLEL`、手順書の起動の時間。
- [設定](docs/configuration.ja.md)に、`TF_KV_PAGES`・`TF_GLM_CLEAR_THINKING` と、上流が2026-10-25に足したGLMの道が読む二つの設定、`TENSORFOLD_PREFILL_SHARE` と `TF_QMMF_HALF_BELOW` を、空の値で何をするかとともに載せました。そのNCCLの節・手順書§1と§5・運用・決定・チートシートは、上流のbootstrapを書きます。
- READMEのエンジンの行と2.x系との違いは1.1.5を名指し、`clear_thinking` の制限と、Next Actionの#1178・#1050・`clear_thinking` の項目はなくなりました。決定の、上流のリリースの行とTP=3のbootstrapの行は、3.8.0のリリースのbranchがtagそのものだと書きます。
- README・手順書・運用のコマンドは `glm53-tf3:3.8.0` をbuildして名指します。

### Accepted

2026-10-26に参照機で、リリースのimage（`glm53-tf3:3.8.0`）をそれ自身の `serve.sh` と `cluster.sh` で、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて起動しました：各TPの2回の起動で、XSFP4のdecode検査のhashと `bench --kinds edit` の返答は3.3.0と同じで、1回目ではNLLと199,307 tokenのpromptへの返答も3.3.0と同じで、499,254 tokenのpromptと、TP=3では1,035,295 tokenのpromptの3つの合言葉を全部見つけました。`PARALLEL=` を空にすると、エンジンはTP=2の524,288 tokenの窓で1本、245,760で3本、TP=3ではKVのpageの上で8本のstreamを取り、どれもcountのhashを返しました。tool-eval-bench 2.8.0は、ゲート越しでTP=2が95・TP=3が92、ゲートなしで93と91で、3.6.0と同じ点と、同じ部分点・失敗のシナリオでした。Safety Gateは合格で、`mojibake` は化けた文字を見つけませんでした。同じエンジンで、NVIDIAのNVFP4とFP4-Localも、XSFP4と同じく、BF16の重みに対する次tokenの数が両TPで3.3.0と同じでした（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Not in 3.8.0

3.x系でのNVIDIAのNVFP4と公開したAXLの重み（1.x系と2.x系が配信します）、生成したtokenのlog確率（[制限](README.ja.md#制限)）。

## 3.7.0 — 2026-10-24

道具と文書の版です。imageのファイルは変わらず、3.6.0のままです（`glm53-tf3:3.6.0`、`sha256:cad32a5c50462d4223d16937a83940b5f7a5419ff66278e86e420e46d9fc5083`）。

### Tools

- `python -m glm53_tf mojibake`：日本語と韓国語の答えの化けた文字を数える1.x系の検査（[vLLM #54150](https://github.com/vllm-project/vllm/issues/54150)）を、3.x系のエンジンに向けて。1.x系のpromptで400文字以上の答えを各言語3本ずつ、temperature 0またはsampled（`--temperature`・`--top-p`・`--seed`。i本目はseedにiを足して引く）で求め、答えと `reasoning_content` の中の置換文字（U+FFFD）・孤立サロゲート・改行とタブ以外の制御文字を数え、答えの全文を `--out` に残します。要求は思考のeffortを指定しないので、エンジンは `serve.sh` の既定で考えます。`max_tokens` は `serve.sh` の32,768で、思考と答えがこれを分け合うため、上限で切れた答えはinconclusiveにしました（1.x系はtruncatedの印を付けてpassにします）。各行は長さ、completionのtoken数、応答の `tensorfold` のblockが報告するeffortとsamplingを残します。全ての答えがpassなら0、化けた文字があれば1、それ以外は2で終わります（[設定](docs/configuration.ja.md#道具)）。

### Accepted

- 3.6.0のimageで、各TPに1回の起動：それぞれ12本、temperature 0で6本とsampled（temperature 1.0、top_p 0.95、seed 42〜47）で6本、化けた文字はなく、decode検査のcountは両方の起動で基準のhashを返しました。思考は24本中20本で空で、その文章はほとんど試されていません（[マルチバイト出力](docs/validation.ja.md#マルチバイト出力)）。

### Documentation

- [検証](docs/validation.ja.md)に[マルチバイト出力](docs/validation.ja.md#マルチバイト出力)の節を足しました：検査、そのcommand、合格の条件、基準値。READMEの状況と構成、[設定](docs/configuration.ja.md#道具)の道具、[チートシート](docs/cheatsheet.ja.md#起動を確かめる)の起動の検査がそれを挙げます。
- [チートシート](docs/cheatsheet.ja.md)とREADMEから、上流のTensorFold自身の、CUDAでのこのモデルのrecipeである[GLM-5.3-Flash on CUDA](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md)へリンクしました。上流がこの系列のpull request #1224から自身のmainに入れた頁です。

### Repository

- リポジトリのREADMEに、Macで使うものを書きました（[Macでは](../README.ja.md#macでは)）：この各系列はNVIDIAのGB10機で動き、MacではTensorFoldが自身のMLXのcheckpointでGLM-5.3-Flashを配信します。4-bitのものはそのモデルの表が確かめたMac 2台で、混合幅のものはMac 1台で。3.x系のREADMEはそこを指します。

### Not in 3.7.0

3.x系でのNVIDIAのNVFP4と公開したAXLの重み（1.x系と2.x系が配信します）、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.6.1 — 2026-10-24

文書だけの版です。imageのファイルは変わらず、3.6.0のままです（`glm53-tf3:3.6.0`、`sha256:cad32a5c50462d4223d16937a83940b5f7a5419ff66278e86e420e46d9fc5083`）。

### Documentation

- 新しい頁の[設定](docs/configuration.ja.md)：配信が読む全ての設定を、台本と、imageが固定するエンジンのsourceから並べました：rankのファイル、`serve.sh` が固定するもの、エンジンのflag（labelの後に付けられるものと、GLMが断るもの）、APIのkey、エンジンの環境変数（rankが起動時に比べるものと比べないもの。`TF_ROCE`・`TF_ROCE_MAX_KB`・`TF_GLM_PREFILL_REDUCE` を含む）、NCCL、clusterのファイル、container、メモリの見張り、道具、lockです。READMEの設定の節は、そこを指す要約になりました。
- 新しい頁の[決定](docs/decisions.ja.md)：2.x系が持つのと同じ形で、3.x系が選んだもの・選ばなかったものを、日付・測った効き目・見直すときとともに、エンジン・checkpoint・窓とstream・KV cache・熱・core・draft・fabric・画像の入力について並べ、3.x系で未評価のものも挙げます。理由は、記録のあるところだけに書きました。
- 新しい頁の[チートシート](docs/cheatsheet.ja.md)：上流のTensorFold自身のrecipeを越えてこの構成でできることを、写せる行と代価で並べ、harnessのclientへの注意を二つ書きました：画像はclientが送り直す履歴をまたいで数えること、1M tokenのpromptの最初のtokenはTP=3で約1,000秒後で、1.x系のharnessの注意がZCodeに与える700秒のstreamのtimeoutを越えることです。
- エンジンのsourceと照らした直し：keyのファイルは他のuserが読み書きできると断られ（`0600` と同じく `0400` も通る）、rank 0のファイルの `TENSORFOLD_API_KEY` もkeyを持つこと。prompt cacheは窓の残りで最大16 GiB、TP=3の16.0 GiBはその上限であること。`REASONING_EFFORT` は `low`〜`xhigh` を受け、`max` は起動時にエンジンを止めること（要求では今も指定できる）。動画の上限はMiBであること。熱の天井は3.0.0にもあったこと（3.3.0の節は3.1.0と3.2.0だけを挙げています）。効率coreの代価の1〜3%と起動の約25秒は、3.0.0のエンジンのものであること。
- [運用](docs/operations.ja.md)は、ホストを1.x系へも渡します。1.x系の起動検査は、眠っているだけの3.x系のcontainerがGPUを持つ間は起動を断ります。[手順書](SETUP.ja.md)§8はそこを指し、§6はゲートのtimeoutと本文の上限を書きます。
- [検証](docs/validation.ja.md)は、検査が何の上に立つかを一つの段落で言い、画像・動画・構造化出力の上流自身の配信の検査を、受け入れが回したものとともに名指します。READMEは、TensorFoldの他のrecipeの2.x系の表と、効率coreについての1.1.3のrunbookの節へリンクします。TP=2のrankのファイルの例は、2.x系で測った4 channelの効き目を3.x系のもののようには引かなくなりました。
- swap・ホストのデーモン・peerの喪失を、1.x系の運用から、どの系列も共有する[ホストの準備](../docs/hosts.ja.md)へ移しました。3.x系の運用はそこへリンクし、ホストが消えたときに3.x系のrankがどうするかを、エンジンのsourceから読んで書きます。

### Not in 3.6.1

3.x系でのNVIDIAのNVFP4と公開したAXLの重み（1.x系と2.x系が配信します）、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.6.0 — 2026-10-24

エンジンを上流のTensorFold 1.1.3の上へ移し、3.x系はXSFP4だけを配信します：NVIDIAのNVFP4と公開したAXLの重みは3.x系の選択肢から外れ、1.x系と2.x系には残ります。

### Engine

- forkのbranch `release/3.6.0`（`21778b05`）は、上流v1.1.3に、pull request #1050のcode（15のcommit、上流でopen）と、TP=3のためのこの系列のNCCLのidのファイルを足したものです。そのcommentは今、この系列のpull request #1178を名指します（上流はTPのbootstrap #636を閉じました）。1.1.3から、indexがmodelのfolderの中のfolderにあるshardを名指せることは上流自身のcodeにあるので、3.3.0から持っていたpull request #1179のpatchはbranchから外れます。他のcommitが変える行は、そのcommentを除いて3.5.0と同じです。
- 1.1.3の `zig build grammar` は `libtfgrammar` をnativeのserverの隣、`zig-out/native/lib` に置くので、imageはそこから取ります。Zig・xgrammar・mediaのlibraryは3.5.0の版のままで、1.1.3もその版を固定しています。

### XSFP4 alone

- `download` と `verify-download` は既定の `--checkpoint xsfp4` だけを受け、状態は前と同じく `state/xsfp4` に残します。`pinned` と `axl` は断り、`config/model.lock.json` と `config/axl.lock.json` は系列から外れます。`serve.sh` のcommentはXSFP4だけを名指し、引数は変わりません：rankのファイルの `CHECKPOINT` は今も別のfolderを名指せますが、3.x系の受け入れはそれを扱いません。
- rankのファイルの例から、NVIDIAのNVFP4のためのcommentの `CHECKPOINT` の行と、TP=2でそれに伴っていた245,760 tokenの窓を外しました。
- XSFP4は `88736f91` に固定します。hubの `59c49ac9` の後のrevisionが変えたのはモデルカードだけです（全fileのsize・blob・LFSのsha256を照らし、両側とも53 file）。`serve.sh` は同じbyteを読み、snapshotには直したカードが入ります。
- 公開の監査は、TensorFoldの各系列に、それが配信するcheckpointのlockを求めます（2.x系は `config/model.lock.json`、3.x系は `config/xsfp4.lock.json`）。系列が同じcheckpointを固定するかの系列間の試験は1.x系と2.x系を見ます。

### Image

- `serve.sh` はrank 0のアドレスを両TPで一度だけ名指し、`REASONING_EFFORT` を一度だけ読みます。引数は前と同じです。冒頭のcommentは、上流が#1178を取り込むまでNCCLのidのファイルが残ること、`cluster.sh` は既定の `/work/nccl-id` だけを写すことを書き、TP=3に `TF_GLM_MM=0` が要るとはもう書きません（上流1.1.2がissue #1067を直しました）。
- DockerfileのNCCLのcommentはホストを名指さず、imageはNOTICEが名指すリポジトリの `LICENSES/` を持ちます。

### Documentation

- 3.x系のREADME・手順書・運用・検証はXSFP4だけを書きます。検証の基準値は全節で、3.3.0の受け入れで決めたXSFP4のものです。NVIDIAのprocessorに照らすTP=2の動画の検査はNVIDIAのNVFP4と一緒に外し、2.x系のNLLの列は参考として残します。checkpointの節は、同じエンジンでのNVIDIAのNVFP4の数を比べとしてだけ載せます。
- 検証のtool-eval-benchの基準は、3.5.3のimageでの2.8.0のものです：TP=2で95、TP=3で92、Safety Gateは合格。2.7.0と2.8.0は多くのシナリオを2.6.1.dev52（XSFP4は両TPで93）より厳しく採点するので、版の違う点数は比べられません。
- tool引数ゲートを、TensorFoldにないこのリポジトリの中継として、手順書§6・検証・READMEで名指しました。検証とREADMEの測定値は、tool-eval-benchのゲートなしの点をゲート越しの点と並べます。
- リポジトリのREADME・文書の地図・ライセンスの手引きは、XSFP4を3.x系のcheckpointとして名指します。Next ActionはNCCLのidのファイルについて#1178を待ち、#1179の項目は済みました。README・手順書・運用のコマンドは `glm53-tf3:3.6.0` をbuildして名指し、手順書の起動の時間は3.6.0のものです。

### Accepted

2026-10-24に参照機で、リリースのimage（`glm53-tf3:3.6.0`）をそれ自身の `serve.sh` と `cluster.sh` で、rankのファイルに `CHECKPOINT` も `CONTEXT` も書かず、全containerを効率coreに置いて起動しました：各TPの2回の起動で、XSFP4のdecode検査のhashと `bench --kinds edit` の返答は3.3.0と同じで、1回目ではNLLと199,307 tokenのpromptへの返答も3.3.0と同じで、499,254 tokenのpromptと、TP=3では1,035,295 tokenのpromptの3つの合言葉を全部見つけました。TP=2で `PARALLEL=` を空にした起動は1本のstreamを取り、countのhashを返しました。ゲート越しのtool-eval-bench 2.8.0は、TP=2で95、TP=3で92で、3.5.3のimageと同じ点と、同じ部分点・失敗のシナリオでした。ゲートなしでは、各TPでもう1回の起動で93と91で、Safety Gateは合格、TC-43も落としました（[リリースでの測定値](README.ja.md#リリースでの測定値)）。

### Not in 3.6.0

3.x系でのNVIDIAのNVFP4と公開したAXLの重み（1.x系と2.x系が配信します）、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.5.3 — 2026-10-24

文書と道具だけの版です。imageのファイルは変わらず、3.5.0のままです（`glm53-tf3:3.5.0`、`sha256:ac98364d3745d55ec016ab60617a77ef87c5af2ae0ce877a14381e810c4b850c`）。

### Documentation

- [検証](docs/validation.ja.md)：`score-nll` の例はXSFP4の `tokenizer.json`（NVIDIAのNVFP4のものと同じファイル）を読み、全要求が答えればpassで、各本文の2回の差は報告として出ること、熱の見張りには3.x系のcontainerとprocessを渡すこと、containerの中では作業directory（cacheの他にcontainerがmountする唯一のホストのdirectory）の下のcheckoutから道具を動かすことを書きました。
- [README](README.ja.md)：TP=2のrank 0のmodelの大きさは245,760 tokenの窓のもの、その窓でNVIDIAのNVFP4が2本のstreamに残すprompt cacheは、1本のときの5.2 GiBに対して1.5 GiBで、配信の既定は1本のときを5.1〜5.2 GiBと書く、配信の既定のKVの行は制限の節の選んで使うFP8のlatent cacheを指す、設定の表に `VISION` を足し、`cluster.sh` が写すのは `/work/nccl-id` だけと書いた、構成に `docker/Dockerfile.build` と `assets/` を足した、未検証の項目はそれぞれの置き場へリンクする、Next Actionの#1053の測り直しは開いたまま（3.3.0の後のリリースは効率coreで回した）。
- [手順書](SETUP.ja.md)：`API_KEY_FILE` はrank 0のもの、tool引数ゲートはcontainerの中では作業directoryの下のcheckoutから。[測り方](docs/benchmarks.ja.md)：499,622 tokenのpromptは3.5.0からTP=2でも。
- TP=3のrankのファイルの例から、2.x系から写した2つのコメント（そのエンジンの4 channelの時間、そのTCPStore）を外し、`cluster.sh` が写すのは既定の `ID_FILE` の場所だけと書きました。

### Tools

- 振る舞いは変わりません：`agreement.py` から、3.x系のどの道具も使っていない `TEXTS` と `compare_records`（`score-nll` はNLL採点セットの本文を渡す）を、その6つのテストと一緒に外しました。`tool-gate` のhelpに `--timeout` を足し、`bench` と `download` は他が持つ名前を使い回さなくなりました。

### Repository

- [ホストのツール](../host/README.ja.md)に、熱の見張りの3.x系の起動を書きました。既定値（2.x系のcontainerとprocess）のままでは、3.x系のホストではエンジンが見つからず、一度も読まずにすぐ終わります。3.x系のエンジン自身の熱の待ちと `nccl_probe.py` も挙げ、見張りのhelpも同じことを言います。
- リポジトリのREADME、[ライセンスの整理](../docs/licensing.ja.md)、ホスト・ネットワーク・NCCLの頁、文書一覧、`CONTRIBUTING`、`AGENTS.md` で、2つの系列を挙げていた所に3.x系を足しました：画像と動画、imageのlibjpeg-turbo・libwebp・FFmpeg（LGPL-2.1-or-later）、MITの重みと並ぶXSFP4のOpen Model Agreement、3.x系の手順書・rankのファイル・7.0のkernelでのリリース。

### Not in 3.5.3

公開したAXLの重み、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.5.2 — 2026-10-24

文書だけの版です。imageのファイルは変わらず、3.5.0のままです（`glm53-tf3:3.5.0`、`sha256:ac98364d3745d55ec016ab60617a77ef87c5af2ae0ce877a14381e810c4b850c`）。

### Documentation

- [リリースでの測定値](README.ja.md#リリースでの測定値)の、数を2度書く振る舞いを、fp32の参照とvLLMでの測りを受けて直しました。場所はこのエンジンではなくcheckpointのものです。同じ重みをfp32で計算しても、NVIDIAのNVFP4は生成が2度書く所で152をもう一度選び、同じcheckpointのvLLMも同じ場所でほぼ同じ回数だけ数を外します。3.5.1の「重みではなくエンジンから来ます」は取り下げ、項の名を「数を2度書くこと」にしました（英語版はXSFP4のmodel cardと同じA number written twice）。測りは[TensorFold #1214](https://github.com/ashhart/TensorFold/issues/1214)にあります。

### Not in 3.5.2

公開したAXLの重み、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

## 3.5.1 — 2026-10-24

文書だけの版です。imageのファイルは変わらず、3.5.0のままです（`glm53-tf3:3.5.0`、`sha256:ac98364d3745d55ec016ab60617a77ef87c5af2ae0ce877a14381e810c4b850c`）。

### Documentation

- [リリースでの測定値](README.ja.md#リリースでの測定値)のエンジンの既知の振る舞いを言い直しました。壊れた1か所の値は見つかっておらず、バグとみるかは上流の[TensorFold #1214](https://github.com/ashhart/TensorFold/issues/1214)で問うています（3.4.0はバグとみられると書いていました）。数を守るのが生成とprefillのいつも片方とは限らず、TP=3でも起き、場所はbuildでも変わります。
- 制限の節に、選んで使うFP8のlatent cacheをTP=2で一度試した結果を書きました（1,048,576 tokenの窓に1本入り、1,035,295 tokenのpromptで3つの合言葉を全部見つけた）。`serve.sh` はBF16のままです。
- 3.5.0の段落に、同じimageでのeditの速さのA/Bを足しました（245,760と524,288のどちらも中央値82.4〜82.8 tok/s）。

### Not in 3.5.1

公開したAXLの重み、生成したtokenのlog確率、chat templateへの `clear_thinking` の受け渡し（[制限](README.ja.md#制限)）。

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

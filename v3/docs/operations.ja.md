# 運用（3.x）

[English](operations.md) · [3.x系の概要](../README.ja.md) · [配備の手順書](../SETUP.ja.md) · [検証](validation.ja.md)

3.x系の起動がうまくいかないときにすることと、その周りの日常の作業（新しいcontainer、新しいimage、別のcheckpoint、電源が落ちたホスト、ホストを2.x系へ渡す）です。各節は、台本が何をするかと、参照機がどの場合に出会ったかを書きます。出会っていない場合はそう書きます。コマンドはcheckoutのルートから、clusterのファイルを `state/cluster.env` に置いて実行します（[手順書 §5](../SETUP.ja.md#5-起動)）。ホストを変える他のコマンドと同じく、運用者が許可した時間の中で行います。

## 起動の結果

`cluster.sh state/cluster.env start <label>` の終わり方は次のどれかです：

- **`READY after N s`** とrank 0の最後の8行の `[tensorfold]` と `[serve.sh]`。起動の行と、参照機で起動にかかった時間は[手順書 §5](../SETUP.ja.md#5-起動)にあります。
- **`FAILED on rank R`**：あるrankのlogに `REFUSE` の行があるか、あるrankのcontainerでエンジンが動いていない。台本は全rankのlogの最後の25行（NCCLの `INFO` の行を除く）を表示して終わり、何も止めません。他のrankとメモリの見張りは動いたままのことがあるので、次の起動の前に `cluster.sh state/cluster.env status`、続いて `stop` を実行します。
- **`FAILED: rank 0 wrote no NCCL id`**（TP=3）：rank 0が5分以内に `/work/nccl-id` を書かなかったか、そのエンジンが先に終わった。rank 0は全rankの生存の線がつながってから書くので、全rankのlogを読みます。
- **`TIMEOUT`**：15分以内にrank 0の `serving` の行が出ない。全rankのlogを読み、上と同じく `stop` します。

各rankのlogは `<WORK>/logs/serve-r<RANK>-<LABEL>.log` で、同じlabelの起動が上書きします。前のlogを残すには、起動ごとに別のlabelを付けます。メモリの見張りは `hostwatch-<LABEL>.log` に追記します：2秒ごとの時刻とGiB単位の `MemAvailable`、エンジンを止めたときの `KILLED`、エンジンがいなくなったときの `done` です。

エンジンは起動時に、空きメモリからstreamの大きさを決め、入らない大きさは断って、rankのうち最も余裕の小さいものを名指しします。例えば `--parallel 2 needs 4.55 GiB for its streams at a 245760-token window, and the CUDA memory budget leaves 4.41 GiB on rank 1, the smallest room of the ranks: serve --parallel 1, or lower --context` です（TP=2、3.0.0のエンジンで参照対が出会いました）。GB10の統合メモリでは、エンジンは空きを `/proc/meminfo` の `MemAvailable` から取り、これはページキャッシュを空きに数えるので、前の読み込みでキャッシュに残ったファイルはその余裕を食いません：別のcheckpointのファイル28 GiBをページキャッシュに置いたまま、3.0.0のTP=2の起動は5.2 GiBを残しました（キャッシュを外した起動は4.4 GiB）。受け入れの窓は各起動の前にHugging Faceのcacheのファイルをページキャッシュから外しましたが（各ファイルに `os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)`）、これは2.x系から残した手順で、エンジンには要りません。

## 一つのrankが止まり、他は待つ

ホストのエンジンを止める見張りは二つで、どちらも自分のホストだけに働きます：

- **メモリの見張り**（`hostwatch.sh`、`cluster.sh` が起動）は、`MemAvailable` が5 GiBを切るとcontainerの中の `pkill -9` でエンジンを止め、`KILLED` と書きます。
- **熱の見張り**（[`host/thermal-watch`](../../host/README.ja.md#長い運転の間)、運用者が `--container glm53-tf3 --process 'tensorfold-native serve'` で起動）は、94 °C以上の読みが2回続くとエンジンを止め、`ABORT` と書きます。

3.0.0〜3.3.0の受け入れでは、どちらもエンジンを止めませんでした。2.x系では、一つのrankが終わっても他のrankは一緒には終わらず、`cluster.sh stop` が終わらせるまでcollectiveで待ちました。どれかのrankが止まったら、全rankを止め、見張りのlogで原因を探し、全rankを起動し直します。

エンジンの熱の待ちは、どれかのrankの最も熱いzoneが92 °Cを超えている間、chunkの合間でpromptの処理を止め、全rankが88 °C以下になるまで待ちます（[配信の既定](../README.ja.md#配信の既定)）。待ちに時間の上限はありません。待つごとの秒数は、rank 0のlogの `heat_wait_s` の行に出ます。

熱の見張りは全てのACPIのzoneを読み、GB10の7つのzoneのうち5つはCPUのものです。エンジンの空回りするthreadは返答の長い連続の間これを温め、熱の待ちはそれを止めません。containerの既定のcoreがこれを低く保ちます（[効率coreにする理由](../README.ja.md#配信の既定)）。全coreで作ったcontainerは `docker update` で移せます（[containerを作り直す](#containerを作り直す)）。

## エンジンが残る停止

`cluster.sh state/cluster.env stop` はrank 0のcontainerの中で `pkill -TERM -f 'tensorfold-native serve'` を送り（他のrankはrank 0が終わると抜けます）、rankごとにエンジンが終わるのを最大60秒待ち、まだ動いているrankに同じものを送ってから、各ホストのエンジンのプロセス数と `MemAvailable` を表示します。数が0より大きいrankはまだ動いています：`docker exec glm53-tf3 pkill -9 -f 'tensorfold-native serve'` か、containerの中の全プロセスを終わらせる `docker stop glm53-tf3` の後、もう一度 `status` を実行します。3.0.0と3.1.0の受け入れでは、どの停止も全rankで0で終わりました。

## NCCLがsocketに落ちる

rankどうしはTCPのsocketではなくRoCEで話す必要があります：

- `create_container.sh` は、NCCLがsocketに落ちる `/dev/infiniband` の無いホストを拒みます。
- rankのファイルの `NCCL_DEBUG=INFO` と `NCCL_DEBUG_SUBSYS=INIT,NET` で、NCCLは起動時に各接続の経路を一度logに出します。`grep -c 'via NET/IB' <WORK>/logs/serve-r<RANK>-<LABEL>.log` で数え、`NET/Socket` は一つもあってはいけません。
- `NET/IB` でない接続があれば、rankのファイルをホストと照らします：`NCCL_IB_HCA`、`NCCL_IB_GID_INDEX`、`NCCL_SOCKET_IFNAME`。どれも[手順書 §1](../SETUP.ja.md#1-機体とfabric)で記録したものです。GIDのindexは、リンクが落ちたりホストの電源が落ちたりした後に動くことがあります（[GID indexが動く](../../docs/nccl-validation.ja.md#gid-indexが動く)）。

3.0.0〜3.3.0の受け入れでは、どの起動も全接続が `NET/IB` でした。

## containerを作り直す

`cluster.sh state/cluster.env stop` の後、各ホストで：

```sh
docker rm -f glm53-tf3                                  # containerは起動の合間は眠っているだけ
v3/scripts/create_container.sh glm53-tf3:3.4.0 ~/glm53-tf3
```

`create_container.sh` はcontainerに名前を付けるので、古いものを先に消します（または改名します：`docker rename glm53-tf3 glm53-tf3-old` の後に `docker stop`）。ホストのディレクトリは残ります：rankのファイルとlogです。containerの中では何もbuildしません。

作るときにcontainerのcoreを出します（[手順書§4](../SETUP.ja.md#4-各ホストのcontainerとrankのファイル)）。後からは `docker inspect -f '{{.HostConfig.CpusetCpus}}' glm53-tf3` で見られ、全coreなら空です。別のcoreに移すのに新しいcontainerは要りません：次の起動の前に `docker update --cpuset-cpus 0-4,10-14 glm53-tf3` で移します。

## 新しいimageへ移る

新しいimageは新しいエンジンのbuildです。日常の利用の前に受け入れ直します。

1. 一台でbuildします（[手順書 §3](../SETUP.ja.md#3-image)）。先に全ホストで、使っているimageに二つ目のtagを付けて残します。戻るのがcontainer一つで済みます。
2. 他のホストへ読み込み、全ホストのimageのIDを比べます。等しくなければなりません。各containerの `/usr/share/doc/tf3/ENGINE` が、エンジンのcommitと各binaryのSHA-256を示します。
3. 止めてから、全ホストで新しいimageからcontainerを作り直します（[上](#containerを作り直す)）。
4. 起動し、decode検査から[検証](validation.ja.md)を回します。同じエンジンのcommitのimageは基準のhashを出さなければなりません。エンジンを動かすリリースは、どのhashがなぜ変わるかをその検証に書きます（3.1.0：上流のtiledのkernelでのTP=2。3.3.0：上流1.1.2で、TP=3もそのkernelで）。それ以外の違いは説明すべき所見で、置き換える値ではありません。

## checkpointを替える

既定のXSFP4とNVIDIAのNVFP4（[checkpoint](../README.ja.md#checkpoint)）は同じimageとcontainerで動きます。どちらにするかはrankのファイルが決めます。

1. 全ホストでもう一方のcheckpointを取得して検証します（[手順書 §2](../SETUP.ja.md#2-checkoutとcheckpoint)）。両方をcacheに置いたままにできます。
2. 止めてから、全rankのファイルの `CHECKPOINT` をNVIDIAのNVFP4のsnapshotにするか、XSFP4（`serve.sh` の既定）ならその行を消します。rankがそれぞれ別のcheckpointを名指すと、エンジンは起動を断ります。
3. 起動し、そのcheckpointの基準値に照らして[検証](validation.ja.md)を回します。あるcheckpointの最初の起動はそれをdiskから読むので、参照機のTP=2で約300秒長くかかりました。

## 電源が落ちたホスト

GB10のホストは持続する負荷で電源が落ちることがあります（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）。参照機は3.x系では落ちていないので、この節は記録した復旧ではなく台本からの読みです。予防はクロックの上限、熱の待ち、長い要求の合間の冷却gate、熱の見張りです。

- 他のホストのrankはcollectiveで待つので、止めます。
- `create_container.sh` は再起動の方針を設定しないので、ホストが起動してもcontainerは動いていません。`docker start glm53-tf3` するか、作り直します。
- 起動の前に、[ホストの準備](../../docs/hosts.ja.md)が不正な再起動の後について書くことと、そのGIDのindexを確かめます。
- 全rankを一緒に起動し、日常の利用の前にdecode検査を回します。

## ホストを2.x系へ渡す

```sh
v3/scripts/cluster.sh state/cluster.env stop
docker stop glm53-tf3          # 全ホストで
```

3.x系と2.x系のcontainerはどちらも全GPUを要求するので、エンジンは一度に一つの系列だけを動かします。`docker start glm53-tf` と2.x系の `cluster.sh` でホストを2.x系へ渡し（[2.x系の手順書](../../v2/SETUP.ja.md)）、`docker start glm53-tf3` で、同じcontainerと作業ディレクトリのまま戻します。

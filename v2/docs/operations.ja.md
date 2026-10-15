# 運用（2.x）

[English](operations.md) · [2.x系の概要](../README.ja.md) · [セットアップ手順書](../SETUP.ja.md) · [検証](validation.ja.md)

2.x系の起動がうまくいかないときにすることと、その周りの日常の作業（containerの作り直し、新しいimage、電源が落ちたホスト、ホストを1.x系へ渡す）です。各節は、台本が何をするかと、参照機がどの場合に出会ったかを書きます。出会っていない場合はそう書きます。コマンドはcheckoutのルートから、clusterのファイルを `state/cluster.env` に置いて実行します（[手順書 §6](../SETUP.ja.md#6-起動)）。ホストを変える他のコマンドと同じく、運用者が許可した時間の中で行います。

## 起動の結果

`cluster.sh state/cluster.env start <label>` の終わり方は三つです：

- **`READY after N s`** とrank 0の最後の8行の `[tensorfold]`。起動の行と、参照機で起動にかかった時間は[手順書 §6](../SETUP.ja.md#6-起動)にあります。
- **`FAILED on rank R`**：あるrankのlogに `Traceback` があるか、あるrankのcontainerでエンジンが動いていない。台本は全rankのlogの最後の25行を表示して終わり、何も止めません。他のrankとメモリの見張りは動いたままのことがあるので、次の起動の前に `cluster.sh state/cluster.env status`、続いて `stop` を実行します。
- **`TIMEOUT`**：15分以内にrank 0の `serving` の行が出ない。全rankのlogを読み、上と同じく `stop` します。

各rankのlogは `~/glm53-tf/logs/serve-r<RANK>-<LABEL>.log` で、同じlabelの起動が上書きします。前のlogを残すには、起動ごとに別のlabelを付けます。メモリの見張りは `hostwatch-<LABEL>.log` に追記します：2秒ごとの時刻とGiB単位の `MemAvailable`、エンジンを止めたときの `KILLED`、エンジンがいなくなったときの `done` です。

新しいimageを読み込んだ直後や、別のエンジンが重みを読んだ直後には、起動が `CUDA startup memory budget cannot fit requested context 300000` ですぐに止まることもあります。GB10の統合メモリでは、CUDAが返す空きはページキャッシュの分を含まないので、キャッシュに残った重みが窓の余裕を食います（2026-10-06には9 GiBのキャッシュで空きが108.8 GiBになり、TP=2の窓が入りませんでした）。全ホストでHugging Faceのcacheのファイルのキャッシュを捨てるようカーネルに伝え（各ファイルに `os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)`、rootは要りません）、起動し直します。起動が見る空きは、containerの中の `python3 -c "import torch; print(torch.cuda.mem_get_info())"` で分かります。

どの重みを配信するかはrankのファイルの `CHECKPOINT` で決まります：設定しなければ固定のsnapshot、任意で公開したAXLの重みのsnapshotです（[設定](../README.ja.md#設定)）。変えるには、止めてから全rankのファイルに同じ `CHECKPOINT` を書き、起動し直します。違うcheckpointで起動したrankどうしは起動を断ります。

## 一つのrankが止まり、他は待つ

ホストのエンジンを止める見張りは二つで、どちらも自分のホストだけに働きます：

- **メモリの見張り**（`hostwatch.sh`、`cluster.sh` が起動）は、`MemAvailable` が5 GiBを切るとcontainerの中の `pkill -9` でエンジンを止め、`KILLED` と書きます。
- **熱の見張り**（[`host/thermal-watch`](../../host/README.ja.md#長い運転の間)、運用者が起動）は、94 °C以上の読みが2回続くとエンジンを止め、`ABORT` と書きます。

他のrankは一緒には終わりません。2026-10-04、同じ規則の熱の見張りが、熱の待ちの無いエンジンでTP=3の1M tokenのprefillを始めて6分半のところでrank 0を止めました。rank 1と2はそれ以上何もlogに出さずcollectiveで待ち、そのメモリの見張りも動いたままで、`cluster.sh state/cluster.env stop` がそれらを終わらせました。どれかのrankが止まったら、全rankを止め、見張りのlogで原因を探し、全rankを起動し直します。記録ではいつも全rankを一緒に起動し直しており、一つのrankだけの起動は試していません。

メモリの見張りが配信中のエンジンを止めたことは参照機ではありません。参照機が下がった `MemAvailable` の最低値は[検証](validation.ja.md#メモリと温度)にあります。止め方そのものは、containerの中のrootのプロセスで確かめました。ホストの利用者の `pkill` はそれに「許可されていない操作」で失敗し、それでも0を返します。見張りが `docker exec` を通るのはこのためです。

エンジン自身の熱の待ちが、長いprefillを熱の見張りの「94 °Cが2回続く」より下に保ちます（[配信の既定](../README.ja.md#配信の既定)）。1M tokenのpromptの終わり近くでは、chunkの合間の確認の後にchunk一つで約7 °C上がるので、待ちは1 chunk先も見込み、続けて流した直前のchunkの上がり幅で見込める範囲で次の読みを93 °C以内に保ちます。それでも越えることはあり、2.4.0の受け入れでは上がり幅がほぼ0のchunkの次のchunkが1回、2.9.2の1M tokenの確かめでは待ちの2つ後のchunkが9回（最高93.7 °C、終盤は上がり幅が増える）越えました。越えると次の確認で待ちに入ります（[リリースでの測定値](../README.ja.md#リリースでの測定値)、[決定の記録](decisions.ja.md#熱)）。待ちに時間の上限はありません。一度始まると、全ホストが下の帯以下になるまで要求は待ち、その間は全rankが1分ごとに `[tensorfold] heat: waiting <s> s, hottest zone <°C> C` を出します。この行は部屋が熱いことを示し、エンジンが止まっていることを示すものではありません。

## エンジンが残る停止

`cluster.sh state/cluster.env stop` はrank 0から順に各containerの中で `pkill -f 'tensorfold serve'` を送り、rankごとにエンジンが終わるのを最大60秒待ってから、各ホストのエンジンのプロセス数と `MemAvailable` を表示します。数が0より大きいrankはまだ動いています。停止の直後の `MemAvailable` は、メモリを解放している途中で低く出ることがあります：参照対のある停止で、直後に16 GiB、20秒後に117 GiBでした。

参照機の記録では、どの停止も全rankで0で終わり、次の手は要りませんでした。数が0のままにならないホストで要るのは、見張りと同じ形の `docker exec glm53-tf pkill -9 -f 'tensorfold serve'` か、containerの中の全プロセスを終わらせる `docker stop glm53-tf` です。その後でもう一度 `cluster.sh state/cluster.env status` を実行します。

## NCCLがsocketに落ちる

rankどうしはTCPのsocketではなくRoCEで話す必要があります：

- `create_container.sh` は、NCCLがsocketに落ちる `/dev/infiniband` の無いホストを拒みます。
- rankのファイルの `NCCL_DEBUG=INFO` と `NCCL_DEBUG_SUBSYS=INIT,NET` で、NCCLは起動時に各接続の経路を一度logに出します。`grep 'via NET' ~/glm53-tf/logs/serve-r<RANK>-<LABEL>.log` で一覧でき、どれも `NET/IB` でなければなりません。TP=2では、行が両方のrail（`NET/IB/0` と `NET/IB/1`）を同じ数ずつ示します。片方しか出ないなら `NCCL_IB_HCA` を確かめます。
- `NET/IB` でない接続があれば、rankのファイルをホストと照らします：`NCCL_IB_HCA`（リンク上のRDMAデバイス、両方のrail）、`NCCL_IB_GID_INDEX`（リンクのIPv4アドレスでRoCE v2になる項目）、`NCCL_SOCKET_IFNAME`（rankが待ち合わせるinterface）。どれも[手順書 §1](../SETUP.ja.md#1-機体とfabric)で記録したものです。GIDのindexは、リンクが落ちたりホストの電源が落ちたりした後に動くことがあります（[GID indexが動く](../../docs/nccl-validation.ja.md#gid-indexが動く)）。[NCCLの診断](../../docs/nccl-validation.ja.md)はエンジン抜きでfabricを確かめます。

記録に残る2.x系の起動では、どれも全接続が `NET/IB` でした。

## containerを作り直す

`cluster.sh state/cluster.env stop` の後、各ホストで：

```sh
docker rm -f glm53-tf                                  # containerは起動の合間は眠っているだけ
v2/scripts/create_container.sh glm53-tf:2.9.2
docker exec glm53-tf bash /opt/glm53-tf/build_ext.sh
```

`create_container.sh` はcontainerに名前を付けるので、古いものを先に消します。ホストのディレクトリ `~/glm53-tf` は残ります：rankのファイル、compileしたextension（`ext/`）、logです。`build_ext.sh` はそのimageに足りないextensionをbuildし、残りはbuild済みのものを見つけます。新しいcontainerでの最初の起動の前に毎回実行します。

## 新しいimageへ移る

新しいimageは新しいエンジンのbuildです。日常の利用の前に受け入れ直します。

1. 一台でbuildします（[手順書 §3](../SETUP.ja.md#3-image)）。先に全ホストで、使っているimageに二つ目のtagを付けて残します（記録と同じく `docker tag glm53-tf:<current> glm53-tf:<current>-<engine>`）。戻るのがcontainer一つで済みます。
2. 他のホストへ読み込み、全ホストのimageのIDを比べます。等しくなければなりません。`docker images` が示すIDはbuildの来歴も含み、buildしたcheckoutごとに変わります（[changelogの2.0.0](../CHANGELOG.ja.md)）。
3. 止めてから、全ホストで新しいimageからcontainerを作り直し、`build_ext.sh` を実行します（[上](#containerを作り直す)）。参照機では、新しいエンジンのたびに7つのextensionを全部buildし直し、1台あたり約155〜160秒でした。
4. 起動し、decode検査から[検証](validation.ja.md)を回します。新しいエンジンは基準のhashを出さなければなりません。出さなければ、それは説明すべき所見で、置き換える値ではありません。

戻すには、残したtagからcontainerを作り直します。

## 電源が落ちたホスト

GB10のホストは持続する負荷で電源が落ちることがあります（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）。参照機は2.x系では落ちていないので、この節は記録した復旧ではなく台本からの読みです。予防はクロックの上限、長い要求の合間の冷却gate、熱の見張りです（[ホストのツール](../../host/README.ja.md#長い運転の間)）。

- 他のホストのrankは上と同じくcollectiveで待つので、止めます。
- `create_container.sh` は再起動の方針を設定しないので、ホストが起動しても `glm53-tf` のcontainerは動いていません。`docker start glm53-tf` するか、作り直します。
- 起動の前に、[ホストの準備](../../docs/hosts.ja.md)が不正な再起動の後について書くこと（負荷時のクロックと電力）と、そのGIDのindex（[GID indexが動く](../../docs/nccl-validation.ja.md#gid-indexが動く)）を確かめます。参照対では1.x系の運用中、headの電源が落ちた後にpeerのrailの一つのindexが動きました。
- 全rankを一緒に起動し、日常の利用の前にdecode検査を回します。

## ホストを1.x系へ渡す

```sh
v2/scripts/cluster.sh state/cluster.env stop
docker stop glm53-tf          # 全ホストで
```

エンジンを止めるだけでは足りません。containerは全GPUを指定して作られており、1.x系の `server preflight` は、他の動いているcontainerがGPUを要求していると起動を拒みます：2026-10-04、眠っているだけでGPUのプロセスの無い `glm53-tf` のcontainerがホストで動いていたため、`exclusive_gpu` がfalseで拒みました（[1.x系の起動検査](../../v1/docs/operations.ja.md#フルモデルの起動検査)）。`docker start glm53-tf` で、同じcontainerと `~/glm53-tf` のままホストを2.x系へ戻せます。その前に、[必要な環境](../README.ja.md#必要な環境)のとおり1.x系のサーバーを止めます。

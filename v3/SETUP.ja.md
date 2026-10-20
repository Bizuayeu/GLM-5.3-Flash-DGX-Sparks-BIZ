# 配備の手順書（3.x）

[English](SETUP.md) · [3.x系の概要](README.ja.md) · [検証](docs/validation.ja.md)

2台のTP=2または3台のTP=3で、TensorFoldのネイティブエンジンの3.x系を配信する手順を順に並べます。機体・ケーブル・kernel・checkpointの準備は2.x系と同じで、その段は[2.x系の手順書](../v2/SETUP.ja.md)を指します。全ホストに同じcheckoutを置き、以下のコマンドはimageのbuild contextがあるそのルートから実行します。この系列のPythonの道具は `v3/` から実行します。ホストを変えるコマンド（他のサーバーの停止、このサーバーの起動）は、運用者が許可した時間の中で行います。

## 1. 機体とfabric

[2.x系の手順1](../v2/SETUP.ja.md#1-機体とfabric)のとおりです：ConnectX-7のリンクを持つDGX Sparkまたは互換のGB10機を2台か3台、対は直結、3台はリングにし、各ホストのRDMAデバイス名、RoCE v2のGIDのindex、rankが待ち合わせるアドレスを記録し、長い処理の前にGPUクロックに上限を設けます。参照機のリングでは、TP=3の各ホストのアドレスはdummyのinterfaceの `/32` で、リンクの上に経路を張ります（[3台をリングにつなぐ](../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。rankどうしの生存の線は `NCCL_COMM_ID` でそこのrank 0に届きますが、NCCLはそれで集まれないので、TP=3では各rankがNCCLの環境からそれを外し、rank 0がNCCLのidをファイルに書き、他のrankがそれを読みます（[手順5](#5-起動)）。

## 2. checkoutとcheckpoint

全ホストで同じ確認済みのcommitをcheckoutします（`v3.*` のリリースのtag）。checkpointは1.x系・2.x系と同じもので、revisionは [`config/model.lock.json`](config/model.lock.json) にあります。2.x系のためにすでに持っているホストはそのまま使えます。無ければ `v3/` から道具の仮想環境を用意し、[2.x系の手順2](../v2/SETUP.ja.md#2-checkoutとcheckpoint)のとおりに取得して検証します：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/huggingface.lock.txt
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait
```

エンジンは各ホストのHugging Faceのcache（既定は `~/.cache/huggingface/hub`）からcheckpointを読み、containerには読み取り専用でmountします。

## 3. image

GB10ホストの1台（linux/arm64）で、checkoutのルートからbuildします：

```sh
docker build -f v3/docker/Dockerfile -t glm53-tf3:3.2.0 .
docker image inspect --format '{{.Id}}' glm53-tf3:3.2.0
```

buildは、[`config/engine.lock.json`](config/engine.lock.json) のcommit（`ENGINE_REF`）のTensorFoldのBIZ releaseからエンジンをcompileします。Zigのcompilerはlockが名指す版で、SHA-256で確かめます。構造化出力の `libtfgrammar` も、lockが固定するxgrammarのreleaseからcommitで確かめてbuildします。画像と動画の入力のために、lockがSHA-256で固定するreleaseのtarballから、libjpeg-turbo・libwebpのdecoder・静的なFFmpegをbuildし、そのFFmpegの上にエンジンの `libtfvideo` を作ります。実行のimageには、`/usr/local/bin` に `tensorfold-native` と `tf-cuda-test`、`/usr/local/lib` に `libtfgrammar.so`・`libturbojpeg.so.0`・`libwebpdecoder.so.3`・`libtfvideo.so`、NCCL 2.30.7とRDMAのuserspace、`/opt/glm53-tf3/` に `serve.sh`、エンジンのcommitとmediaのreleaseと各binary・libraryのSHA-256を書いた `/usr/share/doc/tf3/ENGINE`、このリポジトリ・xgrammar・libjpeg-turbo・libwebp・FFmpeg・エンジンの表示（`/usr/share/doc/tf3/` の下）が入ります。2つのbaseのimageはdigestで固定しています。参照機では、baseのimageを取ってから3.2.0のimageのbuildに約13分かかりました。同じcommitでも別のホストでbuildするとbinaryのSHA-256が変わることがあります（参照機のbuildでもそうでした）。2つのbuildが同じに答えるかは、hashではなくdecode検査で見ます。他のホストへimageを写し（リンク越しに `docker save glm53-tf3:3.2.0 | ssh <host> docker load`）、全ホストのimage IDを比べます。同じでなければいけません。

## 4. 各ホストのcontainerとrankのファイル

```sh
v3/scripts/create_container.sh glm53-tf3:3.2.0 ~/glm53-tf3   # container glm53-tf3、~/glm53-tf3 を /work に
cp v3/examples/tp3-rank0.env ~/glm53-tf3/rank.env             # このホストのrank：tp2-rank0/1 か tp3-rank0/1/2
```

`create_container.sh` はcontainerに割り当てるcoreを出します。`CPUSET` が無ければ最大周波数の最も低いcoreで、GB10では効率coreの `cpuset 0-4,10-14` です。エンジンのthreadが空回りする間も、CPUの温度を低く保ちます（[配信の既定](README.ja.md#配信の既定)）。前に `CPUSET=` を付けると全core、`CPUSET=<list>` で書いたcoreです。

`~/glm53-tf3/rank.env` をこのホストの値に直します：`MASTER`（リンク上のrank 0のアドレス、全rankで同じ）、`NCCL_IB_HCA`（リンクのRDMAデバイス、2本のrail）、`NCCL_IB_GID_INDEX`、`NCCL_SOCKET_IFNAME`。29583が使われていれば `NCCL_PORT` も。exampleは参照機のファイルで、各行が何と測られたかを書いています。TP=3のexampleは `TF_GLM_MM=0` も書いています。上流がissue #1067を直すまで、TP=3では全rankにこれが要ります（[配信の既定](README.ja.md#配信の既定)）。このファイルは `bash` が読み込むもので、`docker --env-file` には渡しません。exampleがコメントにしている行は、全rankで同じに既定を変えます：`PARALLEL`、`CONTEXT`、熱の帯、`API_KEY_FILE`（[設定](README.ja.md#設定)）。

エンジンにはホストでのbuildの段がありません。kernelはbinaryの中にあります。

## 5. 起動

全ホストにSSHできる機械から、[`examples/cluster.tp2.env`](examples/cluster.tp2.env) か [`cluster.tp3.env`](examples/cluster.tp3.env) を `state/cluster.env`（Gitが追わないので、拠点の値がGitに入らない）に写し、`HOSTS`（rankの順のSSHの名前）と `CHECKOUT`（ホスト上のこのリポジトリ）、既定と違えば `CONTAINER`・`WORK`・`SSH` を設定してから：

```sh
v3/scripts/cluster.sh state/cluster.env start first
```

TP=2では大きいrankから起動し、rank 0を最後にします。TP=3では3つのrankをまとめて起動し、rank 0を最後にします。全rankの生存の線がつながると、rank 0が `/work/nccl-id` にNCCLのid（16進256文字）を書き、scriptがそのファイルを他のホストへ写し、そこのrankはそれを待って読みます。各rankはcontainerの中で `serve.sh TP RANK /work/rank.env` を動かします。全ホストでメモリの見張り（`hostwatch.sh`：`MemAvailable` が5 GiBを切るとエンジンを止める）を起動し、rank 0の `[tensorfold] serving` の行を待ちます。終わりは、`READY` とかかった秒数、rankが断ったかエンジンが消えたかrank 0がidを書かなかったときの `FAILED` と各rankのlogの末尾、15分たっての `TIMEOUT` のどれかです。各rankのlogは `<WORK>/logs/serve-r<RANK>-<LABEL>.log`、見張りのlogは `hostwatch-<LABEL>.log` です。labelの後の引数は全rankの `tensorfold-native serve` に渡り、`cluster.sh state/cluster.env status` は各rankのエンジンのprocessを数えます。`FAILED` か `TIMEOUT` の後は[運用](docs/operations.ja.md#起動の結果)を見ます。

各rankの起動の行を読みます：

- `[serve.sh]`：TP、rank、`MASTER`、窓（`context`：TP=2で245760、TP=3で1048576）、`parallel`（rankのファイルが別の値を書かなければ1、空の `PARALLEL=` なら `auto`）、`vision`（1、空の `VISION=` なら `off`）、熱の帯、imageのエンジンのcommit、`TF_GLM_MM`（rankのファイルが書かなければ `unset`）
- TP=3では、各rankの `NCCL_COMM_ID … leaves NCCL's environment`
- rank 0のloadの行 `[tensorfold] CUDA sm_121 …`：modelのGiB、`1 stream at once` とその窓でのGiB、残りのGiB、prompt cacheのGiB
- 各rankのNCCLの行（`via NET/IB`、rankのファイルの `NCCL_DEBUG` の行で起動時に一度だけ出る）：全接続が `NET/IB` で、socketは無い
- `serving` の行：modelの名前（rankのファイルで `MODEL_NAME` を設定しなければ `glm-tf`）、`HOST` と `PORT` を設定しなければ `127.0.0.1:8095`、窓

rank 0がloopbackでOpenAI互換のAPIを配信します。参照機では、3.2.0のimageで起動にTP=3で246〜554秒、TP=2で301〜615秒かかりました。長い方は各containerの最初の起動で、checkpoint全体を読んでdigestも取ります（参照機で190.4 GiBに約300秒、rank 0のlogに `checkpoint digest: … 0/33 cached files`）。同じcontainerの次からの起動はdigestをcacheから読み、TP=3で246〜258秒、TP=2で301〜302秒でした。

## 6. tool引数ゲート（任意）

ゲートは2.x系の中継で、各tool callの引数をtoolの必須項目と突き合わせ、外れたらmodelにもう一度だけ尋ねます（[2.x系の手順7](../v2/SETUP.ja.md#7-tool引数ゲート任意)）。エンジンには依存しません。rank 0で、`v3/` から仮想環境で、またはcontainerの中でcheckoutから：

```sh
python -m glm53_tf tool-gate --port 8896 --upstream http://127.0.0.1:8095 --log ../records/<run>/gate.jsonl
```

toolを使うclientは、以後port 8896と話します。

## 7. 受け入れ

[検証](docs/validation.ja.md)の確かめをその順に回し、日常の利用の前に基準値と比べます。長い要求の間はホストを冷まします。

3.x系が何について受け入れられたかはimageごとにREADMEの[状況](README.ja.md#要約)にあり、各項目の物証は[リリースでの測定値](README.ja.md#リリースでの測定値)にあります。その範囲の外は保証しません。

## 8. 停止

```sh
v3/scripts/cluster.sh state/cluster.env stop
```

rank 0を先に止め（他はそれで抜けます）、残ったrankを止め、各ホストのエンジンのprocessの数と `MemAvailable` を出します。数が0より大きければ、そのrankはまだ動いています。containerは残ります。`docker stop glm53-tf3` でGPUの確保を外します。一つのrankだけが止まったとき、エンジンが残る停止、新しいimageは[運用](docs/operations.ja.md)にあります。

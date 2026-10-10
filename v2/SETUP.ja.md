# 配備の手順書（2.x）

[English](SETUP.md) · [2.x系の概要](README.ja.md) · [検証](docs/validation.ja.md)

2台のTP=2または3台のTP=3で2.x系を配信する手順を順に並べます。機体・ケーブル・kernel・checkpointの準備は1.x系と同じで、その段は[1.x系の手順書](../v1/SETUP.ja.md)を指します。全ホストに同じcheckoutを置き、以下のコマンドはimageのbuild contextがあるそのルートから実行します。この系列のPythonの道具は `v2/` から実行します。ホストを変えるコマンド（他のサーバーの停止、このサーバーの起動）は、運用者が許可した時間の中で行います。

## 1. 機体とfabric

ConnectX-7のリンクを持つDGX Sparkまたは互換のGB10機を2台か3台、[1.x系の手順1](../v1/SETUP.ja.md#1-必要情報を集め2台とも現状確認する)のとおりに準備・確認します（棚卸し、kernel、他の負荷）。ケーブルとfabricの検証は[1.x系の手順5](../v1/SETUP.ja.md#5-ケーブル接続とfabric検証)のとおりで、対は直結、3台はリングです（[3台をリングにつなぐ](../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。各ホストについて、リンクのRDMAデバイス名（`ibdev2netdev`）、リンクのIPv4アドレスでRoCE v2になるGIDのindex、rankが待ち合わせるinterfaceかアドレスを記録します。

長い処理の前に、全ホストのGPUクロックに上限を設けます（[GPUクロックの上限](../docs/hosts.ja.md#gpuクロックの上限)）。[ホストのツール](../host/README.ja.md#据え付け)が上限を起動時のunitとして据え付けます。

## 2. checkoutとcheckpoint

全ホストで同じ確認済みのcommitをcheckoutします（`v2.*` のリリースのtag）。各ホストで、`v2/` から道具の仮想環境を用意します：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/huggingface.lock.txt
python -m glm53_tf --version
```

固定のcheckpointを一度だけ、ある1台の `v2/` から取得して検証します。revisionは [`config/model.lock.json`](config/model.lock.json) にあります：

```sh
python -m glm53_tf download --background
python -m glm53_tf verify-download --hf .venv/bin/hf --output ../records/checksum --wait
```

代わりに公開したAXLの重みを配信するなら（任意。[設定](README.ja.md#設定)）、同じように取得して検証します。revisionは [`config/axl.lock.json`](config/axl.lock.json) にあり、取得の状態は固定のcheckpointのものとは別の `state/axl/` に置きます：

```sh
python -m glm53_tf download --checkpoint axl --background
python -m glm53_tf verify-download --checkpoint axl --hf .venv/bin/hf --output ../records/checksum-axl --wait
```

その後、他のホストへcacheを写し、写しごとに同じ `verify-download` で検証します。各ホストで先に `download` を一度（AXLは `--checkpoint axl` を付けて）回して `state/` にsnapshotを記録させ（写したファイルを使い、欠けたものだけ取ります）、それから `verify-download` を `--wait` なしで回します。写し方と、読み込む前に検証する理由は[1.x系の手順3](../v1/SETUP.ja.md#3-重みを一度取得しそれぞれのコピーを検証する)と同じです。エンジンは各ホストのHugging Faceのcache（既定は `~/.cache/huggingface/hub`）から読みます。

写す前に、modelのフォルダがファイルを持っていることを確かめます。たとえば大きさで（`du -sh ~/.cache/huggingface/hub/models--<owner>--<name>`）。新しいHugging Face hubのclientは、modelのファイルをcache全体で共有する置き場（`hub/blobs/xx/…`）に置き、modelのフォルダにはlinkだけを残すことがあります：参照機の1台ではhuggingface_hub 1.32.0がそうしました。lockが入れる版の1.30.0は、他の機でmodel自身の `blobs/` に置きました。そのようなフォルダを写すとlinkしか写らず、写し先の次の `download` がInternetから全部取り直します。共有の `hub/blobs/` の中身も写すか、全ホストで同じ版のclientを使います。

## 3. image

GB10のホスト（linux/arm64）の一台で、checkoutのルートからbuildします。

```sh
docker build -f v2/docker/Dockerfile -t glm53-tf:2.9.0 .
docker image inspect --format '{{.Id}}' glm53-tf:2.9.0
```

Dockerfileはエンジンを一つのcommit（`TENSORFOLD_REF`）に固定し、完全なSHAでなければbuildを拒みます。imageを他のホストへ写すか（リンク越しに `docker save glm53-tf:2.9.0 | ssh <host> docker load`）そこでbuildし、全ホストのimage IDを比べます。一致していなければなりません。base imageはdigestで固定しています：`nvcr.io/nvidia/pytorch@sha256:2140e699b3beaf7f96a0081fd9c9406bc3832b435cdb60dfa2d261f7d2f34a1c`（測定したときの `nvcr.io/nvidia/pytorch:26.07-py3`）。tagが動いても変わりません。imageのtagは、imageに写るファイル（Dockerfile・`serve.sh`・`build_ext.sh`・ライセンスのファイル）を最後に変えた版の名前です。文書やホスト側の道具だけを変える版では、tagはそのままです。

## 4. 各ホストのcontainerとrankのファイル

```sh
v2/scripts/create_container.sh glm53-tf:2.9.0        # container glm53-tf、~/glm53-tf を /work に
cp v2/examples/tp3-rank0.env ~/glm53-tf/rank.env      # このホストのrank：tp2-rank0/1 か tp3-rank0/1/2
```

`~/glm53-tf/rank.env` をこのホストの値に直します：`MASTER`（リンク上のrank 0のアドレス、全rankで同じ）、`NCCL_IB_HCA`（リンクのRDMAデバイス、2本のrail）、`NCCL_IB_GID_INDEX`、`NCCL_SOCKET_IFNAME`。例は参照機のファイルで、各行を何として測ったかが書いてあります。このファイルは `bash` が読み込むもので、`docker --env-file` には渡しません。公開したAXLの重みを配信するには、全rankのファイルに `CHECKPOINT=/hub/models--Bizuayeu--GLM-5.3-Flash-NVFP4-attn-lmhead-W4A16/snapshots/bbad98c8f380588c16a2326bf5a2ab7344190b07` を足します。書かなければrankは固定のsnapshotを配信し、違うcheckpointで起動したrankどうしは起動を断ります。

## 5. エンジンのextensionをbuildする

各ホストで、imageごとに一度：

```sh
docker exec glm53-tf bash /opt/glm53-tf/build_ext.sh
```

GLMのNVFP4の経路が読み込むCUDAのextensionを、重みを読む前に `~/glm53-tf/ext` へcompileします。これをしないと最初の起動が読み込みの最中にcompileし、参照機の対ではrank 0の空きが6〜7 GiBまで下がりました（見張りの閾値は5 GiB）。

## 6. 起動

全ホストへSSHできる機械で、[`examples/cluster.tp2.env`](examples/cluster.tp2.env) か [`cluster.tp3.env`](examples/cluster.tp3.env) を `state/cluster.env` へコピーし（Git追跡外なので、自分の環境の値がGitに入りません）、`HOSTS`（rank順のSSH名）と `CHECKOUT`（ホスト上のこのリポジトリ）を直してから：

```sh
v2/scripts/cluster.sh state/cluster.env start first
```

最も大きいrankから順にrank 0を最後に、各containerで `serve.sh TP RANK /work/rank.env` を起動し、全ホストでメモリの見張り（`hostwatch.sh`：`MemAvailable` が5 GiB未満でエンジンを止める）を起動して、rank 0の `[tensorfold] serving` の行を待ちます。終わりは、`READY` とrank 0の最後の `[tensorfold]` の行、最初の `Traceback` かエンジンが消えたrankで `FAILED` と全rankのlogの末尾、15分たつと `TIMEOUT` のどれかです。各rankのlogは `~/glm53-tf/logs/serve-r<RANK>-<LABEL>.log`、見張りのlogは `hostwatch-<LABEL>.log` です。labelの後の引数は全rankの `tensorfold serve` に渡り、`cluster.sh state/cluster.env status` は各rankのエンジンのプロセス数を数えます。台本を使わない場合は、各ホストで同じ順に `docker exec -d glm53-tf bash /opt/glm53-tf/serve.sh <TP> <RANK> /work/rank.env` を実行します。`FAILED` や `TIMEOUT` の後は[運用](docs/operations.ja.md#起動の結果)を見ます。

rank 0の起動の行を読みます：

- `allocated prompt/reply window`：TP=2で300000、TP=3は収まる最大（参照機のリングで1048576）
- `other conversations' prompts are kept in …` の行が無い：既定の3 GiBの保持promptが窓の横に収まった
- 各rankのlogにあるNCCLの行（`via NET/IB`。rankファイルの `NCCL_DEBUG` の行で起動時に一度だけ出る）が全接続 `NET/IB` で、socketに落ちたものが無い
- `serving` の行：モデル名（rankのファイルで `MODEL_NAME` を設定しなければ `glm-tf`）、`HOST`・`PORT` を設定しなければ `127.0.0.1:8095`、`context`

rank 0がOpenAI互換のAPIをloopbackで出します。参照機では、読み込みを含む起動にTP=3で約100〜120秒、TP=2で約130秒かかりました。

## 7. tool引数ゲート（任意）

ゲートは1.x系のものの写しで、tool呼び出しの引数を各toolの必須項目と照らし、満たさなければモデルにもう一度だけ尋ねる中継です（[tool引数ゲート](../v1/docs/harnesses.ja.md#tool引数ゲート)）。エンジンに依存しません。rank 0で、`v2/` からその仮想環境で：

```sh
python -m glm53_tf tool-gate --port 8896 --upstream http://127.0.0.1:8095 --log ../records/<run>/gate.jsonl
```

toolを使うクライアントはport 8896へつなぎます。

## 8. 受け入れ

日常の利用の前に[検証](docs/validation.ja.md)の項目を、decode検査（`bench --kinds edit` の応答を含む）からメモリと温度まで、その順に回して基準値と比べます。公開のAXLの重みの基準値は、検証にあるものはそれ自身の値です。長い要求の間はホストを冷まします。

2.x系がimageごとに何について受け入れられているかはREADMEの[状態](README.ja.md#要約)、各項目の証拠は[リリースでの測定値](README.ja.md#リリースでの測定値)にあります。その範囲の外は検収していません。

## 9. 停止

```sh
v2/scripts/cluster.sh state/cluster.env stop
```

rank 0を先に、続いて他のrankを止めます。rankごとにエンジンが終わるのを最大60秒待ち、各ホストのエンジンのプロセス数と `MemAvailable` を表示します。数が0より大きいrankはまだ動いています。containerは残ります。`docker stop glm53-tf` でそのGPUの割り当てが外れます。1.x系の `server preflight` は1.x系の起動の前にこれを検査します。一つのrankだけが止まった場合、エンジンが残る停止、新しいimageは[運用](docs/operations.ja.md)にあります。

# チートシート（3.x）

[English](cheatsheet.md) · [3.x系の概要](../README.ja.md) · [設定](configuration.ja.md) · [運用](operations.ja.md)

[上流のTensorFold自身のrecipe](https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md)を越えて、この系列の構成でできることを、写せる行で並べます：rankのファイルの行、`cluster.sh` のlabelの後の引数、またはコマンドです。各項目は代価と、測った場所へのリンクを書き、3.x系の受け入れの外の項目はそう書きます。rankのファイルの行は、項目がrank 0と書かない限り全rankの `/work/rank.env` に入れ、次の起動で効きます。コマンドはcheckoutのルートから、clusterのファイルを `state/cluster.env` に置いて実行し（[手順書 §5](../SETUP.ja.md#5-起動)）、ホストを変える他のコマンドと同じく、運用者が許可した時間の中で行います。全ての設定とその既定は[設定](configuration.ja.md)にあります。

## XSFP4とFP4-Localの形式をそのまま

エンジンは、pull request #1050のcode（1.1.5から上流自身のもの。それより前の上流のリリースがGLMに受けたのは、NVIDIAのNVFP4のrecipe（`modelopt-nvfp4`）だけ）で、NVIDIAのGLM-5.3-Flash-FP4-Localとその派生のXSFP4を、保存された形のまま読みます。XSFP4は `serve.sh` の既定なので、何も設定しません。FP4-Local自身（道具はdownloadしない）や別のfolderは、全rankのファイルの `CHECKPOINT` で、受け入れの外です（[checkpoint](../README.ja.md#checkpoint)）：

```sh
CHECKPOINT=/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/<revision>
```

## switchの無いリングでTP=3

3台をリングにつなぎ、各台にリンクの上で経路を引いた `/32` のアドレスを置きます（[3台をリングにつなぐ](../../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。`cluster.sh` はrankを一緒に起動し、rank 0のNCCLのidはrankどうしの線で他へ届きます。この系列のpull request #1178からの上流のbootstrapです（[手順書 §5](../SETUP.ja.md#5-起動)）：

```sh
cp v3/examples/cluster.tp3.env state/cluster.env   # HOSTS in rank order, CHECKOUT
v3/scripts/cluster.sh state/cluster.env start ring
```

## TP=2で1M tokenの窓（FP8のlatent cache）

エンジンの選べるFP8のlatent cacheは、GiBあたり約2倍の窓を持ちます。TP=2でXSFP4とvision towerで一度試しました：1本のstreamが1,048,576 tokenの窓に収まり、prefillは約5%長く、decode検査のtokenはBF16のものと違いました。受け入れの外で、上流はその確かめを保留としています（[制限](../README.ja.md#制限)）。両方のrankのファイルに `CONTEXT=1048576` を書き、次のとおり：

```sh
v3/scripts/cluster.sh state/cluster.env start fp8 --kv-cache fp8
```

## 一度に複数の要求

TP=2の既定の窓は1本のstreamを持ちます。小さい窓ならもっと持て、空の `PARALLEL=` はエンジンに収まるだけを取らせます（[制限](../README.ja.md#制限)）。一度に複数の要求は受け入れの外です：

```sh
PARALLEL=2
CONTEXT=245760
```

## textだけ

空の `VISION=` はvision towerを読み込まず、rank 0のそのメモリはprompt cacheに回ります。`VISION=0` では読み込みます。空でない値はどれも `--vision` を渡すからです（[設定](configuration.ja.md#rankのファイル)）。そのときは、画像や動画のpartのある要求は400で断られます：

```sh
VISION=
```

## keyを付けてloopbackの外へ

rank 0だけです。エンジンは他のuserが読み書きできるkeyのファイルを断り、変わった後にファイルを読み直します（[APIのkey](configuration.ja.md#apiのkey)）。エンジンは平のHTTPを話すので、信頼できないnetworkでは、前にTLSのproxyを置きます。この系列の道具は、実行する場所の `TENSORFOLD_API_KEY` を送ります：

```sh
umask 077; printf 'ops: %s\n' "$(openssl rand -hex 32)" > ~/glm53-tf3/api-key   # on rank 0's host
# rank 0's rank file:
HOST=0.0.0.0
API_KEY_FILE=/work/api-key
```

## 全core、または別のcore

containerは既定で効率coreで動きます。全coreでは、長く続く返答が3.1.0のエンジンで熱の見張りの止める温度の1 °C以内に迫り、3.0.0のエンジンで達しました（[効率coreにする理由](../README.ja.md#配信の既定)）。[熱の見張り](../../host/README.ja.md#長い運転の間)を回します。`docker update` は次の起動の前にcontainerのcoreを動かします（[containerを作り直す](operations.ja.md#containerを作り直す)）：

```sh
docker update --cpuset-cpus 0-19 glm53-tf3        # every core of a GB10
docker update --cpuset-cpus 0-4,10-14 glm53-tf3   # back to the efficiency cores
```

## 別の熱の帯、または無し

prefillの熱の待ちの帯で、全rankで同じにします。帯を下げると、待ったpromptが26〜89%遅くなり、1M tokenのpromptの最高温度は下がりませんでした。帯が無いと、そのようなpromptは1台を94〜97.7 °Cに保ちました（[決定](decisions.ja.md#熱)）。待たないときは両方を空にします。エンジンは片方だけを断ります：

```sh
TF_HEAT_HIGH=90
TF_HEAT_LOW=86
```

## tool引数ゲート

このリポジトリのrelayで、TensorFoldの一部ではありません：各tool callの引数をtoolの必須の欄と照らし、一つでも欠ければモデルにもう一度問います（[手順書 §6](../SETUP.ja.md#6-tool引数ゲート任意)）。toolを使うclientはそのportに話します。tool-eval-benchの点にどう効いたかは[検証](validation.ja.md#tool引数ゲート越しのtool)にあります：

```sh
python -m glm53_tf tool-gate --port 8896 --upstream http://127.0.0.1:8095 --log ../records/<run>/gate.jsonl
```

## 起動を確かめる

この系列の受け入れの道具で、`v3/` からrank 0のloopbackに向けて回します。それぞれの基準値は[検証](validation.ja.md)にあります：decode検査のhash、NLLの集合、長い入力、速さ、マルチバイト出力です。

```sh
PROMPT_KIND=count python -m glm53_tf decode-check
python -m glm53_tf score-nll --url http://127.0.0.1:8095 --tokenizer <snapshot>/tokenizer.json --out ../records/<run>/nll.json
python -m glm53_tf long-input --passphrases 3 --tokens 499622
python -m glm53_tf bench --kinds prefill,decode,edit --out ../records/<run>/bench.jsonl
python -m glm53_tf mojibake --out ../records/<run>/mojibake.json
```

## 新しいimage

使っているimageを全ホストで二つ目のtagに残して、戻すのをcontainer一つの手間にし、新しいimageはdecode検査から受け入れます（[新しいimageへ移る](operations.ja.md#新しいimageへ移る)）：

```sh
docker tag glm53-tf3:<in use> glm53-tf3:previous      # on every host, before the new build
docker image inspect --format '{{.Id}}' glm53-tf3:<new>   # equal on every host
```

## clientとharness

一つの要求では出会わず、harnessのclientが出会うことが二つあります：

- **画像は履歴をまたいで数える。** 要求が持てる画像は4枚で、送るmessageの全ての画像を数えます。前のturnを画像ごと送り直すclientは、履歴に5枚目が入ると400で断られます。labelの後の `--vision-max-images` で上げられ、64まで、全rankで同じにします。画像は `--vision-image-tokens` も上げない限り4,096の画像のtokenを分け合い、上げた分は窓から取ります（[エンジンのflag](configuration.ja.md#エンジンのflag)）。受け入れの外です。
- **長いpromptの最初のtokenは遅い。** 1,035,295 tokenのpromptは、TP=3で約1,000秒で最初のtokenを出しました（[リリースでの測定値](../README.ja.md#リリースでの測定値)）。最初のイベントまでをstreamのtimeoutで数えるclientは、その前に諦めます：1.x系のharnessの注意はZCodeのそれを700秒にしており、そのようなpromptはそれを越えます（[モデル上限](../../v1/docs/harnesses.ja.md#zcodeの権限モードモデル上限既存ファイルガード)）。配信する最長のprefillより大きくします。このエンジンのstreamのkeepaliveが最初のtokenの前にclientへ届くかは、確かめていません。

```sh
v3/scripts/cluster.sh state/cluster.env start harness --vision-max-images 16
```

# NVFP4 BIZ 3.x（TensorFold ネイティブ）

[English](README.md) · [リポジトリの索引](../README.ja.md) · [手順書](SETUP.ja.md) · [変更履歴](CHANGELOG.ja.md)

3.x系は1.x系・2.x系と同じNVIDIAの固定GLM-5.3-Flash NVFP4 checkpointを、TensorFoldのネイティブエンジンで配信します。TensorFoldのPythonのエンジンに代わったZigとCUDAのエンジンで、[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold)のBIZ版からbuildします。3.0.0に向けて準備中で、まだリリースはありません。それまで動かすのは[2.x系](../v2/README.ja.md)です。

## 目次（3.0.0で埋める）

- エンジン：TensorFoldのネイティブエンジンのBIZ版を、固定した一つのcommitからimageへbuildする。このリポジトリの外の利用者にも役立つものは上流のTensorFoldへpull requestとして出し、BIZ版はこの配信に固有のものを持つ
- 範囲：2.x系が2台のTP=2と3台のTP=3で配信するもの（テキスト、tool呼び出し、MTPのdraft、2.x系の文脈の窓）と、複数の要求の同時処理。画像の入力と公開したAXLの重みは3.0.0の後
- セットアップ：image、起動の台本、rankごとの環境ファイル一枚。2.x系と同じ形（[手順書](SETUP.ja.md)）
- 検証：2.x系を受け入れている検査を、BF16 KVで取った基準値に対して
- 2.x系からの移行：名前の変わる設定とmetrics、3.0.0にまだ無いもの
- ライセンス：リポジトリのルートの[LICENSE](../LICENSE)、[NOTICE](../NOTICE)、[第三者の表示](../THIRD_PARTY_NOTICES.md)

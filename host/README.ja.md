# ホストのツール

[English](README.md) · [リポジトリのREADME](../README.ja.md) · [ホストの準備](../docs/hosts.ja.md)

持続負荷でGB10の電源が落ちることへの、ホスト側のツールです。配信のエンジンには依りません。GPUクロックの上限、常時記録、長い要求の合間に呼ぶ冷却gate、エンジンを止める熱の見張り、ホストが熱いままの間クロックの上限を下げる熱の上限（選んで入れる）からなります。どれもエンジンの一部ではなくホストの設定で、コンテナの外のホストで動きます。上限と閾値は参照機（MSI EdgeXpert GB10）で決めました。上限の根拠と測った代償は[GPUクロックの上限](../docs/hosts.ja.md#gpuクロックの上限)にあります。他の機は自分の記録で確かめてください。

## ファイル

| ファイル | 役割 |
|---|---|
| `gb10-clock-cap.service` | systemdのoneshot。起動のたびに `nvidia-smi -lgc` でGPUクロックの範囲を固定し、止めるときに `-rgc` で外す |
| `gb10-telemetry` | Pythonの記録係。2秒ごとに1行のJSONを `/var/log/gb10-telemetry/<UTCの日付>.jsonl` に書き、電源断でも直前の標本が残るよう1行ずつfsyncする。14日分を残す |
| `gb10-telemetry.service` | 記録係をサービスのユーザーで常駐させる（`Restart=always`） |
| `install.sh` | 2つのunitを据え付けて有効にし、入れ直しでも新しいプログラムで動くよう記録係を再起動し、状態、固定したクロック、記録の最後の1行を表示する。`--heat-cap` のときは熱の上限も |
| `cool-gate` | 記録を読み、ホストが冷えるまで待つ |
| `thermal-watch` | 記録を読み、ホストが熱いままならエンジンを止める |
| `gb10-heat-cap` | 記録を読み、ホストが熱いままの間クロックの上限を2,000 MHzに下げ、冷えたら戻す（[熱で下げる上限](#熱で下げる上限)） |
| `gb10-heat-cap.service` | 熱の上限を、上限のunitと記録係の後にrootで常駐させる（`Restart=on-failure`）。上限のunitを止める・再起動すると、これも止まる・再起動する（`PartOf=`）。`--heat-cap` のときだけ据え付ける |
| `nccl_probe.py` | モデルの重みなしで、2台か3台のrankの間のNCCLを確かめる。NCCLつきのPyTorchが要る（[NCCL診断](../docs/nccl-validation.ja.md)） |

`gb10-telemetry`・`cool-gate`・`thermal-watch`・`gb10-heat-cap` は、Pythonの標準ライブラリだけを使います。`cool-gate`・`thermal-watch`・`gb10-heat-cap` は `/var/log/gb10-telemetry`、または `GB10_TELEMETRY_DIR` のディレクトリを読みます。記録係もそこへ書きます。

## 記録の項目

| 項目 | 意味 |
|---|---|
| `epoch` | 標本のUnix時刻（秒） |
| `acpi_c` | ACPIの全thermal zoneをzone順に（°C）。読めなかったzoneは `null` |
| `gpu_c` | GPUの温度（°C） |
| `power_w` | GPUの消費電力（W） |
| `clock_mhz` | グラフィックスクロック（MHz） |
| `util_pct` | GPUの使用率（%） |
| `event_reasons` | `nvidia-smi` が表示する `clocks_event_reasons.active` |
| `load1` | 1分のload average |
| `mem_available_gib` | `MemAvailable`（GiB） |
| `event_counters_us` | 累積の `clocks_event_reasons_counters.*`（µs）：`sw_power_cap`・`sync_boost`・`sw_thermal_slowdown`・`hw_thermal_slowdown`・`hw_power_brake_slowdown`。`nvidia-smi` が読めないカウンタは `null` |

下の2つのツールは、`acpi_c` のうち `null` でない最高値で熱を判断します。参照機の `nvidia-persistenced` は `--no-persistence-mode` で動くので、記録係が走らせ続ける `nvidia-smi` がGPUのクライアントとしても張り付きます。上限が効いているかは、負荷時の `clock_mhz` に表れます。カウンタを記録するのは、GB10では電力上限とメモリのクロックがN/Aと読め、標本と標本の間に入って抜けるSWの電力上限はカウンタにしか表れないためです。2026-10-06には、参照機の `sw_power_cap` はエンジンが動いていない間（208〜305 MHz、約5.5 W）にだけ増え、prefillの間には一度も増えませんでした。

## 据え付け

各ホストで、このディレクトリから：

```bash
sudo sh install.sh          # 記録係はsudoを呼んだユーザーで動く
sudo sh install.sh <user>   # または既存の別のユーザーで
sudo sh install.sh [<user>] --heat-cap   # 熱の上限も
```

rootでなければ実行を断ります。記録係のunitにユーザーを書き込み、そのユーザーが所有する `/var/log/gb10-telemetry` を作り、最後に `installed for <user>` を表示します。`--heat-cap` が無ければ、記録係と上の2つのunitだけを据え付け、ほかには何も入れません。あれば[熱の上限](#熱で下げる上限)も据え付け、最後の行の前にその状態を表示します。

外すとき：`sudo systemctl disable --now gb10-clock-cap.service gb10-telemetry.service`（上限のunitを止めると上限が外れます）、`/etc/systemd/system/` の2つのunitと `/usr/local/sbin/gb10-telemetry` を消し、`sudo systemctl daemon-reload`。熱の上限は先に同じ形で外します：`sudo systemctl disable --now gb10-heat-cap.service`（止めると2,200 MHzに戻ります）、そのunitと `/usr/local/sbin/gb10-heat-cap` を消します。

## 熱で下げる上限

`gb10-heat-cap` はrootのサービスで、ホストが熱いままの間、起動時の上限を2,200 MHzから2,000 MHzに下げ、冷えたら戻します。エンジンはコンテナの中で動きクロックを変えられないので、これはホストで動きます。2秒ごとに記録の最新の行（UTCの日が替わった直後は前の日のfileも）を読み、`null` でないACPIの最高温度で判断します：

- 2,200 MHzのとき：直近300秒のうち、最高温度が90 °C以上だった時間が半分（150秒、行のepochで数える）を越えたら、`nvidia-smi -lgc 300,2000` を掛けます。時間は上限が2,200になった時点からだけ数えるので、起動直後の少ない読みも、戻る前の熱い読みも、早まった切り替えを起こしません。
- 2,000 MHzのとき：75 °C以下の読みが120秒続いたら、`-lgc 300,2200` を掛け直します。それより熱い読み、zoneの無い読み、記録の途切れがあれば数え直します。
- 記録が無いか、30秒（`cool-gate` の限度）より古いときは2,000 MHzを掛け、理由を記録します。記録が戻っても、戻るには75 °C以下の120秒が要るので、記録係がまだ書いていない起動では、少なくともその間は2,000 MHzで始まります。
- 2,200 MHzで始め（記録が古ければ2,000）、SIGTERMで終わる前に2,200を掛けます。`-rgc` でクロックを外すことはなく、2,200より上を掛けることもありません（`--top-mhz` も2,200まで）。`nvidia-smi` が失敗したら、または30秒（古い記録とみなす線）答えなければ、記録して次の読みで掛け直します。それでサービスが終わることはありません。

**線の出どころ。** 参照機の長いprefillです。2026-11-11には、2,200 MHzでの2M tokenのprefillが始まって2〜4分で90 °Cに届き、終わり近くまで88〜92 °Cにいて、driverのソフトウェアの熱による速度落としが1回、0.1秒起きました。2026-11-12の2,000 MHzでは、TP=3の2M tokenとTP=2の1M tokenのprefillが90 °Cに届かず、rank 0では温まった後に79〜89 °Cを上下し、どの負荷も終わって12秒のうちに75 °Cを下回りました。戻りの線がこの帯の中にあると、prefillの途中で上限が戻ります。その日の2,000 MHzの記録に当てると、最初の案の85 °Cではrank 0に負荷が掛かっている間に7回そうなり（2M tokenのprefillで4回、1M tokenのprefillで3回）、75 °Cでは戻りはどれも負荷の後でした。rank 0の2,200 MHzの記録（[`tests/data/heat-cap-2m-prefill.csv`](../tests/data/heat-cap-2m-prefill.csv)）に当てると、GPUがprefillを始めて408秒で2,000 MHzを掛け、終わって124秒で2,200に戻します。記録はずっと2,200 MHzなので、戻りは2,200でのそのホストのものです。2,000 MHzの記録（[`tests/data/heat-cap-2m-prefill-2000.csv`](../tests/data/heat-cap-2m-prefill-2000.csv)）に、prefillが88 °Cに届いた読みから当てると、負荷の終わりまで2,000 MHzのままで、終わって124秒で戻します。線はどれも引数（`--high`・`--low`・`--window`・`--share`・`--hold`・`--hot-mhz`・`--top-mhz`・`--stale`）で、起動の時に厳密に読みます。読めない値や範囲の外の値は、名前と値と受ける形を出して終了コード2で終わります。

**ほかの守りとの関係。** エンジンの熱の待ちは92 °Cを越えるとprefillのchunkを88 °Cまで待たせ、`thermal-watch` は94 °C以上が2回続くとエンジンを止めます。熱の上限はそのどちらよりも先にクロックを下げ、2つは下の網として残ります。

**記録するもの。** 切り替えのたびに、記録のディレクトリの `heat-cap.log`（ほかのツールが記録として読む `*.jsonl` の名前ではない）へ、fsyncした1行のJSONを書きます。時刻、前と後のMHz、理由、窓の中の90 °C以上の秒、75 °C以下の秒、最新の行の値です。`nvidia-smi` の失敗は原因ごとに1行を足し、上限がもう2,000 MHzの間に記録が古くなったときも、新しくなるまでに1行（`kept`）を足します。`/run/gb10-heat-cap.json` は今の上限と、いつ・なぜ掛けたかを持ちます。切り替えのたびに一度に置き換え、どのユーザーも読め、`gb10-heat-cap --status` がその中身を1行のJSONで表示します（無ければ終了コード1）。受領証はこの行と記録の `clock_mhz` からcellごとに2,000 MHzだった秒を数え、運転のpreflightは `--status` で今の上限を読みます。

**既定では入れない。** ホストのすべての測定の条件を変えるので、`sudo sh install.sh [<user>] --heat-cap` のときだけ据え付けて有効にします。`gb10-clock-cap.service` を止める・再起動すると、熱の上限も止まる・再起動します（`PartOf=`）。熱の上限が先に2,200 MHzを掛けて終わり、上限のunitが `-rgc` でクロックを外すか2,200を掛け直し、再起動した熱の上限は起動の時と同じに始めます。止めた熱の上限は止まったままです。上限のunitの再起動で起こし直すのは動いている熱の上限だけで（2026-11-13に参照機で確かめた）、戻すには `sudo systemctl start gb10-heat-cap.service` を打ちます。`nvidia-smi -lgc` で自分の上限を掛けて運転するときは、先に熱の上限を止めます。動いている熱の上限は、熱で2,000 MHzに下げた後にホストが冷えたときと、止まる・起動するときに、その上限の上から2,200 MHzを掛けるためです。

## 長い運転の間

2.x系と3.x系のエンジンは、要求の中でもprompt chunkの合間に熱で待ちます（2.x系は `TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW`、[2.x README](../v2/README.ja.md)。3.x系は `TF_HEAT_HIGH`・`TF_HEAT_LOW`、[3.x README](../v3/README.ja.md#配信の既定)）。この2つのツールは要求の外で働きます。

**冷却gate。** 長い要求の前ごとに、各ホストでcheckoutのルートから：

```bash
python3 host/cool-gate --label <text>
```

ACPIの最高温度が `--band`（既定60 °C）以下になるか、`--cap` 秒（既定600）たつと戻り、1行のJSONを表示します。戻った理由（`cool` か `cap`）、待った秒数、始めと終わりの温度です。終了コード0なら続けます。2は記録が無いか30秒より古いことを示し、記録の無いまま運転を続けるべきではありません。既定値は参照機の記録から来ています。60 °Cはそこで測ったアイドルの帯のすぐ上で、600秒はそこで測ったその帯への戻りの最も遅いものより長い時間です。

**熱の見張り。** エンジンが配信している間、各ホストで：

```bash
python3 host/thermal-watch ~/glm53-tf/logs/therm-<label>.log &      # 2.x：コンテナとプロセスは既定値
python3 host/thermal-watch ~/glm53-tf3/logs/therm-<label>.log \
  --container glm53-tf3 --process 'tensorfold-native serve' &       # 3.x
```

2秒ごとに、時刻、記録の行のepoch、ACPIの最高温度、GPUの温度・電力・クロックをlogに足します。94.0 °C以上が2回続くと、コンテナの中の `pkill -f` でエンジンを止めます。この規則は参照機の記録から来ています。決めた時点で電源断なしに終わった最高の値は93.7 °Cで、2026-10-15の暖かい午後には1台が95.0 °Cまで読み（94 °C以上が2回、どれも続けてではない）、電源は落ちませんでした。`--threshold` と `--readings` で変えられます。エンジン自身の熱の待ちはprefillのchunkの合間だけで働くので、長く続くdecode（たとえばtool-eval-benchの実行）の熱を守るのはこの見張りだけです。エンジンはコンテナの中でrootとして動くので、見張りは `docker exec` を通して探し、止めます。止めるのはコンテナの中で起動したプロセスです（`cluster.sh` は `docker exec` でエンジンを起動します）。コンテナのPID 1は止まりません。PID 1は既定でこのsignalを無視するためです。`therm-<label>.stop`（logの名前の末尾を `.stop` にしたもの）ができるか、エンジンがいなくなると終わります。

既定値は2.x系のコンテナ `glm53-tf` とプロセス `tensorfold serve` で、見張りはこれで確かめました（下）。3.x系のホストではこの既定値ではエンジンが見つからず、見張りは一度も読まずにすぐ終わります。上のとおり3.x系のコンテナとプロセスを渡します（[3.x系の運用](../v3/docs/operations.ja.md#一つのrankが止まったとき)）。`--container` と `--process` で別のコンテナとプロセスも指定できます。たとえば別の `CONTAINER` で作ったコンテナです。

**確かめたこと。** 2026-10-04に参照機の一台（GB10）で、sudoなしで確かめました。記録係は一時ディレクトリへ2秒ごとに1行を書きました。`cool-gate` は生きた記録で `cool`・終了コード0を、記録が無いと `telemetry stale`・終了コード2を返しました。`thermal-watch` は `--threshold 0` で、`docker exec` で起動したプロセスを2回目の読みで止め、コンテナが無いときはすぐに終わりました。`install.sh` は実行していません（rootでなければ断るため）。

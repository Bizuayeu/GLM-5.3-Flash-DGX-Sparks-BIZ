# ホストのツール

[English](README.md) · [リポジトリのREADME](../README.ja.md) · [ホストの準備](../docs/hosts.ja.md)

持続負荷でGB10の電源が落ちることへの、ホスト側のツールです。配信のエンジンには依りません。GPUクロックの上限、常時記録、長い要求の合間に呼ぶ冷却gate、エンジンを止める熱の見張りからなります。どれもエンジンの一部ではなくホストの設定で、コンテナの外のホストで動きます。上限と閾値は参照機（MSI EdgeXpert GB10）で決めました。上限の根拠と測った代償は[GPUクロックの上限](../docs/hosts.ja.md#gpuクロックの上限)にあります。他の機は自分の記録で確かめてください。

## ファイル

| ファイル | 役割 |
|---|---|
| `gb10-clock-cap.service` | systemdのoneshot。起動のたびに `nvidia-smi -lgc` でGPUクロックの範囲を固定し、止めるときに `-rgc` で外す |
| `gb10-telemetry` | Pythonの記録係。2秒ごとに1行のJSONを `/var/log/gb10-telemetry/<UTCの日付>.jsonl` に書き、電源断でも直前の標本が残るよう1行ずつfsyncする。14日分を残す |
| `gb10-telemetry.service` | 記録係をサービスのユーザーで常駐させる（`Restart=always`） |
| `install.sh` | 2つのunitを据え付けて有効にし、入れ直しでも新しいプログラムで動くよう記録係を再起動し、状態、固定したクロック、記録の最後の1行を表示する |
| `cool-gate` | 記録を読み、ホストが冷えるまで待つ |
| `thermal-watch` | 記録を読み、ホストが熱いままならエンジンを止める |

Pythonのツールは標準ライブラリだけを使います。`cool-gate` と `thermal-watch` は `/var/log/gb10-telemetry`、または `GB10_TELEMETRY_DIR` のディレクトリを読みます。記録係もそこへ書きます。

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
```

rootでなければ実行を断ります。記録係のunitにユーザーを書き込み、そのユーザーが所有する `/var/log/gb10-telemetry` を作り、最後に `installed for <user>` を表示します。

外すとき：`sudo systemctl disable --now gb10-clock-cap.service gb10-telemetry.service`（上限のunitを止めると上限が外れます）、`/etc/systemd/system/` の2つのunitと `/usr/local/sbin/gb10-telemetry` を消し、`sudo systemctl daemon-reload`。

## 長い運転の間

2.x系のエンジンは、要求の中でもprompt chunkの合間に熱で待ちます（`TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW`、[2.x README](../v2/README.ja.md)）。この2つのツールは要求の外で働きます。

**冷却gate。** 長い要求の前ごとに、各ホストでcheckoutのルートから：

```bash
python3 host/cool-gate --label <text>
```

ACPIの最高温度が `--band`（既定60 °C）以下になるか、`--cap` 秒（既定600）たつと戻り、1行のJSONを表示します。戻った理由（`cool` か `cap`）、待った秒数、始めと終わりの温度です。終了コード0なら続けます。2は記録が無いか30秒より古いことを示し、記録の無いまま運転を続けるべきではありません。既定値は参照機の記録から来ています。60 °Cはそこで測ったアイドルの帯のすぐ上で、600秒はそこで測ったその帯への戻りの最も遅いものより長い時間です。

**熱の見張り。** エンジンが配信している間、各ホストで：

```bash
python3 host/thermal-watch ~/glm53-tf/logs/therm-<label>.log &
```

2秒ごとに、時刻、記録の行のepoch、ACPIの最高温度、GPUの温度・電力・クロックをlogに足します。94.0 °C以上が2回続くと、コンテナの中の `pkill -f` でエンジンを止めます。この規則は参照機の記録から来ています。決めた時点で電源断なしに終わった最高の値は93.7 °Cで、2026-10-15の暖かい午後には1台が95.0 °Cまで読み（94 °C以上が2回、どれも続けてではない）、電源は落ちませんでした。`--threshold` と `--readings` で変えられます。エンジン自身の熱の待ちはprefillのchunkの合間だけで働くので、長く続くdecode（たとえばtool-eval-benchの実行）の熱を守るのはこの見張りだけです。エンジンはコンテナの中でrootとして動くので、見張りは `docker exec` を通して探し、止めます。止めるのはコンテナの中で起動したプロセスです（`cluster.sh` は `docker exec` でエンジンを起動します）。コンテナのPID 1は止まりません。PID 1は既定でこのsignalを無視するためです。`therm-<label>.stop`（logの名前の末尾を `.stop` にしたもの）ができるか、エンジンがいなくなると終わります。

見張りは2.x系のエンジン、つまり既定値のコンテナ `glm53-tf` とプロセス `tensorfold serve` で確かめました。`--container` と `--process` で別のコンテナとプロセスを指定できます。たとえば別の `CONTAINER` で作ったコンテナです。

**確かめたこと。** 2026-10-04に参照機の一台（GB10）で、sudoなしで確かめました。記録係は一時ディレクトリへ2秒ごとに1行を書きました。`cool-gate` は生きた記録で `cool`・終了コード0を、記録が無いと `telemetry stale`・終了コード2を返しました。`thermal-watch` は `--threshold 0` で、`docker exec` で起動したプロセスを2回目の読みで止め、コンテナが無いときはすぐに終わりました。`install.sh` は実行していません（rootでなければ断るため）。

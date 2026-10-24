# Cheatsheet (3.x)

[日本語](cheatsheet.ja.md) · [3.x overview](../README.md) · [Configuration](configuration.md) · [Operations](operations.md)

What this line's setup does beyond upstream TensorFold's own recipe, as lines to copy: a rank file line, an argument after `cluster.sh`'s label or a command. Each item says what it costs and links where it was measured, and an item outside 3.x's acceptance says so. A rank file line goes into every rank's `/work/rank.env` unless the item says rank 0, and takes effect at the next start; commands run from the checkout root with the cluster file at `state/cluster.env` ([setup §5](../SETUP.md#5-start)), and like every command that changes a host, inside a window the operator has authorized. Every setting and its default are in [configuration](configuration.md).

## XSFP4 and FP4-Local's formats as stored

The engine loads NVIDIA's GLM-5.3-Flash-FP4-Local and XSFP4, its derivative, as stored, with the code of pull request #1050, which upstream has not taken; upstream's own release takes NVIDIA's NVFP4 recipe (`modelopt-nvfp4`) alone for GLM. XSFP4 is `serve.sh`'s default, so nothing is set. FP4-Local itself, which the tools do not download, or another folder is `CHECKPOINT` in every rank file, outside the acceptance ([checkpoints](../README.md#checkpoints)):

```sh
CHECKPOINT=/hub/models--nvidia--GLM-5.3-Flash-FP4-Local/snapshots/<revision>
```

## TP=3 on a ring without a switch

Three hosts cabled in a ring, each with a `/32` address routed over the links ([three hosts in a ring](../../docs/qsfp-network.md#8-three-hosts-in-a-ring)). `cluster.sh` starts the ranks together and hands rank 0's NCCL id to the others in a file, a commit of this line's until upstream takes pull request #1178 ([setup §5](../SETUP.md#5-start)):

```sh
cp v3/examples/cluster.tp3.env state/cluster.env   # HOSTS in rank order, CHECKOUT
v3/scripts/cluster.sh state/cluster.env start ring
```

## A 1M-token window at TP=2 (FP8 latent cache)

The engine's opt-in FP8 latent cache holds about twice the window per GiB. Tried once at TP=2 with XSFP4 and the vision tower: one stream fit the 1,048,576-token window, the prefill took about 5% longer, and the decode check's tokens differ from BF16's. Outside the acceptance; upstream calls its qualification pending ([limits](../README.md#limits)). `CONTEXT=1048576` in both rank files, then:

```sh
v3/scripts/cluster.sh state/cluster.env start fp8 --kv-cache fp8
```

## More than one request at once

At TP=2 the default window holds one stream; a smaller window holds more, and an empty `PARALLEL=` lets the engine take what fits ([limits](../README.md#limits)). More than one request at a time is outside the acceptance:

```sh
PARALLEL=2
CONTEXT=245760
```

## Text alone

An empty `VISION=` leaves the vision tower out, and its memory on rank 0 goes to the prompt cache; `VISION=0` keeps it in, since any value but an empty one passes `--vision` ([configuration](configuration.md#rank-file)). A request with an image or a video part is then refused with 400:

```sh
VISION=
```

## Serving beyond loopback with a key

Rank 0 only. The engine refuses a key file that other users may read or write, and rereads it after it changes ([API keys](configuration.md#api-keys)); the engine speaks plain HTTP, so a network that is not trusted still wants a proxy with TLS in front. This line's tools send `TENSORFOLD_API_KEY` from where they run:

```sh
umask 077; printf 'ops: %s\n' "$(openssl rand -hex 32)" > ~/glm53-tf3/api-key   # on rank 0's host
# rank 0's rank file:
HOST=0.0.0.0
API_KEY_FILE=/work/api-key
```

## Every core, or other cores

The containers run on the efficiency cores by default. On every core long runs of replies came within 1 °C of the thermal watch's stop with 3.1.0's engine and reached it with 3.0.0's ([why the efficiency cores](../README.md#serving-defaults)); run the [thermal watch](../../host/README.md#during-long-runs). `docker update` moves a container's cores before the next start ([recreate the container](operations.md#recreate-the-container)):

```sh
docker update --cpuset-cpus 0-19 glm53-tf3        # every core of a GB10
docker update --cpuset-cpus 0-4,10-14 glm53-tf3   # back to the efficiency cores
```

## Other heat bands, or none

The prefill heat wait's band, the same on every rank. Lower bands made the prompts that waited 26 to 89% slower without lowering a 1M-token prompt's peak, and without a band such a prompt held one host at 94 to 97.7 °C ([decisions](decisions.md#heat)). Empty both for no wait; the engine refuses one without the other:

```sh
TF_HEAT_HIGH=90
TF_HEAT_LOW=86
```

## The tool-argument gate

This repository's relay, not part of TensorFold: it checks each tool call's arguments against the tool's required fields and asks the model once more when one fails ([setup §6](../SETUP.md#6-tool-argument-gate-optional)). Clients that use tools talk to its port; what it changed in tool-eval-bench's scores is in [validation](validation.md#tools-through-the-tool-argument-gate):

```sh
python -m glm53_tf tool-gate --port 8896 --upstream http://127.0.0.1:8095 --log ../records/<run>/gate.jsonl
```

## Checking a launch

This line's acceptance tools, run from `v3/` against rank 0's loopback, each with its reference values in [validation](validation.md): the decode check's hashes, the NLL set, long inputs, speed and multibyte output.

```sh
PROMPT_KIND=count python -m glm53_tf decode-check
python -m glm53_tf score-nll --url http://127.0.0.1:8095 --tokenizer <snapshot>/tokenizer.json --out ../records/<run>/nll.json
python -m glm53_tf long-input --passphrases 3 --tokens 499622
python -m glm53_tf bench --kinds prefill,decode,edit --out ../records/<run>/bench.jsonl
python -m glm53_tf mojibake --out ../records/<run>/mojibake.json
```

## A new image

Keep the image in use under a second tag on every host, so going back is a container away, and accept the new one from the decode check on ([move to a new image](operations.md#move-to-a-new-image)):

```sh
docker tag glm53-tf3:<in use> glm53-tf3:previous      # on every host, before the new build
docker image inspect --format '{{.Id}}' glm53-tf3:<new>   # equal on every host
```

## Clients and harnesses

Two things a harness client meets that a single request does not:

- **Images count across the history.** A request may hold 4 images, counting every image of the messages it sends, so a client that resends earlier turns with their images is refused with 400 once the history holds a fifth. `--vision-max-images` after the label raises it, up to 64 and the same on every rank; the images still share 4,096 image tokens unless `--vision-image-tokens` raises those too, which takes them from the window ([engine flags](configuration.md#engine-flags)). Outside the acceptance.
- **A long prompt's first token is slow.** A 1,035,295-token prompt gave its first token after about 1,000 s at TP=3 ([measured on the release](../README.md#measured-on-the-release)). A client whose stream timeout counts until the first event gives up first: 1.x's harness notes set ZCode's to 700 s, which such a prompt passes ([model limits](../../v1/docs/harnesses.md#zcode-permission-modes-model-limits-and-the-existing-file-guard)). Set it above the longest prefill served; whether this engine's stream keepalives reach the client before the first token was not checked.

```sh
v3/scripts/cluster.sh state/cluster.env start harness --vision-max-images 16
```

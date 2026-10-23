# Contributing

[日本語](CONTRIBUTING.ja.md)

This is an engineering project with a measured scope. Keep claims limited to the exact hardware, image, weights, precision and workload tested.

Use Python 3.11 or newer. The 1.x line (vLLM) lives in `v1/`, the 2.x line (TensorFold) in `v2/` and the 3.x line (TensorFold's native engine) in `v3/`; each line holds what is specific to its engine, and the checkout root holds what the lines share: the host and fabric pages in `docs/`, the host tools in `host/` and the repository tools (the publication audit and the release notes). Install the pinned check tools and 1.x's test dependencies once (`python -m pip install -r requirements/dev.lock.txt -r v1/requirements/test.lock.txt`: Ruff for every line, NumPy, which some 1.x tests need, and filelock, which the download lock test of every line needs), then run the checks of each place, as [CI](.github/workflows/ci.yml) does:

```sh
# in v1/
python -m unittest discover -s tests -t . -v
ruff check glm53_setup tests tools
ruff format --check glm53_setup tests tools
# in v2/
python -m unittest discover -s tests -t . -v
ruff check glm53_tf tests
ruff format --check glm53_tf tests
# in v3/
python -m unittest discover -s tests -t . -v
ruff check glm53_tf tests
ruff format --check glm53_tf tests
# at the checkout root; the host tools have no extension, so ruff is given them by name
python -m unittest discover -s tests -t . -v
ruff check tools tests host/nccl_probe.py host/gb10-telemetry host/cool-gate host/thermal-watch
ruff format --check tools tests host/nccl_probe.py host/gb10-telemetry host/cool-gate host/thermal-watch
python tools/check_publication.py
```

The audit applies its line rules to every line (version, license, model pin; 2.x and 3.x also a changelog section for the version, which `tests/test_lines.py` checks for every line; 1.x also its document map, architecture page and README citations). `python tools/check_publication.py --duplicates` also lists measured-looking numbers found on more than one page of a line; it is a warning for whoever edits the documents, since a number has one owner page but may be cited deliberately.

An optional CI job also runs 1.x's tests with torch built for CPU (`v1/requirements/cpu-torch.lock.txt`, installed after 1.x's test lock), so the tests that need torch but no GPU run too; those that need CUDA or the pinned vLLM image still skip there and run on the GPU hosts only. GPU checks are separate from CPU tests. Use the pinned image and record effective arguments, output completeness, numerical differences and failures. The validation procedures are each line's: [1.x](v1/docs/validation.md), [2.x](v2/docs/validation.md) and [3.x](v3/docs/validation.md).

- Do not commit credentials, local site configuration, model weights, raw logs or private experiment records.
- Keep model/cache artifacts read-only during inference and preserve failed runs.
- Do not relax a runtime guard or a numerical criterion just to obtain a passing result.
- Keep original notices for copied/adapted code. New project contributions are submitted under Apache-2.0; third-party portions keep their applicable notices.
- Mark modified upstream files prominently and review the [licensing guide](docs/licensing.md) for the actual distribution scope.
- Keep ZCode and Claude Code results separate in the [harness acceptance matrix](v1/docs/harnesses.md); never mark unexecuted cases passed.
- Update the English and Japanese versions of every paired document together when user-visible content changes; the [document map](docs/README.md) lists the pairs.

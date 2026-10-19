# The 3.x serving image: TensorFold's native engine (tensorfold-native, tf-cuda-test) built from the BIZ release of
# the engine, which v3/config/engine.lock.json pins, on CUDA's devel image; then the binaries alone on the runtime
# image. They carry their kernels and link libc alone; at run time they open the driver's libcuda.so.1 (from the host
# through the NVIDIA runtime) and libnccl.so.2 (here). Build from the checkout root on a GB10 (aarch64):
#   docker build -f v3/docker/Dockerfile -t glm53-tf3:<tag> .
# The bases by digest, not by tag (a tag can move): CUDA 13.3.1 on Ubuntu 24.04 (nvcc 13.3.73, the compiler the 3.x
# kernels were measured with; glibc 2.39, the engine needs 2.36).
ARG BUILD_IMAGE=nvidia/cuda:13.3.1-devel-ubuntu24.04@sha256:4ff859525f99de5782aa73607ce24219b07dddd48d12b97c1c301d7e1cfb0a87
ARG RUNTIME_IMAGE=nvidia/cuda:13.3.1-runtime-ubuntu24.04@sha256:63da350831208559df18c7b8f3e0d5d1c984eaa815cdde690aacd6606cd0cb11
# The engine and its compiler as v3/config/engine.lock.json pins them (v3/tests/test_engine_lock.py keeps them equal).
ARG ENGINE_REPO=https://github.com/Bizuayeu/TensorFold.git
ARG ENGINE_REF=1a8f1efdc47b778c68cfdd30c1ba4966b2fe9064
ARG ZIG_URL=https://ziglang.org/download/0.17.0/zig-aarch64-linux-0.17.0.tar.xz
ARG ZIG_SHA256=9e8d11661d4ae3bd57702a3832781e23ad151dde5798e16a5ccd503f65234ff8
ARG BUILD_FLAGS="-Dnvcc=/usr/local/cuda/bin/nvcc -Dsm=121"
# Structured output's library (libtfgrammar: the engine's C ABI over xgrammar's C++), from the xgrammar release the
# engine pins, checked by commit
ARG XGRAMMAR_REPO=https://github.com/mlc-ai/xgrammar.git
ARG XGRAMMAR_TAG=v0.2.8
ARG XGRAMMAR_REF=97787376faee5ed8466cfad57c99855e4ce2f6aa

FROM ${BUILD_IMAGE} AS build
ARG ENGINE_REPO
ARG ENGINE_REF
ARG ZIG_URL
ARG ZIG_SHA256
ARG BUILD_FLAGS
RUN apt-get update \
 && apt-get install -y --no-install-recommends git xz-utils curl ca-certificates python3 \
 && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /tmp/zig.tar.xz "$ZIG_URL" \
 && echo "$ZIG_SHA256  /tmp/zig.tar.xz" | sha256sum -c - \
 && mkdir /opt/zig && tar -xJf /tmp/zig.tar.xz -C /opt/zig --strip-components=1 && rm /tmp/zig.tar.xz
RUN git clone "$ENGINE_REPO" /src \
 && git -C /src checkout --detach "$ENGINE_REF" \
 && test "$(git -C /src rev-parse HEAD)" = "$ENGINE_REF"
# The plain build installs tf-cuda-test in zig-out/bin; `native` puts tensorfold-native in zig-out/native/bin.
WORKDIR /src
RUN /opt/zig/zig build $BUILD_FLAGS \
 && /opt/zig/zig build native $BUILD_FLAGS \
 && mkdir /out && cp zig-out/native/bin/tensorfold-native zig-out/bin/tf-cuda-test /out/ \
 && cd /out && printf "engine %s\nref %s\nzig %s\nflags %s\n" "$ENGINE_REPO" "$ENGINE_REF" "$ZIG_URL" "$BUILD_FLAGS" > ENGINE \
 && sha256sum tensorfold-native tf-cuda-test >> ENGINE
ARG XGRAMMAR_REPO
ARG XGRAMMAR_TAG
ARG XGRAMMAR_REF
# `zig build grammar` puts libtfgrammar.so in zig-out/lib; xgrammar's and dlpack's notices go with it
RUN git clone --branch "$XGRAMMAR_TAG" --recurse-submodules "$XGRAMMAR_REPO" /xgrammar \
 && test "$(git -C /xgrammar rev-parse HEAD)" = "$XGRAMMAR_REF" \
 && /opt/zig/zig build grammar -Dxgrammar=/xgrammar $BUILD_FLAGS \
 && cp zig-out/lib/libtfgrammar.so /out/ \
 && mkdir /out/LICENSES \
 && cp /xgrammar/LICENSE /out/LICENSES/xgrammar-Apache-2.0.txt \
 && cp /xgrammar/NOTICE /out/LICENSES/xgrammar-NOTICE.txt \
 && cp /xgrammar/3rdparty/dlpack/LICENSE /out/LICENSES/dlpack-Apache-2.0.txt \
 && cd /out && printf "xgrammar %s %s %s\n" "$XGRAMMAR_REPO" "$XGRAMMAR_TAG" "$XGRAMMAR_REF" >> ENGINE \
 && sha256sum libtfgrammar.so >> ENGINE
# The engine's own notices, which its binaries carry (a step of its own, after the builds)
RUN mkdir /out/engine \
 && cp -r /src/LICENSE /src/NOTICE /src/THIRD_PARTY_NOTICES.md /src/LICENSES /out/engine/

FROM ${RUNTIME_IMAGE}
ARG ENGINE_REF
LABEL org.opencontainers.image.revision=$ENGINE_REF
# NCCL as measured on the reference pair and in the 04/05 NCCL check (2.30.7), held there; rdma-core's verbs and
# their providers so NCCL takes RoCE (NET/IB) rather than sockets; python3 with tokenizers for the HTTP checks.
ARG NCCL_VERSION=2.30.7-1+cuda13.3
ARG TOKENIZERS_VERSION=0.23.1
RUN apt-get update \
 && apt-get install -y --no-install-recommends --allow-downgrades --allow-change-held-packages \
      "libnccl2=${NCCL_VERSION}" libibverbs1 ibverbs-providers rdma-core ibverbs-utils \
      python3 python3-pip curl procps util-linux ca-certificates \
 && apt-mark hold libnccl2 \
 && pip3 install --no-cache-dir --break-system-packages "tokenizers==${TOKENIZERS_VERSION}" \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build /out/tensorfold-native /out/tf-cuda-test /usr/local/bin/
COPY --from=build /out/ENGINE /usr/share/doc/tf3/ENGINE
# the server looks in ../lib beside its binary for the grammar library
COPY --from=build /out/libtfgrammar.so /usr/local/lib/
COPY --from=build /out/LICENSES/ /usr/share/doc/tf3/LICENSES/
COPY --from=build /out/engine/ /usr/share/doc/tf3/engine/
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md /usr/share/doc/tf3/
# The rank's start (cluster.sh runs it in the container on every host)
COPY v3/scripts/serve.sh /opt/glm53-tf3/serve.sh
WORKDIR /work

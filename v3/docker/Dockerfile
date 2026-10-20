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
# Image and video input's libraries (--vision), the releases the engine checks by version at load: libjpeg-turbo's
# TurboJPEG for JPEG, libwebp's decoder for WebP, and FFmpeg's decoders inside the engine's libtfvideo for video
ARG JPEG_TURBO_URL=https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/3.1.4.1/libjpeg-turbo-3.1.4.1.tar.gz
ARG JPEG_TURBO_SHA256=ecae8008e2cc9ade2f2c1bb9d5e6d4fb73e7c433866a056bd82980741571a022
ARG WEBP_URL=https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-1.6.0.tar.gz
ARG WEBP_SHA256=e4ab7009bf0629fd11982d4c2aa83964cf244cffba7347ecd39019a9e38c4564
ARG FFMPEG_URL=https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz
ARG FFMPEG_SHA256=8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e

# The media libraries, beside the engine's build: shared TurboJPEG and WebP decoder, and a static PIC FFmpeg with the
# engine's tools/zig/build_ffmpeg.sh configuration (decoders only, no GPL parts: LGPL-2.1), linked into libtfvideo below
FROM ${BUILD_IMAGE} AS media
ARG JPEG_TURBO_URL
ARG JPEG_TURBO_SHA256
ARG WEBP_URL
ARG WEBP_SHA256
ARG FFMPEG_URL
ARG FFMPEG_SHA256
RUN apt-get update \
 && apt-get install -y --no-install-recommends cmake make xz-utils curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/media
RUN curl -fsSL -o jpeg.tar.gz "$JPEG_TURBO_URL" && echo "$JPEG_TURBO_SHA256  jpeg.tar.gz" | sha256sum -c - \
 && mkdir jpeg && tar -xzf jpeg.tar.gz -C jpeg --strip-components=1 \
 && cmake -S jpeg -B jpeg/b -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/jpeg -DENABLE_STATIC=OFF \
      -DWITH_TURBOJPEG=ON \
 && cmake --build jpeg/b -j"$(nproc)" && cmake --install jpeg/b
RUN curl -fsSL -o webp.tar.gz "$WEBP_URL" && echo "$WEBP_SHA256  webp.tar.gz" | sha256sum -c - \
 && mkdir webp && tar -xzf webp.tar.gz -C webp --strip-components=1 \
 && cd webp && ./configure --prefix=/opt/webp --disable-static --enable-libwebpdecoder --disable-libwebpmux \
      --disable-libwebpdemux --disable-png --disable-jpeg --disable-tiff --disable-gif --disable-wic \
 && make -j"$(nproc)" && make install
RUN curl -fsSL -o ffmpeg.tar.xz "$FFMPEG_URL" && echo "$FFMPEG_SHA256  ffmpeg.tar.xz" | sha256sum -c - \
 && mkdir ffmpeg && tar -xJf ffmpeg.tar.xz -C ffmpeg --strip-components=1 \
 && cd ffmpeg && ./configure --prefix=/opt/ffmpeg --enable-static --disable-shared --enable-pic \
      --disable-programs --disable-doc --disable-network --disable-autodetect --disable-everything \
      --disable-avdevice --disable-avfilter --disable-swresample \
      --enable-avcodec --enable-avformat --enable-swscale \
      --enable-decoder=h264,hevc,vp8,vp9,mpeg4 \
      --enable-parser=h264,hevc,vp8,vp9,mpeg4video \
      --enable-demuxer=mov,matroska \
      --enable-bsf=vp9_superframe_split \
 && make -j"$(nproc)" && make install
# The libraries the engine opens (libturbojpeg.so.0, libwebpdecoder.so.3) and the three projects' notices
RUN mkdir -p /out/lib /out/LICENSES \
 && cp -P /opt/jpeg/lib*/libturbojpeg.so.0* /opt/webp/lib/libwebpdecoder.so.3* /out/lib/ \
 && cp jpeg/LICENSE.md /out/LICENSES/libjpeg-turbo-LICENSE.md \
 && cp jpeg/README.ijg /out/LICENSES/libjpeg-turbo-README.ijg \
 && cp webp/COPYING /out/LICENSES/libwebp-COPYING.txt && cp webp/PATENTS /out/LICENSES/libwebp-PATENTS.txt \
 && cp ffmpeg/COPYING.LGPLv2.1 /out/LICENSES/FFmpeg-LGPL-2.1.txt && cp ffmpeg/LICENSE.md /out/LICENSES/FFmpeg-LICENSE.md

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
# Video input's libtfvideo (`zig build video` puts it in zig-out/native/lib) over the media stage's static FFmpeg; the
# media libraries' versions and every library's SHA-256 go into ENGINE
ARG JPEG_TURBO_URL
ARG WEBP_URL
ARG FFMPEG_URL
COPY --from=media /opt/ffmpeg /opt/ffmpeg
COPY --from=media /out/lib/ /out/media/
RUN /opt/zig/zig build video -Dffmpeg=/opt/ffmpeg \
 && cp zig-out/native/lib/libtfvideo.so /out/media/ \
 && cd /out && printf "media %s\nmedia %s\nmedia %s\n" "$JPEG_TURBO_URL" "$WEBP_URL" "$FFMPEG_URL" >> ENGINE \
 && cd /out/media && sha256sum libtfvideo.so libturbojpeg.so.0.* libwebpdecoder.so.3.* >> /out/ENGINE
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
# and in the loader's path for the media libraries (JPEG, WebP, video), which it opens at the first such input
COPY --from=build /out/media/ /usr/local/lib/
RUN ldconfig
COPY --from=build /out/LICENSES/ /usr/share/doc/tf3/LICENSES/
COPY --from=media /out/LICENSES/ /usr/share/doc/tf3/LICENSES/
COPY --from=build /out/engine/ /usr/share/doc/tf3/engine/
COPY LICENSE NOTICE THIRD_PARTY_NOTICES.md /usr/share/doc/tf3/
# The rank's start (cluster.sh runs it in the container on every host)
COPY v3/scripts/serve.sh /opt/glm53-tf3/serve.sh
WORKDIR /work

ARG OLLAMA_BASE=docker.io/ollama/ollama@sha256:4be1eaabf0dd0152bfbb780347e2888b5fe86ec25d0faa3eb4b1a956173736fb
FROM ${OLLAMA_BASE} AS build
ARG BUILD_JOBS=4
ARG LIBDRM_VERSION=2.4.125-1ubuntu0.1~24.04.2
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git dpkg-dev ca-certificates python3 python3-venv python3-pip \
    python3-mako python3-yaml python3-packaging pkg-config ninja-build flex bison \
    libdrm-dev=${LIBDRM_VERSION} libexpat1-dev libelf-dev libzstd-dev zlib1g-dev \
    libx11-dev libx11-xcb-dev libxcb-dri3-dev libxcb-present-dev libxcb-randr0-dev \
    libxcb-shm0-dev libxcb-sync-dev libxcb-xfixes0-dev libxshmfence-dev \
    libwayland-dev wayland-protocols glslang-tools spirv-tools \
    llvm-20-dev clang-20 libclang-20-dev libclang-cpp20-dev libclc-20-dev \
    libllvmspirvlib-20-dev llvm-spirv-20 && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv --system-site-packages /opt/mesa-build-tools && \
    /opt/mesa-build-tools/bin/pip install --no-cache-dir meson==1.7.2
ENV PATH=/opt/mesa-build-tools/bin:/usr/lib/llvm-20/bin:$PATH
WORKDIR /build/lab
COPY versions/ versions/
COPY patches/ patches/
COPY scripts/fetch-mesa-source.py scripts/fetch-mesa-source.py
COPY tests/test_patch.py tests/test_patch.py
COPY tests/test_gpu_reclaim.c tests/test_gpu_reclaim.c
COPY tests/test_anv_integration.c tests/test_anv_integration.c
RUN python3 -m unittest discover -s tests -p test_patch.py -v && \
    python3 scripts/fetch-mesa-source.py --destination /build/source && \
    cd /build/source/mesa-25.2.8 && \
    git apply --check --whitespace=error-all /build/lab/patches/0001-anv-experimental-gpu-reclaim.patch && \
    git apply /build/lab/patches/0001-anv-experimental-gpu-reclaim.patch
RUN meson setup /build/mesa /build/source/mesa-25.2.8 \
    --prefix=/opt/mesa-anv-test --libdir=lib --buildtype=release \
    -Dplatforms=x11,wayland -Dvulkan-drivers=intel -Dgallium-drivers= \
    -Dglx=disabled -Degl=disabled -Dopengl=false -Dgles1=disabled -Dgles2=disabled \
    -Dllvm=enabled -Dbuild-tests=false -Dvalgrind=disabled -Dlibunwind=disabled && \
    meson compile -C /build/mesa -j ${BUILD_JOBS} && \
    meson install -C /build/mesa --destdir /build/install --tags runtime
RUN mkdir -p /build/install/opt/mesa-anv-test/build-evidence && \
    cp /build/lab/versions/*.json /build/install/opt/mesa-anv-test/build-evidence/ && \
    sha256sum /build/lab/patches/*.patch > /build/install/opt/mesa-anv-test/build-evidence/patch-sha256.txt && \
    dpkg-query -W > /build/install/opt/mesa-anv-test/build-evidence/build-packages.txt && \
    meson introspect /build/mesa --buildoptions > /build/install/opt/mesa-anv-test/build-evidence/meson-options.json && \
    cp /build/install/opt/mesa-anv-test/share/vulkan/icd.d/intel_icd.*.json \
       /build/install/opt/mesa-anv-test/share/vulkan/icd.d/intel_icd.json

FROM ${OLLAMA_BASE}
ARG LAB_COMMIT=unknown
LABEL org.opencontainers.image.source=https://github.com/dryaka/anv-gpu-reclaim-lab \
      org.opencontainers.image.revision=${LAB_COMMIT}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libvulkan1=1.3.275.0-1build1 vulkan-tools && rm -rf /var/lib/apt/lists/*
COPY --from=build /build/install/opt/mesa-anv-test /opt/mesa-anv-test
ENV VK_DRIVER_FILES=/opt/mesa-anv-test/share/vulkan/icd.d/intel_icd.json \
    ANV_EXPERIMENTAL_GPU_RECLAIM=0 \
    ANV_EXPERIMENTAL_GPU_RECLAIM_DEBUG=0
RUN ldd /opt/mesa-anv-test/lib/libvulkan_intel.so > /opt/mesa-anv-test/build-evidence/runtime-ldd.txt 2>&1 && \
    ! grep -q 'not found' /opt/mesa-anv-test/build-evidence/runtime-ldd.txt && \
    sha256sum /opt/mesa-anv-test/lib/libvulkan_intel.so > /opt/mesa-anv-test/build-evidence/driver-sha256.txt && \
    dpkg-query -W > /opt/mesa-anv-test/build-evidence/runtime-packages.txt

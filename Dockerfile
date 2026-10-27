# Governed Claims Coverage Engine - OFFLINE SYNTHETIC DEMO image (not a production image; see governance/).
#
# Reproducibility: base image pinned by digest (python:3.11-slim-bookworm, resolved 2026-10-27 from the public
# registry API); Python dependencies pinned by version AND SHA-256 (requirements-container.txt, --require-hashes).
# No model is downloaded at build or start-up. Semantic mode is OPTIONAL (see target `semantic` and compose.yaml).
#
# STATUS: written 2026-10-27 on a machine whose Docker daemon was NOT running, so this file has NOT been built or run
# locally. CI is configured to build it and smoke-test /healthz, but CI has not been run either.

ARG PYTHON_IMAGE=python:3.11-slim-bookworm@sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf

# ---------- builder: install hash-pinned wheels into a venv (no compilers, wheels only) ----------
FROM ${PYTHON_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY requirements-container.txt /tmp/requirements-container.txt
RUN /opt/venv/bin/pip install --require-hashes --only-binary=:all: -r /tmp/requirements-container.txt

# ---------- base: everything common to both variants ----------
FROM ${PYTHON_IMAGE} AS base
LABEL org.opencontainers.image.title="governed-claims-engine-demo" \
      org.opencontainers.image.description="Offline synthetic-data demo. No authentication. Not production-ready." \
      org.opencontainers.image.licenses="NOASSERTION"
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
# Only what the app needs: code, the bundled SYNTHETIC policies, and the calibrated abstention policy.
COPY src/ ./src/
COPY data/ ./data/
COPY calibration/abstain_policy.json ./calibration/abstain_policy.json
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GRADIO_ANALYTICS_ENABLED=False \
    GRADIO_TEMP_DIR=/tmp/gradio \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    CLAIMS_ALLOW_NONLOOPBACK=1
# CLAIMS_ALLOW_NONLOOPBACK=1 is required to listen on 0.0.0.0 INSIDE the container. It is only safe if the port is
# published to loopback (-p 127.0.0.1:7860:7860) or sits behind an authenticating reverse proxy.
USER 10001:10001
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/healthz', timeout=4).status == 200 else 1)"]
ENTRYPOINT ["python", "-m", "claims_engine.app"]
CMD ["--host", "0.0.0.0", "--port", "7860"]

# ---------- optional: semantic mode (UNTESTED, larger, torch/sentence-transformers not hash-pinned) ----------
# Build:  docker build --target semantic -t claims-demo:semantic .
# Run:    mount a model folder you fetched yourself (python -m claims_engine.fetch_model) read-only and pass --semantic:
#         docker run --rm -p 127.0.0.1:7860:7860 -v "$PWD/models:/app/models:ro" claims-demo:semantic --host 0.0.0.0 --port 7860 --semantic
# The image build installs CPU-only PyTorch + sentence-transformers wheels; it NEVER downloads the model itself, and the
# app refuses to load a model whose files do not match the pinned manifest (embeddings.verify_local_model).
FROM base AS semantic
USER root
RUN /opt/venv/bin/pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 \
 && /opt/venv/bin/pip install --no-cache-dir "sentence-transformers==6.2.0" "transformers==5.21.0" "tokenizers==0.23.3" "safetensors==0.8.0"
USER 10001:10001

# ---------- runtime: the DEFAULT target (last stage) = lexical-only demo, no model, no extra packages ----------
FROM base AS runtime
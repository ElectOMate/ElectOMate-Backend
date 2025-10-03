# An example of using standalone Python builds with multistage images.

# First, build the application in the `/app` directory
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Configure the Python directory so it is consistent
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

# Install Python before the project for caching
RUN uv python install 3.13

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Then, use a final image without uv
FROM debian:bookworm-slim

ARG PRELOAD_DOCLING_MODELS=true

# Install system dependencies for the entrypoint script
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    dialog \
    openssh-server \
    ca-certificates \
    openssl \
    gosu \
    # Required for https outbound traffic
    && update-ca-certificates \
    # Required for ssh into the container
    && echo "root:Docker!" | chpasswd \
    # Check gosu works properly
    && gosu nobody true \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app user and group
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Copy the Python version
COPY --from=builder --chown=app:app /python /python

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# Copy the entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/healthcheck.sh /healthcheck.sh
COPY docker/sshd_config /etc/ssh/
RUN chmod u+x /entrypoint.sh

# Create SSH directory and set permissions
RUN mkdir -p /run/sshd && chmod 755 /run/sshd

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Preload all the models in the image (optional for development builds)
RUN if [ "$PRELOAD_DOCLING_MODELS" = "true" ]; then \
      gosu app docling-tools models download; \
    else \
      echo "Skipping Docling model download during image build"; \
    fi

# Expose ssh port
EXPOSE 8000 2222

# Use the entrypoint script (keep as root initially)
ENTRYPOINT ["/entrypoint.sh"]

# Run the FastAPI application by default
CMD ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000", "/app/src/em_backend/main.py"]
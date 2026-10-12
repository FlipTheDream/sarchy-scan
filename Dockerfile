# Official ClamAV image: ships the ClamAV engine and current definitions.
# Bump CLAMAV_VERSION to pin a newer release (see https://hub.docker.com/r/clamav/clamav/tags).
ARG CLAMAV_VERSION=1.5.4
FROM clamav/clamav:${CLAMAV_VERSION}-debian13-slim

# Python runtime for the sub-agent, plus the tools needed to install the GitHub CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install the official GitHub CLI (gh)
RUN mkdir -p -m 755 /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY scan_agent.py /app/scan_agent.py

# Override the base image's ClamAV entrypoint with the sub-agent.
ENTRYPOINT ["python3", "/app/scan_agent.py"]

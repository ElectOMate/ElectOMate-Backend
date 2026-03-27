FROM apache/age:latest

# Install pgvector for PG18
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-18-pgvector && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

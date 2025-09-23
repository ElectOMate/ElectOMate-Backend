# ElectOMate-Backend

This repository contains the backend code for the ElectOMate project. The backend is built using Python and provides various functionalities related to election data management and processing.

## Table of Contents

- [Local development](#local-development)
- [Local testing](#test-the-deployement-locally)

## Local Development

You will need to have [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Docker](https://docs.docker.com/get-started/introduction/get-docker-desktop/) installed.

To set up the project locally, follow these steps:

1. **Clone the repository:**

    ```bash
    git clone https://github.com/ElectOMate/ElectOMate-Backend.git
    cd ElectOMate-Backend
    ```

2. **Install dependencies:**

    ```bash
    uv sync
    ```

3. **Launch a local postgres instance**:

    ```bash
    docker run -d \
        --name em_postgres \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres \
        -e POSTGRES_DB=em \
        -p 5432:5432 \
        -v pgdata:/var/lib/postgresql/data \
        postgres
    uv run alembic upgrade head
    ```

4. **Setup the environment variables:** fill out the `.env-sample` file and name it `.env`.

5. **Run the project:**

    ```bash
    uv run --dev --env-file .env fastapi dev src/em_backend/main.py
    ```

## Test the deployement locally

1. **Build the container:**

    ```bash
    docker build -t em/backend .
    ```

2. **Run the container:**

    ```bash
    docker run --env-file ./.env -p 8000:8000 em/backend
    ```

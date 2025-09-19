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
    git clone git@github.com:ElectOMate/ElectOMate-Backend.git
    cd ElectOMate-Ghana-Backend
    ```

2. **Install dependencies:**

    ```bash
    uv sync
    ```

3. **Setup the environment variables:** fill out the `.env-sample` file and name it `.env`.

4. **Run the project:**

    ```bash
    fastapi dev src/em_backend/main.py
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

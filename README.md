# ElectOMate-Backend

This repository contains the backend code for the ElectOMate project. The backend is built using Python and provides various functionalities related to election data management and processing.

## Table of Contents

- [Installation](#installation)
- [Local development](#local-development)
- [Local testing](#test-the-deployement-locally)
- [Deployement](#deploy-the-new-container)

## Installation

To set up the project locally, follow these steps:

1. **Clone the repository:**

    ```bash
    git clone git@github.com:ElectOMate/ElectOMate-Ghana-Backend.git
    cd ElectOMate-Ghana-Backend
    ```

2. **Create a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Setup the environment variables:** fill out the `.env-sample` file

## Local development

1. **Edit the files**
2. **Test the server locally:**

    ```bash
    fastapi dev app.py
    ```

## Test the deployement locally

1. **Build the container:**

    ```bash
    docker build --tag em-backend .
    ```

2. **Run the container:**

    ```bash
    docker run --detach --publish 3100:3100 em-backend
    ```

## Deploy the new container

1. **Log into the azure cli:**

    ```bash
    az login
    ```

2. **Deploy the ew container:**

    ```bash
    az acr build \
        --resource-group em-backend-rg \
        --registry embackendacr \
        --image em-backend:latest .
    ```

3. **Upgrade the webapp:**

    ```bash
    az webapp update \
        --resource-group em-backend-rg \
        --name em-backend
    ```

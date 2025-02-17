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

You will need to have the kubectl and helm cli tools installed.

1. **Log into the azure cli:**

    ```bash
    az login
    ```

2. **Get the acr logins:**

    ```bash
    ACR_NAME=em-backend
    USER_NAME="00000000-0000-0000-0000-000000000000"
    PASSWORD=$(az acr login --name $ACR_NAME --expose-token --output tsv --query accessToken)
    helm registry login $ACR_NAME.azurecr.io \
      --username $USER_NAME \
      --password $PASSWORD
    ```

3. **Build the container:**

    ```bash
    az acr build \
        -f Dockerfile.prod \
        -r embackendacr \
        -t docker/backend:v6 .
    ```

4. **Get the kubernetes logins:**
   ```bash
   az aks get-credentials --resource-group em-backend-rg --name em-backend-aks
   ```

5. **Deploy the helm charts:**
   ```bash
   helm ugrade --install \
       em-backend . \
       -n em-backend
   ```

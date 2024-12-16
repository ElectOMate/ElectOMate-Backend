# ElectOMate-Ghana-Backend

This repository contains the backend code for the ElectOMate project in Ghana. The backend is built using Python and provides various functionalities related to election data management and processing.

## Table of Contents

- [Installation](#installation)

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

4. **Install Azure Functions Core Tools:**

Install Azure Functions Core Tools to run the Azure Functions locally. You can find the installation instructions [here](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=linux%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-python).

5. **Set up environment variables:**

   Create a `local.settings.json` file in the root directory and add the necessary environment variables. For example:

    ```env
    {
        "IsEncrypted": false,
        "Values": {
            "AzureWebJobsStorage": "",
            "FUNCTIONS_WORKER_RUNTIME": "python",
            "OPENAI_API_KEY": "<YOUR_OPENAI_API_KEY>",
            "AZURE_AI_SEARCH_SERVICE_NAME": "<SERVICE_NAME>",
            "AZURE_AI_SEARCH_INDEX_NAME": "<SERVICE_INDEX_NAME>",
            "AZURE_AI_SEARCH_API_KEY": "<YOUR_AZURE_SEARCH_API_KEY>",
            "AZURE_AI_SEARCH_ADMIN_KEY": "<YOUR_AZURE_SEARCH_ADMIN_KEY>",
            "AZURE_STORAGE_ID": "<YOUR_AZURE_STORAGE_ID>",
        }
    }
    ```
   
6. **Start the function locally:**

    ```bash
    func start
    ```

for the challenge's original README click [here](oldREADME.md)
# Take-Home Challenge: TracOS ↔ Client Integration Flow

## Introduction

This repository contains Iury Santos' solution to the "TracOS ↔ Client
Integration Flow" technical challenge as part of the hiring process for System
Integrations Engineer.

---

## What the System Does

1. **Inbound** Flow  
   - Read JSON files (simulating the client's API response) from an input folder  
   - For each work order:  
     - Validate required fields using json schema
     - Translate payload from client format → TracOS format  
     - Insert or update the record in a MongoDB collection  

2. **Outbound**  
   - Query MongoDB for work orders with `isSynced = false`  
   - For each record:  
     - Translate from TracOS format → client format  
     - Write the output JSON into an output folder, ready to "send" to the client  
     - Mark the document in MongoDB with `isSynced = true` and set a `syncedAt` timestamp  

3. **Translation / Normalization**  
   - All date fields are enforced to be ISO 8061 compliant via Pydantic model
     validations

4. **Resilience**  
   - Clear success and error logs without unreadable stack traces  
   - Handle I/O errors (corrupted file, permission issues) gracefully  
   - Simple retry or reconnect logic for MongoDB failures  

---

## Installing and running

Make sure you have the following dependencies installed: `make`, `poetry`,
`python 3.11+`, `docker` and `docker compose`. Installation of these
prerequisites (except `poetry`) depends on your package manager.

1. **Clone the repository**
   ```bash
   git clone git@github.com:iuryr/tractian_take_home_challenge.git
   cd tractian_take_home_challenge
   ```
2. **Building the project**
    ```bash
    make all #this will build MongoDB container and run setup.py to generate
    samples
    ```
3. **Running the project**
    ```bash
    make run
    ```

### Environment Variables configuration
The program accepts the definition of environment variables from .env files.
Default values are used as an example below - feel free to change them:
```bash
cat <<EOF >.env
DATA_INBOUND_DIR=data/inbound
DATA_OUTBOUND_DIR=data/outbound
MONGO_URI="mongodb://localhost:27017"
MONGO_DATABASE=tractian
MONGO_COLLECTION=workorders
EOF
```
    

## Non-Technical Requirements

- **Complete README**: explain how to run and a summary of the chosen architecture
- **Configuration via environment variables**:  
  - `MONGO_URI` → MongoDB connection string  
  - `DATA_INBOUND_DIR` and `DATA_OUTBOUND_DIR` → input/output folders  
- **Basic tests**:  
  - Sample input and output JSON  
  - End-to-end workflow verification (full coverage not required)  
- **Best practices**: informative logging, readable code, simple modularity  

---

## Deliverables

1. Git repository forking this repository, containing:  
   - Running `main.py` should start the entire pipeline  
   - Clear modules for:  
     - Read/write on our system
     - Read/write on customer's system
     - Translating data between systems
2. Complete the `README.md` file with the folder structure and a general overview of how the system works.  
3. At least **one** automated test with `pytest` testing the end-to-end flow  

---
## Evaluation Criteria

- **Functionality**: inbound/outbound flows work as described  
- **Robustness**: proper error handling and logging  
- **Clarity**: self-explanatory, comprehensive README  
- **Maintainability**: clear separation of concerns, modular code  
- **Tests**: basic coverage of the main workflow  

---

## Setting Up The Project

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Poetry for dependency management

### Installation Steps


2. **Install dependencies with Poetry**
   ```bash
   # Install Poetry if you don't have it
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Install dependencies
   poetry install
   ```

3. **Start MongoDB using Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Run the setup script to initialize sample data**
   ```bash
   poetry run python setup.py
   ```

5. **Configure environment variables**
   ```bash
   # Create a .env file or export directly in your shell
   echo "MONGO_URI=mongodb://localhost:27017/tractian" > .env
   echo "DATA_INBOUND_DIR=./data/inbound" >> .env
   echo "DATA_OUTBOUND_DIR=./data/outbound" >> .env
   ```

## Project Structure

```
integrations-engineering-code-assesment/
├── docker-compose.yml       # MongoDB container configuration
├── pyproject.toml           # Poetry configuration
├── setup.py                 # Setup script for sample data
├── data/                    # Data directories
│   ├── inbound/             # Client → TracOS JSON files
│   └── outbound/            # TracOS → Client JSON files
├── src/                     # Source code
│   └── main.py              # Main execution script
│   ...
└── tests/                   # Test directory
|   ...
```

## Running the Application

1. **Execute the main script**
   ```bash
   python src/main.py
   ```

## Testing

Run the tests with:
```bash
poetry run pytest
```

## Troubleshooting

- **MongoDB Connection Issues**: Ensure Docker is running and the MongoDB container is up with `docker ps`
- **Missing Dependencies**: Verify Poetry environment is activated or run `poetry install` again
- **Permission Issues**: Check file permissions for data directories



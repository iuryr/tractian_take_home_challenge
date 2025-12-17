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
prerequisites (except `poetry`) depends on your package manager (varies by
distribution).

1. **Clone the repository**
   ```bash
   git clone git@github.com:iuryr/tractian_take_home_challenge.git
   cd tractian_take_home_challenge
   ```
2. **Preparing to run the project**
    ```bash
    make all #this will build MongoDB container and run setup.py to generate
    samples
    ```
3. **Running the project**
    ```bash
    make run
    ```
4. **Rebuilding and cleaning the project (OPTIONAL)**
- To rebuild: `make re`
- To clean: `make clean`

5. **End to End testing (at project root)**

`poetry run pytest -v` or `poetry run pytest -v -s` (if you want to see log
messages)


### Environment Variables configuration
The program accepts the definition of environment variables from a .env file
located in the root of the project.
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

---
## Architecture and Code Design
The architecture can be summarized by the figure below:

![Architecture Diagram](./architecture_diagram.png)

Class `ClientERP` in [client_erp_adapter.py](./src/client_erp_adapter.py) is responsible for reading
and writing json to relevant directories. Class `TracOSAdapter` in [tracos_adapter.py](./src/tracos_adapter.py) is responsible
for reading and writing to the relevant MongoDB instance, as well as performing
some transformations between dicts (output of queries) and in-memory objects
(used for translation to and from client format).

We use `pydantic` to enforce that in-memory objects used by the main application
are always well formed and adhere to restraints (like having UTC aware
datetime). Translation between in-memory formats form TracOS and client ERP are
made by functions defined in [translator.py](./src/translator.py).

Input data from client ERP are always validated against a JSON schema contained
in [client_erp_schema.py](./src/schemas/client_erp_schema.py).

[main.y](./src/main.py) has the general flow of the program, as well as some
utility functions.


## Project Structure

```
.
├── docker-compose.yml #Create MongoDB instance on container and run it
├── Makefile #automates building, rebuilding and cleaning of project
├── poetry.lock
├── poetry.toml
├── pyproject.toml
├── README.md
├── setup.py #Generates sample data
├── data
│   ├── inbound
│   └── outbound
├── src
│   ├── client_erp_adapter.py #read and write json to relevante directories
│   ├── __init__.py
│   ├── main.py # inbound and outbound general flow
│   ├── tracos_adapter.py # read and write to MongoDB (TracOS)
│   ├── translator.py # TracOSWorkorder <-> CustomerSystemWorkorder
│   ├── models #pydantic models
│   │   ├── customer_system_models.py
│   │   └── tracOS_models.py
│   └── schemas
│       └── client_erp_schema.py #json schema for client payload
└── tests
```


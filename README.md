# Sample API with FastAPI

This is a lightweight Python API application built with FastAPI and uvicorn. It provides example POST and PUT endpoints with Swagger UI for testing.

## NixOS Setup

This project uses Nix Flakes for dependency management and development environment setup.

### Development Environment

Enter the development shell:

```bash
nix develop
```

Once in the development shell, start the server:

```bash
uvicorn app:app --reload
```

### Running the Application

You can run the application directly without entering the development shell:

```bash
nix run
```

Or build and run the package:

```bash
nix build
./result/bin/start-api-server
```

## Alternative Setup (Non-NixOS)

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

On Linux/Mac:
```bash
source venv/bin/activate
```

On Windows:
```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the server

```bash
uvicorn app:app --reload
```

The server will start at http://127.0.0.1:8000

## API Documentation

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## API Endpoints

- `POST /items/`: Create a new item
- `GET /items/{item_id}`: Get an item by ID
- `GET /items/`: Get all items
- `PUT /items/{item_id}`: Update an item
- `DELETE /items/{item_id}`: Delete an item

## Example Usage

### Creating an item (POST)

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/items/' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Example Item",
  "description": "This is an example item",
  "price": 19.99,
  "tags": ["example", "sample"]
}'
```

### Updating an item (PUT)

```bash
curl -X 'PUT' \
  'http://127.0.0.1:8000/items/1' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "Updated Item",
  "description": "This item has been updated",
  "price": 29.99,
  "tags": ["updated", "example"]
}'
```

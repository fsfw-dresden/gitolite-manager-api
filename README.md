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

- `PUT /gitolite/repo`: Create a new Gitolite repository with SSH key access

## Rate Limiting

The API implements rate limiting to prevent abuse. By default, clients are limited to:
- 10 requests per minute

Rate limiting is configured using the `RATE_LIMIT` environment variable.

## Example Usage

### Creating a Gitolite Repository (PUT)

```bash
curl -X 'PUT' \
  'http://127.0.0.1:8000/gitolite/repo' \
  -H 'Content-Type: application/json' \
  -d '{
  "ssh_pubkey": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0/Ho+OQP... user@example.com",
  "unit_name": "Learning Unit 101",
  "username": "student_name"
}'
```

The response will contain the Git repository URL:

```json
{
  "repo_url": "gitolite@example.com:learning_unit_101_1678901234",
  "message": "Repository created successfully"
}
```

You can then clone the repository using:

```bash
git clone gitolite@example.com:learning_unit_101_1678901234
```

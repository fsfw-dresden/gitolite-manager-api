# Gitolight Management API with FastAPI

This is a lightweight Python API application built with FastAPI and uvicorn. It is meant to allow anonymous users to create Gitolite repositories with open access
in order to contribute OER materials for the learning portal.

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

## Using as a NixOS Module

You can include this service in your NixOS system configuration. Here's an example of how to use it in your `flake.nix`:

```nix
{
  description = "NixOS system configuration with Gitolite Manager API";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    gitolite-manager-api = {
      url = "github:fsfw-dresden/gitolite-manager-api";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, gitolite-manager-api, ... }: {
    nixosConfigurations.your-hostname = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = {
        inherit gitolite-manager-api;
      };
      modules = [
        gitolite-manager-api.nixosModules.default
        ({ pkgs, ... }: {
          # Your other system configuration...
          
          # Enable the Gitolite Manager API service
          services.gitolite-manager-api = {
            enable = true;
            port = 8000;
            # Optional: Provide environment file with credentials
            environmentFile = "/path/to/gitolite-api.env";
            # The service will run as user service - under which user should the service run?
            users = [ "bob" ];
          };
          
          # You might want to configure a reverse proxy like nginx
          services.nginx = {
            enable = true;
            virtualHosts."gitolite-api.example.com" = {
              locations."/" = {
                proxyPass = "http://127.0.0.1:8000";
              };
            };
          };
          
          # Open firewall if needed
          networking.firewall.allowedTCPPorts = [ 80 443 ];
        })
      ];
    };
  };
}
```

The service will be managed by systemd and will start automatically on boot.








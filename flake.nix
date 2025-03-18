{
  description = "FastAPI to manage Gitolite repositories with open access";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      # Define the NixOS module at the top level
      nixosModule = { config, lib, pkgs, ... }:
        with lib;
        let cfg = config.services.gitolite-manager-api;
        in {
          options.services.gitolite-manager-api = {
            enable = mkEnableOption "Gitolite Manager API service";

            port = mkOption {
              type = types.port;
              default = 8000;
              description = "Port to listen on";
            };

            host = mkOption {
              type = types.str;
              default = "127.0.0.1";
              description = "Host to bind to";
            };

            environmentFile = mkOption {
              type = types.nullOr types.path;
              default = null;
              description =
                "Path to environment file containing API credentials";
            };

            users = mkOption {
              type = types.listOf types.str;
              default = [];
              description = "User accounts under which the service runs";
            };

          };

          config = mkIf cfg.enable {
            
            systemd.user.services.gitolite-manager-api = {
              description = "Gitolite Manager API Service";
              wantedBy = [ "default.target" ];
              after = [ "network.target" ];

              unitConfig = {
                # Only enable the service for the specified users
                ConditionUser = concatStringsSep "|" cfg.users;
              };

              serviceConfig = {
                Type = "simple";
                ExecStart = ''
                  ${
                    self.packages.${pkgs.system}.default
                  }/bin/start-api-server \
                    --host ${cfg.host} \
                    --port ${toString cfg.port}
                '';
                Restart = "always";
                EnvironmentFile =
                  optional (cfg.environmentFile != null) cfg.environmentFile;
              };
            };
          };
        };
    in
    # Merge the per-system outputs with the top-level module
    {
      # Top-level NixOS module
      nixosModules.default = nixosModule;
    } // flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;
        pythonPackages = python.pkgs;

        # Define the Python application with its dependencies
        pythonApp =
          python.withPackages (ps: with ps; [ fastapi uvicorn pydantic python-dotenv slowapi ]);
      in {
        packages = {
          default = pkgs.stdenv.mkDerivation {
            name = "gitolite-manager-api";
            src = ./.;
            buildInputs = [ pythonApp pkgs.git pkgs.openssh ];
            installPhase = ''
              mkdir -p $out/bin
              mkdir -p $out/lib
              cp -r ${./.}/* $out/lib/

              cat > $out/bin/start-api-server << EOF
              #!${pkgs.bash}/bin/bash
              cd $out/lib
              export PATH="${pkgs.git}/bin:${pkgs.openssh}/bin:\$PATH"
              # Ensure git is in PATH and print debug info if needed
              which git || echo "Git not found in PATH: \$PATH"
              # Use absolute path to git to avoid PATH issues
              export GIT="${pkgs.git}/bin/git"
              exec ${pythonApp}/bin/uvicorn app:app "\$@"
              EOF

              chmod +x $out/bin/start-api-server
            '';
          };
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/start-api-server";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonApp
            pythonPackages.black # Code formatter
            pythonPackages.isort # Import sorter
            pythonPackages.flake8 # Linter
            pythonPackages.python-dotenv
            pythonPackages.slowapi

          ];

          shellHook = ''
            echo "Entering Gitolite Manager API development environment"
            echo "Run 'uvicorn app:app --reload' to start the server"
          '';
        };
      });
}

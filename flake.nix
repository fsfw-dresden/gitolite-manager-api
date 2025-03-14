{
  description = "FastAPI to manage Gitolite repositories with open access";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;
        pythonPackages = python.pkgs;

        # Define the Python application with its dependencies
        pythonApp =
          python.withPackages (ps: with ps; [ fastapi uvicorn pydantic ]);
      in {
        packages = {
          default = pkgs.stdenv.mkDerivation {
            name = "gitolite-manager-api";
            src = ./.;
            buildInputs = [ pythonApp ];
            installPhase = ''
              mkdir -p $out/bin
              mkdir -p $out/lib
              cp -r ${./.}/* $out/lib/

              cat > $out/bin/start-api-server << EOF
              #!${pkgs.bash}/bin/bash
              cd $out/lib
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

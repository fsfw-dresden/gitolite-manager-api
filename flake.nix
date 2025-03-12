{
  description = "FastAPI Sample Application";

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
        pythonApp = python.withPackages (ps: with ps; [
          fastapi
          uvicorn
          pydantic
        ]);
      in
      {
        packages = {
          default = pkgs.stdenv.mkDerivation {
            name = "fastapi-sample-app";
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
            pkgs.nodePackages.pyright  # Python type checking
            pythonPackages.black       # Code formatter
            pythonPackages.isort       # Import sorter
            pythonPackages.flake8      # Linter
          ];
          
          shellHook = ''
            echo "Entering FastAPI development environment"
            echo "Run 'uvicorn app:app --reload' to start the server"
          '';
        };
      }
    );
}

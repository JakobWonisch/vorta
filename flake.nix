{
  description = "Vorta – desktop backup client for BorgBackup";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };

        lib = pkgs.lib;

        version =
          let
            versionFile = builtins.readFile ./src/vorta/_version.py;
          in
          builtins.elemAt (builtins.match ''.*"(.*)".*'' versionFile) 0;

        python = pkgs.python312;

        pythonPackages = pkgs.python312Packages;

        vorta = pythonPackages.buildPythonApplication rec {
          pname = "vorta";
          inherit version;
          pyproject = true;

          src = lib.cleanSource ./.;

          nativeBuildInputs = [
            pkgs.qt6.wrapQtAppsHook
          ];

          buildInputs = [
            pkgs.qt6.qtsvg
          ]
          ++ lib.optionals pkgs.stdenv.hostPlatform.isLinux [
            pkgs.qt6.qtwayland
          ];

          build-system = with pythonPackages; [
            setuptools
          ];

          dependencies = with pythonPackages; [
            packaging
            peewee
            platformdirs
            psutil
            pyqt6
            secretstorage
          ];

          postPatch = ''
            substituteInPlace src/vorta/assets/metadata/com.borgbase.Vorta.desktop \
              --replace-fail com.borgbase.Vorta "com.borgbase.Vorta-symbolic"
          '';

          postInstall = ''
            install -Dm644 src/vorta/assets/metadata/com.borgbase.Vorta.desktop \
              $out/share/applications/com.borgbase.Vorta.desktop
            install -Dm644 src/vorta/assets/icons/icon.svg \
              $out/share/pixmaps/com.borgbase.Vorta-symbolic.svg
          '';

          preFixup = ''
            makeWrapperArgs+=(
              "''${qtWrapperArgs[@]}"
              --prefix PATH : ${lib.makeBinPath [ pkgs.borgbackup ]}
            )
          '';

          # Local builds skip the upstream test suite; run `make test` in the dev shell instead.
          doCheck = false;

          meta = {
            description = "Desktop Backup Client for Borg";
            homepage = "https://vorta.borgbase.com/";
            license = lib.licenses.gpl3Only;
            mainProgram = "vorta";
          };
        };
      in
      {
        packages.default = vorta;
        packages.vorta = vorta;

        apps.default = {
          type = "app";
          program = "${vorta}/bin/vorta";
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            borgbackup
            uv
            python
            pre-commit
            ruff
          ];

          nativeBuildInputs = with pkgs; [
            qt6.wrapQtAppsHook
          ];

          buildInputs = with pkgs; [
            qt6.qtsvg
            qt6.qtwayland
          ];

          shellHook = ''
            export QT_PLUGIN_PATH="${pkgs.qt6.qtbase}/${pkgs.qt6.qtbase.qtPluginPrefix}"
            echo "Vorta dev shell"
            echo "  uv sync          # install Python deps"
            echo "  uv run vorta     # run from source"
            echo "  make test        # run tests"
            echo "  nix build        # build the package"
          '';
        };

        formatter = pkgs.nixfmt-rfc-style;
      }
    );
}

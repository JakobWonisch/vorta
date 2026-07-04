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

        # PyPI PyQt6 ships its own Qt; only expose non-Qt system libs it links against.
        devShellInputs = with pkgs; [
          stdenv.cc.cc.lib
          glib
          fontconfig
          freetype
          libx11
          libGL
          libxkbcommon
          libdrm
          zlib
          zstd
          dbus
          brotli
          krb5
          pcsclite
          libpulseaudio
          wayland
          libxcb
          libxcb-util
          libxcb-cursor
          libxcb-image
          libxcb-keysyms
          libxcb-render-util
          libxcb-wm
        ];
      in
      {
        packages.default = vorta;
        packages.vorta = vorta;

        apps.default = {
          type = "app";
          program = "${vorta}/bin/vorta";
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.borgbackup
            pkgs.uv
            python
            pkgs.pre-commit
            pkgs.ruff
          ];

          buildInputs = devShellInputs;

          shellHook = ''
            export UV_PYTHON="${python}/bin/python3"
            export LD_LIBRARY_PATH="${lib.makeLibraryPath devShellInputs}${
              lib.optionalString (builtins.getEnv "LD_LIBRARY_PATH" != "") ":${builtins.getEnv "LD_LIBRARY_PATH"}"
            }"
            if [ -d .venv/lib/python3.12/site-packages/PyQt6/Qt6/plugins ]; then
              export QT_PLUGIN_PATH="$PWD/.venv/lib/python3.12/site-packages/PyQt6/Qt6/plugins"
            fi
            echo "Vorta dev shell (Python ${python.version})"
            echo "  uv sync          # install Python deps"
            echo "  uv run vorta     # run from source"
            echo "  make test        # run tests"
            echo "  nix build        # build the package"
            echo "  nix run          # run the Nix-built package (not live source)"
          '';
        };

        formatter = pkgs.nixfmt-rfc-style;
      }
    );
}

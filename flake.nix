{
  description = "data-forge dev shell: pixi (in an FHS environment on Linux, so conda-forge binaries run on NixOS)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
      tools = pkgs: with pkgs; [ pixi git ];
      # FHS wrapper: runs its arguments, or $SHELL / bash if none are given.
      fhs = pkgs: pkgs.buildFHSEnv {
        name = "data-forge";
        targetPkgs = tools;
        runScript = pkgs.writeShellScript "data-forge-run" ''
          if [ "$#" -gt 0 ]; then exec "$@"; fi
          exec "''${DATA_FORGE_SHELL:-''${SHELL:-bash}}"
        '';
      };
    in
    {
      packages = forAll (pkgs: nixpkgs.lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux { default = fhs pkgs; });

      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = if pkgs.stdenv.hostPlatform.isLinux then [ (fhs pkgs) ] else tools pkgs;
        };
      });
    };
}

{
  description = "data-forge dev shell: pixi (in an FHS environment on Linux, so conda-forge binaries run on NixOS)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAll (pkgs:
        let
          tools = with pkgs; [ pixi git ];
        in
        {
          default =
            if pkgs.stdenv.isLinux then
              (pkgs.buildFHSEnv {
                name = "data-forge";
                targetPkgs = _: tools;
                runScript = "bash";
              }).env
            else
              pkgs.mkShell { packages = tools; };
        });
    };
}

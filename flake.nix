{
  description = "Szakdolgozat review sync";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            git
            pandoc
            python3
            rclone
            typst
            uv
          ];
          shellHook = ''
            export PS1="\[\e[1;34m\][dev-shell]\[\e[0m\] $PS1"
          '';
        };
      });
    };
}

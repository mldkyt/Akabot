{
  pkgs,
  lib,
  config,
  ...
}:
{
  # https://devenv.sh/languages/
  languages = {
    python = {
      enable = true;
      version = "3.12";
      uv.enable = true;
    };
  };

  processes.pycharm.exec = "${lib.getExe pkgs.jetbrains.pycharm-oss} .";
  processes.nekona.exec = "${lib.getExe pkgs.watchexec} --filter \"*.py\" --restart -- uv run main.py";

  # https://devenv.sh/packages/
  packages = with pkgs; [
    jetbrains.pycharm-oss
    watchexec
  ];

  # Symlink the devenv managed venv to a local .venv directory for PyCharm to detect it
  # https://devenv.sh/basics/
  enterShell = ''
    # Create a symlink to the Python virtual environment for IDE compatibility
    if [ ! -L "$DEVENV_ROOT/venv" ]; then
        ln -s "$DEVENV_STATE/venv/" "$DEVENV_ROOT/venv"
    fi
  '';

  # See full reference at https://devenv.sh/reference/options/
}

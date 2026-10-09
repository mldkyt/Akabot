{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  packages = with pkgs; [
    postgresql.pg_config
  ];

  services.postgres = {
    enable = true;
    listen_addresses = "localhost";
    initialDatabases = [
      {
        name = "akabot";
        user = "akabot";
        pass = "akabot";
      }
    ];
  };

  env.DB_URL = "postgresql://akabot:akabot@localhost:5432/akabot";
  dotenv.enable = true;

  languages.python = {
    enable = true;
    uv.enable = true;
    uv.sync.enable = true;
  };

  processes.web = {
    exec = "uv run webmain.py";
    watch = {
      paths = [
        ./webmain.py
        ./web
        ./utils
      ];

      extensions = [
        "py"
        "html"
      ];
    };
  };

  processes.bot = {
    exec = "uv run main.py";
    watch = {
      paths = [
        ./cogs
        ./utils
        ./main.py
      ];
    };
  };

  tasks."db:push" = {
    exec = "uv run alembic upgrade head";
    before = [
      "devenv:processes:bot"
      "devenv:processes:web"
    ];
    after = [
      "devenv:processes:postgres"
    ];
  };

  enterShell = ''
    echo ""
    echo "You can use following commands: "
    echo "    create_migration <message>"
    echo ""
  '';

  scripts.create_migration = {
    exec = ''
      uv run alembic revision --autogenerate -m "$1"
      uv run alembic upgrade head
    '';
  };
}

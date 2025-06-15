{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = with pkgs; [
    git
    zlib  # Add zlib for numpy
    quarto  # Add Quarto for presentations and documentation
  ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    package = pkgs.python3;
  };

  # Python packages
  languages.python.venv.enable = true;
  languages.python.venv.requirements = ./requirements.txt;

  # Ruby for Jekyll with proper gem management
  languages.ruby = {
    enable = true;
    package = pkgs.ruby;
    bundler.enable = true;  # Enable bundler
  };

  # https://devenv.sh/scripts/
  scripts.hello.exec = ''
    echo hello from $GREET
  '';

  scripts.serve-docs.exec = ''
    cd docs && bundle exec jekyll serve --host 0.0.0.0 --port 4000
  '';

  scripts.setup-jekyll.exec = ''
    cd docs && bundle install
  '';

  enterShell = ''
    hello
    git --version
    echo "Run 'setup-jekyll' to install Jekyll dependencies"
  '';

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';
}
[karlo.observer/cli/](https://karlo.observer/cli/)

A collection of small, self-contained Python 3 command-line scripts (system
info, file search, document conversion, diffs, ...). Every script uses only
the standard library, so it runs anywhere Python does, with nothing to install.
External tools (mutool, pandoc, nvidia-smi, ...) are used when present and
skipped gracefully when not.

## Usage

Start the interactive launcher, which lists the available scripts:

    # Linux / macOS
    curl -s https://karlo.observer/cli/ | (python3 || python)

    # Windows (PowerShell)
    irm https://karlo.observer/cli/ | python

    # Windows (cmd)
    curl.exe -s https://karlo.observer/cli/ | python

At the `cli>` prompt, type a script name with its arguments, `help <script>`
for its usage, or `exit`.

Run a single script directly, without the prompt:

    curl -s https://karlo.observer/cli/ | python3 - sysinfo
    curl -s https://karlo.observer/cli/ | python3 - largest ~/Downloads 20

The launcher exits with the script's exit code, so this works in shell scripts.

## Running locally

Each script is a standalone file and can be run directly:

    python3 search book.txt "query"

## Adding a script

See [SPEC](SPEC) for the required file layout, output conventions, and how to
register a script in `index.html`. Run `python3 _check.py` to verify that all
scripts follow it.

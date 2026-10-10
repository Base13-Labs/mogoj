# Contributing to Mogoj

Thank you for helping make local AI memory safer and easier to use.

## Set up and test

Mogoj supports Python 3.9+ and uses only the standard library at runtime.

```bash
git clone https://github.com/Base13-Labs/mogoj.git
cd mogoj
python3 -m unittest discover -s tests -v
```

Try the complete first-use flow in a temporary directory:

```bash
./bin/mogoj --root /tmp/mogoj-test init
./bin/mogoj --root /tmp/mogoj-test save "SQLite keeps memory local"
./bin/mogoj --root /tmp/mogoj-test rebuild
./bin/mogoj --root /tmp/mogoj-test search "SQLite"
./bin/mogoj --root /tmp/mogoj-test doctor
```

Create a focused branch, add regression tests, run the full suite, and open a pull request using the template. Do not commit real memories, credentials, database files, or backups. Use synthetic fixtures only.

Base13 Labs maintains Mogoj on a best-effort basis. Community pull requests are welcome, but reviews and releases have no guaranteed response time. Maintainers may decline features that add hosted dependencies, telemetry, unsafe migration behavior, or significant beginner-facing complexity.

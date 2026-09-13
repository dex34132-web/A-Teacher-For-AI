# Lerev Troubleshooting

## Bridge not found

Run `lerev doctor` to see which tier of bridge discovery succeeded.

If no bridge is found:
1. Ensure Python 3.11+ is installed
2. Run `pip install lerev`
3. Run `lerev install`

## Plugin not loading

1. Check `~/.config/opencode/opencode.jsonc` has `~/.config/opencode/node_modules/lerev` in the `plugin` array
2. Check `~/.config/opencode/node_modules/lerev/lerev.ts` exists
3. Restart OpenCode

## Memory not persisting

1. Check that `.lerev/memory/` directory exists in your project
2. Check that the bridge can write to it
3. Run `lerev doctor` for diagnostics

## Permission errors

On Linux/macOS, if you get permission errors:

```bash
pip3 install --user lerev
```

On Windows, try running as administrator or use `--user` flag.

## Python version issues

Lerev requires Python 3.11+. Check your version:

```bash
python3 --version
```

If you have multiple Python versions, ensure `python3` points to 3.11+.

## Spaces in paths

Lerev supports spaces in installation paths. If you encounter issues:
1. Use a path without spaces
2. Quote paths in commands
3. Report the issue at https://github.com/dkshs/lerev/issues

## Cross-platform notes

- On Windows, `python` is used; on macOS/Linux, `python3` is preferred
- The bridge discovery cascade: LEREV_HOME → PATH → installed module → dev fallback
- `.lerev/memory/` is per-project; global installation does not share memory
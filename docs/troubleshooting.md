# Teacher Troubleshooting

## Bridge not found

Run `teacher doctor` to see which tier of bridge discovery succeeded.

If no bridge is found:
1. Ensure Python 3.11+ is installed
2. Run `pip install teacher`
3. Run `teacher install`

## Plugin not loading

1. Check `~/.config/opencode/opencode.jsonc` has `~/.config/opencode/node_modules/teacher` in the `plugin` array
2. Check `~/.config/opencode/node_modules/teacher/teacher.ts` exists
3. Restart OpenCode

## Memory not persisting

1. Check that `.teacher/memory/` directory exists in your project
2. Check that the bridge can write to it
3. Run `teacher doctor` for diagnostics

## Permission errors

On Linux/macOS, if you get permission errors:

```bash
pip3 install --user teacher
```

On Windows, try running as administrator or use `--user` flag.

## Python version issues

Teacher requires Python 3.11+. Check your version:

```bash
python3 --version
```

If you have multiple Python versions, ensure `python3` points to 3.11+.

## Spaces in paths

Teacher supports spaces in installation paths. If you encounter issues:
1. Use a path without spaces
2. Quote paths in commands
3. Report the issue at https://github.com/dex34132-web/lerev/issues

## Cross-platform notes

- On Windows, `python` is used; on macOS/Linux, `python3` is preferred
- The bridge discovery cascade: TEACHER_HOME → PATH → installed module → dev fallback
- `.teacher/memory/` is per-project; global installation does not share memory
# Northstar capture: the plugin folder in this repository

This folder is for one use: trying capture from a checkout with `claude --plugin-dir`.

```
claude --plugin-dir ./plugin
```

Its hooks run `${CLAUDE_PLUGIN_ROOT}/../.venv/bin/python -P -m northstar_agent_memory.capture.hook <Event>`, which is
the checkout's own virtual environment, found by going up one folder from the plugin. That path only exists while the
plugin is read in place from this checkout. `--plugin-dir` reads it in place, so it works.

It is not for a marketplace install. Claude Code copies a marketplace plugin into its own plugin cache, away from this
checkout, where `${CLAUDE_PLUGIN_ROOT}/..` holds no virtual environment and every hook would fail. That is why this
folder has no `marketplace.json`.

To keep capture across sessions, use one of the two ways Northstar writes for you, each with the absolute path of the
interpreter in every hook:

```
northstar capture install --plugin-dir PATH     # renders a self-contained plugin into PATH, then prints the commands
northstar capture install --settings PATH       # or merges the hooks into a settings.json you name
```

Use one, not both: with both in place every turn would be recorded twice, so the second install is refused. Neither
runs without a path, and neither looks for your real Claude Code settings on its own.

Nothing is captured until the data folder is known to be encrypted at rest (`northstar capture install` checks and
leaves a stamp the hook looks for) and `[capture] personal_paths` in Northstar's settings names the folders to capture.

This file is the only file here that is not part of the plugin; `tests/capture/test_install.py` checks that
`.claude-plugin/plugin.json` and `hooks/hooks.json` match what the installer would write for this relative path.

# /reset-settings — Reset Claude Settings to Template Defaults

This command resets the Claude Code configuration to the template defaults. Use when settings get corrupted or overwritten.

## What It Does

1. **Backs up current settings**:
   ```bash
   cp ~/.claude/settings.json ~/.claude/settings.json.bak.$(date +%Y%m%d_%H%M%S)
   cp .claude/settings.json .claude/settings.json.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null
   ```

2. **Restores global settings** from `~/claude-ultra-template/scripts/reset-claude-settings.sh`

3. **Restores project settings** from `~/claude-ultra-template/.claude/settings.json`

4. **Verifies hooks are executable**:
   ```bash
   chmod +x .claude/hooks/*.sh
   ```

5. **Reports what was changed**:
   - Settings that were restored
   - MCPs that are now configured
   - Permissions that are now set
   - Hooks that are now active

## Instructions

Run the reset script:
```bash
~/claude-ultra-template/scripts/reset-claude-settings.sh
```

Then verify by checking:
- `~/.claude/settings.json` — global settings
- `.claude/settings.json` — project settings
- `.claude/hooks/*.sh` — hook scripts are executable

Report the result to Gáborovka with a summary of what was restored.

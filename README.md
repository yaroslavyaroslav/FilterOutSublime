# FilterOut: live grep-style folding for output panels

A tiny Sublime Text 4 plugin that lets you **visually grep any output panel** and hide everything else.  
Two commands:

| Command | Palette name | What it does |
|---------|--------------|--------------|
| `panel_live_filter` | **Panel Live Filter** | Pick an output panel, type a query; only matching lines stay visible (folds update on every keystroke). Spaces split the query into OR-tokens (`warning:` `note:` ⇒ *warning:* **or** *note:*). The filter freezes when you hit **Enter**. |
| `panel_filter_reset` | **Panel Filter Reset** | Unfolds everything in the currently-visible output panel (or the one you name in the command args). |

## Installation

### With Package Control
1. `Package Control: Add Repository` → `https://github.com/yourname/FilterOut`  
2. `Package Control: Install Package` → **FilterOut**

### Manual
Clone / download into your `Packages` folder (e.g. `~/Library/Application Support/Sublime Text/Packages/FilterOut`).

That’s it – no settings file required.

## Usage

1. **Command Palette** → **Panel Live Filter**.  
2. Choose an output panel (build output, LSP Log, etc.).  
3. The same top-overlay instantly turns into a filter field.  
4. Start typing – the panel updates live; space acts as OR.  
5. Press **Enter** to lock the filter (folds stay until you reset).  
6. Run **Panel Filter Reset** (or close/reopen the panel) to show everything again.

## Optional key-bindings

```json
// Preferences ▸ Key Bindings
{ "keys": ["ctrl+alt+f"], "command": "panel_live_filter" },
{ "keys": ["ctrl+alt+u"], "command": "panel_filter_reset" }
```

## Notes

* Works on any *output.* panel (build results, test runners, linters, etc.).  
* Filtering is case-insensitive and strictly substring match.  
* Sublime’s default “…” markers show where large blocks were folded; file contents aren’t modified.  
* Tested on ST ≥ 4121, macOS & Linux.

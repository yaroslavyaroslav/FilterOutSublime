from __future__ import annotations
import re
import sublime
import sublime_plugin


def _project_settings() -> dict:  # noqa: D401 – helper
    """Return the ``view.settings()['codex']`` mapping if available."""

    try:
        window = sublime.active_window()
        view = window.active_view() if window else None
        if view:
            return view.settings().get("FilterOut", {}) or {}
    except Exception:  # noqa: BLE001 – may run in unit-tests
        pass
    return {}


# ───────────────────────── core helper ─────────────────────────
def _apply_filter(view: sublime.View, raw: str, context: int = 3):
    view.unfold(sublime.Region(0, view.size()))

    tokens = [re.escape(t) for t in raw.split() if t]
    if not tokens:
        return
    pat = re.compile("|".join(tokens), re.IGNORECASE)

    # 1) build windows of “match + context”
    all_lines = view.lines(sublime.Region(0, view.size()))
    windows = []
    for idx, line in enumerate(all_lines):
        if pat.search(view.substr(line)):
            start = line.begin()
            end_idx = min(idx + context, len(all_lines) - 1)
            end = all_lines[end_idx].end()
            windows.append((start, end))

    # no match → fold everything
    if not windows:
        view.fold(sublime.Region(0, view.size()))
        return

    # 2) merge overlaps
    windows.sort()
    merged = []
    cur_s, cur_e = windows[0]
    for s, e in windows[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))

    # 3) compute fold regions *between* merged windows,
    #    leaving exactly one line of gap visible between them
    folds = []
    # before first window?
    first_s = merged[0][0]
    if first_s > 0:
        # leave the first line, fold the rest up to the match start
        folds.append(sublime.Region(1, first_s))

    # between windows
    for (prev_s, prev_e), (next_s, next_e) in zip(merged, merged[1:]):
        # fold from just after the “one-line gap” to the next window
        gap_start = prev_e + 1  # skip the newline after the context
        gap_end = next_s  # up to the next match start
        if gap_start < gap_end:
            folds.append(sublime.Region(gap_start, gap_end))

    # after last window?
    last_e = merged[-1][1]
    if last_e < view.size():
        # leave one blank line, then fold the rest
        folds.append(sublime.Region(last_e + 1, view.size()))

    # 4) apply folding
    for r in folds:
        view.fold(r)


# ───────────────────────── main command ────────────────────────
class PanelLiveFilterCommand(sublime_plugin.WindowCommand):
    def run(self, panel_name: str, pattern: str):
        v = self.window.find_output_panel(panel_name)
        settings = sublime.load_settings("FilterOut.sublime-settings")
        conf = _project_settings()

        window_size: int = settings.get("window_size", 0)
        window_size = conf.get("window_size", window_size)
        if v:
            _apply_filter(v, pattern, window_size)

    # Input-handler chain: panel → pattern (top overlay only)
    def input(self, args):
        if "panel_name" not in args:
            return _PanelChooser(self.window)
        if "pattern" not in args:
            return _FilterPattern(self.window, args["panel_name"])
        return None


# ───────────────────────── list input (panel) ──────────────────
class _PanelChooser(sublime_plugin.ListInputHandler):
    def __init__(self, window):
        self.window = window

    def name(self):
        return "panel_name"

    def placeholder(self):
        return "Output panel"

    def list_items(self):
        panels = [p for p in self.window.panels() if p.startswith("output.")]
        return [(p[7:], p[7:]) for p in panels]  # strip “output.” prefix

    def preview(self, value):
        self.window.run_command("show_panel", {"panel": f"output.{value}"})
        return f"Filtering → {value}"


# ───────────────────────── text input (pattern) ────────────────
class _FilterPattern(sublime_plugin.TextInputHandler):
    def __init__(self, window, panel):
        self.window, self.panel = window, panel
        settings = sublime.load_settings("FilterOut.sublime-settings")
        conf = _project_settings()

        window_size: int = settings.get("window_size", 0)
        self.window_size = conf.get("window_size", window_size)

    def name(self):
        return "pattern"

    def placeholder(self):
        return "Filter text (live)"

    def preview(self, text):
        v = self.window.find_output_panel(self.panel)
        if v:
            _apply_filter(v, text, self.window_size)
        return f"Live filtering “{self.panel}”…"


# ───────────────────────── reset command ───────────────────────
class PanelFilterResetCommand(sublime_plugin.WindowCommand):
    def run(self, panel_name: str | None = None):
        if not panel_name:
            pnl = self.window.active_panel()
            if not pnl or not pnl.startswith("output."):
                return
            panel_name = pnl[7:]
        v = self.window.find_output_panel(panel_name)
        if v:
            v.unfold(sublime.Region(0, v.size()))

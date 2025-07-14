from __future__ import annotations
import re
import sublime
import sublime_plugin


# ───────────────────────── core helper ─────────────────────────
def _apply_filter(view: sublime.View, text: str):
    view.unfold(sublime.Region(0, view.size()))
    if not text:
        return
    pat = re.compile(re.escape(text), re.IGNORECASE)
    folds, start = [], None
    for line in view.lines(sublime.Region(0, view.size())):
        if pat.search(view.substr(line)):
            if start is not None:
                folds.append(sublime.Region(start, line.begin()))
                start = None
        else:
            if start is None:
                start = line.begin()
    if start is not None:
        folds.append(sublime.Region(start, view.size()))
    for r in folds:
        view.fold(r)


# ───────────────────────── main command ────────────────────────
class PanelLiveFilterCommand(sublime_plugin.WindowCommand):
    def run(self, panel_name: str, pattern: str):
        v = self.window.find_output_panel(panel_name)
        if v:
            _apply_filter(v, pattern)

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

    def name(self):
        return "pattern"

    def placeholder(self):
        return "Filter text (live)"

    def preview(self, text):
        v = self.window.find_output_panel(self.panel)
        if v:
            _apply_filter(v, text)
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

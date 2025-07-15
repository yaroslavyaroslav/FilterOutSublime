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
def _apply_filter(view: sublime.View, raw: str, context: int = 5):
    """Show each matching line + `context` lines after; fold every gap
    by starting at the first folded line, so the … marker is on top."""

    # 1) reset any previous folds
    view.unfold(sublime.Region(0, view.size()))

    # 2) build OR-pattern
    tokens = [re.escape(t) for t in raw.split() if t]
    if not tokens:
        return
    pat = re.compile("|".join(tokens), re.IGNORECASE)

    # 3) get all lines and their count
    all_lines = view.lines(sublime.Region(0, view.size()))
    n = len(all_lines)

    # 4) collect (start_idx, end_idx) windows in line indices
    windows = []
    for i, lr in enumerate(all_lines):
        if pat.search(view.substr(lr)):
            start_i = i
            end_i = min(i + context, n - 1)
            windows.append((start_i, end_i))

    # 5) if nothing matches, fold everything
    if not windows:
        view.fold(sublime.Region(0, view.size()))
        return

    # 6) merge overlapping windows (in index space)
    windows.sort()
    merged = []
    cs, ce = windows[0]
    for s, e in windows[1:]:
        if s <= ce + 1:
            ce = max(ce, e)
        else:
            merged.append((cs, ce))
            cs, ce = s, e
    merged.append((cs, ce))

    # 7) compute gaps between merged windows
    folds = []

    # 7a) top gap
    first_s, first_e = merged[0]
    if first_s > 0:
        # fold from line 0 up to line first_s-1
        start_pt = all_lines[0].begin()
        end_pt = all_lines[first_s - 1].end()
        folds.append(sublime.Region(start_pt, end_pt))

    # 7b) middle gaps
    for (ps, pe), (ns, ne) in zip(merged, merged[1:]):
        gap_start = pe + 1
        gap_end = ns - 1
        if gap_start <= gap_end:
            start_pt = all_lines[gap_start].begin()
            end_pt = all_lines[gap_end].end()
            folds.append(sublime.Region(start_pt, end_pt))

    # 7c) bottom gap
    last_s, last_e = merged[-1]
    if last_e < n - 1:
        start_pt = all_lines[last_e + 1].begin()
        end_pt = all_lines[-1].end()
        folds.append(sublime.Region(start_pt, end_pt))

    # 8) apply folding
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

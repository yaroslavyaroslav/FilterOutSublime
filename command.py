from __future__ import annotations
import re
import sublime
import sublime_plugin


class PanelLiveFilterCommand(sublime_plugin.WindowCommand):
    """
    1. Pick an output panel.
    2. Show an input panel for the filter text.
    3. Fold non-matching lines live as you type.
    4. Press Enter → freeze filter until reset.
    """

    def run(self):
        panels = [p for p in self.window.panels() if p.startswith("output.")]
        if not panels:
            sublime.error_message("No output panels found.")
            return
        names = [p[7:] for p in panels]  # strip "output."
        self.panels = dict(zip(names, panels))  # {name: full_id}
        self.window.show_quick_panel(names, self.on_pick)

    # ── step 1 ────────────────────────────────────────────
    def on_pick(self, index: int):
        if index == -1:
            return
        self.panel_name = list(self.panels.keys())[index]
        self.panel_view = self.window.find_output_panel(self.panel_name)
        if not self.panel_view:
            return
        # bring panel to front
        self.window.run_command("show_panel", {"panel": self.panels[self.panel_name]})
        # step 2: ask for filter text
        self.freeze = False
        self.window.show_input_panel(
            f"Filter “{self.panel_name}” ›",
            "",
            self.on_done,  # Enter
            self.on_change,  # every keystroke
            None,  # Esc
        )

    # ── live update ───────────────────────────────────────
    def on_change(self, text: str):
        if not self.freeze:
            self.apply_filter(text)

    # ── freeze on Enter ───────────────────────────────────
    def on_done(self, text: str):
        self.freeze = True
        self.apply_filter(text)

    # ── folding logic ─────────────────────────────────────
    def apply_filter(self, text: str):
        v = self.panel_view
        if not v:
            return
        v.unfold(sublime.Region(0, v.size()))
        if not text:
            return
        pat = re.compile(re.escape(text), re.IGNORECASE)
        folds, start = [], None
        for line in v.lines(sublime.Region(0, v.size())):
            if pat.search(v.substr(line)):
                if start is not None:
                    folds.append(sublime.Region(start, line.begin()))
                    start = None
            else:
                if start is None:
                    start = line.begin()
        if start is not None:
            folds.append(sublime.Region(start, v.size()))
        for r in folds:
            v.fold(r)


class PanelFilterResetCommand(sublime_plugin.WindowCommand):
    """Unfold everything in the active panel or a named one."""

    def run(self, panel_name: str | None = None):
        if panel_name is None:
            pnl = self.window.active_panel()
            if not pnl or not pnl.startswith("output."):
                return
            panel_name = pnl[7:]
        view = self.window.find_output_panel(panel_name)
        if view:
            view.unfold(sublime.Region(0, view.size()))

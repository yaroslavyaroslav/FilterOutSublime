import re
import sublime
import sublime_plugin


class PanelLiveFilterCommand(sublime_plugin.WindowCommand):
    """
    1. Let the user pick one of the currently-open output panels.
    2. Open an input panel and, on every keystroke, fold away all lines
       that do **not** contain the typed text (case-insensitive).
    """

    def run(self):
        self.panels = [p for p in self.window.panels() if p.startswith("output.")]
        if not self.panels:
            sublime.error_message("No output panels found.")
            return

        self.window.show_quick_panel(
            self.panels,
            self.on_panel_selected,
        )

    def on_panel_selected(self, index):
        if index == -1:
            return  # user cancelled

        # Strip the "output." prefix for find_output_panel()
        name = self.panels[index][len("output.") :]
        self.view_to_filter = self.window.find_output_panel(name)
        if not self.view_to_filter:
            sublime.error_message("Selected panel disappeared.")
            return

        # Start live filtering
        self.window.show_input_panel(
            "Live filter ›",  # caption
            "",  # initial text
            lambda _: None,  # on_done – no-op
            self.on_change,  # on_change – live updates
            None,  # on_cancel – leave folds as-is
        )

    # --- helpers ---------------------------------------------------------

    def on_change(self, text):
        v = self.view_to_filter
        if not v:
            return

        # Always unfold first
        v.unfold(sublime.Region(0, v.size()))

        if not text:
            return  # empty filter → nothing folded

        pat = re.compile(re.escape(text), re.IGNORECASE)
        fold_regions = []
        start = None

        # Walk every line once; collect contiguous non-matches into regions
        for line in v.lines(sublime.Region(0, v.size())):
            if pat.search(v.substr(line)):
                if start is not None:
                    fold_regions.append(sublime.Region(start, line.begin()))
                    start = None
            else:
                if start is None:
                    start = line.begin()

        if start is not None:
            fold_regions.append(sublime.Region(start, v.size()))

        for r in fold_regions:
            v.fold(r)


class PanelFilterResetCommand(sublime_plugin.TextCommand):
    """Unfold everything in the current view."""

    def run(self, edit):
        self.view.unfold(sublime.Region(0, self.view.size()))

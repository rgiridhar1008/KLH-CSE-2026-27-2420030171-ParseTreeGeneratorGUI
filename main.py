"""Grammar Analyzer and Parse Tree Generator GUI."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from grammar import (
    GrammarError,
    compute_first_sets,
    compute_follow_sets,
    detect_left_factoring,
    detect_left_recursion,
    left_factoring,
    parse_grammar,
    remove_left_recursion,
)
from parser import build_parse_table, parse_input
from utils import SAMPLES, build_report, save_text_report
from visualizer import ParseTreeWindow


class GrammarAnalyzerApp:
    """Main Tkinter application."""

    def __init__(self, root):
        self.root = root
        self.root.title("Grammar Analyzer and Parse Tree Generator")
        self.root.geometry("1180x760")
        self.root.minsize(1000, 650)
        self.root.configure(bg="#eef2f7")
        self.report_text = ""
        self.parse_tree = None
        self.current_grammar = None

        self._configure_style()
        self._build_ui()
        self._load_sample(3)

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#eef2f7")
        style.configure("Panel.TFrame", background="#ffffff", relief=tk.FLAT)
        style.configure("TButton", padding=8, font=("Segoe UI", 10))
        style.configure("Primary.TButton", padding=9, font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#eef2f7", font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background="#ffffff", font=("Segoe UI", 10))
        style.configure("Hint.TLabel", background="#ffffff", foreground="#64748b", font=("Segoe UI", 9))
        style.configure("Header.TLabel", background="#eef2f7", font=("Segoe UI", 19, "bold"))
        style.configure("Status.TLabel", background="#dbeafe", foreground="#1e3a8a", font=("Segoe UI", 10))

    def _build_ui(self):
        shell = ttk.Frame(self.root, padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        shell.columnconfigure(0, weight=0)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)
        shell.rowconfigure(2, weight=0)

        title = ttk.Label(shell, text="Grammar Analyzer and Parse Tree Generator", style="Header.TLabel")
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        input_panel = ttk.Frame(shell, padding=12, style="Panel.TFrame")
        input_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 12))

        ttk.Label(input_panel, text="Grammar Input", style="Panel.TLabel").pack(anchor="w")
        ttk.Label(
            input_panel,
            text="Use # for epsilon. Spaces are optional for common examples.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(2, 4))
        self.grammar_text = tk.Text(input_panel, width=44, height=18, wrap=tk.WORD, font=("Consolas", 11), undo=True)
        self.grammar_text.pack(fill=tk.BOTH, expand=True, pady=(5, 12))

        ttk.Label(input_panel, text="Input String", style="Panel.TLabel").pack(anchor="w")
        self.input_entry = ttk.Entry(input_panel, width=44, font=("Consolas", 11))
        self.input_entry.pack(fill=tk.X, pady=(5, 12))

        sample_row = ttk.Frame(input_panel)
        sample_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(sample_row, text="Sample", style="Panel.TLabel").pack(side=tk.LEFT)
        self.sample_var = tk.StringVar(value=SAMPLES[3][0])
        sample_box = ttk.Combobox(
            sample_row,
            textvariable=self.sample_var,
            values=[sample[0] for sample in SAMPLES],
            state="readonly",
            width=24,
        )
        sample_box.pack(side=tk.LEFT, padx=8)
        sample_box.bind("<<ComboboxSelected>>", self._on_sample_selected)

        button_grid = ttk.Frame(input_panel)
        button_grid.pack(fill=tk.X, pady=(4, 0))
        self.analyze_button = ttk.Button(button_grid, text="Analyze", style="Primary.TButton", command=self.analyze)
        self.clear_button = ttk.Button(button_grid, text="Clear", command=self.clear)
        self.export_button = ttk.Button(button_grid, text="Export TXT", command=self.export_report, state=tk.DISABLED)
        self.tree_button = ttk.Button(button_grid, text="Parse Tree", command=self.show_tree, state=tk.DISABLED)
        self.analyze_button.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        self.clear_button.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        self.export_button.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        self.tree_button.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        button_grid.columnconfigure(0, weight=1)
        button_grid.columnconfigure(1, weight=1)

        shortcuts = ttk.Label(
            input_panel,
            text="Shortcuts: Ctrl+Enter analyze, Ctrl+L clear, Ctrl+S export",
            style="Hint.TLabel",
        )
        shortcuts.pack(anchor="w", pady=(10, 0))

        results_panel = ttk.Frame(shell, padding=10, style="Panel.TFrame")
        results_panel.grid(row=1, column=1, sticky="nsew")
        results_panel.rowconfigure(0, weight=1)
        results_panel.columnconfigure(0, weight=1)

        self.results = tk.Text(
            results_panel,
            wrap=tk.NONE,
            font=("Consolas", 10),
            undo=False,
            bg="#fbfdff",
            fg="#0f172a",
            insertbackground="#2563eb",
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        ybar = ttk.Scrollbar(results_panel, orient=tk.VERTICAL, command=self.results.yview)
        xbar = ttk.Scrollbar(results_panel, orient=tk.HORIZONTAL, command=self.results.xview)
        self.results.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.results.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")

        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(shell, textvariable=self.status_var, style="Status.TLabel", padding=8)
        status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.root.bind("<Control-Return>", lambda _event: self.analyze())
        self.root.bind("<Control-l>", lambda _event: self.clear())
        self.root.bind("<Control-L>", lambda _event: self.clear())
        self.root.bind("<Control-s>", lambda _event: self.export_report())
        self.root.bind("<Control-S>", lambda _event: self.export_report())

    def _on_sample_selected(self, _event=None):
        selected = self.sample_var.get()
        for index, sample in enumerate(SAMPLES):
            if sample[0] == selected:
                self._load_sample(index)
                return

    def _load_sample(self, index):
        _, grammar_text, input_text = SAMPLES[index]
        self.grammar_text.delete("1.0", tk.END)
        self.grammar_text.insert(tk.END, grammar_text)
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, input_text)
        self.status_var.set(f"Loaded sample: {SAMPLES[index][0]}")

    def analyze(self):
        try:
            self.status_var.set("Analyzing grammar...")
            self.root.update_idletasks()
            original = parse_grammar(self.grammar_text.get("1.0", tk.END))
            recursion_findings = detect_left_recursion(original)
            transformed = remove_left_recursion(original) if recursion_findings else original.clone()
            factoring_findings = detect_left_factoring(transformed)
            if factoring_findings:
                transformed = left_factoring(transformed)

            first_sets = compute_first_sets(transformed)
            follow_sets = compute_follow_sets(transformed, first_sets)
            table, conflicts = build_parse_table(transformed, first_sets, follow_sets)
            parse_result = parse_input(transformed, table, self.input_entry.get())

            self.report_text = build_report(
                original,
                transformed,
                recursion_findings,
                factoring_findings,
                first_sets,
                follow_sets,
                table,
                conflicts,
                parse_result,
            )
            self.parse_tree = parse_result.parse_tree
            self.current_grammar = transformed
            self._set_results(self.report_text)
            self._set_analysis_actions(True)
            self.status_var.set(parse_result.message)
        except GrammarError as exc:
            self._set_results("")
            self._set_analysis_actions(False)
            self.status_var.set("Grammar error")
            messagebox.showerror("Grammar Error", str(exc))
        except Exception as exc:  # Keeps the GUI friendly for classroom use.
            self._set_results("")
            self._set_analysis_actions(False)
            self.status_var.set("Analysis failed")
            messagebox.showerror("Analysis Error", f"Unable to analyze grammar:\n{exc}")

    def _set_results(self, content):
        self.results.configure(state=tk.NORMAL)
        self.results.delete("1.0", tk.END)
        self.results.insert(tk.END, content)
        self.results.configure(state=tk.NORMAL)

    def clear(self):
        self.grammar_text.delete("1.0", tk.END)
        self.input_entry.delete(0, tk.END)
        self._set_results("")
        self.report_text = ""
        self.parse_tree = None
        self.current_grammar = None
        self._set_analysis_actions(False)
        self.status_var.set("Cleared")

    def _set_analysis_actions(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.export_button.configure(state=state)
        self.tree_button.configure(state=state)

    def export_report(self):
        if not self.report_text:
            messagebox.showinfo("Export", "Run analysis before exporting.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Analysis Report",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        save_text_report(path, self.report_text)
        messagebox.showinfo("Export", "Analysis report saved.")

    def show_tree(self):
        if not self.parse_tree or not self.current_grammar:
            messagebox.showinfo("Parse Tree", "Run analysis before opening the parse tree.")
            return
        ParseTreeWindow(self.root, self.parse_tree, self.current_grammar)


def main():
    root = tk.Tk()
    app = GrammarAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

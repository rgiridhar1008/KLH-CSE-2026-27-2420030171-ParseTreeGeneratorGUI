"""Tkinter canvas parse-tree visualization."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from grammar import EPSILON


class ParseTreeWindow(tk.Toplevel):
    """Scrollable, zoomable parse tree window."""

    def __init__(self, master, root_node, grammar):
        super().__init__(master)
        self.title("Parse Tree Visualization")
        self.geometry("1000x650")
        self.root_node = root_node
        self.grammar = grammar
        self.scale = 1.0

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(toolbar, text="Zoom +", command=lambda: self.zoom(1.15)).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Zoom -", command=lambda: self.zoom(0.85)).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Reset", command=self.reset_zoom).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Save PNG", command=self.save_png).pack(side=tk.LEFT, padx=3)

        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame, bg="white")
        xbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        ybar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.draw()

    def zoom(self, factor):
        self.scale *= factor
        self.draw()

    def reset_zoom(self):
        self.scale = 1.0
        self.draw()

    def save_png(self):
        path = filedialog.asksaveasfilename(
            title="Save Parse Tree",
            defaultextension=".png",
            filetypes=[("PNG Images", "*.png"), ("All Files", "*.*")],
        )
        if not path:
            return

        try:
            from PIL import Image
        except ImportError:
            messagebox.showerror(
                "PNG Export",
                "PNG export requires Pillow. Install it with: pip install pillow",
            )
            return

        ps_path = path + ".ps"
        self.canvas.postscript(file=ps_path, colormode="color")
        Image.open(ps_path).save(path, "png")
        messagebox.showinfo("PNG Export", "Parse tree saved.")

    def draw(self):
        self.canvas.delete("all")
        if not self.root_node:
            return

        next_x = [60]
        self._layout(self.root_node, 0, next_x)
        self._draw_edges(self.root_node)
        self._draw_nodes(self.root_node)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _layout(self, node, depth, next_x):
        vertical_gap = 90 * self.scale
        horizontal_gap = 85 * self.scale
        node.y = 50 * self.scale + depth * vertical_gap
        if not node.children:
            node.x = next_x[0] * self.scale
            next_x[0] += horizontal_gap
            return
        for child in node.children:
            self._layout(child, depth + 1, next_x)
        node.x = sum(child.x for child in node.children) / len(node.children)

    def _draw_edges(self, node):
        for child in node.children:
            self.canvas.create_line(node.x, node.y + 18, child.x, child.y - 18, fill="#555555", width=2)
            self._draw_edges(child)

    def _draw_nodes(self, node):
        radius = max(18, 22 * self.scale)
        color = self._node_color(node)
        self.canvas.create_oval(
            node.x - radius,
            node.y - radius,
            node.x + radius,
            node.y + radius,
            fill=color,
            outline="#1f2937",
            width=2,
        )
        self.canvas.create_text(node.x, node.y, text=node.value, fill="white", font=("Segoe UI", int(11 * self.scale), "bold"))
        for child in node.children:
            self._draw_nodes(child)

    def _node_color(self, node):
        if node.value == EPSILON:
            return "#6b7280"
        if node.value in self.grammar.productions:
            return "#2563eb"
        return "#16a34a"

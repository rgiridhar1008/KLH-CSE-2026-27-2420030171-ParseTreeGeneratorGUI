"""Parse-tree node model."""

from grammar import EPSILON


class TreeNode:
    """Simple tree node used by the parser and canvas visualizer."""

    def __init__(self, value):
        self.value = value
        self.children = []
        self.x = 0
        self.y = 0

    def add_child(self, child):
        self.children.append(child)

    @property
    def is_epsilon(self):
        return self.value == EPSILON

    def is_terminal(self, grammar):
        return self.value != EPSILON and self.value not in grammar.productions

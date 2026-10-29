"""LL(1) parse-table construction and predictive parsing."""

from dataclasses import dataclass, field

from grammar import ENDMARK, EPSILON, first_of_sequence, format_production, format_symbols
from tree import TreeNode


@dataclass
class ParseStep:
    stack: str
    remaining_input: str
    action: str


@dataclass
class ParseResult:
    accepted: bool
    steps: list = field(default_factory=list)
    leftmost_derivation: list = field(default_factory=list)
    rightmost_derivation: list = field(default_factory=list)
    parse_tree: TreeNode | None = None
    message: str = ""


def build_parse_table(grammar, first_sets, follow_sets):
    """Build an LL(1) parse table and collect conflicts."""
    table = {nt: {} for nt in grammar.productions}
    conflicts = []

    for lhs, alternatives in grammar.productions.items():
        for production in alternatives:
            first = first_of_sequence(production, first_sets, grammar)
            targets = set(first - {EPSILON})
            if EPSILON in first:
                targets.update(follow_sets[lhs])

            for terminal in targets:
                current = table[lhs].get(terminal)
                if current and current != production:
                    conflicts.append(
                        f"M[{lhs}, {terminal}] has {format_symbols(current)} "
                        f"and {format_symbols(production)}"
                    )
                table[lhs][terminal] = production

    return table, conflicts


def tokenize_input(input_text, grammar):
    """Tokenize input using known terminals from the grammar."""
    text = input_text.strip()
    if not text:
        return []
    if " " in text:
        return text.split()

    terminals = sorted(grammar.terminals, key=len, reverse=True)
    tokens = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        matched = next((term for term in terminals if text.startswith(term, index)), None)
        if matched:
            tokens.append(matched)
            index += len(matched)
        else:
            tokens.append(text[index])
            index += 1
    return tokens


def parse_input(grammar, parse_table, input_text):
    """Validate input with a predictive parser and build a parse tree."""
    tokens = tokenize_input(input_text, grammar) + [ENDMARK]
    stack = [ENDMARK, grammar.start_symbol]
    root = TreeNode(grammar.start_symbol)
    node_stack = [None, root]
    steps = []
    left_forms = [[grammar.start_symbol]]
    applied = []
    pointer = 0

    while stack:
        top = stack.pop()
        node = node_stack.pop()
        current = tokens[pointer] if pointer < len(tokens) else ENDMARK

        if top == EPSILON:
            continue

        if top == ENDMARK:
            if current == ENDMARK:
                steps.append(_step(stack, tokens[pointer:], "Accept"))
                return ParseResult(
                    True,
                    steps,
                    _format_derivation(left_forms),
                    _rightmost_derivation(grammar, applied),
                    root,
                    "String Accepted",
                )
            steps.append(_step(stack, tokens[pointer:], f"Reject: expected end, found {current}"))
            return ParseResult(False, steps, _format_derivation(left_forms), [], root, "String Rejected")

        if top not in grammar.productions:
            if top == current:
                pointer += 1
                steps.append(_step(stack, tokens[pointer:], f"Match {top}"))
            else:
                steps.append(_step(stack, tokens[pointer:], f"Reject: expected {top}, found {current}"))
                return ParseResult(False, steps, _format_derivation(left_forms), [], root, "String Rejected")
            continue

        production = parse_table.get(top, {}).get(current)
        if production is None:
            steps.append(_step(stack, tokens[pointer:], f"Reject: no rule for {top} on {current}"))
            return ParseResult(False, steps, _format_derivation(left_forms), [], root, "String Rejected")

        steps.append(_step(stack + [top], tokens[pointer:], f"Expand {format_production(top, production)}"))
        children = [TreeNode(symbol) for symbol in production]
        for child in children:
            node.add_child(child)

        applied.append((top, production))
        _apply_leftmost(left_forms, top, production)

        for symbol, child in reversed(list(zip(production, children))):
            if symbol != EPSILON:
                stack.append(symbol)
                node_stack.append(child)

    return ParseResult(False, steps, _format_derivation(left_forms), [], root, "String Rejected")


def _step(stack, remaining, action):
    return ParseStep(" ".join(reversed(stack)), " ".join(remaining), action)


def _apply_leftmost(forms, lhs, production):
    current = list(forms[-1])
    for index, symbol in enumerate(current):
        if symbol == lhs:
            replacement = [] if production == [EPSILON] else production
            forms.append(current[:index] + replacement + current[index + 1:])
            return


def _rightmost_derivation(grammar, applied):
    forms = [[grammar.start_symbol]]
    for lhs, production in applied:
        current = list(forms[-1])
        for index in range(len(current) - 1, -1, -1):
            if current[index] == lhs:
                replacement = [] if production == [EPSILON] else production
                forms.append(current[:index] + replacement + current[index + 1:])
                break
    return _format_derivation(forms)


def _format_derivation(forms):
    formatted = []
    for index, form in enumerate(forms):
        text = " ".join(form) if form else EPSILON
        formatted.append(text if index == 0 else "=> " + text)
    return formatted

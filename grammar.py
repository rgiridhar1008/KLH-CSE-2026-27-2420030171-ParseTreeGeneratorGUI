"""Grammar parsing, validation, transformation, and set generation."""

from collections import OrderedDict
from copy import deepcopy

EPSILON = "#"
ENDMARK = "$"
ARROW = "->"
KNOWN_WORD_TERMINALS = {"id", "num", "expr"}


class GrammarError(Exception):
    """Raised when a grammar cannot be analyzed safely."""


class Grammar:
    """Container for a context-free grammar."""

    def __init__(self, productions, start_symbol):
        self.productions = OrderedDict(
            (nt, [list(prod) for prod in alternatives])
            for nt, alternatives in productions.items()
        )
        self.start_symbol = start_symbol

    @property
    def non_terminals(self):
        return list(self.productions.keys())

    @property
    def terminals(self):
        symbols = set()
        for alternatives in self.productions.values():
            for production in alternatives:
                for symbol in production:
                    if symbol != EPSILON and symbol not in self.productions:
                        symbols.add(symbol)
        return sorted(symbols)

    def clone(self):
        return Grammar(deepcopy(self.productions), self.start_symbol)


def parse_grammar(grammar_text):
    """Parse user text into a Grammar object."""
    if not grammar_text.strip():
        raise GrammarError("Grammar is empty.")

    raw_rules = []
    non_terminals = []
    seen_lhs = set()

    for line_number, line in enumerate(grammar_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if line.count(ARROW) != 1:
            raise GrammarError(f"Line {line_number}: invalid production format.")

        lhs, rhs = [part.strip() for part in line.split(ARROW)]
        if not lhs:
            raise GrammarError(f"Line {line_number}: missing left-hand side.")
        if not rhs:
            raise GrammarError(f"Line {line_number}: missing right-hand side.")

        if lhs not in seen_lhs:
            non_terminals.append(lhs)
            seen_lhs.add(lhs)
        raw_rules.append((line_number, lhs, rhs))

    if not raw_rules:
        raise GrammarError("Grammar is empty.")

    productions = OrderedDict((nt, []) for nt in non_terminals)
    duplicate_check = set()

    for line_number, lhs, rhs in raw_rules:
        for alternative in rhs.split("|"):
            alternative = alternative.strip()
            if not alternative:
                raise GrammarError(f"Line {line_number}: empty alternative.")
            production = tokenize_production(alternative, non_terminals)
            key = (lhs, tuple(production))
            if key in duplicate_check:
                raise GrammarError(f"Duplicate production: {format_production(lhs, production)}")
            duplicate_check.add(key)
            productions[lhs].append(production)

    grammar = Grammar(productions, non_terminals[0])
    validate_grammar(grammar)
    return grammar


def tokenize_production(text, non_terminals):
    """Tokenize one right-hand side alternative.

    Space-separated input is respected. Compact productions are split with a
    small compiler-design-friendly heuristic: known non-terminals are matched
    greedily, common word terminals like id/num stay whole, and other lowercase
    runs are split into characters so examples such as A -> abc can be factored.
    """
    if text == EPSILON:
        return [EPSILON]
    if " " in text:
        parts = text.split()
        return [EPSILON] if parts == [EPSILON] else parts

    tokens = []
    index = 0
    nts_by_length = sorted(non_terminals, key=len, reverse=True)

    while index < len(text):
        if text[index].isspace():
            index += 1
            continue

        matched = next(
            (nt for nt in nts_by_length if text.startswith(nt, index)),
            None,
        )
        if matched:
            tokens.append(matched)
            index += len(matched)
            continue

        if text[index].isalnum() or text[index] == "_":
            end = index + 1
            while end < len(text) and (text[end].isalnum() or text[end] == "_"):
                end += 1
            word = text[index:end]
            if word in KNOWN_WORD_TERMINALS:
                tokens.append(word)
            else:
                tokens.extend(word)
            index = end
            continue

        tokens.append(text[index])
        index += 1

    return tokens or [EPSILON]


def validate_grammar(grammar):
    """Validate reachability, references, and productive productions."""
    if not grammar.start_symbol:
        raise GrammarError("Missing start symbol.")

    undefined = set()
    for alternatives in grammar.productions.values():
        for production in alternatives:
            for symbol in production:
                if _looks_like_non_terminal(symbol) and symbol not in grammar.productions:
                    undefined.add(symbol)
    if undefined:
        raise GrammarError("Undefined non-terminals: " + ", ".join(sorted(undefined)))

    reachable = {grammar.start_symbol}
    changed = True
    while changed:
        changed = False
        for lhs in list(reachable):
            for production in grammar.productions[lhs]:
                for symbol in production:
                    if symbol in grammar.productions and symbol not in reachable:
                        reachable.add(symbol)
                        changed = True

    unreachable = set(grammar.productions) - reachable
    if unreachable:
        raise GrammarError("Unreachable non-terminals: " + ", ".join(sorted(unreachable)))

    productive = set()
    changed = True
    while changed:
        changed = False
        for lhs, alternatives in grammar.productions.items():
            if lhs in productive:
                continue
            for production in alternatives:
                if all(
                    symbol == EPSILON
                    or symbol not in grammar.productions
                    or symbol in productive
                    for symbol in production
                ):
                    productive.add(lhs)
                    changed = True
                    break

    useless = set(grammar.productions) - productive
    if useless:
        raise GrammarError("Useless productions for: " + ", ".join(sorted(useless)))


def _looks_like_non_terminal(symbol):
    return any(ch.isupper() for ch in symbol)


def detect_left_recursion(grammar):
    """Return direct and indirect left-recursion findings."""
    findings = []
    for nt, alternatives in grammar.productions.items():
        if any(prod and prod[0] == nt for prod in alternatives):
            findings.append(f"Direct left recursion in {nt}")

    left_corners = {nt: set() for nt in grammar.productions}
    for nt, alternatives in grammar.productions.items():
        for production in alternatives:
            first = production[0]
            if first in grammar.productions and first != nt:
                left_corners[nt].add(first)

    for nt in grammar.productions:
        stack = list(left_corners[nt])
        seen = set()
        while stack:
            current = stack.pop()
            if current == nt:
                findings.append(f"Indirect left recursion in {nt}")
                break
            if current in seen:
                continue
            seen.add(current)
            stack.extend(left_corners[current] - seen)
    return findings


def remove_left_recursion(grammar):
    """Remove direct and indirect left recursion using the standard algorithm."""
    result = grammar.clone()
    nts = result.non_terminals
    new_productions = OrderedDict((nt, result.productions[nt]) for nt in nts)

    for i, ai in enumerate(nts):
        expanded = []
        for production in new_productions[ai]:
            if production[0] in nts[:i]:
                aj = production[0]
                suffix = production[1:]
                for aj_prod in new_productions[aj]:
                    expanded.append(_concat_without_double_epsilon(aj_prod, suffix))
            else:
                expanded.append(production)
        new_productions[ai] = expanded
        _remove_direct_left_recursion(new_productions, ai)

    result.productions = new_productions
    return result


def _remove_direct_left_recursion(productions, nt):
    recursive = []
    non_recursive = []

    for production in productions[nt]:
        if production[0] == nt:
            recursive.append(production[1:] or [EPSILON])
        else:
            non_recursive.append(production)

    if not recursive:
        return

    helper = _fresh_non_terminal(nt + "'", productions)
    productions[helper] = []
    productions[nt] = []

    for beta in non_recursive:
        productions[nt].append(_concat_without_double_epsilon(beta, [helper]))
    for alpha in recursive:
        productions[helper].append(_concat_without_double_epsilon(alpha, [helper]))
    productions[helper].append([EPSILON])


def left_factoring(grammar):
    """Perform iterative left factoring."""
    result = grammar.clone()
    changed = True
    while changed:
        changed = False
        for nt in list(result.productions.keys()):
            groups = _prefix_groups(result.productions[nt])
            group = next((g for g in groups if len(g) > 1), None)
            if not group:
                continue

            prefix = _longest_common_prefix(group)
            helper = _fresh_non_terminal(nt + "'", result.productions)
            remaining = [prod for prod in result.productions[nt] if prod not in group]
            remaining.append(prefix + [helper])
            result.productions[nt] = remaining
            result.productions[helper] = [
                prod[len(prefix):] if prod[len(prefix):] else [EPSILON]
                for prod in group
            ]
            changed = True
            break
    return result


def detect_left_factoring(grammar):
    return [
        nt for nt, alternatives in grammar.productions.items()
        if any(len(group) > 1 for group in _prefix_groups(alternatives))
    ]


def _prefix_groups(alternatives):
    groups = OrderedDict()
    for production in alternatives:
        if production == [EPSILON]:
            continue
        groups.setdefault(production[0], []).append(production)
    return list(groups.values())


def _longest_common_prefix(productions):
    prefix = []
    for symbols in zip(*productions):
        if len(set(symbols)) == 1:
            prefix.append(symbols[0])
        else:
            break
    return prefix


def _fresh_non_terminal(base, productions):
    candidate = base
    while candidate in productions:
        candidate += "'"
    return candidate


def _concat_without_double_epsilon(left, right):
    merged = ([] if left == [EPSILON] else list(left)) + ([] if right == [EPSILON] else list(right))
    return merged or [EPSILON]


def compute_first_sets(grammar):
    first = {nt: set() for nt in grammar.productions}
    changed = True
    while changed:
        changed = False
        for nt, alternatives in grammar.productions.items():
            for production in alternatives:
                before = len(first[nt])
                first[nt].update(first_of_sequence(production, first, grammar))
                changed = changed or len(first[nt]) > before
    return first


def first_of_sequence(sequence, first_sets, grammar):
    if not sequence or sequence == [EPSILON]:
        return {EPSILON}

    result = set()
    for symbol in sequence:
        if symbol == EPSILON:
            result.add(EPSILON)
            break
        if symbol not in grammar.productions:
            result.add(symbol)
            break
        result.update(first_sets[symbol] - {EPSILON})
        if EPSILON not in first_sets[symbol]:
            break
    else:
        result.add(EPSILON)
    return result


def compute_follow_sets(grammar, first_sets):
    follow = {nt: set() for nt in grammar.productions}
    follow[grammar.start_symbol].add(ENDMARK)

    changed = True
    while changed:
        changed = False
        for lhs, alternatives in grammar.productions.items():
            for production in alternatives:
                for index, symbol in enumerate(production):
                    if symbol not in grammar.productions:
                        continue
                    trailer = production[index + 1:]
                    first_trailer = first_of_sequence(trailer, first_sets, grammar)
                    before = len(follow[symbol])
                    follow[symbol].update(first_trailer - {EPSILON})
                    if not trailer or EPSILON in first_trailer:
                        follow[symbol].update(follow[lhs])
                    changed = changed or len(follow[symbol]) > before
    return follow


def format_grammar(grammar):
    return "\n".join(
        f"{nt} -> {' | '.join(format_symbols(prod) for prod in alternatives)}"
        for nt, alternatives in grammar.productions.items()
    )


def format_production(lhs, production):
    return f"{lhs} -> {format_symbols(production)}"


def format_symbols(symbols):
    if symbols == [EPSILON]:
        return EPSILON
    return " ".join(symbols)

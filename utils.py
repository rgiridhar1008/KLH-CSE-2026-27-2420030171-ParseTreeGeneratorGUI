"""Formatting and export helpers for the GUI."""

from pathlib import Path

from grammar import ENDMARK, EPSILON, format_grammar, format_symbols


SAMPLES = [
    ("Simple", "S -> aA\nA -> b", "ab"),
    ("Factoring", "A -> ab | ac", "ab"),
    (
        "Left recursion",
        "E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id",
        "id+id*id",
    ),
    (
        "LL(1) expression",
        "E -> T E'\nE' -> + T E' | #\nT -> F T'\nT' -> * F T' | #\nF -> ( E ) | id",
        "id+id*id",
    ),
]


def format_sets(title, sets):
    lines = [title, "-" * len(title)]
    for symbol, values in sets.items():
        lines.append(f"{symbol} = {{ {', '.join(sorted(values))} }}")
    return "\n".join(lines)


def format_parse_table(grammar, table):
    terminals = grammar.terminals + [ENDMARK]
    lines = ["LL(1) Parse Table", "-" * 17]
    header = ["Non-Terminal"] + terminals
    widths = [max(12, len(item)) for item in header]

    rows = []
    for nt in grammar.productions:
        row = [nt]
        for terminal in terminals:
            production = table.get(nt, {}).get(terminal)
            row.append(format_symbols(production) if production else "")
        rows.append(row)
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]

    lines.append("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(header)))
    lines.append("  ".join("-" * width for width in widths))
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
    return "\n".join(lines)


def format_steps(steps):
    lines = ["Parsing Steps", "-" * 13]
    lines.append(f"{'Stack':<28}{'Input':<28}Action")
    lines.append("-" * 78)
    for step in steps:
        lines.append(f"{step.stack:<28}{step.remaining_input:<28}{step.action}")
    return "\n".join(lines)


def build_report(
    original,
    transformed,
    recursion_findings,
    factoring_findings,
    first_sets,
    follow_sets,
    table,
    conflicts,
    parse_result,
):
    sections = [
        "Original Grammar\n----------------\n" + format_grammar(original),
        "Transformed Grammar\n-------------------\n" + format_grammar(transformed),
    ]

    notes = []
    notes.extend(recursion_findings or ["No left recursion detected."])
    notes.extend(
        [f"Left factoring applied to {', '.join(factoring_findings)}"]
        if factoring_findings else ["No left factoring needed."]
    )
    sections.append("Grammar Transformations\n-----------------------\n" + "\n".join(notes))
    sections.append(format_sets("FIRST Sets", {f"FIRST({k})": v for k, v in first_sets.items()}))
    sections.append(format_sets("FOLLOW Sets", {f"FOLLOW({k})": v for k, v in follow_sets.items()}))
    sections.append(format_parse_table(transformed, table))

    status_lines = ["Grammar Status", "--------------"]
    status_lines.append("LL(1) Grammar" if not conflicts else "Not LL(1)")
    if conflicts:
        status_lines.append("Conflicts:")
        status_lines.extend(conflicts)
    sections.append("\n".join(status_lines))

    sections.append("Leftmost Derivation\n-------------------\n" + "\n".join(parse_result.leftmost_derivation or [EPSILON]))
    sections.append("Rightmost Derivation\n--------------------\n" + "\n".join(parse_result.rightmost_derivation or [EPSILON]))
    sections.append(format_steps(parse_result.steps))
    sections.append("String Validation Result\n------------------------\n" + parse_result.message)
    return "\n\n".join(sections)


def save_text_report(path, content):
    Path(path).write_text(content, encoding="utf-8")

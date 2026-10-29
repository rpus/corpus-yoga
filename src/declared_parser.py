"""declared_parser.py — argparse parsers GENERATED from src/main/cli/ declarations.

A declaration already states a command's structure — verbs, arguments, arity,
wording, outward sends — so its parser is derived, never hand-built (issues/474, issues/476):
argparse owns the parsing, the printer owns the -h and the refusal (DeclaredParser,
issues/973), the declaration owns everything it can say,
and a target contributes only its semantic residue (default, type, dest, nargs)
as per-argument overrides. verb_parser() is one verb's standalone parser (the
bash targets' parse_argv face); command_parser() is a python target's whole
surface — command-level arguments, one subparser per verb, the root's flags
re-accepted after each verb (issues/33) so the position the declaration renders
parses too.

prog is `corpus-yoga <command> [<verb>]`, never the implementing file: the reader is
shown what they typed. Cardinality speaks arity: blank — optional (nargs='?' as
a positional, a plain flag); '1' — required; '1/<class>' — the class's members
form one required mutually exclusive group. A flag with a declared type takes a
value (the type is its metavar); one without is a bare switch. Declared sends
render as each verb's epilog — an outward call is part of what the invocation
DOES (issues/29).

Stdlib only, and imported by stdlib-only faces (parse_argv.py) that run before
any venv exists.
"""
import argparse
import sys
from pathlib import Path
from typing import NoReturn


class DeclaredParser(argparse.ArgumentParser):
    """A generated parser whose help is the declaration's entry of the noun's help through
    the one printer (issues/973): `declared` names (command, verb) - verb None for a
    command's own parser - and -h prints that entry as `corpus-yoga <command> -h` prints
    it. argparse keeps the parsing and the usage line of a refusal, plain: it is told
    not to paint where the interpreter offers to (python 3.14's argparse colours a
    terminal unless told otherwise)."""

    def __init__(self, *args, declared: tuple, command_arguments: bool = False, **kwargs):
        try:
            super().__init__(*args, color=False, **kwargs)
        except TypeError:                   # an interpreter whose argparse has no colour
            super().__init__(*args, **kwargs)
        self.declared = declared
        self.command_arguments = command_arguments   # a subparser re-accepts the command's flags (issues/33)

    def _shape(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'main' / 'cli'))
        from cli import help_shape
        return help_shape(*self.declared, command_arguments=self.command_arguments)

    def format_help(self) -> str:
        """The help as a capture reads it: one line a fact."""
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'main'))
        import facts
        return '\n'.join(facts.lines(facts.plain(self._shape()), facts.depth(), width=None)) + '\n'

    def print_help(self, file=None) -> None:
        """The help as the reader sees it: said as every status is, at the terminal's width."""
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'main'))
        import facts
        if file is None or file is sys.stdout:
            facts.say(self._shape())
        else:
            file.write(self.format_help())

    def error(self, message: str) -> NoReturn:
        """A refusal restates the declaration (issues/973): the form of what was typed and what it
        requires, as facts on stderr, then the effect line `<act>: NOT DONE - <what was refused>`
        - handed up to the launcher where it dispatched this act, last on stderr otherwise
        (an inner invocation, a step of another verb, hands nothing up: facts.handed_up holds
        the act to its own). A command's parser refuses leftover argv on the verb's behalf,
        so the act is the verb typed, read from argv."""
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'main'))
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'main' / 'cli'))
        import facts
        from cli import refusal_shape, subcommands_of
        command, verb = self.declared
        if verb is None:                      # a command's parser refuses leftover argv on the verb's behalf: the verb typed
            verb = next((word for word in sys.argv[1:] if word in subcommands_of(command)), None)
        act = f'{command} {verb}' if verb else command
        shape = refusal_shape(command, verb)
        lines = facts.lines(facts.plain(shape), facts.depth(), width=None)
        effect = f'{act}: NOT DONE - {message}'
        if not facts.handed_up(effect):
            lines.append(effect)
        print('\n'.join(lines), file=sys.stderr, flush=True)
        sys.exit(2)


def _rows(command: str) -> list[dict]:
    """The command's declared rows — asked of cli, which is the one reader of
    src/main/cli/. Imported at CALL time so import order between the faces and
    cli can never cycle."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'main' / 'cli'))
    from cli import command_rows
    return command_rows(command)


def _sends(command: str, verb: str) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'main' / 'cli'))
    from cli import sends_of
    return sends_of(command, verb)


def _description(rows: list[dict]) -> str | None:
    return next((r['help'] for r in rows if not r['arg-name']), None)


def _epilog(command: str, verb: str) -> str | None:
    return '\n'.join(f'sends: {call} — {occasion}'
                     for call, occasions in _sends(command, verb).items()
                     for occasion in occasions) or None


# A declared metavar's python value type, matched EXACTLY (the PATH_ARG_TYPES
# pattern in cli.py: a metavar is a name, and reading meaning from its spelling
# would make <n-list> a number). A metavar absent here parses as a string,
# which is the safe way to be wrong.
VALUE_ARG_TYPES = {'<n>': int}


def _path_arg_types() -> set:
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'main' / 'cli'))
    from cli import PATH_ARG_TYPES
    return PATH_ARG_TYPES


def _tier_path(declared: str) -> str:
    """A declared repo-relative path under the tiers in force (src/main/tier.py, issues/702): a
    default naming data/ or tmp/ resolves to the stage's scratch when a rehearsal is named,
    the checkout's otherwise - never against the working directory, and never the
    checkout's from inside a rehearsal."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'main'))
    import tier
    return str(tier.path(declared))


def _add_arguments(parser, rows: list[dict], overrides: dict) -> None:
    """Each declared row becomes one add_argument call; overrides supply the
    residue and may not invent an argument the declaration lacks. A declared
    default is data (issues/477): a path-typed argument's default is repo-relative and
    resolves through the tier contract here (issues/702), any other passes verbatim — and the
    help shows the value as declared, so no help prose restates it."""
    groups: dict[str, object] = {}
    for r in rows:
        if not r['arg-name']:
            continue
        kwargs: dict = {'help': r['help'], **overrides.get(r['arg-name'], {})}
        card = r['cardinality']
        if r.get('default') is not None:
            declared = r['default']
            value = _tier_path(declared) if r['arg-type'] in _path_arg_types() else declared
            kwargs.setdefault('default', value)
        if '/' in card:
            # never setdefault here: its group argument is evaluated on EVERY
            # member, and each extra evaluation registers a stray EMPTY required
            # group on the parser — which then refuses every VALID exclusive
            # invocation (cli.exclusive_class_parses ships against the live bug)
            if card not in groups:
                groups[card] = parser.add_mutually_exclusive_group(
                    required=card.split('/')[0] == '1')
            holder = groups[card]
        else:
            holder = parser
        if r['arg-type'] in VALUE_ARG_TYPES:
            kwargs.setdefault('type', VALUE_ARG_TYPES[r['arg-type']])
        if r['arg-name'].startswith('--'):
            if r['arg-type']:
                kwargs.setdefault('metavar', r['arg-type'])
                if card == '*':
                    kwargs.setdefault('action', 'append')   # repeatable: each occurrence one value
            else:
                kwargs.setdefault('action', 'store_true')
            if card == '1':
                kwargs.setdefault('required', True)
        else:
            if r['arg-type']:
                kwargs.setdefault('metavar', r['arg-type'])
            if card == '*':
                kwargs.setdefault('nargs', '*')
            elif not card:
                kwargs.setdefault('nargs', '?')
        holder.add_argument(r['arg-name'], **kwargs)  # type: ignore[attr-defined]


def verb_parser(command: str, verb: str,
                overrides: dict | None = None) -> argparse.ArgumentParser:
    """One verb's standalone parser, whole from its declaration."""
    rows = [r for r in _rows(command) if r['subcommand'] == verb]
    parser = DeclaredParser(
        prog=f'corpus-yoga {command} {verb}', description=_description(rows),
        epilog=_epilog(command, verb),
        formatter_class=argparse.RawDescriptionHelpFormatter, declared=(command, verb))
    _add_arguments(parser, rows, (overrides or {}))
    return parser


def command_parser(command: str, overrides: dict | None = None,
                   dest: str = 'verb') -> argparse.ArgumentParser:
    """A command's whole parser: root arguments, one subparser per declared verb.
    overrides is keyed by verb ('' for the command level), each value
    {arg-name: add_argument kwargs}; dest names the attribute the chosen verb
    lands in (most targets read args.verb, agent its args.direction)."""
    rows = _rows(command)
    over = overrides or {}
    root_rows = [r for r in rows if not r['subcommand']]
    parser = DeclaredParser(prog=f'corpus-yoga {command}',
                            description=_description(root_rows), declared=(command, None))
    _add_arguments(parser, root_rows, over.get('', {}))
    verbs: list[str] = []
    for r in rows:
        if r['subcommand'] and r['subcommand'] not in verbs:
            verbs.append(r['subcommand'])
    if verbs:
        action = parser.add_subparsers(dest=dest, parser_class=DeclaredParser)
        for verb in verbs:
            verb_rows = [r for r in rows if r['subcommand'] == verb]
            sub = action.add_parser(verb, description=_description(verb_rows),
                                    epilog=_epilog(command, verb),
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    declared=(command, verb), command_arguments=True)
            _add_arguments(sub, verb_rows, over.get(verb, {}))
            # Re-accept the root's flags after the verb (issues/33). SUPPRESS defaults:
            # a subparser writes its defaults into the shared namespace AFTER the
            # root has parsed, so a real default here would overwrite a value
            # given before the verb.
            for r in root_rows:
                if not r['arg-name'].startswith('--'):
                    continue
                kwargs = {'help': r['help'], 'default': argparse.SUPPRESS}
                if r['arg-type']:
                    kwargs['metavar'] = r['arg-type']
                else:
                    kwargs['action'] = 'store_true'
                sub.add_argument(r['arg-name'], **kwargs)
    return parser

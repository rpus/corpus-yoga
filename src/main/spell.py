"""
spell.py - the one spelling of a corpus-yoga command, built from its declaration (issues/885):
line() spells `corpus-yoga <noun> [<verb>] [<positional>...] [--flag [value]]...` from
src/main/cli/<noun>/<noun>.json and <noun>/<verb>.json, so that a noun, a verb or a flag the
declarations do not hold is unrepresentable - Undeclared is raised where it is asked for -
and a rename reaches every site that spells the command. mentions() reads the spellings a
text carries, as the gate holds every source and document to the declarations.
"""
import re
import shlex
from pathlib import Path

CLI = Path(__file__).resolve().parent / 'cli'
ROOT = 'corpus-yoga'
PLACEHOLDER = re.compile(r'^(\{[^}]*\}|<[^>]*>|\$\S*|\.\.\.)$')     # a value a site fills at run time, never a word to check


class Undeclared(LookupError):
    """A spelling no declaration holds: the noun, the verb or the flag named."""


def _load(path: Path) -> dict:
    import json
    return json.loads(path.read_text())


def nouns() -> list[str]:
    return sorted(p.name for p in CLI.iterdir() if p.is_dir() and (p / f'{p.name}.json').is_file())


def verbs(noun: str) -> list[str]:
    if noun not in nouns():
        raise Undeclared(f'{ROOT} declares no noun {noun!r}')
    return sorted(p.stem for p in (CLI / noun).glob('*.json') if p.stem != noun)


def arguments(noun: str = '', verb: str = '') -> list[dict]:
    """The declared arguments of the root (no noun), a noun, or a noun's verb."""
    if not noun:
        return _load(CLI / f'{ROOT}.json').get('args', [])
    if noun not in nouns():
        raise Undeclared(f'{ROOT} declares no noun {noun!r}')
    if not verb:
        return _load(CLI / noun / f'{noun}.json').get('args', [])
    if verb not in verbs(noun):
        raise Undeclared(f'{ROOT} {noun} declares no verb {verb!r}')
    return _load(CLI / noun / f'{verb}.json').get('args', [])


def _flags(args: list[dict]) -> dict[str, dict]:
    return {a['name']: a for a in args if a['name'].startswith('-')}


def _positionals(args: list[dict]) -> list[dict]:
    return [a for a in args if not a['name'].startswith('-')]


def takes(noun: str, verb: str, flag: str) -> bool:
    """Whether the verb (or the bare noun) declares the flag, named with or without its dashes."""
    return _dashed(flag) in _flags(arguments(noun, verb))


def _dashed(flag: str) -> str:
    if flag.startswith('-'):
        return flag
    name = flag.replace('_', '-')
    return f'-{name}' if len(name) == 1 else f'--{name}'


def line(noun: str = '', verb: str = '', *positional, **flag) -> str:
    """The command as typed: the root, the noun, the verb, each declared positional in its
    declared order, then each flag given in its declared order - a boolean flag by its name
    where its value is true, an option with its value. What the declaration does not hold
    raises Undeclared."""
    args = arguments(noun, verb)
    flags, positionals = _flags(args), _positionals(args)
    words = [ROOT] + ([noun] if noun else []) + ([verb] if verb else [])
    required = [a for a in positionals if a['cardinality'] == '1']
    variadic = positionals and positionals[-1]['cardinality'] == '*'
    if len(positional) < len(required):
        raise Undeclared(f'{" ".join(words)} takes {len(required)} positional argument(s), {", ".join(a["name"] for a in required)}; {len(positional)} given')
    if len(positional) > len(positionals) and not variadic:
        raise Undeclared(f'{" ".join(words)} takes at most {len(positionals)} positional argument(s); {len(positional)} given')
    words += [shlex.quote(str(value)) for value in positional]
    given = {_dashed(name): value for name, value in flag.items()}
    for name in given:
        if name not in flags:
            raise Undeclared(f'{" ".join(words[:3 if verb else 2])} declares no flag {name}')
    for name, declared in flags.items():
        if name not in given:
            continue
        value = given[name]
        if declared['type'] == '':
            if value:
                words.append(name)
        else:
            words += [name, shlex.quote(str(value))]
    return ' '.join(words)


_MENTION = re.compile(r'corpus-yoga((?: [^\s`"\'(),;:]+)*)')


def mentions(text: str) -> list[tuple[str, str]]:
    """Each spelling of a corpus-yoga command the text carries, with the fault the
    declarations find in it, or '' where it is declared. A word after corpus-yoga is a noun
    where it is declared, and prose where it is not - the product's name is used in prose -
    unless the word after it is a verb some noun declares, which makes the pair a spelling of
    a noun that is not declared. A word after the noun that is one of its verbs is the verb;
    each flag after that must be declared for the verb, for the noun where no verb stands,
    or at the root, an option's value skipped; a placeholder - {word}, <word>, $word - stands
    for a value and is not checked, and a placeholder noun's verb and flags must be declared
    by every noun that declares the verb. Any other word ends the spelling: the text goes on
    as prose."""
    found = []
    known = nouns()
    for m in _MENTION.finditer(text):
        tokens = m.group(1).split()
        spelling = 'corpus-yoga' + (' ' + ' '.join(tokens) if tokens else '')
        if not tokens:
            found.append((spelling, ''))
            continue
        noun = tokens[0]
        if noun.startswith('-'):
            found.append((spelling, _check_flags('', '', tokens, [])))
            continue
        if PLACEHOLDER.match(noun):
            found.append((spelling, _check_placeholder_noun(tokens[1:], known)))
            continue
        if noun not in known:
            verb_like = len(tokens) > 1 and any(tokens[1] in verbs(n) for n in known)
            found.append((spelling, f'no noun {noun!r}' if verb_like and re.match(r'^[a-z][a-z0-9-]*$', noun) else ''))
            continue
        verb, rest = '', tokens[1:]
        if rest and rest[0] in verbs(noun):
            verb, rest = rest[0], rest[1:]
        found.append((spelling, _check_flags(noun, verb, rest, [])))
    return found


def _check_flags(noun: str, verb: str, rest: list[str], _unused) -> str:
    flags = {**_flags(arguments()), **_flags(arguments(noun, verb))}     # the root's flags stand before or after the command word
    i = 0
    while i < len(rest):
        token = rest[i]
        if not token.startswith('-') or token == '-' or PLACEHOLDER.match(token):
            break
        name = token.split('=')[0]
        if name not in flags:
            where = ' '.join(w for w in (ROOT, noun, verb) if w)
            return f'{where} declares no flag {name}'
        if flags[name]['type'] != '' and '=' not in token:
            i += 1      # the option's value
        i += 1
    return ''


def _check_placeholder_noun(rest: list[str], known: list[str]) -> str:
    if not rest or PLACEHOLDER.match(rest[0]):
        return ''
    verb = rest[0]
    holders = [n for n in known if verb in verbs(n)]
    if not holders:
        return ''      # the placeholder is the product's name in prose
    faults = [f'{n}: {fault}' for n in holders if (fault := _check_flags(n, verb, rest[1:], []))]
    return '; '.join(faults)

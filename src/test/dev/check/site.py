"""site.py - the dev gate's checks of the site and the server: the page against the corpus and rpus.co, and the daemon."""
import os
import sys
from pathlib import Path

from gate import (
    REPO_ROOT,
    SRC,
    check,
)


@check(tier='code', on=['src/main/page_declaration.py', 'src/main/markdown_projection.py', 'src/main/model/compare_pages.py'], says=(
    'site.lag_is_read_from_declarations',
    'site.page_comparison_lists_measure_changes',
    'site.page_comparison_survives_a_new_column',
    'site.turn_instant_is_read_from_the_heading',
))
def check_site_lag(run) -> None:
    """The corpus page declares what it was rendered from per conversation - human turns,
    assistant turns, bytes - and the site status reads those declarations against the corpus
    now: a conversation that grew is a lag, one that shrank in any metric is a
    regression said as a warning, one in the corpus and not on the page is absent, one on the
    page and not in the corpus is gone. Held over the one derivation in process, with planted
    declarations: the room's page and corpus are the usr gate's."""
    import importlib
    sys.path.insert(0, str(SRC / 'main'))
    try:
        declared = importlib.import_module('page_declaration')
    except ModuleNotFoundError:
        run('site: the page lags where its declarations differ from the corpus', False,
            'src/main/page_declaration.py is absent: nothing declares what the page was rendered from', check='site.lag_is_read_from_declarations')
        return
    md = ('---\nuuid: aaaa\nhuman: 2\nassistant: 1\n---\n\n# t\n\n## Human (1) <a id="h1"></a>\n\nhello\n\n---\n\n'
          '## Claude (1) <a id="a1"></a>\n\nhi there\n\n---\n\n## Human (2) <a id="h2"></a>\n\nmore\n\n---\n')   # as a projection writes it (issues/1001)
    counts = declared.declared_of(md)
    ok = counts == {'human': 2, 'assistant': 1, 'bytes': len(md.encode())}
    run('site: a conversation declares its human turns, assistant turns and bytes', ok,
        None if ok else f'the declaration read {counts}', check='site.lag_is_read_from_declarations')
    page = {'grown': {'human': 2, 'assistant': 2, 'bytes': 100}, 'shrunk': {'human': 3, 'assistant': 3, 'bytes': 300},
            'same': {'human': 1, 'assistant': 1, 'bytes': 10}, 'gone': {'human': 1, 'assistant': 1, 'bytes': 10}}
    corpus = {'grown': {'human': 3, 'assistant': 3, 'bytes': 160}, 'shrunk': {'human': 3, 'assistant': 2, 'bytes': 280},
              'same': {'human': 1, 'assistant': 1, 'bytes': 10}, 'new': {'human': 1, 'assistant': 0, 'bytes': 5}}
    lag = declared.lag(page, corpus)
    got = (sorted(lag.lagging), sorted(lag.regressed), sorted(lag.absent_from_page), sorted(lag.gone_from_corpus))
    expected = (['grown'], ['shrunk'], ['new'], ['gone'])
    run('site: the page lags where its declarations differ from the corpus', got == expected,
        None if got == expected else f'the lag read {got}, where (lagging, regressed, absent, gone) are {expected}',
        check='site.lag_is_read_from_declarations')
    # A turn's instant is read from its heading first - the instant a projection wrote beside the
    # anchor - and from a v7 uuid only where the heading carries none (issues/1007): a code
    # session's v4 uuids carry no instant, and its spans, bars and hover were absent for it.
    instants = getattr(declared, 'turn_instants', None)
    md = ('## Human (1) <a id="5d4f5604-b345-41d2-a166-05facdd3931d" data-at="2026-08-05T07:21:53Z"></a>\n\nx\n\n---\n\n'
          '## Claude (1) <a id="01990000-0000-7000-8000-000000000000"></a>\n\ny\n\n---\n\n'
          '## Human (2) <a id="human-2"></a>\n\nz\n\n---\n')
    got = [i.isoformat() for i in instants(md)] if instants else None
    expected = ['2026-08-05T07:21:53+00:00', '2025-08-31T12:00:24.064000+00:00']
    ok = got == expected
    run('site: a turn\'s instant is read from its heading, then from a v7 uuid', ok,
        None if ok else f'the instants read {got}, where the heading\'s and the v7 uuid\'s are {expected}',
        check='site.turn_instant_is_read_from_the_heading')
    # The landing's page comparison says a column one page lacks, once, as the table's change -
    # never a crash the status reads as nothing to land, and never a change of every row.
    sys.path.insert(0, str(SRC / 'main' / 'model'))
    compare_pages = importlib.import_module('compare_pages')
    old_table = {'columns': ['chat', 'uuid', 'name', 'turns'], 'rows': [[1, 'aaaa', 'a', 2]]}
    new_table = {'columns': ['chat', 'uuid', 'name', 'turns', 'human'], 'rows': [[1, 'aaaa', 'a', 2, 1]]}
    try:
        said = compare_pages.compare_table('data-chats', old_table, new_table, {}, {})
        why = None if said == [('data-chats', 'columns added', 'human')] else f'the comparison said {said!r}'
    except Exception as error:   # noqa: BLE001 - the failure IS the finding
        why = f'the comparison raised {type(error).__name__}: {error}'
    run('site: the page comparison says a column one page lacks once, as the table\'s change', why is None, why,
        check='site.page_comparison_survives_a_new_column')
    # A row whose content measures changed is listed with them, and rows changed elsewhere alone
    # are counted (issues/1028): a change of turns can be held to expectation, a uniform change
    # of bytes is a format's - and every count has its denominator. The live case: reading-room,
    # 2026-11-08, 127 chats changed in bytes alone listed among any whose turns had changed.
    columns = ['chat', 'uuid', 'name', 'provider', 'channel', 'turns', 'human', 'assistant', 'bytes']
    old_chats = {'columns': columns, 'rows': [[1, 'aaaaaaaa', 'a', 'claude', 'chat', 2, 1, 1, 10], [2, 'bbbbbbbb', 'b', 'claude', 'chat', 2, 1, 1, 20],
                                              [3, 'cccccccc', 'c', 'claude', 'chat', 2, 1, 1, 30]]}
    new_chats = {'columns': columns, 'rows': [[1, 'aaaaaaaa', 'a', 'claude', 'chat', 4, 2, 2, 12], [2, 'bbbbbbbb', 'b', 'claude', 'chat', 2, 1, 1, 25],
                                              [3, 'cccccccc', 'c', 'claude', 'chat', 2, 1, 1, 35], [4, 'dddddddd', 'd', 'gemini', 'chat', 2, 1, 1, 40]]}
    try:
        facts_said = compare_pages.compare_table('data-chats', old_chats, new_chats, {}, {})
    except Exception as error:   # noqa: BLE001 - the failure IS the finding
        facts_said = f'raised {type(error).__name__}: {error}'
    want = [('data-chats', 'added', 'gemini/chat (1 of 1)', 'dddddddd "d"'),
            ('data-chats', 'turns changed', 'claude/chat (1 of 3)', 'aaaaaaaa "a"', 'human', '2 (+1)'),
            ('data-chats', 'turns changed', 'claude/chat (1 of 3)', 'aaaaaaaa "a"', 'assistant', '2 (+1)'),
            ('data-chats', 'changed in bytes alone', 'claude/chat', '2 of 3')]
    run('site: the page comparison says what is added, removed and changed by group, each count of its group\'s whole - the turns changed listed, the rest counted',
        facts_said == want, None if facts_said == want else f'the comparison said {facts_said!r}', check='site.page_comparison_lists_measure_changes')


@check(tier='code', on=['src/main/cli/site', 'src/main/enact.sh', 'src/main/send.sh', 'src/main/report.sh'], says=(
    'site.clone_position_is_said',
    'site.landing_reads_the_fetched_origin',
    'site.publish_levels_the_clone',
    'site.reads_the_served_branch',
))
def check_site_reads_rpus_co(run) -> None:
    """The site reads rpus.co as it stands: what publish would land is the publish
    tree against the clone's fetched origin, never the clone's files as they last stood; the
    clone's position to that origin is said - behind, diverged - and publish brings it level by
    a fast-forward, refusing where it cannot. Held over planted clones of a local bare
    repository, since the room's clone is the usr gate's."""
    import subprocess
    import tempfile
    library = SRC / 'main' / 'cli' / 'site' / 'landing.sh'
    if not library.is_file():
        run('site: what publish would land is read against the clone\'s fetched origin', False,
            'src/main/cli/site/landing.sh does not exist: the landing compares with the clone\'s files as they last stood',
            check='site.landing_reads_the_fetched_origin')
        return
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        # the remote is a local directory, so nothing leaves the machine; and no variable git exports to a
        # hook reaches these clones - under the commit hook GIT_INDEX_FILE names the index being
        # committed, and a planted clone's add and commit wrote into it (reading-room, 2026-11-08)
        environment = {k: v for k, v in os.environ.items() if k != 'CORPUS_YOGA_NO_SEND' and not k.startswith('GIT_')}
        environment['CORPUS_YOGA_DECLARATION'] = 'src/main/cli/site/publish.json'   # the clone's sends are publish's, run against a planted origin
        environment.update({'GIT_AUTHOR_NAME': 'gate', 'GIT_AUTHOR_EMAIL': 'gate@localhost', 'GIT_COMMITTER_NAME': 'gate',
                            'GIT_COMMITTER_EMAIL': 'gate@localhost', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1'})
        def git(*words, cwd=root):
            subprocess.run(['git', *words], cwd=cwd, env=environment, check=True, capture_output=True)
        def commit(clone, text):
            (clone / 'page.html').write_text(text)
            git('add', '-A', cwd=clone)
            git('commit', '-q', '-m', text, cwd=clone)
        git('init', '-q', '--bare', '-b', 'main', 'origin.git')
        git('clone', '-q', 'origin.git', 'publisher')
        publisher = root / 'publisher'
        commit(publisher, 'one')
        git('push', '-q', 'origin', 'HEAD:main', cwd=publisher)
        for name in ('behind', 'diverged', 'elsewhere'):
            git('clone', '-q', 'origin.git', name)
        commit(root / 'diverged', 'local')
        git('switch', '-q', '-c', 'feature', cwd=root / 'elsewhere')     # a clone standing on a branch rpus.co does not serve (issues/1026)
        commit(root / 'elsewhere', 'feature')
        git('push', '-q', '-u', 'origin', 'feature', cwd=root / 'elsewhere')
        commit(publisher, 'two')
        git('push', '-q', 'origin', 'HEAD:main', cwd=publisher)
        for name in ('behind', 'diverged', 'elsewhere'):
            git('fetch', '-q', cwd=root / name)
        tree = root / 'tree'
        tree.mkdir()
        (tree / 'page.html').write_text('two')
        def said(function, *arguments):
            script = (f'REPO_DIR={str(REPO_ROOT)!r}; source "$REPO_DIR/src/main/report.sh"; source "$REPO_DIR/src/main/send.sh"; '
                      f'source "$REPO_DIR/src/main/enact.sh"; source "$REPO_DIR/src/main/cli/site/landing.sh"; {function} "$@"')
            done = subprocess.run(['bash', '-c', script, 'landing', *map(str, arguments)], env=environment, capture_output=True, text=True)
            return done.returncode, [line.split('\t') for line in done.stdout.splitlines() if line]
        _, landed = said('landing', root / 'behind', tree)
        run("site: what publish would land is read against the clone's fetched origin", landed == [],
            None if landed == [] else f'a clone one commit behind lands {landed}, where rpus.co already holds the tree',
            check='site.landing_reads_the_fetched_origin')
        _, behind = said('clone_position', root / 'behind')
        _, diverged = said('clone_position', root / 'diverged')
        told = (len(behind) == 1 and behind[0][:1] == ['clone'] and behind[0][1].startswith('behind')
                and len(diverged) == 1 and diverged[0][1].startswith('diverged'))
        run("site: the clone's position to its fetched origin is said", told,
            None if told else f'said {behind} of a clone behind and {diverged} of a diverged one', check='site.clone_position_is_said')
        levelled, _ = said('level_clone', root / 'behind')
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root / 'behind', env=environment, capture_output=True, text=True).stdout
        tip = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=publisher, env=environment, capture_output=True, text=True).stdout
        refused, _ = said('level_clone', root / 'diverged')
        level = levelled == 0 and head == tip and refused != 0
        run('site: publish brings a clone level by a fast-forward, and refuses where it cannot', level,
            None if level else f'levelling exited {levelled} (head {"at" if head == tip else "not at"} the origin) and {refused} on a diverged clone',
            check='site.publish_levels_the_clone')
        # rpus.co is the branch it serves, the remote's default, whatever the clone has checked out
        # (issues/1026): a clone on another branch lands what rpus.co lacks, says the branch it
        # stands on, and is refused the publish by name
        _, elsewhere_lands = said('landing', root / 'elsewhere', tree)
        _, elsewhere_stands = said('clone_position', root / 'elsewhere')
        _, off = said('off_served', root / 'elsewhere')
        _, on = said('off_served', root / 'behind')
        served = (elsewhere_lands == [] and len(elsewhere_stands) == 1 and 'feature' in elsewhere_stands[0][1]
                  and off == [['feature']] and on == [])
        run('site: rpus.co is read as the branch it serves, whatever branch the clone has checked out', served,
            None if served else f'a clone on feature lands {elsewhere_lands}, stands {elsewhere_stands}, is off the served branch as {off}; one on it as {on}',
            check='site.reads_the_served_branch')


@check(tier='code', on=['src/main/cli/server/status.py', 'src/main/facts.py'], says=(
    'server.now_names_the_stop_or_the_start',
))
def check_server_standing(run) -> None:
    """The server's standing is a function of two facts of the room: the stop
    while the daemon runs, the start while the corpus is rendered and the daemon is down,
    none otherwise - read from the status's own function, since the gate's room never
    runs the daemon and a rendered-output check would sample one state."""
    import importlib.util
    sys.path.insert(0, str(SRC / 'main'))
    spec = importlib.util.spec_from_file_location('server_status', SRC / 'main' / 'cli' / 'server' / 'status.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules['server_status'] = module
    spec.loader.exec_module(module)
    daemon_act = getattr(module, 'daemon_act', None)
    facts = sys.modules.get('facts') or __import__('facts')
    said = {case: (facts.now_of({'remedy': daemon_act(*case)}) or 'none - nothing to do') for case in ((True, True), (True, False), (False, True), (False, False))} if daemon_act else {}
    want = {(True, True): {'corpus-yoga server stop': {'would stop': {'serve_markdown daemon': 1}}},
            (True, False): {'corpus-yoga server stop': {'would stop': {'serve_markdown daemon': 1}}},
            (False, True): {'corpus-yoga server start --daemon': {'would serve': {'data/output/markdown': 1}}},
            (False, False): 'none - nothing to do'}
    run("server: its now: names the stop while the daemon runs, the start while the corpus is rendered and the daemon is down, none otherwise",
        said == want, None if said == want else ('status.py declares no daemon_act(running, rendered)' if not daemon_act else f'said {said!r}'),
        check='server.now_names_the_stop_or_the_start')

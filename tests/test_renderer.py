from __future__ import annotations

import io
import re

from rich.console import Console
from rich.text import Text

from app.core.battle_system import TurnBattleSystem
from app.core.player import Trainer
from app.schemas.typing import Typing
from app.ui.renderer import _render_log, _render_moves, _style_log_entry

from .conftest import make_move, make_pkmn

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def _segments(text: Text) -> list[tuple[str, bool | None, bool | None, bool | None, str | None]]:
    console = Console(force_terminal=True, width=120, highlight=False)
    out = []
    for seg in text.render(console):
        st = seg.style
        out.append((
            seg.text,
            st.italic if st else None,
            st.dim if st else None,
            st.bold if st else None,
            st.color.name if (st and st.color) else None,
        ))
    return out


def _render_plain(renderable) -> str:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120, highlight=False)
    console.print(renderable)
    return _ANSI_RE.sub('', buf.getvalue())


class TestStyleLogEntry:
    def test_move_italic(self):
        t = Text('Snorlax used Counter!')
        _style_log_entry(t, set(), set())
        segs = _segments(t)
        counter = next(s for s in segs if s[0] == 'Counter')
        assert counter[1] is True
        assert counter[2] is None
        assert counter[4] is None

    def test_player_pokemon_cyan(self):
        t = Text('Go, Tentacruel!')
        _style_log_entry(t, {'tentacruel'}, set())
        segs = _segments(t)
        tent = next(s for s in segs if s[0] == 'Tentacruel')
        assert tent[1] is True
        assert tent[4] == 'cyan'

    def test_ai_pokemon_red(self):
        t = Text('Vulpix fainted!')
        _style_log_entry(t, set(), {'vulpix'})
        segs = _segments(t)
        vulpix = next(s for s in segs if s[0] == 'Vulpix')
        assert vulpix[1] is True
        assert vulpix[4] == 'red'

    def test_unknown_pokemon_dim(self):
        t = Text('Mewtwo used Psywave!')
        _style_log_entry(t, {'snorlax'}, {'vulpix'})
        segs = _segments(t)
        mewtwo = next(s for s in segs if s[0] == 'Mewtwo')
        assert mewtwo[1] is True
        assert mewtwo[2] is True
        assert mewtwo[4] is None

    def test_plain_text_untouched(self):
        t = Text('It is confused!')
        _style_log_entry(t, set(), set())
        segs = _segments(t)
        assert len(segs) == 1
        assert segs[0][1] is None
        assert segs[0][4] is None

    def test_multiline_styles_each_line(self):
        t = Text('Snorlax used Counter!\nIt\'s super effective!')
        _style_log_entry(t, set(), set())
        segs = _segments(t)
        assert any(s[0] == 'Counter' and s[1] is True for s in segs)
        assert any(s[1] is None and "It's super effective!" in s[0] for s in segs)

    def test_last_entry_bold_white_keeps_owner_color(self):
        t = Text('Vulpix fainted!')
        t.stylize('bold white', 0, len(t))
        _style_log_entry(t, set(), {'vulpix'})
        segs = _segments(t)
        vulpix = next(s for s in segs if s[0] == 'Vulpix')
        assert vulpix[3] is True
        assert vulpix[4] == 'red'
        tail = next(s for s in segs if s[0] == ' fainted!')
        assert tail[3] is True
        assert tail[4] == 'white'


class TestRenderLog:
    def _make_bs(self) -> TurnBattleSystem:
        player = Trainer()
        ai = Trainer()
        bs = TurnBattleSystem(player, ai)
        bs.player.team = [make_pkmn(name='Tentacruel', level=50)] + [None] * 5
        bs.ai.team = [make_pkmn(name='Vulpix', level=50)] + [None] * 5
        player.in_battle = bs.player.team[0]
        ai.in_battle = bs.ai.team[0]
        bs.player_mon = player.in_battle
        bs.enemy_mon = ai.in_battle
        return bs

    def test_renders_round_side_and_message(self):
        bs = self._make_bs()
        bs.log_message('player', 'Tentacruel used Hydro Pump!')
        bs.log_message('ai', 'Vulpix used Rage!')

        out = _render_plain(_render_log(bs))

        assert 'R1' in out
        assert 'Player' in out
        assert 'AI' in out
        assert 'Hydro Pump' in out
        assert 'Rage' in out

    def test_entries_separated_by_blank_line(self):
        bs = self._make_bs()
        bs.log_message('player', 'Tentacruel used Hydro Pump!')
        bs.log_message('ai', 'Vulpix used Rage!')

        lines = _render_plain(_render_log(bs)).splitlines()

        assert any('Hydro Pump!' in line for line in lines)
        assert any('Rage!' in line for line in lines)
        assert any(not line.strip() for line in lines)

    def test_line_budget_keeps_recent_entries_only(self):
        bs = self._make_bs()
        for i in range(20):
            bs.log_message('player', f'msg {i}')

        out = _render_plain(_render_log(bs))

        assert 'msg 19' in out
        assert 'msg 5' not in out

    def test_owner_color_renders_for_fainted_enemy(self):
        bs = self._make_bs()
        bs.log_message('player', 'Tentacruel used Hydro Pump!\nVulpix fainted!')

        out = _render_plain(_render_log(bs))

        assert 'Tentacruel' in out
        assert 'Vulpix fainted' in out

    def test_last_entry_highlighted(self):
        bs = self._make_bs()
        bs.log_message('player', 'Tentacruel used Hydro Pump!')
        bs.log_message('ai', 'Vulpix used Rage!')

        out = _render_plain(_render_log(bs))

        assert 'Vulpix used Rage!' in out


class TestRenderMoves:
    def test_renders_moves_with_slot_type_pp(self):
        p = make_pkmn(
            name='Blastoise',
            moves=[
                make_move(name='Hydro Pump', typing=Typing.WATER),
                make_move(name='Tackle'),
                None,
                None,
            ],
        )

        out = _render_plain(_render_moves(p))

        assert '[1]' in out
        assert '[2]' in out
        assert 'Hydro Pump' in out
        assert 'WATER' in out
        assert 'NORMAL' in out
        assert '/35' in out

    def test_no_pp_move_flagged(self):
        p = make_pkmn(
            name='Blastoise', moves=[make_move(name='Hydro Pump', pp=0), None, None, None],
        )

        out = _render_plain(_render_moves(p))

        assert '(no PP)' in out
        assert '0/0' in out

    def test_skips_empty_slots(self):
        p = make_pkmn(
            name='Blastoise',
            moves=[
                make_move(name='Hydro Pump', typing=Typing.WATER),
                None, None, None,
            ],
        )

        out = _render_plain(_render_moves(p))

        assert '[1]' in out
        assert '[2]' not in out

    def test_no_literal_broken_tag(self):
        p = make_pkmn(
            name='Blastoise',
            moves=[make_move(name='Hydro Pump'), None, None, None],
        )

        out = _render_plain(_render_moves(p))

        assert '[/{c}]' not in out
        assert '[/' not in out

    def test_type_colored(self):
        p = make_pkmn(
            name='Blastoise',
            moves=[make_move(name='Hydro Pump', typing=Typing.WATER), None, None, None],
        )

        out = _render_plain(_render_moves(p))

        assert 'WATER' in out

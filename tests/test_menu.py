"""Tests for arrow-key menu."""
from rocky.ui.menu import ArrowMenu


class TestArrowMenu:
    def test_menu_creation(self):
        menu = ArrowMenu(
            title="Test?",
            options=["Yes", "No", "Maybe"],
            default=0
        )
        assert menu.selected == 0
        assert len(menu.options) == 3

    def test_move_down(self):
        menu = ArrowMenu(title="Test?", options=["A", "B", "C"])
        menu.move_down()
        assert menu.selected == 1
        menu.move_down()
        assert menu.selected == 2

    def test_move_down_wraps(self):
        menu = ArrowMenu(title="Test?", options=["A", "B", "C"])
        menu.move_down()
        menu.move_down()
        menu.move_down()
        assert menu.selected == 0  # wraps to top

    def test_move_up(self):
        menu = ArrowMenu(title="Test?", options=["A", "B", "C"], default=2)
        menu.move_up()
        assert menu.selected == 1

    def test_move_up_wraps(self):
        menu = ArrowMenu(title="Test?", options=["A", "B", "C"], default=0)
        menu.move_up()
        assert menu.selected == 2  # wraps to bottom

    def test_get_selected(self):
        menu = ArrowMenu(title="Test?", options=["Yes", "No", "Maybe"], default=1)
        assert menu.get_selected() == "No"

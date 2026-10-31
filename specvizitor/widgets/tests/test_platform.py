"""On GNOME's Wayland session the application draws its own title bar, and Qt6's looks blurrier and lags behind a
fast object switch: specvizitor runs through XWayland there instead, as it always did with Qt5.
"""

import pytest

from specvizitor.main import prefer_xwayland_on_gnome


@pytest.mark.parametrize('desktop', ['GNOME', 'ubuntu:GNOME', 'gnome'])
def test_gnome_on_wayland_prefers_xwayland(desktop):
    environ = {'XDG_SESSION_TYPE': 'wayland', 'XDG_CURRENT_DESKTOP': desktop}
    prefer_xwayland_on_gnome(environ)

    assert environ['QT_QPA_PLATFORM'] == 'xcb;wayland'


@pytest.mark.parametrize('session, desktop', [('wayland', 'KDE'), ('x11', 'GNOME'), ('wayland', '')])
def test_other_sessions_are_left_to_qt(session, desktop):
    environ = {'XDG_SESSION_TYPE': session, 'XDG_CURRENT_DESKTOP': desktop}
    prefer_xwayland_on_gnome(environ)

    assert 'QT_QPA_PLATFORM' not in environ


def test_an_explicit_platform_wins():
    environ = {'XDG_SESSION_TYPE': 'wayland', 'XDG_CURRENT_DESKTOP': 'GNOME', 'QT_QPA_PLATFORM': 'wayland'}
    prefer_xwayland_on_gnome(environ)

    assert environ['QT_QPA_PLATFORM'] == 'wayland'

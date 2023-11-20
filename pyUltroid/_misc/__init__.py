# Ultroid - UserBot
# Copyright (C) 2021-2022 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

from .. import udB


CMD_HELP = {}


class _SudoManager:
    __slots__ = ("owner",)

    def __init__(self):
        self.owner = udB.get_key("OWNER_ID")

    def get_sudos(self):
        SUDOS = udB.get_key("SUDOS")
        return SUDOS or []

    def is_sudo(self, id_):
        return id_ in self.get_sudos()

    @property
    def should_allow_sudo(self):
        return udB.get_key("SUDO")

    def owner_and_sudos(self):
        return [self.owner, *self.get_sudos()]

    @property
    def fullsudos(self):
        fsudos = udB.get_key("FULLSUDO")
        if not fsudos:
            return [self.owner]
        fsudos = str(fsudos).split()
        fsudos.append(self.owner)
        return [int(u) for u in fsudos]


SUDO_M = _SudoManager()
owner_and_sudos = SUDO_M.owner_and_sudos
sudoers = SUDO_M.get_sudos
is_sudo = SUDO_M.is_sudo


# ------------------------------------------------ #


def append_or_update(load, func, name, arggs):
    if isinstance(load, list):
        return load.append(func)
    if isinstance(load, dict):
        if load.get(name):
            return load[name].append((func, arggs))
        return load.update({name: [(func, arggs)]})

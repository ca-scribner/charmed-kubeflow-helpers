from ops.charm import CharmBase

from ..exceptions import LeadershipError


def is_leader(charm: CharmBase, raise_if_not_leader: bool = True):
    if not charm.unit.is_leader():
        if raise_if_not_leader:
            raise LeadershipError()
        else:
            return False
    return True

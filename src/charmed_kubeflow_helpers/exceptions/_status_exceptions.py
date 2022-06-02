from ops.model import WaitingStatus
from ..status_handling import CharmStatusType


class ErrorWithStatus(Exception):
    """Raised when an exception occurs and the raiser has an opinion on the resultant charm status
    """
    # TODO: Should this status base class just accept an instanced Status rather than msg and status_type?
    #       The msg+type feels like a chore for the user
    def __init__(self, msg: str, status_type: CharmStatusType):
        super().__init__(str(msg))
        self.msg = str(msg)
        self.status_type = status_type

    @property
    def status(self):
        return self.status_type(self.msg)


class LeadershipError(ErrorWithStatus):
    """Raised when a charm should be in WaitingStatus because it is not the leader"""
    def __init__(
            self,
            msg: str = "Waiting for leadership",
            status_type: CharmStatusType = WaitingStatus
    ):
        super().__init__(msg, status_type)

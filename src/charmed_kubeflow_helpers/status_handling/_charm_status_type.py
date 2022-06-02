from typing import Union
from ops.model import ActiveStatus, WaitingStatus, BlockedStatus, MaintenanceStatus

CharmStatusType = Union[ActiveStatus, WaitingStatus, BlockedStatus, MaintenanceStatus]

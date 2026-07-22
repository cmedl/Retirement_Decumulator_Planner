"""Financial account models."""

from dataclasses import dataclass
from enum import StrEnum


class AccountType(StrEnum):
    RRSP = "rrsp"
    SPOUSAL_RRSP = "spousal_rrsp"
    TFSA = "tfsa"
    NON_REGISTERED = "non_registered"


ACCOUNT_TYPE_VALUES: tuple[str, ...] = tuple(member.value for member in AccountType)


@dataclass(slots=True)
class AccountBalance:
    """Single account balance for an owner."""

    owner_name: str
    account_type: AccountType
    balance: float

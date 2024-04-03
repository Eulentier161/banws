from typing import TypedDict


class Block(TypedDict):
    type: str
    account: str
    previous: str
    representative: str
    balance: str
    balance_decimal: str
    link: str
    link_as_account: str
    signature: str
    work: str
    subtype: str


class ConfirmationMessage(TypedDict):
    account: str
    amount: str
    amount_decimal: str
    hash: str
    confirmation_type: str
    block: Block


class NodeWebsocketResponse(TypedDict):
    topic: str
    time: str
    message: ConfirmationMessage
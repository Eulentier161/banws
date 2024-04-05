import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Literal, TypedDict

import httpx
import websockets
from cachetools.func import ttl_cache

from banws.dicts import NodeWebsocketResponse

logging.basicConfig(format="%(message)s", level=logging.INFO)

with open("users.json") as f:
    users: dict = {user["address"]: {**user, "user_id": str(user["user_id"])} for user in json.load(f)}


class Options(TypedDict):
    filter: Literal["all", "discord"]
    blocktypes: list[Literal["send", "receive", "change"]]
    accounts: list[str]


CONNECTIONS: dict[websockets.WebSocketServerProtocol, Options] = dict()


def early_skip(resp: NodeWebsocketResponse):
    con_vals = CONNECTIONS.values()
    if not any(resp["message"]["block"]["subtype"] in c["blocktypes"] for c in con_vals):
        return True
    if not any(resp["message"]["account"] in c["accounts"] for c in con_vals) and not any(
        c["accounts"] == [] for c in con_vals
    ):
        return True
    return False


async def source(ws_uri: str):
    async for client in websockets.connect(ws_uri):
        try:
            await client.send('{"action": "subscribe", "topic": "confirmation"}')
            async for message in client:
                if not CONNECTIONS:
                    continue

                resp = NodeWebsocketResponse(json.loads(message))

                block_account = resp["message"]["account"]
                link_as_account = resp["message"]["block"]["link_as_account"]

                if early_skip(resp):
                    continue

                # users = get_users()
                known = get_known()

                discord_block_account: dict = users.get(block_account, {})
                discord_link_as_account: dict = users.get(link_as_account, {})

                data = json.dumps(
                    {
                        "block_account": {
                            "account": block_account,
                            "discord_id": discord_block_account.get("user_id", None),
                            "discord_name": discord_block_account.get("user_last_known_name", None),
                            "alias": known.get(block_account, None),
                        },
                        "link_as_account": {
                            "account": link_as_account,
                            "discord_id": discord_link_as_account.get("user_id", None),
                            "discord_name": discord_link_as_account.get("user_last_known_name", None),
                            "alias": known.get(link_as_account, None),
                        },
                        "amount": resp["message"]["amount"],
                        "amount_decimal": resp["message"]["amount_decimal"],
                        "time": resp["time"],
                        "hash": resp["message"]["hash"],
                        "block": resp["message"]["block"],
                    }
                )

                broadcast_list = []
                for ws, opts in CONNECTIONS.items():
                    if not opts["accounts"] == []:
                        if not resp["message"]["account"] in opts["accounts"]:
                            # if the block account is not being monitored
                            # but there are specific accounts selected
                            continue
                    if not resp["message"]["block"]["subtype"] in opts["blocktypes"]:
                        # if the block type is not being monitored
                        continue
                    if opts["filter"] == "discord" and not any(
                        acc.get("user_id", False) for acc in [discord_block_account, discord_link_as_account]
                    ):
                        # if discord filter is active
                        # but neither side appears to be a discord account
                        continue
                    broadcast_list.append(ws)

                websockets.broadcast(broadcast_list, data)

        except websockets.ConnectionClosed:
            continue


async def server(ws: websockets.WebSocketServerProtocol):
    CONNECTIONS[ws] = {"filter": "discord", "blocktypes": ["send"], "accounts": []}
    try:
        async for message in ws:
            try:
                m = json.loads(message)
                assert isinstance(m, dict)

                filter = m.get("filter", None)
                assert filter in ["all", "discord"]

                blocktypes = m.get("blocktypes", [])
                assert isinstance(blocktypes, list)
                for blocktype in blocktypes:
                    assert blocktype in ["send", "receive", "change"]

                accounts = m.get("accounts", [])
                assert isinstance(accounts, list)
                for account in accounts:
                    assert isinstance(account, str)
                    assert re.match(r"^(ban)_[13]{1}[13456789abcdefghijkmnopqrstuwxyz]{59}$", account)

            except (AssertionError, json.JSONDecodeError):
                await ws.send("error")
                continue

            CONNECTIONS[ws] = {"filter": filter, "blocktypes": blocktypes, "accounts": accounts}

    finally:
        del CONNECTIONS[ws]


# @ttl_cache(maxsize=1, ttl=timedelta(minutes=30), timer=datetime.now)
# def get_users():
#     res = httpx.get("https://bananobotapi.banano.cc/users")
#     return {user["address"]: {**user, "user_id": str(user["user_id"])} for user in res.json()}


@ttl_cache(maxsize=1, ttl=timedelta(minutes=1), timer=datetime.now)
def get_known():
    res = httpx.post("https://api.spyglass.eule.wtf/banano/v1/known/accounts")
    return {e["address"]: e["alias"] for e in res.json()}


async def main():
    await asyncio.gather(websockets.serve(server, "localhost", 8765), source("ws://localhost:7074"))


if __name__ == "__main__":
    asyncio.run(main())

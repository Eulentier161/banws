import asyncio
import json
import logging
import re
from datetime import datetime, timedelta

import httpx
import websockets
from cachetools.func import ttl_cache

from banws.dicts import NodeWebsocketResponse, Options

logging.basicConfig(format="%(message)s", level=logging.INFO)


CONNECTIONS: dict[websockets.WebSocketServerProtocol, Options] = dict()


@ttl_cache(maxsize=1, ttl=timedelta(minutes=30), timer=datetime.now)
def get_users():
    res = httpx.get("https://bananobotapi.banano.cc/users")
    return {user["address"]: {**user, "user_id": str(user["user_id"])} for user in res.json()}


@ttl_cache(maxsize=1, ttl=timedelta(minutes=30), timer=datetime.now)
def get_known():
    res = httpx.post("https://api.spyglass.eule.wtf/banano/v1/known/accounts")
    return {e["address"]: e["alias"] for e in res.json()}


def early_skip(resp: NodeWebsocketResponse):
    connections_options = CONNECTIONS.values()
    blocktypes, accounts = set(), set()
    for connection_options in connections_options:
        blocktypes.update(connection_options["blocktypes"])
        accounts.update(connection_options["accounts"])
    if not resp["message"]["block"]["subtype"] in blocktypes:
        return True
    if not resp["message"]["account"] in accounts and not any(c["accounts"] == [] for c in connections_options):
        return True
    return False


async def source(ws_uri: str):
    async for client in websockets.connect(ws_uri):
        try:
            await client.send('{"action": "subscribe", "topic": "confirmation"}')
            async for message in client:
                if not CONNECTIONS:
                    continue

                node_response = NodeWebsocketResponse(json.loads(message))

                block_account = node_response["message"]["account"]
                link_as_account = node_response["message"]["block"]["link_as_account"]

                if early_skip(node_response):
                    continue

                users = get_users()
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
                        "amount": node_response["message"]["amount"],
                        "amount_decimal": node_response["message"]["amount_decimal"],
                        "time": node_response["time"],
                        "hash": node_response["message"]["hash"],
                        "block": node_response["message"]["block"],
                    }
                )

                broadcast_list = []
                for ws, opts in CONNECTIONS.items():
                    if not opts["accounts"] == []:
                        if not node_response["message"]["account"] in opts["accounts"]:
                            # if the block account is not being monitored
                            # but there are specific accounts selected
                            continue
                    if not node_response["message"]["block"]["subtype"] in opts["blocktypes"]:
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
            except (json.JSONDecodeError, AssertionError):
                await ws.send("error: malformed input")
                continue

            filter = m.get("filter", None)
            try:
                assert filter in ["all", "discord"]
            except AssertionError:
                await ws.send('error: "filter" has to be either "all" or "discord"')
                continue

            blocktypes = m.get("blocktypes", [])
            try:
                assert isinstance(blocktypes, list)
                for blocktype in blocktypes:
                    assert blocktype in ["send", "receive", "change"]
            except AssertionError:
                await ws.send('error: "blocktypes" has to be an array of "send", "receive", "change"')
                continue

            accounts = m.get("accounts", [])
            try:
                assert isinstance(accounts, list)
                for account in accounts:
                    assert isinstance(account, str)
                    assert re.match(r"^(ban)_[13]{1}[13456789abcdefghijkmnopqrstuwxyz]{59}$", account)
            except AssertionError:
                await ws.send('error: "accounts" has to be an array of valid banano public addresses')
                continue

            CONNECTIONS[ws] = {"filter": filter, "blocktypes": blocktypes, "accounts": accounts}

    finally:
        del CONNECTIONS[ws]


async def main():
    await asyncio.gather(websockets.serve(server, "localhost", 8765), source("ws://localhost:7074"))


if __name__ == "__main__":
    asyncio.run(main())

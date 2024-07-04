import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta

import httpx
import typer
import websockets
from cachetools.func import ttl_cache
from dotenv import load_dotenv
from typing_extensions import Annotated

from banws.dicts import NodeWebsocketResponse, Options

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
load_dotenv()
BANANOBOT_TOKEN = os.getenv("BANANOBOT_TOKEN")

CONNECTIONS: dict[websockets.WebSocketServerProtocol, Options] = dict()
app = typer.Typer()


@ttl_cache(maxsize=1, ttl=timedelta(minutes=30), timer=datetime.now)
def get_users():
    try:
        res = httpx.get("https://bananobotapi.banano.cc/users", headers={"Authorization": BANANOBOT_TOKEN})
        data = {user["address"]: {**user, "user_id": str(user["user_id"])} for user in res.json()}
        with open("users.json", "w+") as f:
            json.dump(data, f)
    except httpx.HTTPError:
        with open("users.json") as f:
            data = json.load(f)

    return data


@ttl_cache(maxsize=1, ttl=timedelta(minutes=30), timer=datetime.now)
def get_known():
    try:
        res = httpx.post("https://api.spyglass.eule.wtf/banano/v1/known/accounts")
        data = {e["address"]: e["alias"] for e in res.json()}
        with open("known.json", "w+") as f:
            json.dump(data, f)
    except httpx.HTTPError:
        with open("known.json") as f:
            data = json.load(f)

    return data


def early_skip(resp: NodeWebsocketResponse):
    connections_options = CONNECTIONS.values()
    blocktypes, accounts = set(), set()
    for connection_option in connections_options:
        blocktypes.update(connection_option["blocktypes"])
        accounts.update(connection_option["accounts"])
    if not resp["message"]["block"]["subtype"] in blocktypes:
        return True
    if not resp["message"]["account"] in accounts and not any(c["accounts"] == [] for c in connections_options):
        return True
    return False


async def source(ws_url: str):
    async for client in websockets.connect(ws_url):
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
                    assert re.match(r"^(ban)_[13][13456789abcdefghijkmnopqrstuwxyz]{59}$", account)
            except AssertionError:
                await ws.send('error: "accounts" has to be an array of valid banano public addresses')
                continue

            CONNECTIONS[ws] = {"filter": filter, "blocktypes": blocktypes, "accounts": accounts}

    finally:
        del CONNECTIONS[ws]


async def start_server(serve_host: str, serve_port: int, node_host: str, node_port: int):
    await asyncio.gather(
        websockets.serve(server, host=serve_host, port=serve_port),
        source(f"ws://{node_host}:{node_port}"),
    )


@app.command()
def main(
    serve_host: Annotated[
        str, typer.Option("--serve_host", "-sh", help="host for serving the new websocket", rich_help_panel="Server")
    ] = "localhost",
    serve_port: Annotated[
        int, typer.Option("--serve_port", "-sp", help="port for serving the new websocket", rich_help_panel="Server")
    ] = 8765,
    node_host: Annotated[
        str, typer.Option("--node_host", "-nh", help="host of the banano node websocket", rich_help_panel="Node")
    ] = "localhost",
    node_port: Annotated[
        int, typer.Option("--node_port", "-np", help="port of the banano node websocket", rich_help_panel="Node")
    ] = 7074,
):
    """start the banano websocket proxy"""
    assert BANANOBOT_TOKEN
    asyncio.run(start_server(serve_host, serve_port, node_host, node_port))


if __name__ == "__main__":
    app()

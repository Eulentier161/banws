import asyncio
import json
import logging
from datetime import datetime, timedelta

import httpx
import websockets
from cachetools.func import ttl_cache

from banws.dicts import NodeWebsocketResponse

logging.basicConfig(format="%(message)s", level=logging.INFO)

with open("users.json") as f:
    users: dict = {user["address"]: {**user, 'user_id': str(user['user_id'])} for user in json.load(f)}

CONNECTIONS = set()


async def source(ws_uri: str):
    async for client in websockets.connect(ws_uri):
        try:
            await client.send('{"action": "subscribe", "topic": "confirmation"}')
            async for message in client:
                if not CONNECTIONS:
                    continue
                resp = NodeWebsocketResponse(json.loads(message))
                if resp["message"]["block"]["subtype"] != "send":
                    continue
                sender = resp["message"]["block"]["account"]
                receiver = resp["message"]["block"]["link_as_account"]
                if not any(addr in users.keys() for addr in [sender, receiver]):
                    continue
                # users = get_users()
                known = get_known()
                discord_sender: dict = users.get(sender, {})
                discord_receiver: dict = users.get(receiver, {})
                data = json.dumps(
                    {
                        "sender": {
                            "address": sender,
                            "discord_id": discord_sender.get("user_id", None),
                            "discord_name": discord_sender.get(
                                "user_last_known_name", None
                            ),
                            "alias": known.get(sender, None),
                        },
                        "receiver": {
                            "address": receiver,
                            "discord_id": discord_receiver.get("user_id", None),
                            "discord_name": discord_receiver.get(
                                "user_last_known_name", None
                            ),
                            "alias": known.get(receiver, None),
                        },
                        "amount": resp["message"]["amount"],
                        "amount_decimal": resp["message"]["amount_decimal"],
                        "time": resp["time"],
                        "block": resp["message"]["block"],
                    }
                )
                websockets.broadcast(CONNECTIONS, data)
        except websockets.ConnectionClosed:
            continue


async def server(ws: websockets.WebSocketServerProtocol):
    CONNECTIONS.add(ws)
    try:
        await ws.wait_closed()
    finally:
        CONNECTIONS.remove(ws)


# @ttl_cache(maxsize=1, ttl=timedelta(minutes=30), timer=datetime.now)
# def get_users():
#     res = httpx.get("https://bananobotapi.banano.cc/users")
#     return {user["address"]: user for user in res.json()}


@ttl_cache(maxsize=1, ttl=timedelta(minutes=1), timer=datetime.now)
def get_known():
    res = httpx.post("https://api.spyglass.eule.wtf/banano/v1/known/accounts")
    return {e["address"]: e["alias"] for e in res.json()}


async def main():
    await asyncio.gather(
        websockets.serve(server, "localhost", 8765), source("ws://localhost:7074")
    )


if __name__ == "__main__":
    asyncio.run(main())

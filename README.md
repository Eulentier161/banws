# banws

small websocket proxy for a [banano](https://banano.cc) node.\
the resulting websocket server publishes confirmed blocks after trying to map each account public address to either a [known account](https://creeper.banano.cc/known-accounts) or a discord users [BananoBot++](https://github.com/bbedward/graham_discord_bot) wallet.

Per default, each client will be "subscribed" to all [send blocks](https://docs.nano.org/protocol-design/blocks/#send) with atleast 1 successfully mapped discord user on either the sending or receiving side. The websocket message to enable this state looks like:

```json
{
  "filter": "discord",
  "blocktypes": ["send"],
  "accounts": []
}
```

- `"filter"`: can be either `"discord"` or `"all"`
  - `discord` will only respond if the block has atleast one discord participant
  - `all` will respond for any block
- `"blocktypes"`: has to be an array with any combination of `"send"`, `"receive"` and `"change"`
  - `"send"`: subscribes to [send blocks](https://docs.nano.org/protocol-design/blocks/#send)
  - `"receive"`: subscribes to [receive blocks](https://docs.nano.org/protocol-design/blocks/#receive)
  - `"change"`: subscribes to [change blocks](https://docs.nano.org/protocol-design/blocks/#change-rep)
- `"accounts"`: has to be a list of valid [account public addresses](https://docs.nano.org/integration-guides/the-basics/#account-public-address) or empty
  - only blocks from the addresses inside the array will be reported back
  - leaving this array empty acts as if all addresses would be selected

> [!IMPORTANT]
> receive blocks do not include the senders public key in their "link" field, but the pairing blocks hash. this means you will never get the senders public address, and discord information from just this block alone.\
> https://docs.nano.org/integration-guides/the-basics/#block-format

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
  - `discord` subscribes to blocks that have atleast one discord participant
  - `all` subscribes to all participants
- `"blocktypes"`: has to be an array with any combination of `"send"`, `"receive"` and `"change"`
  - `"send"`: subscribes to [send blocks](https://docs.nano.org/protocol-design/blocks/#send)
  - `"receive"`: subscribes to [receive blocks](https://docs.nano.org/protocol-design/blocks/#receive)
  - `"change"`: subscribes to [change blocks](https://docs.nano.org/protocol-design/blocks/#change-rep)
- `"accounts"`: has to be a list of valid [account public addresses](https://docs.nano.org/integration-guides/the-basics/#account-public-address) or empty
  - subscribes to those specific accounts
  - leaving the array empty subscribes to all accounts

here is an example to subscribe to everything that happens on the account chains of [JungleTV](https://creeper.banano.cc/account/ban_1jung1eb3uomk1gsx7w6w7toqrikxm5pgn5wbsg5fpy96ckpdf6wmiuuzpca), [JungleTV Prize Faucet](https://creeper.banano.cc/account/ban_1jtprixunfus5mozkzj5gtfm79b54p3pwnje8snh9ugu998cfk13qceepwn5), [JungleTV Rain](https://creeper.banano.cc/account/ban_1rainrjfauss66rbormm3td5gucnnza41w78qepdmzy15dprgb6qrp6x516h) or [JungleTV Skip](https://creeper.banano.cc/account/ban_1skiph85moxba9eqzpxejazxcaqfddq8xwsdgjn7yy4t1ano81oncieo6bib):

```json
{
  "filter": "all",
  "blocktypes": ["send", "receive", "change"],
  "accounts": [
    "ban_1jung1eb3uomk1gsx7w6w7toqrikxm5pgn5wbsg5fpy96ckpdf6wmiuuzpca",
    "ban_1jtprixunfus5mozkzj5gtfm79b54p3pwnje8snh9ugu998cfk13qceepwn5",
    "ban_1rainrjfauss66rbormm3td5gucnnza41w78qepdmzy15dprgb6qrp6x516h",
    "ban_1skiph85moxba9eqzpxejazxcaqfddq8xwsdgjn7yy4t1ano81oncieo6bib"
  ]
}
```

> [!IMPORTANT]
> receive blocks do not include the senders public key in their "link" field, but the pairing blocks hash. this means you will never get the senders public address, and discord information from just this block alone.\
> https://docs.nano.org/integration-guides/the-basics/#block-format

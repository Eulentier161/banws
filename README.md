# banws

small websocket proxy for a [banano](https://banano.cc) node.\
the resulting websocket server publishes confirmed blocks after trying to map each account public address to either a [known account](https://creeper.banano.cc/known-accounts) or a discord users [BananoBot++](https://github.com/bbedward/graham_discord_bot) wallet.

view a demo at https://ws.spyglass.eule.wtf/demo

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

here is an example response

```json
{
  "block_account": {
    "account": "ban_3d8bpoetso3xjq7q5gkhkbzx9f9whua7thx3j8jqmuci1npg8ynmukc3j7iw",
    "discord_id": "958611742118785125",
    "discord_name": "eulentier",
    "alias": null
  },
  "link_as_account": {
    "account": "ban_1eu1enkjdd5wgf8sz7tq5xxbo5nqro4k4yz1o4tmk8bs5ejhu9f3yazmreo3",
    "discord_id": null,
    "discord_name": null,
    "alias": null
  },
  "amount": "1900000000000000000000000000000",
  "amount_decimal": "19.0",
  "time": "1712919572742",
  "hash": "605406BEFA629404F87A14103889A8809EB6E10A790FE79BBFF04DCE9E61BF4F",
  "block": {
    "type": "state",
    "account": "ban_3d8bpoetso3xjq7q5gkhkbzx9f9whua7thx3j8jqmuci1npg8ynmukc3j7iw",
    "previous": "D7D33ABD51B994AB9A251006F544B81A519532713EAAAE5C6946DDC416EDB8E7",
    "representative": "ban_1tipbotgges3ss8pso6xf76gsyqnb69uwcxcyhouym67z7ofefy1jz7kepoy",
    "balance": "190719999999999998299178992140287",
    "balance_decimal": "1907.19999999999998299178992140287",
    "link": "3360652515AC7C734D9F97571F7A9A8E97C545217BE0A8B53919391B22FD9DA1",
    "link_as_account": "ban_1eu1enkjdd5wgf8sz7tq5xxbo5nqro4k4yz1o4tmk8bs5ejhu9f3yazmreo3",
    "signature": "F76F5F20DA0C536B5A87076EA3E1C6796AF0200AAAF8C2CD01409A3D09B824B422566E7E00E9A6FAC2A885B5FF57D08462C2DA9668176BFB9DF6F5A360B87A0B",
    "work": "000000000043ef13",
    "subtype": "send"
  }
}
```

> [!IMPORTANT]
> receive blocks do not include the senders public key in their "link" field, but the pairing blocks hash. this means you will never get the senders public address, and discord information from just this block alone.\
> https://docs.nano.org/integration-guides/the-basics/#block-format

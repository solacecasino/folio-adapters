# Folio Link

Folio Link lets you and other people edit one document together, live. It's an
optional adapter: Folio doesn't include it, and once installed it does nothing
until you choose **Share This Document** or **Join from Clipboard**. It has no
accounts and no servers of our own. Each copy of Folio connects straight to the
others over an encrypted link.

## Installing

Download the `folio-link` zip for your computer (macOS, Windows or Linux)
from [Releases](../../../releases), then in Folio choose **Folio → Adapters…**,
**Add Adapter…**, and pick the zip. Everyone you edit with needs it too, on
any of the three platforms. To build it yourself, run `scripts/build.py`.

The first time it runs, Folio asks you to allow it to read and edit documents
and to go online.

## Sharing

1. With the document open, choose **Folio → Adapters…** and click **Share This Document** under Folio Link.
2. Folio Link copies an invite link (`folio://join#…`) to your clipboard.
   Send it to the people you want to edit with, over any channel you trust.
3. When someone uses the invite, Folio asks whether to let them in. Nobody gets
   the document until you say yes.

The status line shows **● Sharing · N people**. The **People** panel lists
everyone and has links to copy the invite again or stop.
**Stop Sharing** disconnects everyone. Your document stays as it is.

## Joining

1. Click the invite link you were sent. Folio opens and joins. (You need
   Folio 1.0.1 or later and Folio Link 0.3 or later.)
2. Or copy the invite, open a window in Folio (a new, empty one is best)
   and choose **Join from Clipboard** in the Adapters window.
3. Once the host lets you in, the window shows the shared document. If the
   window already had text, Folio asks first, because joining replaces it.

The status line shows **● Joined Name's document**. Other people's carets and
selections appear in their colors. **Stop Sharing** leaves the session; you
keep a copy of the document as it was when you left.

While a session is on, **Undo** and **Redo** apply only to your own edits.
They never take back what someone else typed.

## What is encrypted

Everything. Folio Link uses [iroh](https://iroh.computer): every connection
is QUIC with TLS 1.3, and each end is identified by its public key, so the
link is encrypted from your computer to theirs. The invite carries:

- the host's public key and network addresses, so guests reach the right
  machine and nobody can impersonate it;
- a random document id and a random 128-bit secret, which a guest must present
  before the host is even asked to let them in.

Treat an invite like a key to the document while it's being shared. Once you
stop sharing, the invite stops working. Your identity key is created on first
use and kept in `folio-link/key` in Folio's config folder
(`~/Library/Application Support/Folio` on macOS, `%APPDATA%\Folio` on
Windows, `~/.config/folio` on Linux).

## Relays

Two computers often can't reach each other directly: home routers and office
firewalls get in the way. iroh first tries a direct connection. If that isn't
possible right away, traffic goes through a **relay**: a server that forwards
bytes between the two ends. By default these are the public relays run by
n0, the company that makes iroh.

- A relay only ever sees **encrypted bytes**. It can't read or change the
  document. It does see that two addresses are talking, and roughly how much.
- Once a direct path is found, iroh moves the connection to it and stops
  using the relay.
- With the default setting, your computer's current addresses are also published
  under its public key in n0's DNS, so guests can find it as your network
  changes. Turning relays off turns this off too.
- Nothing connects to a relay, or anywhere else, until you choose Share or Join.

To choose, create `folio-link/settings.toml` in Folio's config folder:

```toml
# "default" uses n0's public relays.
# "none" never uses a relay or address lookup: only direct connections work,
# which usually means the same network (home, office, or a VPN).
# Or the URL of a relay you run yourself (see iroh-relay).
relay = "none"

# Optional: the name others see. Defaults to your account name.
name = "Ana"
```

Everyone in a session should use the same kind of setting. Someone using
`"none"` can't reach a host who is only reachable through a relay.

## Limits

- **The host must stay online.** The host passes edits between guests. When
  the host stops or quits, the session ends. Each person keeps the document
  as it was.
- **No offline catch-up.** Changes made while disconnected aren't merged on
  the next join. Joining always starts from the host's current document.
- **One document per session.** Each session shares one window.
- **Formatting is what Folio has**: paragraph styles, bold, italic and
  underline. If two people change the same text at the same moment, both
  edits are kept and merged character by character. The result can need a
  quick tidy, but nobody's typing is lost.
- **Very large documents** (over about 50,000 characters) are compared line by
  line rather than character by character. That's still correct, just coarser.
- **Undo** covers your edits from the start of the session. A keystroke typed
  at the exact moment someone else's edit arrives may not be undoable.
- **Guests are trusted once admitted.** Anyone you let in can change or delete
  anything in the document.

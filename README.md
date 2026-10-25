# Folio adapters

Optional add-ons for [Folio](https://github.com/solacecasino/folio), the
document editor that ships bare. Folio has nothing extra built in. You add
only the adapters you want.

## 👉 [Browse the catalog](CATALOG.md)

Every adapter, including other people's, with a direct download for macOS,
Windows and Linux. To install one, download the zip for your computer and
**drop it on the Folio window**. Folio shows what the adapter can do and
asks before it first runs.

## Make one and share it

1. **[Use the template](https://github.com/solacecasino/folio-adapter-template/generate):**
   a working Python adapter in about 15 lines, using
   [`folio.py`](sdk/python/folio.py), a one-file helper library.
2. **Push a version tag.** Its workflow publishes your release, with zips for
   every platform if it's compiled.
3. **[List it](https://github.com/solacecasino/folio-adapters/issues/new?template=list-my-adapter.yml):**
   type your repo's name into the form. A check downloads your release and
   opens the listing for you. Later releases show up in the catalog by
   themselves.

Prefer a pull request? Add `catalog/<name>.toml` with `repo = "you/name"`;
see [catalog/README.md](catalog/README.md).

## Folio's own adapters

This repo also holds the adapters made with Folio:

| Adapter | Adds | Built with |
|---|---|---|
| [pdf-export](pdf-export) | **File → Export as PDF**. Print-perfect: matches the page line for line, with your theme's fonts embedded and searchable text. | Rust, [krilla](https://github.com/LaurenzV/krilla) |
| [folio-link](folio-link) | **Live co-editing** with people you invite, over encrypted peer-to-peer links. No accounts, no servers of ours. [How it works](docs/folio-link.md) | Rust, [iroh](https://iroh.computer), [Loro](https://loro.dev) |
| [rich-content](rich-content) | **Bulleted and numbered lists, and links** (Format menu; Cmd+Shift+8, Cmd+Shift+7, Cmd+K). Folio draws and prints them on its own, so documents look right without it; this adds the commands to make them. Needs Folio 1.0.2. | Rust |
| [writing-tools](writing-tools) | A word-count goal panel, today's date, document stats. | Python |

Compiled adapters come as one zip per platform (`-macos-arm64`,
`-windows-x64`, `-linux-x64`). If you pick the wrong one, Folio says which
to get. Python adapters need Python 3: macOS installs it with its developer
tools, most Linux systems have it, and on Windows get it from
[python.org](https://www.python.org/downloads/).

## The protocol

An adapter is a folder with an `adapter.toml` and a program in any language.
Folio starts the program when it's needed and exchanges one JSON message per
line with it over stdin and stdout. The protocol is documented in Folio's
[docs/adapters.md](https://github.com/solacecasino/folio/blob/main/docs/adapters.md).
[writing-tools](writing-tools) is the simplest example.

## Build

```sh
python3 scripts/build.py   # builds the Rust adapters for this computer and makes one zip per adapter in dist/
```

You need [Rust](https://rustup.rs/) and Python 3. Releases are built on all
three platforms by [GitHub Actions](.github/workflows/release.yml) when a
version tag is pushed. Each Rust adapter is its own crate, so
`cd pdf-export && cargo test` works too.

## License

[MIT](LICENSE)

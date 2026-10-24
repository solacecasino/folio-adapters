# Folio adapters

Optional add-ons for [Folio](https://github.com/solacecasino/folio), the
document editor that ships bare. Folio has nothing extra built in. You add
only the adapters you want.

| Adapter | Adds | Built with |
|---|---|---|
| [pdf-export](pdf-export) | **File → Export as PDF** (Cmd+E, or Ctrl+E on Windows and Linux). Print-perfect: matches the page line for line, with your theme's fonts embedded and searchable text. | Rust, [krilla](https://github.com/LaurenzV/krilla) |
| [folio-link](folio-link) | **Live co-editing** with people you invite, over encrypted peer-to-peer links. No accounts, no servers of ours. [How it works](docs/folio-link.md) | Rust, [iroh](https://iroh.computer), [Loro](https://loro.dev) |
| [writing-tools](writing-tools) | A word-count goal panel, today's date, document stats. About 100 lines, a good starting point for your own. | Python |

## Install

1. Download an adapter's zip from [Releases](../../releases).
2. In Folio, choose **Folio → Adapters…** (Cmd+Shift+A, or Ctrl+Shift+A), then **Add Adapter…**, and pick the zip.
3. The first time the adapter runs, Folio shows what it asks for (such as reading your document or going online), and you decide.

You can remove an adapter at any time from the same window.

Folio runs on macOS, Windows and Linux. The compiled adapters come in one zip
per platform; pick the one for your computer:

| Zip ends in | For |
|---|---|
| `-macos-arm64.zip` | Macs with Apple Silicon |
| `-windows-x64.zip` | 64-bit Windows |
| `-linux-x64.zip` | 64-bit Linux |

`writing-tools` is one zip for every platform. It needs Python 3: macOS
installs it with its developer tools, most Linux systems have it, and on
Windows install it from [python.org](https://www.python.org/downloads/).

## Write your own

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

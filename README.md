# Folio adapters

Optional add-ons for [Folio](https://github.com/solacecasino/folio), the
document editor that ships bare. Folio has nothing extra built in. You add
only the adapters you want.

| Adapter | Adds | Built with |
|---|---|---|
| [pdf-export](pdf-export) | **File → Export as PDF** (Cmd+E). Print-perfect: matches the page line for line, with your theme's fonts embedded and searchable text. | Rust, [krilla](https://github.com/LaurenzV/krilla) |
| [folio-link](folio-link) | **Live co-editing** with people you invite, over encrypted peer-to-peer links. No accounts, no servers of ours. [How it works](docs/folio-link.md) | Rust, [iroh](https://iroh.computer), [Loro](https://loro.dev) |
| [writing-tools](writing-tools) | A word-count goal panel, today's date, document stats. About 100 lines, a good starting point for your own. | Python |

## Install

1. Download an adapter's zip from [Releases](../../releases).
2. In Folio, choose **Folio → Adapters…** (Cmd+Shift+A), then **Add Adapter…**, and pick the zip.
3. The first time the adapter runs, Folio shows what it asks for (such as reading your document or going online), and you decide.

You can remove an adapter at any time from the same window.

The compiled adapters (`-macos-arm64`) need a Mac with Apple Silicon.
`writing-tools` needs `python3`, which macOS installs with its developer tools.

## Write your own

An adapter is a folder with an `adapter.toml` and a program in any language.
Folio starts the program when it's needed and exchanges one JSON message per
line with it over stdin and stdout. The protocol is documented in Folio's
[docs/adapters.md](https://github.com/solacecasino/folio/blob/main/docs/adapters.md).
[writing-tools](writing-tools) is the simplest example.

## Build

```sh
scripts/build.sh   # builds the Rust adapters and makes one zip per adapter in dist/
```

You need [Rust](https://rustup.rs/). Each Rust adapter is its own crate, so
`cd pdf-export && cargo test` works too.

## License

[MIT](LICENSE)

# The adapter catalog

Each file here lists one adapter in [CATALOG.md](../CATALOG.md). To add yours,
add a file named after it, such as `word-goals.toml`:

```toml
repo = "you/word-goals"    # a public GitHub repo whose latest release has the adapter's zips
category = "Writing"       # optional: Writing, Export, Collaboration, Look, Tools, ...
```

That's all. Everything else (name, description, author, version, permissions
and the download links) is read from your latest release, so the catalog
stays current every time you release. A check runs on your pull request to
make sure the zips install.

Optional keys:

```toml
adapter = "word-goals"     # the zip name prefix, if the release holds several adapters
tags = ["goals", "stats"]  # extra words people might search for
```

Release zips are named `<adapter>-<version>-<platform>.zip`, with platform
one of `macos-arm64`, `windows-x64` or `linux-x64`, or `<adapter>-<version>.zip`
for script adapters that run everywhere.
[folio-adapter-template](https://github.com/solacecasino/folio-adapter-template)
makes them for you when you push a version tag.

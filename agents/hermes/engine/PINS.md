# Pinned versions

What this agent last ran on. These are the versions it was verified against, not
requirements; newer releases may work. Bump deliberately and re-verify.

| Tool | Version it ran on | Notes |
|---|---|---|
| Hermes Agent | v0.19.1 | Default model `claude-sonnet-5` on the `default` profile. |
| gogcli (`gog`) | v0.31.0 | linux_amd64 release, checksum-verified against the release `checksums.txt`, installed at `~/.local/bin/gog`. Repo: github.com/openclaw/gogcli. |
| gbrain | 0.42.x | Postgres backend, used as an MCP server. |

Do not let anything auto-update gogcli: the binary holds a Google OAuth grant, so a
new version is a new thing to trust. Verify the checksum, then re-check both token
buckets (read-only and write) still work.

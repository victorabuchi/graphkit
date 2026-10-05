# graphkit

A small command-line tool for your GitHub contribution graph. It does two things:

- **`art`**: draws text (A–Z, 0–9) in the contribution grid, like a pixel-art banner.
- **`mirror`**: replays the *dates* of real commits from other local repos, so work done
  elsewhere (a private repo, an old machine, another host) shows up on your graph.

Pure Python standard library. Needs `git` and, optionally, the [GitHub CLI](https://cli.github.com) (`gh`).

> **Be honest about what this is.** Art commits are synthetic: they are not real work. graphkit
> tags them `[graphkit art]`, writes a README into the repo saying so, and always works in its
> own dedicated repo. Don't use it to misrepresent your work to employers, clients or anyone
> else. `mirror` is meant for activity that really happened.

## Install

```bash
git clone https://github.com/<you>/graphkit && cd graphkit
pip install .          # gives you the `graphkit` command
# or just run:  python3 graphkit.py ...
```

Log in once with `gh auth login` (graphkit uses it to find your account and to create the repo).

## Usage

### Graph art

Preview first. This writes nothing:

```bash
graphkit art "HELLO" --preview
```

```
█···█·█████·█·····█······███··
█···█·█·····█·····█·····█···█·
█···█·█·····█·····█·····█···█·
█████·████··█·····█·····█···█·
█···█·█·····█·····█·····█···█·
█···█·█·····█·····█·····█···█·
█···█·█████·█████·█████··███··
```

Then build it and publish:

```bash
graphkit art "HELLO" --out ./hello --density 30 --push contribution-art
```

| Option | Meaning |
| --- | --- |
| `--start YYYY-MM-DD` | A **Sunday**: the left-most column. Default: 51 weeks ago, so the art fits the last year. |
| `--density N` | Commits per lit day. GitHub shades squares relative to your busiest day, so higher = darker. |
| `--out DIR` | New directory for the dedicated repo (must not exist or be empty). |
| `--push REPO` | Create a public GitHub repo with this name and push (asks first; `--yes` skips). |
| `--email` | Commit email. Default: your GitHub no-reply address. |
| `--preview` | Show what would happen and write nothing. |

Text can be up to 52 columns wide: about 8 characters.

### Mirror real activity

```bash
graphkit mirror --source ~/work/api --source ~/old/project \
                --author me@work.com --out ./mirror --preview
```

Drop `--preview` to build it. For every matching commit in the source repos, graphkit makes one
commit in the new repo at the **same timestamp**. Only the timestamp is copied. No commit
messages, file names, paths or code leave the source repos, which makes it safe for private work.
`--author` (repeatable) limits it to commits by those emails.

## How it works

GitHub's graph counts commits by author date, so a commit's date can be set independently of when
it is pushed. graphkit:

1. Builds a list of `(timestamp, message)` pairs: lit grid cells for `art`, real commit dates for `mirror`.
2. Writes them in one pass with `git fast-import`, which creates thousands of commits per second.
3. Optionally creates the repo with `gh` and pushes.

The grid is 7 rows (Sunday to Saturday) by up to 53 week columns, so cell `(col, row)` is the date
`start + 7*col + row` days.

## Getting the dots to show

GitHub only counts a commit if all of these hold:

- The commit **email is linked and verified on your account**. The default, your
  `ID+username@users.noreply.github.com` address, always works. Using any other address that
  belongs to someone else credits *their* profile.
- It is on the repo's **default branch** (graphkit uses `main`).
- The repo is not a fork. Private repos count only if *Show private contributions* is on in your
  profile settings.
- Big pushes can take a while to appear. Give it a few minutes, sometimes longer.

## Undo

Everything lives in one dedicated repo. Delete it (Settings → Danger Zone, or
`gh repo delete NAME` after `gh auth refresh -s delete_repo`) and the dots disappear.

## Safety rails

- Never writes into an existing project; refuses non-empty output directories.
- Pushing is opt-in and asks for confirmation.
- `--preview` on both commands.

## License

MIT

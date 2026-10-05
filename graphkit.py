#!/usr/bin/env python3
"""graphkit - GitHub contribution graph helper (stdlib only).

  art     draw text in the contribution grid (graph art)
  mirror  replay the *dates* of real commits from other local repos

Examples:
  graphkit art "HELLO" --preview
  graphkit art "HELLO" --out ./hello --density 30 --push contribution-art
  graphkit mirror --source ~/work/api --author me@work.com --out ./mirror --preview

Everything is written to a NEW dedicated repo, never into existing projects.
Art commits are tagged "[graphkit art]" and mirror commits "[graphkit mirror]",
so the repo is honest about being synthetic. Undo = delete that repo.
"""
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path

G = {
 "A": [".###.","#...#","#...#","#####","#...#","#...#","#...#"],
 "B": ["####.","#...#","#...#","####.","#...#","#...#","####."],
 "C": [".####","#....","#....","#....","#....","#....",".####"],
 "D": ["####.","#...#","#...#","#...#","#...#","#...#","####."],
 "E": ["#####","#....","#....","####.","#....","#....","#####"],
 "F": ["#####","#....","#....","####.","#....","#....","#...."],
 "G": [".####","#....","#....","#..##","#...#","#...#",".###."],
 "H": ["#...#","#...#","#...#","#####","#...#","#...#","#...#"],
 "I": ["#####","..#..","..#..","..#..","..#..","..#..","#####"],
 "J": ["..###","...#.","...#.","...#.","...#.","#..#.",".##.."],
 "K": ["#...#","#..#.","#.#..","##...","#.#..","#..#.","#...#"],
 "L": ["#....","#....","#....","#....","#....","#....","#####"],
 "M": ["#...#","##.##","#.#.#","#.#.#","#...#","#...#","#...#"],
 "N": ["#...#","##..#","#.#.#","#..##","#...#","#...#","#...#"],
 "O": [".###.","#...#","#...#","#...#","#...#","#...#",".###."],
 "P": ["####.","#...#","#...#","####.","#....","#....","#...."],
 "Q": [".###.","#...#","#...#","#...#","#.#.#","#..#.",".##.#"],
 "R": ["####.","#...#","#...#","####.","#.#..","#..#.","#...#"],
 "S": [".####","#....","#....",".###.","....#","....#","####."],
 "T": ["#####","..#..","..#..","..#..","..#..","..#..","..#.."],
 "U": ["#...#","#...#","#...#","#...#","#...#","#...#",".###."],
 "V": ["#...#","#...#","#...#","#...#","#...#",".#.#.","..#.."],
 "W": ["#...#","#...#","#...#","#.#.#","#.#.#","##.##","#...#"],
 "X": ["#...#","#...#",".#.#.","..#..",".#.#.","#...#","#...#"],
 "Y": ["#...#","#...#",".#.#.","..#..","..#..","..#..","..#.."],
 "Z": ["#####","....#","...#.","..#..",".#...","#....","#####"],
 "0": [".###.","#...#","#..##","#.#.#","##..#","#...#",".###."],
 "1": ["..#..",".##..","..#..","..#..","..#..","..#..",".###."],
 "2": [".###.","#...#","....#","...#.","..#..",".#...","#####"],
 "3": ["####.","....#","....#",".###.","....#","....#","####."],
 "4": ["#...#","#...#","#...#","#####","....#","....#","....#"],
 "5": ["#####","#....","####.","....#","....#","#...#",".###."],
 "6": [".###.","#....","#....","####.","#...#","#...#",".###."],
 "7": ["#####","....#","...#.","..#..",".#...",".#...",".#..."],
 "8": [".###.","#...#","#...#",".###.","#...#","#...#",".###."],
 "9": [".###.","#...#","#...#",".####","....#","....#",".###."],
 " ": ["...","...","...","...","...","...","..."],
}


def run(*cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True).stdout


def default_identity(email=None):
    """Return (name, email). Prefers the GitHub no-reply address, which always
    credits the commits to the right account."""
    if email:
        return email.split("@")[0], email
    try:
        u = json.loads(run("gh", "api", "user"))
        return u.get("name") or u["login"], f"{u['id']}+{u['login']}@users.noreply.github.com"
    except Exception:
        sys.exit("Could not read your GitHub account via `gh`. Pass --email instead.")


def render(text):
    """Return a 7-row list of strings ('#'/'.') for the text."""
    rows = [""] * 7
    for ch in text.upper():
        if ch not in G:
            sys.exit(f"Unsupported character {ch!r} (use A-Z, 0-9, space)")
        for r in range(7):
            rows[r] += G[ch][r] + "."
    return rows


def last_sunday(today):
    return today - dt.timedelta(days=(today.weekday() + 1) % 7)


def art_cells(text, start):
    rows = render(text)
    width = len(rows[0])
    if width > 52:
        sys.exit(f"Text is {width} columns wide; the graph fits 52. Shorten it.")
    cells = []
    for c in range(width):
        for r in range(7):
            if rows[r][c] == "#":
                cells.append(start + dt.timedelta(days=7 * c + r))
    return rows, cells


def preview(rows):
    print("\n".join("".join("█" if x == "#" else "·" for x in row) for row in rows))


def build_repo(out, commits, tag, name, email):
    """commits: list of (unix_ts, message). One fast-import pass, ~thousands/sec."""
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} already exists and is not empty. Pick a new --out.")
    out.mkdir(parents=True, exist_ok=True)
    run("git", "init", "-q", "-b", "main", cwd=out)
    commits = sorted(commits)
    parts = []
    for i, (ts, msg) in enumerate(commits, 1):
        m = f"{msg} [{tag}]\n".encode()
        body = f"{ts}\n".encode()
        hdr = f"commit refs/heads/main\nmark :{i}\nauthor {name} <{email}> {ts} +0000\ncommitter {name} <{email}> {ts} +0000\n"
        parts.append(hdr.encode() + f"data {len(m)}\n".encode() + m)
        if i > 1:
            parts.append(f"from :{i-1}\n".encode())
        parts.append(b"M 100644 inline log.txt\n" + f"data {len(body)}\n".encode() + body + b"\n")
    subprocess.run(["git", "fast-import", "--quiet"], cwd=out, input=b"".join(parts), check=True)
    run("git", "reset", "-q", "--hard", cwd=out)
    (out / "README.md").write_text(
        f"# Synthetic activity ({tag})\n\nGenerated by graphkit. These commits are not real work.\n")
    run("git", "add", "README.md", cwd=out)
    run("git", "-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "-q",
        "-m", "Add README", cwd=out)
    print(f"Created {len(commits)} commits in {out}")


def maybe_push(args, out):
    if not args.push:
        print(f"Not pushed. To publish: cd {out} && gh repo create {args.push or 'NAME'} --public --source=. --push")
        return
    if not args.yes and input(f"Create public repo '{args.push}' and push? [y/N] ").lower() != "y":
        print("Skipped push.")
        return
    run("gh", "repo", "create", args.push, "--public", "--source=.", "--remote=origin", "--push", cwd=out)
    print(f"Pushed. Undo by deleting the repo '{args.push}'.")


def cmd_art(a):
    start = dt.date.fromisoformat(a.start) if a.start else last_sunday(dt.date.today()) - dt.timedelta(weeks=51)
    if start.weekday() != 6:
        sys.exit("--start must be a Sunday (it is the top-left cell of the graph).")
    rows, cells = art_cells(a.text, start)
    preview(rows)
    if a.preview:
        return
    name, email = default_identity(a.email)
    commits = [(int(dt.datetime(d.year, d.month, d.day, 12, 0, k % 60, tzinfo=dt.timezone.utc).timestamp()) + k, f"art {d}")
               for d in cells for k in range(a.density)]
    build_repo(a.out, commits, "graphkit art", name, email)
    maybe_push(a, a.out)


def cmd_mirror(a):
    name, email = default_identity(a.email)
    commits = []
    for src in a.source:
        log = run("git", "-C", src, "log", "--all", "--format=%at\t%ae")
        for line in log.splitlines():
            ts, ae = line.split("\t")
            if a.author and ae not in a.author:
                continue
            # Only the timestamp is copied: no messages, files or paths leak.
            commits.append((int(ts), "mirror: activity"))
    if not commits:
        sys.exit("No matching commits found.")
    print(f"{len(commits)} real commit dates from {len(a.source)} repo(s)")
    if a.preview:
        return
    build_repo(a.out, commits, "graphkit mirror", name, email)
    maybe_push(a, a.out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(s):
        s.add_argument("--out", default="graphkit-repo", help="new directory for the dedicated repo")
        s.add_argument("--email", help="commit email (default: your GitHub no-reply address via gh)")
        s.add_argument("--push", metavar="REPO", help="create this public repo on GitHub and push")
        s.add_argument("--yes", action="store_true", help="skip the push confirmation")
        s.add_argument("--preview", action="store_true", help="show what would happen; write nothing")

    a = sub.add_parser("art", help="draw text in the graph")
    a.add_argument("text")
    a.add_argument("--start", help="Sunday (YYYY-MM-DD) of the left-most column; default: 51 weeks ago")
    a.add_argument("--density", type=int, default=30, help="commits per lit day (higher = darker)")
    common(a)
    a.set_defaults(fn=cmd_art)

    m = sub.add_parser("mirror", help="replay dates of real commits from local repos")
    m.add_argument("--source", action="append", required=True, help="path to a local git repo (repeatable)")
    m.add_argument("--author", action="append", help="only commits by this email (repeatable)")
    common(m)
    m.set_defaults(fn=cmd_mirror)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

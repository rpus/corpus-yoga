# Forge capture - the command behind each file

The recipe `yoga forge capture` (#497) enacts. Every command runs from the
repository root. `$STAMP` is `date -u +%Y-%m-%dT%H%M%SZ`, taken once at the
start; `$DIR` is `data/input/github/forge/gh-CLI/$STAMP/`. The directory's
name is the capture's one time label - no file inside restates it.

## One command per file

| file | command |
| --- | --- |
| `issues_and_pulls.json` | `gh api --paginate 'repos/rpus/yoga/issues?state=all&per_page=100'` |
| `pulls.json` | `gh api --paginate 'repos/rpus/yoga/pulls?state=all&per_page=100'` |
| `issue_comments.json` | `gh api --paginate 'repos/rpus/yoga/issues/comments?per_page=100'` |
| `review_comments.json` | `gh api --paginate 'repos/rpus/yoga/pulls/comments?per_page=100'` |
| `labels.json` | `gh api --paginate 'repos/rpus/yoga/labels?per_page=100'` |
| `repository.json` | `gh api 'repos/rpus/yoga'` |
| `reviews_by_pull.json` | for each number `n` in `pulls.json`: `gh api repos/rpus/yoga/pulls/<n>/reviews` - stored as `{"<n>": [reviews]}` |
| `blocked_by_by_issue.json` | for each issue `n` in `issues_and_pulls.json` without a `pull_request` key: `gh api repos/rpus/yoga/issues/<n>/dependencies/blocked_by` - stored as `{"<n>": [blocking issues]}`; a non-array reply (the endpoint's refusal on an issue with no edges) is stored as `[]` |
| `manifest.json` | not fetched - written from the files above: `room` (machine-name.txt), `session`, `main_at_capture` = `git rev-parse --short origin/main`, and `counts` (array lengths of the five paginated files; issues = entries of `issues_and_pulls.json` lacking `pull_request`; pulls; reviews and blocked_by_edges summed over their maps) |

Each `gh api` stdout is redirected straight to `$DIR/<file>`.

## Post-processing applied to the five paginated files

`gh api --paginate` concatenates one JSON array per page (`[...][...]`). Each
file is re-read, the page boundaries joined (`][` replaced by `,`), parsed,
and rewritten as a single array with `json.dump(..., indent=1)`. The
per-PR and per-issue maps and the manifest are written with the same
`indent=1`. No record is filtered, renamed, or reordered.

## Known limits

- The GitHub REST `issues` list includes pull requests (hence the file's
  name); `pulls.json` is the same objects under the pull-request resource,
  with merge state and head/base shas.
- Only `blocked_by` edges are captured, the repository's one issue
  relation; `blocking` (the inverse) derives from it.
- Not captured: commit status checks, the issue/PR event timelines,
  reactions, and the dependency graph beyond `blocked_by`.
- As written the recipe is not content-keyed: a second enactment deposits a
  second stamped directory whether or not the forge changed. #497's should
  is that an unchanged forge deposits nothing and says so.

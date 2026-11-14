#!/bin/sh
# Prefix the commit message with [#N], where N is the leading number of the branch name.
msg_file="$1"

# Leave merge and squash messages alone
case "$PRE_COMMIT_COMMIT_MSG_SOURCE" in merge|squash) exit 0 ;; esac

branch=$(git symbolic-ref --short HEAD 2>/dev/null) || exit 0   # detached HEAD / rebase
issue=$(printf '%s' "$branch" | sed -n 's/^\([0-9][0-9]*\)-.*/\1/p')
[ -n "$issue" ] || exit 0                                        # branch has no issue number

# Skip if already prefixed (amend, reworded commit)
grep -q "^\[#$issue\]" "$msg_file" && exit 0

sed -i.bak "1s/^/[#$issue] /" "$msg_file" && rm -f "$msg_file.bak"

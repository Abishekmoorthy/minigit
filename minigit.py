#!/usr/bin/env python3
"""
minigit.py - a tiny git-like VCS using Merkle trees and SHA-256.
Features:
- init, add, commit, log, checkout, status
- content-addressed storage: blob, tree, commit objects in .minigit/objects
- verify: tamper detection by recomputing hashes
- revoke: mark commit as revoked (prevents checkout)
This is a learning / toy implementation — not a replacement for git.
"""

import os
import sys
import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Tuple, List, Optional

REPO_DIR = ".minigit"
OBJECTS_DIR = os.path.join(REPO_DIR, "objects")
HEAD_FILE = os.path.join(REPO_DIR, "HEAD")
INDEX_FILE = os.path.join(REPO_DIR, "index")     # staging area (list of tracked files)
REFS_FILE = os.path.join(REPO_DIR, "refs.json") # stores HEAD, branches if added
REVOKE_FILE = os.path.join(REPO_DIR, "revoked.json")  # list of revoked commit hashes

# ---------- Helpers ----------
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def ensure_repo():
    if not os.path.isdir(REPO_DIR):
        print("Not a minigit repository (run 'minigit.py init').")
        sys.exit(1)

def path_in_repo(path: str) -> bool:
    # ensure we don't add files inside .minigit
    ab = os.path.abspath(path)
    repo_ab = os.path.abspath(REPO_DIR)
    return not ab.startswith(repo_ab)

def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

def write_object(data: bytes) -> str:
    """Write an object blob and return its sha256 hash (hex)."""
    h = sha256_bytes(data)
    obj_path = os.path.join(OBJECTS_DIR, h)
    if not os.path.exists(obj_path):
        with open(obj_path, "wb") as f:
            f.write(data)
    return h

def read_object(hash_hex: str) -> bytes:
    obj_path = os.path.join(OBJECTS_DIR, hash_hex)
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"Object {hash_hex} not found")
    with open(obj_path, "rb") as f:
        return f.read()

def current_time_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# ---------- Object formats ----------
# Blob: raw file content stored as bytes
# Tree: a JSON array of entries: [{ "name": <str>, "type": "blob"|"tree", "hash": <hex>, "mode": "100644"/"40000" }]
# Commit: JSON: { "tree": <hash>, "parent": <hash|null>, "message": <str>, "time": <iso>, "revoked": false }

def hash_tree_obj(tree_obj: List[Dict]) -> str:
    payload = json.dumps(tree_obj, separators=(",",":"), sort_keys=True).encode()
    return write_object(payload)

def hash_commit_obj(commit_obj: Dict) -> str:
    payload = json.dumps(commit_obj, separators=(",",":"), sort_keys=True).encode()
    return write_object(payload)

# ---------- Repo commands ----------
def cmd_init(args):
    if os.path.exists(REPO_DIR):
        print(f"{REPO_DIR} already exists.")
        return
    os.makedirs(OBJECTS_DIR, exist_ok=True)
    # init HEAD as null
    write_json(REFS_FILE, {"HEAD": None})
    write_json(REVOKE_FILE, [])
    # empty index
    write_json(INDEX_FILE, [])
    print("Initialized empty minigit repository in", os.path.abspath(REPO_DIR))

def cmd_add(args):
    ensure_repo()
    files = args.files
    if not files:
        print("No files specified to add.")
        return
    idx = read_json(INDEX_FILE) or []
    idx_set = set(idx)
    added = 0
    for f in files:
        if not os.path.exists(f):
            print(f"warning: {f} does not exist, skipping")
            continue
        if not path_in_repo(f):
            print(f"warning: cannot add files inside {REPO_DIR}, skipping {f}")
            continue
        # convert to posix relative path for storage
        r = os.path.normpath(f)
        if r not in idx_set:
            idx.append(r)
            idx_set.add(r)
            added += 1
    write_json(INDEX_FILE, sorted(idx))
    print(f"Added {added} file(s) to index.")

def build_tree_from_index(index_files: List[str]) -> Tuple[str, List[Dict]]:
    """
    Build tree objects from list of file paths (relative) and store blobs/trees.
    Returns (root_tree_hash, tree_obj)
    """
    # Build nested map structure: dict for directories, blobs for files
    tree_map = {}  # nested dict
    for path in index_files:
        parts = Path(path).parts
        cur = tree_map
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        # read file content and write blob
        file_path = path
        with open(file_path, "rb") as f:
            data = f.read()
        blob_hash = write_object(data)
        cur[parts[-1]] = ("blob", blob_hash)

    # Recursively build tree objects and compute hashes
    def build_node(node) -> Tuple[str, List[Dict]]:
        entries = []
        for name in sorted(node.keys()):
            val = node[name]
            if isinstance(val, tuple) and val[0] == "blob":
                entries.append({"name": name, "type": "blob", "hash": val[1], "mode": "100644"})
            else:
                # subtree
                subtree_hash, subtree_obj = build_node(val)
                entries.append({"name": name, "type": "tree", "hash": subtree_hash, "mode": "40000"})
        tree_hash = hash_tree_obj(entries)
        return tree_hash, entries

    root_hash, root_obj = build_node(tree_map)
    return root_hash, root_obj

def cmd_commit(args):
    ensure_repo()
    index = read_json(INDEX_FILE) or []
    if not index:
        print("No files staged. Use add to stage files.")
        return
    # Build tree (writes blobs and trees)
    root_hash, _ = build_tree_from_index(index)
    refs = read_json(REFS_FILE) or {"HEAD": None}
    parent = refs.get("HEAD")
    commit_obj = {
        "tree": root_hash,
        "parent": parent,
        "message": args.message or "",
        "time": current_time_iso(),
        "revoked": False
    }
    commit_hash = hash_commit_obj(commit_obj)
    # update HEAD
    refs["HEAD"] = commit_hash
    write_json(REFS_FILE, refs)
    print(f"Committed: {commit_hash}\nMessage: {commit_obj['message']}")

def cmd_log(args):
    ensure_repo()
    refs = read_json(REFS_FILE) or {"HEAD": None}
    head = refs.get("HEAD")
    if not head:
        print("No commits yet.")
        return
    cur = head
    while cur:
        try:
            raw = read_object(cur)
        except FileNotFoundError:
            print(f"(missing commit object {cur})")
            break
        commit = json.loads(raw.decode())
        revoked = is_revoked(cur)
        print(f"commit {cur}{' [REVOKED]' if revoked else ''}")
        print(f"Date: {commit.get('time')}")
        msg = commit.get("message","")
        print()
        print(f"    {msg}")
        print()
        cur = commit.get("parent")

def is_revoked(commit_hash: str) -> bool:
    revoked = read_json(REVOKE_FILE) or []
    return commit_hash in revoked

def cmd_status(args):
    ensure_repo()
    index = read_json(INDEX_FILE) or []
    refs = read_json(REFS_FILE) or {"HEAD": None}
    head = refs.get("HEAD")
    print(f"HEAD: {head}")
    print("Staged files:")
    for f in index:
        print("  ", f)
    # detect dirty (changes compared to the tree)
    if head:
        try:
            raw = read_object(head)
            commit = json.loads(raw.decode())
            tree_hash = commit["tree"]
            # simple: compare file contents' blob hashes to objects in current tree built from index
            built_root_hash, _ = build_tree_from_index(index) if index else (None, None)
            if built_root_hash != tree_hash:
                print("Working tree differs from HEAD (changes staged vs head).")
            else:
                print("Working tree matches HEAD (for staged files).")
        except Exception:
            print("Could not compare working tree to HEAD (missing objects?)")

def read_tree_to_entries(tree_hash: str) -> List[Dict]:
    raw = read_object(tree_hash)
    return json.loads(raw.decode())

def checkout_tree(tree_hash: str, target_dir: str = "."):
    """
    Given a tree hash, recursively restore all files under target_dir.
    WARNING: Overwrites files in working directory paths referenced in tree.
    """
    def _checkout(tree_hash, cur_path):
        entries = read_tree_to_entries(tree_hash)
        for ent in entries:
            name = ent["name"]
            if ent["type"] == "blob":
                blob_hash = ent["hash"]
                data = read_object(blob_hash)
                out_path = os.path.join(cur_path, name)
                os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(data)
            elif ent["type"] == "tree":
                subtree_hash = ent["hash"]
                new_dir = os.path.join(cur_path, name)
                os.makedirs(new_dir, exist_ok=True)
                _checkout(subtree_hash, new_dir)
            else:
                raise ValueError("Unknown tree entry type")

    _checkout(tree_hash, target_dir)

def cmd_checkout(args):
    ensure_repo()
    target = args.target
    refs = read_json(REFS_FILE) or {"HEAD": None}
    head = refs.get("HEAD")
    commit_hash = None
    if target is None or target.lower() == "head":
        if not head:
            print("No commits yet.")
            return
        commit_hash = head
    else:
        # if target looks like a hash, use it; otherwise we could implement branches. For now assume hash.
        commit_hash = target

    # check revoke
    if is_revoked(commit_hash):
        print(f"ERROR: Commit {commit_hash} is revoked and cannot be checked out.")
        return
    try:
        raw = read_object(commit_hash)
    except FileNotFoundError:
        print(f"Commit {commit_hash} not found.")
        return
    commit = json.loads(raw.decode())
    tree_hash = commit["tree"]
    # restore files (note: this writes files from tree into working dir)
    checkout_tree(tree_hash, ".")
    # update HEAD to this commit
    refs["HEAD"] = commit_hash
    write_json(REFS_FILE, refs)
    print(f"Checked out commit {commit_hash}.")

# ---------- Verify (tamper detection) ----------
def verify_tree(tree_hash: str, seen=set()) -> Tuple[bool, List[str]]:
    """Verify tree and all children: ensure stored object content matches its hash and referenced objects exist."""
    errors = []
    # verify tree object exists
    try:
        raw = read_object(tree_hash)
    except FileNotFoundError:
        return False, [f"Missing tree object {tree_hash}"]
    # recompute hash to ensure object wasn't tampered with
    computed = sha256_bytes(raw)
    if computed != tree_hash:
        errors.append(f"Tree object {tree_hash} content mismatch (hash recomputed {computed})")
    try:
        entries = json.loads(raw.decode())
    except Exception:
        errors.append(f"Tree object {tree_hash} JSON decode error")
        return False, errors
    for ent in entries:
        typ = ent.get("type")
        h = ent.get("hash")
        if typ == "blob":
            # verify blob content exists and matches hash
            try:
                b = read_object(h)
            except FileNotFoundError:
                errors.append(f"Missing blob object {h} (referenced by tree {tree_hash})")
                continue
            if sha256_bytes(b) != h:
                errors.append(f"Blob object {h} content mismatch")
        elif typ == "tree":
            ok_sub, err_sub = verify_tree(h, seen)
            errors.extend(err_sub)
        else:
            errors.append(f"Unknown entry type {typ} in tree {tree_hash}")
    return (len(errors) == 0), errors

def verify_commit(commit_hash: str, visited=set()) -> Tuple[bool, List[str]]:
    errors = []
    try:
        raw = read_object(commit_hash)
    except FileNotFoundError:
        return False, [f"Missing commit object {commit_hash}"]
    if sha256_bytes(raw) != commit_hash:
        errors.append(f"Commit object {commit_hash} content mismatch")
    try:
        commit = json.loads(raw.decode())
    except Exception:
        errors.append(f"Commit object {commit_hash} JSON decode error")
        return False, errors
    # verify tree
    tree_hash = commit.get("tree")
    if tree_hash is None:
        errors.append(f"Commit {commit_hash} missing tree field")
    else:
        ok_tree, tree_err = verify_tree(tree_hash)
        errors.extend(tree_err)
    # verify parent chain recursively
    parent = commit.get("parent")
    if parent:
        if parent in visited:
            errors.append(f"Cycle detected in commit parents at {parent}")
            return False, errors
        visited.add(parent)
        ok_parent, parent_err = verify_commit(parent, visited)
        errors.extend(parent_err)
    return (len(errors) == 0), errors

def cmd_verify(args):
    ensure_repo()
    refs = read_json(REFS_FILE) or {"HEAD": None}
    head = refs.get("HEAD")
    if not head:
        print("No commits to verify.")
        return
    ok, errors = verify_commit(head, set([head]))
    if ok:
        print("OK: repository integrity verified (no tampering detected for stored objects referenced by HEAD).")
    else:
        print("Verification FAILED. Issues found:")
        for e in errors:
            print(" -", e)

# ---------- Revoke ----------
def cmd_revoke(args):
    ensure_repo()
    commit_hash = args.commit
    # check commit exists
    try:
        _ = read_object(commit_hash)
    except FileNotFoundError:
        print(f"Commit {commit_hash} not found.")
        return
    revoked = read_json(REVOKE_FILE) or []
    if commit_hash in revoked:
        print(f"Commit {commit_hash} is already revoked.")
        return
    revoked.append(commit_hash)
    write_json(REVOKE_FILE, revoked)
    print(f"Revoked commit {commit_hash}.")

# ---------- Convenience: show object info ----------
def cmd_cat_file(args):
    ensure_repo()
    oid = args.hash
    try:
        raw = read_object(oid)
    except FileNotFoundError:
        print(f"Object {oid} not found.")
        return
    # try to print JSON pretty if possible, else raw bytes with repr
    try:
        doc = json.loads(raw.decode())
        print(json.dumps(doc, indent=2, sort_keys=True))
    except Exception:
        try:
            print(raw.decode(errors="replace"))
        except Exception:
            print(repr(raw))

# ---------- CLI ----------
def build_parser():
    p = argparse.ArgumentParser(prog="minigit.py")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("init", help="Initialize repository")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("add", help="Add files to index")
    sp.add_argument("files", nargs="+")
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("commit", help="Commit staged files")
    sp.add_argument("-m", "--message", default="", help="Commit message")
    sp.set_defaults(func=cmd_commit)

    sp = sub.add_parser("log", help="Show commit log")
    sp.set_defaults(func=cmd_log)

    sp = sub.add_parser("status", help="Show status")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("checkout", help="Checkout commit")
    sp.add_argument("target", nargs="?", default=None, help="Commit hash or HEAD")
    sp.set_defaults(func=cmd_checkout)

    sp = sub.add_parser("verify", help="Verify repository integrity (tamper detect)")
    sp.set_defaults(func=cmd_verify)

    sp = sub.add_parser("revoke", help="Revoke a commit (mark as revoked)")
    sp.add_argument("commit", help="Commit hash to revoke")
    sp.set_defaults(func=cmd_revoke)

    sp = sub.add_parser("cat-file", help="Print object contents")
    sp.add_argument("hash", help="Object hash")
    sp.set_defaults(func=cmd_cat_file)

    return p

def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return
    # ensure repo dir exists for commands that need it, except init
    if args.cmd != "init" and not os.path.exists(REPO_DIR):
        print("Not a minigit repository (run 'minigit.py init').")
        return
    # ensure objects dir exists for init+others
    if args.cmd == "init":
        args.func(args)
        return
    # ensure directories exist for other commands
    os.makedirs(OBJECTS_DIR, exist_ok=True)
    # ensure index and refs exist
    if not os.path.exists(INDEX_FILE):
        write_json(INDEX_FILE, [])
    if not os.path.exists(REFS_FILE):
        write_json(REFS_FILE, {"HEAD": None})
    if not os.path.exists(REVOKE_FILE):
        write_json(REVOKE_FILE, [])
    args.func(args)

if __name__ == "__main__":
    main(sys.argv[1:])

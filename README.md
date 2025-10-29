# 🧩 MiniGit – Lightweight Version Control using Merkle Trees & SHA-256

**MiniGit** is a lightweight, educational version control system inspired by **Git**, built entirely in **Python**.  
It demonstrates how Git ensures **data integrity and version history** using **Merkle Trees** and **SHA-256 cryptographic hashing**.

---

## 🚀 Overview

MiniGit allows you to:
- Initialize your own repository
- Add (stage) files for commit
- Commit snapshots with full SHA-256 integrity
- View the commit history
- Verify repository integrity (detect any tampering)
- Revoke unsafe commits
- Safely checkout previous versions

Unlike Git, MiniGit is minimal and focuses on **core concepts** — perfect for learning how modern version control systems achieve data immutability and tamper detection.

---

## 🧠 Core Concepts

MiniGit stores your data as **content-addressed objects** in `.minigit/objects`.

- Each file (`blob`), directory (`tree`), and commit (`commit`) is hashed using **SHA-256**.
- The structure forms a **Merkle Tree**, where each commit points to a tree, and each tree references blobs/subtrees.
- Tampering even a single byte in any object changes all hashes above it — instantly detectable.
- The `verify` command traverses the entire commit chain to confirm repository integrity.

---

## 🛠️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Abishekmoorthy/minigit.git
cd minigit
```

### 2️⃣ Run with Python

Make sure you have Python 3.7+ installed.

```bash
python minigit.py <command> [options]
```

---

## ⚙️ Available Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize a new MiniGit repository |
| `add <files>` | Stage files for commit |
| `commit -m "message"` | Create a new commit from staged files |
| `log` | Display commit history |
| `status` | Show current status (HEAD, staged files, etc.) |
| `checkout <commit_hash>` | Restore files from a specific commit |
| `verify` | Verify data integrity (Merkle tree check) |
| `revoke <commit_hash>` | Revoke a specific commit |
| `cat-file <hash>` | View the content of any object by hash |

---

## 🧩 Example Workflow

### 🔹 Step 1 — Initialize a Repository

**Input:**
```bash
python minigit.py init
```

**Output:**
```
Initialized empty minigit repository in E:\minigit\.minigit
```

### 🔹 Step 2 — Add Files to Stage

**Input:**
```bash
echo "Hello MiniGit" > hello.txt
python minigit.py add hello.txt
```

**Output:**
```
Added 1 file(s) to index.
```

### 🔹 Step 3 — Commit Changes

**Input:**
```bash
python minigit.py commit -m "Initial commit"
```

**Output:**
```
Committed: 2c97b83f32c23a2e9a5b0b4c12a458db46c99f2438f0a79d5a3f7466f4af07e3
Message: Initial commit
```

### 🔹 Step 4 — View Commit History

**Input:**
```bash
python minigit.py log
```

**Output:**
```
commit 2c97b83f32c23a2e9a5b0b4c12a458db46c99f2438f0a79d5a3f7466f4af07e3
Date: 2025-10-29T14:42:00Z

    Initial commit
```

### 🔹 Step 5 — Check Repository Status

**Input:**
```bash
python minigit.py status
```

**Output:**
```
HEAD: 2c97b83f32c23a2e9a5b0b4c12a458db46c99f2438f0a79d5a3f7466f4af07e3
Staged files:
   hello.txt
Working tree matches HEAD (for staged files).
```

### 🔹 Step 6 — Verify Repository Integrity

**Input:**
```bash
python minigit.py verify
```

**Output:**
```
OK: repository integrity verified (no tampering detected for stored objects referenced by HEAD).
```

If any object is tampered with (for example, someone manually edits `.minigit/objects/<hash>`), you'll see:

```
Verification FAILED. Issues found:
 - Blob object 4d8f2... content mismatch
```

### 🔹 Step 7 — Revoke a Commit

**Input:**
```bash
python minigit.py revoke 2c97b83f32c23a2e9a5b0b4c12a458db46c99f2438f0a79d5a3f7466f4af07e3
```

**Output:**
```
Revoked commit 2c97b83f32c23a2e9a5b0b4c12a458db46c99f2438f0a79d5a3f7466f4af07e3.
```

Now, this commit is marked as revoked. If you try to check it out:

```
ERROR: Commit 2c97b83f32c23a2e9a5b0b4c12a458db46c99f2438f0a79d5a3f7466f4af07e3 is revoked and cannot be checked out.
```

---

## 📂 Repository Structure

```
minigit/
│
├── minigit.py           # Main program file
├── README.md            # Documentation
└── .minigit/            # Auto-created directory (after init)
    ├── objects/         # SHA-256 content-addressed blobs, trees, commits
    ├── index            # Staged files
    ├── refs.json        # HEAD pointer and refs
    └── revoked.json     # Revoked commit list
```

---

## 🧰 Technical Implementation

- **Language:** Python 3
- **Hashing Algorithm:** SHA-256
- **Merkle Tree Structure:**
  - `blob` → file content
  - `tree` → directory mapping (JSON of names + hashes)
  - `commit` → metadata + pointer to tree + parent
- **Tamper Detection:** Verifies recursive hashes for all blobs/trees/commits.
- **Revocation:** Maintains a blacklist of revoked commits to prevent unsafe checkouts.

---

## 🔐 Security Insight

MiniGit shows how Git ensures cryptographic integrity:

Every commit's hash depends on all underlying file content. If any file, even deep in history, changes — the hash chain breaks.

This Merkle-tree based verification ensures:

- **Integrity** — any modification is detectable
- **Non-repudiation** — history cannot be silently altered
- **Traceability** — each commit references its parent

---

## 🧾 Sample Console Session

```bash
E:\minigit> python minigit.py init
Initialized empty minigit repository in E:\minigit\.minigit

E:\minigit> echo "Sample text" > test.txt
E:\minigit> python minigit.py add test.txt
Added 1 file(s) to index.

E:\minigit> python minigit.py commit -m "Add test.txt"
Committed: 0c8a9a66c8e13ef56b69cbd458cf2b6c68f6e80df44c728b15a1237d7f77e63b
Message: Add test.txt

E:\minigit> python minigit.py log
commit 0c8a9a66c8e13ef56b69cbd458cf2b6c68f6e80df44c728b15a1237d7f77e63b
Date: 2025-10-29T14:46:00Z

    Add test.txt

E:\minigit> python minigit.py verify
OK: repository integrity verified (no tampering detected for stored objects referenced by HEAD).
```

---

## 🧑‍💻 Author

**Abishek Moorthy**  
📍 GitHub: [@Abishekmoorthy](https://github.com/Abishekmoorthy)

---

## 📜 License

This project is licensed under the MIT License — you are free to use, modify, and distribute it for educational or research purposes.

---

## 🌟 Final Note

MiniGit is not a full replacement for Git — it's a learning project that opens the black box of how version control systems manage data integrity, history, and verification using cryptographic methods.

If you're curious about how Git stores commits internally or want a hands-on introduction to Merkle trees — this project is a perfect starting point.

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
- `verify` command traverses the entire commit chain to confirm repository integrity.

---

## 🛠️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Abishekmoorthy/minigit.git
cd minigit

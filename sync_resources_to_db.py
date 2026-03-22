#!/usr/bin/env python3
"""
Sync Claude Agent SDK documentation to SQLite database
"""

import os
import re
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime


def get_db_connection():
    """Get database connection"""
    db_path = Path(__file__).parent / "data" / "knowledge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create tables if they don't exist
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            category TEXT,
            tags TEXT,
            content_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category);
        CREATE INDEX IF NOT EXISTS idx_resources_tags ON resources(tags);
        CREATE INDEX IF NOT EXISTS idx_resources_hash ON resources(content_hash);
    """)

    return conn


def extract_frontmatter(content):
    """Extract YAML frontmatter from markdown"""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = {}
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"\'')
            return frontmatter, parts[2].strip()
    return {}, content


def extract_title(content, filepath):
    """Extract title from content or filename"""
    # Try frontmatter first
    frontmatter, _ = extract_frontmatter(content)
    if 'title' in frontmatter:
        return frontmatter['title']

    # Try first heading
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Use filename
    return Path(filepath).stem.replace('-', ' ').replace('_', ' ').title()


def extract_category(filepath):
    """Extract category from file path"""
    parts = Path(filepath).parts
    if 'docs' in parts:
        idx = parts.index('docs')
        if idx + 1 < len(parts) - 1:
            return parts[idx + 1]
    return 'general'


def extract_tags(content, category):
    """Extract tags from content"""
    tags = [category]

    # Extract code blocks
    code_blocks = re.findall(r'```(\w+)', content)
    tags.extend(code_blocks)

    # Extract common keywords
    keywords = [
        'agent', 'sdk', 'api', 'tool', 'mcp', 'prompt',
        'claude', 'anthropic', 'streaming', 'async', 'sync'
    ]
    content_lower = content.lower()
    for kw in keywords:
        if kw in content_lower:
            tags.append(kw)

    return ','.join(set(tags))


def compute_hash(content):
    """Compute content hash"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def sync_file(conn, filepath):
    """Sync a single file to database"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  [ERROR] Failed to read {filepath}: {e}")
        return False

    title = extract_title(content, filepath)
    category = extract_category(filepath)
    tags = extract_tags(content, category)
    content_hash = compute_hash(content)
    source = str(filepath)

    # Check if already exists with same hash
    cursor = conn.execute(
        "SELECT id FROM resources WHERE source = ? AND content_hash = ?",
        (source, content_hash)
    )
    if cursor.fetchone():
        print(f"  [SKIP] {title} (unchanged)")
        return True

    # Check if exists with different hash
    cursor = conn.execute(
        "SELECT id FROM resources WHERE source = ?",
        (source,)
    )
    existing = cursor.fetchone()

    if existing:
        # Update existing
        conn.execute("""
            UPDATE resources
            SET title = ?, content = ?, category = ?, tags = ?, content_hash = ?, updated_at = ?
            WHERE id = ?
        """, (title, content, category, tags, content_hash, datetime.now(), existing['id']))
        print(f"  [UPDATE] {title}")
    else:
        # Insert new
        conn.execute("""
            INSERT INTO resources (title, content, source, category, tags, content_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, content, source, category, tags, content_hash))
        print(f"  [INSERT] {title}")

    conn.commit()
    return True


def sync_directory(conn, base_path, pattern='**/*.md'):
    """Sync all files in directory"""
    base = Path(base_path)

    if not base.exists():
        print(f"[ERROR] Directory not found: {base_path}")
        return

    files = list(base.glob(pattern))
    print(f"\n[SYNC] Found {len(files)} files in {base_path}")

    for filepath in sorted(files):
        sync_file(conn, filepath)


def main():
    print("=" * 60)
    print("Claude Agent SDK Documentation Sync")
    print("=" * 60)

    conn = get_db_connection()

    # Sync docs directory
    docs_path = Path(__file__).parent / "docs" / "claude-agent-sdk"
    sync_directory(conn, docs_path)

    # Also sync any other docs
    other_docs = Path(__file__).parent / "docs"
    if other_docs.exists():
        for subdir in other_docs.iterdir():
            if subdir.is_dir() and subdir.name != 'claude-agent-sdk':
                sync_directory(conn, subdir)

    # Print summary
    cursor = conn.execute("SELECT COUNT(*) as count FROM resources")
    count = cursor.fetchone()['count']

    cursor = conn.execute("SELECT category, COUNT(*) as count FROM resources GROUP BY category")
    categories = cursor.fetchall()

    print("\n" + "=" * 60)
    print(f"[DONE] Total resources: {count}")
    print("=" * 60)

    for cat in categories:
        print(f"  {cat['category']}: {cat['count']}")

    conn.close()


if __name__ == '__main__':
    main()

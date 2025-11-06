# arxiv_paper_pulse/bot.py
"""
Bot class with memory, reflection, and comprehensive logging capabilities.
Single AI unit with display capabilities for multi-agent systems.
"""

import sqlite3
import json
import hashlib
import os
import time
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
import numpy as np
from google import genai
from . import config


class Bot:
    """
    Bot class - a single AI unit with display capabilities.

    Features:
    - Synchronous Gemini API integration
    - Dual memory system (internal/external)
    - Thought journal with queryable database
    - Request/response matching and similarity search
    - Complete I/O logging
    - Action logging with optional reflection
    - Safety protocols for external folder access
    """

    def __init__(self, name, role, model=None, system_instruction=None, working_dir=None):
        """
        Initialize Bot instance.

        Args:
            name: Bot name/identifier
            role: Bot role/description
            model: Gemini model to use (default from config)
            system_instruction: Custom system instruction
            working_dir: Working directory path (default: config.BOT_WORKING_DIR/name)
        """
        self.name = name
        self.role = role
        self.model = model or config.DEFAULT_MODEL

        # Initialize Gemini client
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment. Please set it in your .env file.")
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

        # System instruction
        self.system_instruction = system_instruction or f"You are {name}, a {role}."

        # Working directory setup
        if working_dir is None:
            working_dir = Path(config.BOT_WORKING_DIR) / name.lower().replace(' ', '_')
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)

        # Database path
        self.db_path = self.working_dir / "bot_data.db"

        # Context file paths & limits
        self.context_file = self.working_dir / "context.md"
        self.context_history_dir = self.working_dir / config.CONTEXT_HISTORY_DIRNAME
        self.context_history_dir.mkdir(parents=True, exist_ok=True)
        self.context_max_bytes = config.CONTEXT_MAX_BYTES
        self.context_history_retention = config.CONTEXT_HISTORY_RETENTION

        # Display buffer
        self.display_buffer = []

        # External memory state
        self.external_memory_path = None

        # Initialize database
        self._init_database()

        # Initialize context file if it doesn't exist
        self._init_context_file()

        # Embedding client (lazy initialization)
        self._embedding_client = None

    def _init_database(self):
        """Initialize SQLite database with all tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Memory table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            # Thoughts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thoughts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    thought_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    parent_id INTEGER,
                    metadata TEXT
                )
            """)

            # Requests table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_hash TEXT UNIQUE NOT NULL,
                    request_text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    embedding BLOB
                )
            """)

            # Responses table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    response_text TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    success_rating TEXT,
                    metadata TEXT,
                    FOREIGN KEY (request_id) REFERENCES requests(id)
                )
            """)

            # Actions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    reflection TEXT
                )
            """)

            # API logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    content TEXT NOT NULL,
                    prompt_hash TEXT,
                    response_hash TEXT,
                    model TEXT,
                    response_time REAL
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_hash ON requests(request_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory(namespace)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_tags ON thoughts(tags)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type)")

            conn.commit()

    def _init_context_file(self):
        """Initialize context.md file if it doesn't exist."""
        if not self.context_file.exists():
            default_context = f"""# Current Context - {self.name}

## Current Status
- Role: {self.role}
- Status: Active
- Last Updated: {datetime.now().isoformat()}

## Current Awareness
- What I'm currently working on:
- What I know:
- What I'm tracking:

## Pending Items / Todos
- [ ]

## Important URLs
-

## Folder Locations & Paths
- Working Directory: {self.working_dir}
- Database: {self.db_path}

## Rules / Limits / Boundaries
-

## Reference Material
- Where to find more information:
- Useful resources:

## Notes
-

---
*This file is automatically loaded into every prompt. Update it as needed to maintain context.*
"""
            self.context_file.write_text(default_context + "\n", encoding='utf-8')

    # ============================================================================
    # CONTEXT FILE MANAGEMENT
    # ============================================================================

    def get_context(self):
        """Get current context from context.md file."""
        if self.context_file.exists():
            return self.context_file.read_text(encoding='utf-8')
        return ""

    def update_context(self, content):
        """
        Replace entire context file content.

        Args:
            content: New markdown content
        """
        self._write_context(content, action='full_update')

    def append_to_context(self, content, section=None):
        """
        Append content to context file, optionally to a specific section.

        Args:
            content: Content to append
            section: Optional section name (e.g., "## Notes") to append under
        """
        def modifier(existing):
            existing = (existing or "").rstrip('\n')
            lines = existing.split('\n') if existing else []

            def ensure_blank_before(idx):
                if idx > 0 and lines[idx - 1].strip():
                    lines.insert(idx, "")
                    return idx + 1
                return idx

            if section:
                header = section.strip()
                if not header.startswith("##"):
                    header = f"## {header}"

                section_index = None
                for i, line in enumerate(lines):
                    if line.strip() == header:
                        section_index = i
                        break

                if section_index is None:
                    if lines and lines[-1].strip():
                        lines.append("")
                    lines.append(header)
                    lines.append(content)
                else:
                    insert_index = section_index + 1
                    for i in range(section_index + 1, len(lines)):
                        if lines[i].startswith('##'):
                            insert_index = i
                            break
                        insert_index = i + 1
                    insert_index = ensure_blank_before(insert_index)
                    lines.insert(insert_index, content)
                return "\n".join(lines)

            # No section specified
            if lines:
                if lines[-1].strip():
                    lines.append("")
                lines.append(content)
                return "\n".join(lines)
            return content

        updated = modifier(self.get_context())
        self._write_context(updated, action='append', metadata={'section': section} if section else None)

    def update_context_section(self, section_name, content):
        """
        Update a specific section in context file.

        Args:
            section_name: Section name (e.g., "Current Awareness")
            content: New content for the section
        """
        header = section_name.strip()
        if not header.startswith("##"):
            header = f"## {header}"

        def modifier(existing):
            existing = existing or ""
            lines = existing.split('\n') if existing else []
            section_index = None
            for i, line in enumerate(lines):
                if line.strip() == header:
                    section_index = i
                    break

            if section_index is None:
                new_lines = lines + (["", header, content] if lines else [header, content])
                return "\n".join(new_lines)

            end_index = section_index + 1
            for i in range(section_index + 1, len(lines)):
                if lines[i].startswith('##'):
                    end_index = i
                    break
                end_index = i + 1

            new_lines = lines[:section_index + 1] + [content] + lines[end_index:]
            return "\n".join(new_lines)

        updated = modifier(self.get_context())
        self._write_context(updated, action='section_update', metadata={'section': section_name})

    def list_context_history(self, limit=None):
        """List available context snapshots (newest first)."""
        snapshots = sorted(self.context_history_dir.glob("context_*.md"), reverse=True)
        if limit is not None:
            try:
                limit_value = int(limit)
                if limit_value >= 0:
                    snapshots = snapshots[:limit_value]
            except (ValueError, TypeError):
                pass
        return [
            {
                'path': str(path),
                'name': path.name,
                'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            }
            for path in snapshots
        ]

    def load_context_snapshot(self, snapshot: Union[int, str, Path]):
        """Load snapshot content by index or path."""
        if isinstance(snapshot, int):
            snapshots = sorted(self.context_history_dir.glob("context_*.md"), reverse=True)
            if snapshot < 0 or snapshot >= len(snapshots):
                raise IndexError("Snapshot index out of range")
            path = snapshots[snapshot]
        else:
            path = Path(snapshot)
            if not path.is_absolute():
                path = self.context_history_dir / path

        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {path}")

        return path.read_text(encoding='utf-8')

    def _get_context_for_prompt(self):
        """Ensure context fits within size limit before inclusion in prompt."""
        content = self.get_context()
        if not content:
            return ""

        if len(content.encode('utf-8')) <= self.context_max_bytes:
            return content

        # Context exceeds limit (likely edited externally) – snapshot & trim automatically
        self._write_context(
            content,
            action='auto_trim',
            metadata={'reason': 'prompt_overflow'},
            snapshot_reason='prompt_overflow'
        )
        return self.get_context()

    def _write_context(self, content, *, action, metadata=None, snapshot_reason=None):
        """Normalize, limit, snapshot, and write context content."""
        normalized = self._normalize_context_content(content)
        normalized = self._refresh_last_updated(normalized)

        encoded = normalized.encode('utf-8')
        trimmed = False
        if len(encoded) > self.context_max_bytes:
            self._save_context_snapshot(normalized, reason=snapshot_reason or action)
            normalized, trimmed = self._trim_context(normalized)

        if not normalized.endswith('\n'):
            normalized += '\n'

        self.context_file.write_text(normalized, encoding='utf-8')

        log_details = {'action': action, 'bytes': len(normalized.encode('utf-8'))}
        if metadata:
            log_details.update(metadata)
        if trimmed:
            log_details['trimmed'] = True
        self.log_action('context_update', log_details)

    def _normalize_context_content(self, content):
        normalized = (content or "").replace('\r\n', '\n').replace('\r', '\n')
        lines = [line.rstrip() for line in normalized.split('\n')]
        normalized = '\n'.join(lines).strip()
        return normalized

    def _refresh_last_updated(self, content):
        timestamp = datetime.now().isoformat()

        def replacer(match):
            return f"{match.group(1)}{timestamp}"

        updated, count = re.subn(r"(-\s*Last Updated:\s*)(.*)", replacer, content, count=1)
        if count == 0:
            updated = updated.replace(
                "## Current Status",
                f"## Current Status\n- Last Updated: {timestamp}",
                1
            )
        return updated

    def _trim_context(self, content):
        max_bytes = self.context_max_bytes
        encoded = content.encode('utf-8')
        if len(encoded) <= max_bytes:
            return content, False

        separator = "\n---"
        if separator in content:
            header, body = content.split(separator, 1)
            header += separator
        else:
            header, body = "", content

        notice = "\n\n(… trimmed to fit context limit …)\n"
        static_block = header + notice

        if len(static_block.encode('utf-8')) >= max_bytes:
            truncated = content
            while len(truncated.encode('utf-8')) > max_bytes and truncated:
                truncated = truncated[1:]
            return truncated, True

        # Trim from the front until fits
        body_tail = body
        while body_tail and len((static_block + body_tail).encode('utf-8')) > max_bytes:
            body_tail = body_tail[1:]

        trimmed = header + notice + body_tail
        while len(trimmed.encode('utf-8')) > max_bytes and trimmed:
            trimmed = trimmed[1:]

        return trimmed, True

    def _save_context_snapshot(self, content, reason):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = self.context_history_dir / f"context_{timestamp}.md"
        header = f"<!-- Snapshot created {datetime.now().isoformat()} | Reason: {reason} -->\n\n"
        snapshot_path.write_text(header + content + ("\n" if not content.endswith('\n') else ""), encoding='utf-8')
        self.log_action('context_snapshot', {'path': str(snapshot_path), 'reason': reason})
        self._prune_context_history()

    def _prune_context_history(self):
        retention = max(0, int(self.context_history_retention))
        snapshots = sorted(self.context_history_dir.glob("context_*.md"))
        if retention == 0:
            for path in snapshots:
                path.unlink(missing_ok=True)
            return

        excess = len(snapshots) - retention
        for path in snapshots[:max(0, excess)]:
            path.unlink(missing_ok=True)

    # ============================================================================
    # 2. SYNCHRONOUS API INTEGRATION
    # ============================================================================

    def process(self, prompt, context=None, include_context=True):
        """
        Process a prompt synchronously using Gemini API.

        Args:
            prompt: Input prompt text
            context: Optional context dict
            include_context: Whether to include context.md contents in the prompt

        Returns:
            Response text from Gemini API
        """
        start_time = time.time()

        # Log input
        self._log_input(prompt, context)

        # Build full prompt with context
        full_prompt = self._build_prompt(prompt, context)

        # Log action
        self.log_action('api_call', {'prompt': prompt[:100], 'model': self.model, 'include_context': include_context})

        # Make synchronous Gemini API call
        try:
            if include_context:
                current_context = self._get_context_for_prompt()
                prompt_with_context = f"{full_prompt}\n\n---\n\nCurrent Context (from context.md):\n{current_context}"
            else:
                prompt_with_context = full_prompt

            response = self.client.models.generate_content(
                model=self.model,
                contents=[self.system_instruction, prompt_with_context]
            )

            response_text = response.text if hasattr(response, 'text') else str(response)
            response_time = time.time() - start_time

            # Log output
            self._log_output(response_text, {'model': self.model, 'response_time': response_time})

            # Record thought
            self.record_thought('processing', f"Processed prompt: {prompt[:100]}...")

            return response_text

        except Exception as e:
            # Log error
            self.log_action('api_call', {'error': str(e), 'prompt': prompt[:100]})
            raise

    def _build_prompt(self, prompt, context=None):
        """Build full prompt with context."""
        parts = [prompt]

        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            parts.append(f"\n\nAdditional Context:\n{context_str}")

        return "\n".join(parts)

    # ============================================================================
    # 3. I/O LOGGING SYSTEM
    # ============================================================================

    def _log_input(self, prompt, context=None):
        """Log incoming request."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        content = json.dumps({'prompt': prompt, 'context': context})

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO api_logs (timestamp, direction, content, prompt_hash, model)
                VALUES (?, 'in', ?, ?, ?)
            """, (datetime.now().isoformat(), content, prompt_hash, self.model))
            conn.commit()

    def _log_output(self, response, metadata=None):
        """Log outgoing response."""
        response_hash = hashlib.sha256(response.encode()).hexdigest()
        content = json.dumps({'response': response, 'metadata': metadata})
        response_time = metadata.get('response_time') if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO api_logs (timestamp, direction, content, response_hash, model, response_time)
                VALUES (?, 'out', ?, ?, ?, ?)
            """, (datetime.now().isoformat(), content, response_hash, self.model, response_time))
            conn.commit()

    # ============================================================================
    # 4. DUAL MEMORY SYSTEM (INTERNAL)
    # ============================================================================

    def store_internal(self, key, value, metadata=None):
        """Store in internal memory (permanent)."""
        value_json = json.dumps(value) if not isinstance(value, str) else value
        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory (key, namespace, value, timestamp, metadata)
                VALUES (?, 'internal', ?, ?, ?)
            """, (key, value_json, datetime.now().isoformat(), metadata_json))
            conn.commit()

        self.log_action('memory_write', {'key': key, 'namespace': 'internal'})

    def retrieve_internal(self, key):
        """Retrieve from internal memory."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT value, metadata FROM memory
                WHERE key = ? AND namespace = 'internal'
            """, (key,))
            row = cursor.fetchone()

            if row:
                self.log_action('memory_read', {'key': key, 'namespace': 'internal'})
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return None

    # ============================================================================
    # 5. DUAL MEMORY SYSTEM (EXTERNAL)
    # ============================================================================

    def store_external(self, key, value, metadata=None):
        """Store in external memory (modular)."""
        if not self.external_memory_path:
            raise ValueError("External memory not coupled. Use couple_external_memory() first.")

        value_json = json.dumps(value) if not isinstance(value, str) else value
        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.external_memory_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory (key, namespace, value, timestamp, metadata)
                VALUES (?, 'external', ?, ?, ?)
            """, (key, value_json, datetime.now().isoformat(), metadata_json))
            conn.commit()

        self.log_action('memory_write', {'key': key, 'namespace': 'external'})

    def retrieve_external(self, key):
        """Retrieve from external memory."""
        if not self.external_memory_path:
            raise ValueError("External memory not coupled. Use couple_external_memory() first.")

        with sqlite3.connect(self.external_memory_path) as conn:
            cursor = conn.execute("""
                SELECT value, metadata FROM memory
                WHERE key = ? AND namespace = 'external'
            """, (key,))
            row = cursor.fetchone()

            if row:
                self.log_action('memory_read', {'key': key, 'namespace': 'external'})
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return None

    def couple_external_memory(self, external_path, request_permission=True):
        """
        Couple external memory database.

        Args:
            external_path: Path to external memory database
            request_permission: If True, request permission if outside workspace
        """
        external_path = Path(external_path)

        # Safety check
        if request_permission and not self._is_within_workspace(external_path):
            if not self._check_permission(str(external_path), 'read'):
                raise PermissionError(f"Access denied to external path: {external_path}")

        # Ensure directory exists
        external_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize external database if needed
        if not external_path.exists():
            with sqlite3.connect(external_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory (
                        key TEXT PRIMARY KEY,
                        namespace TEXT NOT NULL,
                        value TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        metadata TEXT
                    )
                """)
                conn.commit()

        self.external_memory_path = external_path
        self.log_action('memory_coupling', {'path': str(external_path)})

    def uncouple_external_memory(self):
        """Uncouple external memory."""
        if self.external_memory_path:
            self.log_action('memory_uncoupling', {'path': str(self.external_memory_path)})
            self.external_memory_path = None

    # ============================================================================
    # 6. THOUGHT JOURNAL
    # ============================================================================

    def record_thought(self, thought_type, content, tags=None, parent_id=None):
        """
        Record a thought in the journal.

        Args:
            thought_type: Type of thought ('reasoning', 'decision', 'reflection', 'planning')
            content: Thought content
            tags: Optional list of tags (auto-extracted if None)
            parent_id: Optional parent thought ID for thought chains
        """
        if tags is None:
            tags = self._extract_tags(content)

        tags_json = json.dumps(tags) if tags else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO thoughts (timestamp, thought_type, content, tags, parent_id)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), thought_type, content, tags_json, parent_id))
            conn.commit()

        self.log_action('thought', {'type': thought_type, 'content_length': len(content)})

    def _extract_tags(self, content):
        """Extract simple tags from content."""
        keywords = ['problem', 'solution', 'decision', 'plan', 'reasoning', 'analysis', 'evaluation']
        content_lower = content.lower()
        tags = [kw for kw in keywords if kw in content_lower]
        return tags if tags else ['general']

    def query_thoughts(self, filters=None, tags=None, time_range=None):
        """
        Query thoughts from journal.

        Args:
            filters: Dict of filters (thought_type, etc.)
            tags: List of tags to filter by
            time_range: Tuple of (start_time, end_time) as ISO strings

        Returns:
            List of thought dicts
        """
        query = "SELECT id, timestamp, thought_type, content, tags, parent_id FROM thoughts WHERE 1=1"
        params = []

        if filters:
            if 'thought_type' in filters:
                query += " AND thought_type = ?"
                params.append(filters['thought_type'])

        if tags:
            # Simple tag matching (tags stored as JSON array)
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f'%{tag}%')

        if time_range:
            query += " AND timestamp BETWEEN ? AND ?"
            params.extend(time_range)

        query += " ORDER BY timestamp DESC"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            thoughts = []
            for row in rows:
                thoughts.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'thought_type': row[2],
                    'content': row[3],
                    'tags': json.loads(row[4]) if row[4] else [],
                    'parent_id': row[5]
                })

            return thoughts

    def get_thought_chain(self, thought_id):
        """Get reasoning chain starting from thought_id."""
        chain = []
        current_id = thought_id

        with sqlite3.connect(self.db_path) as conn:
            while current_id:
                cursor = conn.execute("""
                    SELECT id, timestamp, thought_type, content, parent_id
                    FROM thoughts WHERE id = ?
                """, (current_id,))
                row = cursor.fetchone()

                if row:
                    chain.append({
                        'id': row[0],
                        'timestamp': row[1],
                        'thought_type': row[2],
                        'content': row[3],
                        'parent_id': row[4]
                    })
                    current_id = row[4]
                else:
                    break

        return list(reversed(chain))  # Return in chronological order

    # ============================================================================
    # 7. EXACT REQUEST MATCHING
    # ============================================================================

    def _normalize_request(self, text):
        """Normalize request text for matching."""
        return text.lower().strip().replace('\n', ' ').replace('\r', ' ')

    def _hash_request(self, text):
        """Hash normalized request text."""
        normalized = self._normalize_request(text)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def find_exact_match(self, request_text):
        """
        Find exact word-for-word match.

        Returns:
            Tuple of (request_id, request_text) or None
        """
        request_hash = self._hash_request(request_text)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, request_text FROM requests WHERE request_hash = ?",
                (request_hash,)
            )
            return cursor.fetchone()

    # ============================================================================
    # 8. NEW REQUEST RECORDING
    # ============================================================================

    def record_new_request(self, request_text):
        """
        Record new request if not exact match.

        Returns:
            Request ID
        """
        normalized = self._normalize_request(request_text)
        request_hash = self._hash_request(request_text)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO requests (request_hash, request_text, timestamp)
                VALUES (?, ?, ?)
            """, (request_hash, request_text, datetime.now().isoformat()))

            if cursor.rowcount == 0:
                # Already exists, get ID
                cursor = conn.execute(
                    "SELECT id FROM requests WHERE request_hash = ?",
                    (request_hash,)
                )
                return cursor.fetchone()[0]

            conn.commit()
            return cursor.lastrowid

    # ============================================================================
    # 9. PAST RESPONSE LOOKUP AND DECISION
    # ============================================================================

    def find_past_responses(self, request_id):
        """Get all past responses for a request."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, response_text, attempt_number, timestamp, success_rating, metadata
                FROM responses WHERE request_id = ?
                ORDER BY attempt_number DESC
            """, (request_id,))

            responses = []
            for row in cursor.fetchall():
                responses.append({
                    'id': row[0],
                    'response_text': row[1],
                    'attempt_number': row[2],
                    'timestamp': row[3],
                    'success_rating': json.loads(row[4]) if row[4] else None,
                    'metadata': json.loads(row[5]) if row[5] else None
                })

            return responses

    def should_make_new_attempt(self, request_id, past_responses):
        """
        Decide if new attempt needed (simple heuristic, not AI).

        Returns:
            True if new attempt needed, False to reuse existing
        """
        if not past_responses:
            return True

        # Get most recent response
        most_recent = max(past_responses, key=lambda r: r['timestamp'])
        age = datetime.now() - datetime.fromisoformat(most_recent['timestamp'])

        # If recent (< 1 hour), reuse
        if age.total_seconds() < 3600:
            return False

        return True

    def record_new_attempt(self, request_id, response, metadata=None):
        """Record new response attempt."""
        past_responses = self.find_past_responses(request_id)
        attempt_number = len(past_responses) + 1

        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO responses (request_id, response_text, attempt_number, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (request_id, response, attempt_number, datetime.now().isoformat(), metadata_json))
            conn.commit()

    # ============================================================================
    # 10. SIMILAR PROMPT DETECTION
    # ============================================================================

    def _get_embedding_client(self):
        """Get embedding client (lazy initialization)."""
        if self._embedding_client is None:
            from .embeddings import PaperEmbeddings
            self._embedding_client = PaperEmbeddings()
        return self._embedding_client

    def _generate_embedding(self, text):
        """Generate embedding for text."""
        client = self._get_embedding_client()
        embedding = client.generate_embedding(text)
        return np.array(embedding, dtype=np.float32)

    def _cosine_similarity(self, embedding1, embedding2):
        """Calculate cosine similarity between embeddings."""
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def find_similar_requests(self, prompt, threshold=0.8):
        """
        Find similar prompts using embeddings.

        Args:
            prompt: Prompt text to find similarities for
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of similar requests with similarity scores
        """
        # Generate embedding for current prompt
        embedding = self._generate_embedding(prompt)

        # Get all requests with embeddings
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, request_text, embedding FROM requests WHERE embedding IS NOT NULL"
            )

            similar = []
            for row in cursor.fetchall():
                stored_embedding = np.frombuffer(row[2], dtype=np.float32)
                similarity = self._cosine_similarity(embedding, stored_embedding)

                if similarity >= threshold:
                    similar.append({
                        'id': row[0],
                        'text': row[1],
                        'similarity': similarity
                    })

            # Sort by similarity (descending)
            similar.sort(key=lambda x: x['similarity'], reverse=True)
            return similar

    def store_embedding_for_request(self, request_id, embedding):
        """Store embedding for a request (lazy generation)."""
        embedding_bytes = embedding.tobytes()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE requests SET embedding = ? WHERE id = ?",
                (embedding_bytes, request_id)
            )
            conn.commit()

    # ============================================================================
    # 11. WORKING FOLDER SYSTEM WITH SAFETY PROTOCOLS
    # ============================================================================

    def _get_workspace_root(self):
        """Find workspace root by looking for .git or pyproject.toml."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / '.git').exists() or (parent / 'pyproject.toml').exists():
                return parent
        return current  # Fallback to current directory

    def _is_within_workspace(self, path):
        """Check if path is within workspace root."""
        workspace = self._get_workspace_root()
        try:
            common = os.path.commonpath([Path(workspace).resolve(), Path(path).resolve()])
            return common == str(Path(workspace).resolve())
        except ValueError:
            return False  # No common path = not within workspace

    def _check_permission(self, path, operation):
        """Check if permission exists for path."""
        workspace = self._get_workspace_root()
        permissions_file = workspace / '.bot_permissions.json'

        if not permissions_file.exists():
            return False

        try:
            with open(permissions_file, 'r') as f:
                permissions = json.load(f)

            allowed_paths = permissions.get('allowed_paths', [])
            denied_paths = permissions.get('denied_paths', [])

            # Check denied first
            for denied in denied_paths:
                if Path(path).resolve() == Path(denied).resolve():
                    return False

            # Check allowed
            for allowed in allowed_paths:
                if Path(path).resolve() == Path(allowed).resolve():
                    return True

            return False
        except Exception:
            return False

    def _request_permission(self, path, operation):
        """Request user permission interactively."""
        print(f"Permission requested: {operation} access to {path}")
        print("This path is outside the workspace root.")
        response = input("Grant permission? (yes/no): ")
        return response.lower() == 'yes'

    # ============================================================================
    # 12. ACTION LOGGING AND REFLECTION
    # ============================================================================

    def log_action(self, action_type, details):
        """
        Log an action.

        Args:
            action_type: Type of action ('api_call', 'memory_read', 'memory_write', 'thought', 'decision')
            details: Dict of action details
        """
        details_json = json.dumps(details) if not isinstance(details, str) else details

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO actions (timestamp, action_type, details)
                VALUES (?, ?, ?)
            """, (datetime.now().isoformat(), action_type, details_json))
            conn.commit()

    def get_action_history(self, limit=None, with_reflection=False):
        """
        Get recent actions.

        Args:
            limit: Maximum number of actions to return
            with_reflection: If True, only return actions with reflection

        Returns:
            List of action dicts
        """
        query = "SELECT id, timestamp, action_type, details, reflection FROM actions"

        if with_reflection:
            query += " WHERE reflection IS NOT NULL"

        query += " ORDER BY timestamp DESC"

        if limit:
            # Validate limit is an integer to prevent SQL injection
            limit = int(limit)
            query += f" LIMIT {limit}"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()

            actions = []
            for row in rows:
                actions.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'action_type': row[2],
                    'details': json.loads(row[3]) if row[3] else {},
                    'reflection': row[4]
                })

            return actions

    def batch_reflect(self, limit=50):
        """
        Batch reflect on recent actions (calls Gemini API).

        Args:
            limit: Number of actions to reflect on

        Returns:
            Dict mapping action IDs to reflections
        """
        # Get recent actions without reflection
        actions = self.get_action_history(limit=limit)
        actions_without_reflection = [a for a in actions if not a.get('reflection')]

        if not actions_without_reflection:
            return {}

        # Build reflection prompt
        actions_summary = "\n".join([
            f"{i+1}. [{a['action_type']}] {a['details']}"
            for i, a in enumerate(actions_without_reflection[:limit])
        ])

        prompt = f"""Reflect on these recent actions:
{actions_summary}

For each action, provide:
1. Why it was taken
2. What was learned
3. What could be improved
4. Connections to past actions

Format your response as a JSON array where each element corresponds to an action and contains:
{{"action_id": <id>, "reflection": "<reflection text>"}}"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt]
            )

            reflection_text = response.text if hasattr(response, 'text') else str(response)

            # Try to parse JSON response
            try:
                reflections = json.loads(reflection_text)
                if not isinstance(reflections, list):
                    reflections = [reflections]
            except json.JSONDecodeError:
                # Fallback: create simple reflection for all actions
                reflections = [
                    {'action_id': a['id'], 'reflection': reflection_text}
                    for a in actions_without_reflection
                ]

            # Store reflections
            reflection_map = {}
            with sqlite3.connect(self.db_path) as conn:
                for reflection in reflections:
                    action_id = reflection.get('action_id')
                    reflection_text = reflection.get('reflection', '')

                    if action_id:
                        conn.execute("""
                            UPDATE actions SET reflection = ? WHERE id = ?
                        """, (reflection_text, action_id))
                        reflection_map[action_id] = reflection_text

                conn.commit()

            return reflection_map

        except Exception as e:
            self.log_action('reflection_error', {'error': str(e)})
            return {}

    # ============================================================================
    # DISPLAY METHODS
    # ============================================================================

    def display(self, content):
        """Add content to display buffer."""
        self.display_buffer.append(content)

    def get_display(self):
        """Get formatted display content."""
        return "\n".join(self.display_buffer)

    def clear_display(self):
        """Clear display buffer."""
        self.display_buffer = []


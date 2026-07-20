from app.schemas import (
    UserCreate,
    PersonaCreate,
    PersonaUpdate,
    ForumCreate,
    MessageCreate,
    SkillCreate,
    SkillUpdate,
    AttachmentCreate,
    ArtifactCreate,
    TaskRunCreate,
    TaskRunUpdate,
)
from app.core.hashing import Hasher
from app.db.client import fetch_one, fetch_all, RowObject, db_transaction, db_execute_commit
from app.core.cache import cache_service
import json
import logging
from typing import List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Cache Keys ---
def user_cache_key(username: str): return f"user:{username}"
def persona_cache_key(pid: int): return f"persona:{pid}"
def forum_cache_key(fid: int): return f"forum:{fid}"
def forum_participants_cache_key(fid: int): return f"forum:{fid}:participants"


def _maybe_parse_json(value):
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except Exception:
        return value


def _json_or_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def _normalize_persona(persona):
    if persona is not None and hasattr(persona, "theories"):
        persona.theories = _maybe_parse_json(persona.theories)
    if persona is not None and hasattr(persona, "skills"):
        persona.skills = _maybe_parse_json(persona.skills) or ["chat.reply"]
    if persona is not None and hasattr(persona, "skill_policy"):
        parsed_policy = _maybe_parse_json(persona.skill_policy)
        persona.skill_policy = parsed_policy if isinstance(parsed_policy, dict) else {}
    if persona is not None and hasattr(persona, "modalities"):
        persona.modalities = _maybe_parse_json(persona.modalities) or ["text"]
    return persona


def _normalize_forum(forum):
    if forum is not None and hasattr(forum, "summary_history"):
        forum.summary_history = _maybe_parse_json(forum.summary_history)
    return forum

# --- User ---
def get_user_by_username(db, username: str):
    # Cache Aside: Read
    cache_key = user_cache_key(username)
    cached = cache_service.get_cache(cache_key)
    if cached:
        return RowObject(cached) # Convert dict back to RowObject-like

    rs = db.execute("SELECT * FROM users WHERE username = ?", [username])
    user = fetch_one(rs)
    
    if user:
        cache_service.set_cache(cache_key, user.__dict__, expire=3600)
        
    return user

def create_user(db: Any, user: UserCreate):
    password_bytes = user.password.encode('utf-8')
    if len(password_bytes) > 71:
        password_bytes = password_bytes[:71]
    safe_password = password_bytes.decode('utf-8', 'ignore')
    
    try:
        # Use transaction to ensure commit
        pwd_hash = Hasher.get_password_hash(safe_password)
        created_at = datetime.now()
        rs = db_execute_commit(
            db,
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?) RETURNING *",
            [user.username, pwd_hash, user.role, created_at]
        )
        new_user = fetch_one(rs)
            
        if new_user:
             cache_service.set_cache(user_cache_key(new_user.username), new_user.__dict__, expire=3600)
        return new_user
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise

# --- Persona ---
def create_persona(db, persona: PersonaCreate, owner_id: int):
    try:
        theories_json = json.dumps(persona.theories)
        skills = persona.skills or ["chat.reply"]
        modalities = persona.modalities or ["text"]
        skill_policy = persona.skill_policy or {}
        created_at = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO personas (
                owner_id, name, title, bio, theories, stance, system_prompt, is_public,
                avatar, skills, skill_policy, modalities, capabilities_version, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                owner_id,
                persona.name,
                persona.title,
                persona.bio,
                theories_json,
                persona.stance,
                persona.system_prompt,
                persona.is_public,
                persona.avatar,
                json.dumps(skills),
                json.dumps(skill_policy),
                json.dumps(modalities),
                persona.capabilities_version or 1,
                created_at
            ]
        )
        new_persona = fetch_one(rs)
        new_persona = _normalize_persona(new_persona)
        if new_persona:
            _sync_persona_skill_bindings(db, new_persona.id, new_persona.skills, new_persona.skill_policy)
            
        # Cache Aside: Don't set cache on create. Let the first read populate it.
        # This ensures strict adherence to "DB is source of truth" and lazy loading.
        
        return new_persona
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise

def get_persona(db, persona_id: int):
    cache_key = persona_cache_key(persona_id)
    cached = cache_service.get_cache(cache_key)
    if cached:
        return RowObject(cached)

    rs = db.execute("SELECT * FROM personas WHERE id = ?", [persona_id])
    persona = _normalize_persona(fetch_one(rs))
    if persona:
        cache_service.set_cache(cache_key, persona.__dict__)
    return persona

def update_persona(db, persona_id: int, updates: PersonaUpdate):
    try:
        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            return get_persona(db, persona_id)

        set_clauses = []
        values = []
        for key, value in update_data.items():
            set_clauses.append(f"{key} = ?")
            if key in {"theories", "skills", "modalities", "skill_policy"}:
                values.append(json.dumps(value))
            else:
                values.append(value)
        
        values.append(persona_id)
        query = f"UPDATE personas SET {', '.join(set_clauses)} WHERE id = ? RETURNING *"
        
        rs = db_execute_commit(db, query, values)
        updated = _normalize_persona(fetch_one(rs))
        if updated and ("skills" in update_data or "skill_policy" in update_data):
            _sync_persona_skill_bindings(db, persona_id, updated.skills, updated.skill_policy)
        
        # Sync Strategy: Delete Redis Key on Update
        if updated:
            cache_service.delete_cache(persona_cache_key(persona_id))
            
        return updated
    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        raise


def _skill_key_to_id(db, skill_key: str) -> Optional[int]:
    rs = db.execute("SELECT id FROM skills WHERE skill_key = ?", [skill_key])
    row = fetch_one(rs)
    return row.id if row else None


def _sync_persona_skill_bindings(db, persona_id: int, skills: Optional[list[str]], policy: Optional[dict] = None):
    try:
        resolved_skills = [s for s in (skills or ["chat.reply"]) if str(s).strip()]
        policy = policy or {}

        with db_transaction(db) as tx:
            tx.execute("DELETE FROM persona_skill_bindings WHERE persona_id = ?", [persona_id])
            for index, skill_key in enumerate(resolved_skills):
                skill_id = _skill_key_to_id(tx, skill_key)
                if not skill_id:
                    continue
                tx.execute(
                    """
                    INSERT INTO persona_skill_bindings (persona_id, skill_id, enabled, priority, policy)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (persona_id, skill_id) DO UPDATE SET
                        enabled = excluded.enabled,
                        priority = excluded.priority,
                        policy = excluded.policy
                    """,
                    [persona_id, skill_id, True, index, json.dumps(policy.get(skill_key, {}))],
                )
        return True
    except Exception as e:
        logger.error(f"Error syncing persona skill bindings: {e}")
        return False

def delete_persona(db, persona_id: int):
    try:
        # Check if exists first to ensure idempotency and clear error
        rs_check = db.execute("SELECT id FROM personas WHERE id = ?", [persona_id])
        if not fetch_one(rs_check):
            return False

        with db_transaction(db) as tx:
            # Manually set persona_id to NULL in messages to avoid FK violation
            tx.execute("UPDATE messages SET persona_id = NULL WHERE persona_id = ?", [persona_id])
            
            # Cascading deletes should be handled by DB foreign keys, 
            # but let's be explicit if needed or just execute
            rs = tx.execute("DELETE FROM personas WHERE id = ?", [persona_id])
            
            # FORCE COMMIT
            if hasattr(tx, 'commit'):
                tx.commit()
            elif hasattr(db, 'commit'):
                db.commit()
            
        # Sync Strategy: Delete Redis Key on Delete
        cache_service.delete_cache(persona_cache_key(persona_id))
            
        return True
    except Exception as e:
        logger.error(f"Error deleting persona {persona_id}: {e}")
        raise


def list_skills(db):
    rs = db.execute("SELECT * FROM skills ORDER BY category, skill_key ASC", [])
    return fetch_all(rs)


def save_chat_attachments(db, chat_message_id: int, attachment_ids: list[int]):
    saved = []
    for attachment_id in attachment_ids or []:
        linked = link_attachment_to_message(db, attachment_id, chat_message_id)
        if linked:
            saved.append(linked)
    return saved


def get_skill_by_key(db, skill_key: str):
    rs = db.execute("SELECT * FROM skills WHERE skill_key = ?", [skill_key])
    return fetch_one(rs)


def create_skill(db, skill: SkillCreate):
    try:
        created_at = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO skills (
                skill_key, name, category, description, input_modalities, output_types,
                required_models, required_tools, params_schema, permission_scope,
                cost_level, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(skill_key) DO UPDATE SET
                name = excluded.name,
                category = excluded.category,
                description = excluded.description,
                input_modalities = excluded.input_modalities,
                output_types = excluded.output_types,
                required_models = excluded.required_models,
                required_tools = excluded.required_tools,
                params_schema = excluded.params_schema,
                permission_scope = excluded.permission_scope,
                cost_level = excluded.cost_level,
                status = excluded.status,
                updated_at = excluded.updated_at
            RETURNING *
            """,
            [
                skill.skill_key,
                skill.name,
                skill.category,
                skill.description,
                json.dumps(skill.input_modalities),
                json.dumps(skill.output_types),
                json.dumps(skill.required_models),
                json.dumps(skill.required_tools),
                json.dumps(skill.params_schema),
                json.dumps(skill.permission_scope),
                skill.cost_level,
                skill.status,
                created_at,
                created_at,
            ],
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating skill: {e}")
        raise


def create_attachment(db, attachment: AttachmentCreate):
    try:
        created_at = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO attachments (
                owner_id, persona_id, chat_message_id, session_id, file_name,
                mime_type, size, kind, storage_url, preview_url, sha256, meta, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                attachment.owner_id,
                attachment.persona_id,
                attachment.chat_message_id,
                attachment.session_id,
                attachment.file_name,
                attachment.mime_type,
                attachment.size,
                attachment.kind,
                attachment.storage_url,
                attachment.preview_url,
                attachment.sha256,
                json.dumps(attachment.meta or {}),
                created_at,
            ],
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating attachment: {e}")
        raise


def link_attachment_to_message(db, attachment_id: int, chat_message_id: int):
    try:
        rs = db_execute_commit(
            db,
            "UPDATE attachments SET chat_message_id = ? WHERE id = ? RETURNING *",
            [chat_message_id, attachment_id],
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error linking attachment {attachment_id} to message {chat_message_id}: {e}")
        raise


def list_attachments_for_message(db, chat_message_id: int):
    rs = db.execute("SELECT * FROM attachments WHERE chat_message_id = ? ORDER BY created_at ASC", [chat_message_id])
    return fetch_all(rs)


def get_attachment(db, attachment_id: int):
    rs = db.execute("SELECT * FROM attachments WHERE id = ?", [attachment_id])
    return fetch_one(rs)


def create_artifact(db, artifact: ArtifactCreate):
    try:
        created_at = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO artifacts (
                owner_id, persona_id, task_run_id, artifact_type, file_name,
                mime_type, storage_url, preview_url, version, status, meta, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                artifact.owner_id,
                artifact.persona_id,
                artifact.task_run_id,
                artifact.artifact_type,
                artifact.file_name,
                artifact.mime_type,
                artifact.storage_url,
                artifact.preview_url,
                artifact.version,
                artifact.status,
                json.dumps(artifact.meta or {}),
                created_at,
            ],
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating artifact: {e}")
        raise


def get_artifact(db, artifact_id: int):
    rs = db.execute("SELECT * FROM artifacts WHERE id = ?", [artifact_id])
    return fetch_one(rs)


def create_task_run(db, task_run: TaskRunCreate):
    try:
        started_at = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO task_runs (
                owner_id, persona_id, skill_key, session_id, status, progress,
                input_payload, output_payload, error_message, started_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                task_run.owner_id,
                task_run.persona_id,
                task_run.skill_key,
                task_run.session_id,
                task_run.status,
                task_run.progress,
                json.dumps(task_run.input_payload or {}),
                json.dumps(task_run.output_payload or {}),
                task_run.error_message,
                started_at,
            ],
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating task run: {e}")
        raise


def update_task_run(db, task_run_id: int, updates: TaskRunUpdate):
    try:
        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            return get_task_run(db, task_run_id)

        set_clauses = []
        values = []
        for key, value in update_data.items():
            set_clauses.append(f"{key} = ?")
            if key in {"input_payload", "output_payload"}:
                values.append(json.dumps(value))
            else:
                values.append(value)

        if "status" in update_data and update_data["status"] in {"done", "failed", "cancelled"}:
            set_clauses.append("finished_at = ?")
            values.append(datetime.now())

        values.append(task_run_id)
        query = f"UPDATE task_runs SET {', '.join(set_clauses)} WHERE id = ? RETURNING *"
        rs = db_execute_commit(db, query, values)
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error updating task run {task_run_id}: {e}")
        raise


def get_task_run(db, task_run_id: int):
    rs = db.execute("SELECT * FROM task_runs WHERE id = ?", [task_run_id])
    return fetch_one(rs)

# --- Forum ---
def create_forum(db, forum: ForumCreate, creator_id: int):
    try:
        with db_transaction(db) as tx:
            start_time = datetime.now()
            rs = tx.execute(
                """
                INSERT INTO forums (topic, creator_id, moderator_id, status, duration_minutes, start_time, summary_history)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                [
                    forum.topic,
                    creator_id,
                    forum.moderator_id,
                    "pending",
                    forum.duration_minutes,
                    start_time,
                    "[]"
                ]
            )
            db_forum = fetch_one(rs)

            tx.execute("DELETE FROM messages WHERE forum_id = ?", [db_forum.id])
            tx.execute("DELETE FROM forum_participants WHERE forum_id = ?", [db_forum.id])
            tx.execute("DELETE FROM system_logs WHERE forum_id = ?", [db_forum.id])

            if forum.participant_ids:
                unique_pids = list(dict.fromkeys(int(pid) for pid in forum.participant_ids))
                values = []
                placeholders = []
                for pid in unique_pids:
                    placeholders.append("(?, ?, ?)")
                    values.extend([db_forum.id, pid, "[]"])

                if values:
                    query = f"INSERT INTO forum_participants (forum_id, persona_id, thoughts_history) VALUES {', '.join(placeholders)} ON CONFLICT (forum_id, persona_id) DO NOTHING"
                    tx.execute(query, values)
            
            # FORCE COMMIT
            if hasattr(tx, 'commit'):
                tx.commit()
            elif hasattr(db, 'commit'):
                db.commit()

        # Return full object (will trigger cache set in get_forum)
        return get_forum(db, db_forum.id)
    except Exception as e:
        logger.error(f"Error creating forum: {e}")
        raise

def delete_forum(db, forum_id: int):
    logger.info(f"Attempting to delete forum {forum_id}")
    try:
        with db_transaction(db) as tx:
            tx.execute("DELETE FROM messages WHERE forum_id = ?", [forum_id])
            tx.execute("DELETE FROM forum_participants WHERE forum_id = ?", [forum_id])
            tx.execute("DELETE FROM system_logs WHERE forum_id = ?", [forum_id])
            rs = tx.execute("DELETE FROM forums WHERE id = ?", [forum_id])
            
            affected = rs.rows_affected if hasattr(rs, 'rows_affected') else -1
            logger.info(f"Deleted forum {forum_id}, rows affected: {affected}")
            
            # FORCE COMMIT
            if hasattr(tx, 'commit'):
                tx.commit()
                logger.info("Transaction committed explicitly")
            elif hasattr(db, 'commit'):
                db.commit()
                logger.info("DB committed explicitly")
                
            success = affected > 0 if affected != -1 else True
            
            return success
    except Exception as e:
        logger.error(f"Error deleting forum: {e}")
        raise

def get_forum(db, forum_id: int):
    rs = db.execute("SELECT * FROM forums WHERE id = ?", [forum_id])
    forum = fetch_one(rs)
    forum = _normalize_forum(forum)
    if not forum:
        return None
        
    participants = get_forum_participants(db, forum_id)
    setattr(forum, "participants", participants)
    
    if forum.moderator_id:
        mod_rs = db.execute("SELECT * FROM moderators WHERE id = ?", [forum.moderator_id])
        setattr(forum, "moderator", fetch_one(mod_rs))
    else:
        setattr(forum, "moderator", None)
        
    return forum

def update_forum(db, forum_id: int, summary_history: list = None, status: str = None):
    try:
        set_clauses = []
        values = []
        
        if summary_history is not None:
            set_clauses.append("summary_history = ?")
            values.append(json.dumps(summary_history))
            
        if status is not None:
            set_clauses.append("status = ?")
            values.append(status)
            
        if not set_clauses:
            return get_forum(db, forum_id)
            
        values.append(forum_id)
        query = f"UPDATE forums SET {', '.join(set_clauses)} WHERE id = ? RETURNING *"
        
        rs = db_execute_commit(db, query, values)
        updated = fetch_one(rs)
        
        return updated
    except Exception as e:
        logger.error(f"Error updating forum: {e}")
        raise

def get_forum_participants(db, forum_id: int):
    query = """
    SELECT fp.*, p.name as persona_name, p.title as persona_title, p.bio as persona_bio, 
           p.theories as persona_theories, p.stance as persona_stance, 
           p.system_prompt as persona_system_prompt, p.owner_id as persona_owner_id,
           p.created_at as persona_created_at
    FROM forum_participants fp
    JOIN personas p ON fp.persona_id = p.id
    WHERE fp.forum_id = ?
    """
    rs = db.execute(query, [forum_id])
    rows = fetch_all(rs)
    
    results = []
    for row in rows:
        persona_data = {
            "id": row.persona_id,
            "name": row.persona_name,
            "title": row.persona_title,
            "bio": row.persona_bio,
            "theories": _maybe_parse_json(row.persona_theories),
            "stance": row.persona_stance,
            "system_prompt": row.persona_system_prompt,
            "owner_id": row.persona_owner_id,
            "created_at": row.persona_created_at
        }
        setattr(row, "persona", RowObject(persona_data))
        results.append(row)
    return results

def update_forum_participant(db, forum_id: int, persona_id: int, thoughts_history: list = None):
    try:
        if thoughts_history is None:
            return None
            
        query = "UPDATE forum_participants SET thoughts_history = ? WHERE forum_id = ? AND persona_id = ? RETURNING *"
        rs = db_execute_commit(db, query, [json.dumps(thoughts_history), forum_id, persona_id])
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error updating participant: {e}")
        raise

def create_message(db, message: MessageCreate):
    try:
        timestamp = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO messages (forum_id, persona_id, moderator_id, speaker_name, content, turn_count, thought, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [
                message.forum_id,
                message.persona_id,
                message.moderator_id,
                message.speaker_name,
                message.content,
                message.turn_count,
                message.thought,
                timestamp
            ]
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise

def get_forum_messages(db, forum_id: int):
    rs = db.execute("SELECT * FROM messages WHERE forum_id = ? ORDER BY timestamp ASC", [forum_id])
    return fetch_all(rs)

# --- Chat Messages (时空之门单聊历史) ---
def save_chat_message(
    db,
    user_id: int,
    persona_id: int,
    role: str,
    content: str,
    message_type: str = "text",
    metadata: Optional[dict] = None,
):
    """保存单聊消息"""
    try:
        created_at = datetime.now()
        rs = db_execute_commit(
            db,
            """
            INSERT INTO chat_messages (user_id, persona_id, role, message_type, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            [user_id, persona_id, role, message_type, content, json.dumps(metadata or {}), created_at]
        )
        return fetch_one(rs)
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        raise

def get_chat_history(db, user_id: int, persona_id: int):
    """获取用户与指定智能体的聊天历史"""
    rs = db.execute(
        "SELECT * FROM chat_messages WHERE user_id = ? AND persona_id = ? ORDER BY created_at ASC",
        [user_id, persona_id]
    )
    history = fetch_all(rs)
    for message in history:
        setattr(message, "attachments", list_attachments_for_message(db, message.id))
    return history

def clear_chat_history(db, user_id: int, persona_id: int):
    """清空用户与指定智能体的聊天历史"""
    try:
        rs = db_execute_commit(
            db,
            "DELETE FROM chat_messages WHERE user_id = ? AND persona_id = ?",
            [user_id, persona_id]
        )
        return rs is not None
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise



# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import time
from pyrogram import enums, filters, types

from ishu import anon, app, config, db, logger, userbot

# Cache to avoid duplicate log notifications within 30 seconds for the same chat
_recently_logged_chats = {}


def _clean_recent_cache():
    """Prune entries older than 60 seconds from the cache."""
    now = time.time()
    stale = [cid for cid, ts in _recently_logged_chats.items() if now - ts > 60]
    for cid in stale:
        _recently_logged_chats.pop(cid, None)


@app.on_chat_member_updated()
async def bot_chat_member_updated_handler(_, chat_member_updated: types.ChatMemberUpdated):
    try:
        chat = chat_member_updated.chat
        if not chat:
            return

        new_member = chat_member_updated.new_chat_member
        old_member = chat_member_updated.old_chat_member

        target_user = (new_member.user if new_member else None) or (old_member.user if old_member else None)
        if not target_user:
            return

        # Check if the event is for the Bot itself
        is_bot = (target_user.id == app.id)

        # Check if the event is for one of the assistant userbots
        assistant_ids = [ub.id for ub in getattr(userbot, "clients", []) if hasattr(ub, "id") and ub.id]
        is_assistant = (target_user.id in assistant_ids)

        if not (is_bot or is_assistant):
            return

        old_status = old_member.status if old_member else enums.ChatMemberStatus.MEMBER
        new_status = new_member.status if new_member else enums.ChatMemberStatus.LEFT

        # Only process if bot/assistant was removed (BANNED or LEFT)
        if new_status not in (enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT):
            return

        if old_status in (enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT):
            return  # Was already banned or left

        # Deduplication check
        _clean_recent_cache()
        now = time.time()
        cache_key = f"{chat.id}_{target_user.id}"
        if cache_key in _recently_logged_chats and (now - _recently_logged_chats[cache_key] < 30):
            return
        _recently_logged_chats[cache_key] = now

        # Perform cleanup in DB & active calls
        if is_bot:
            await db.rm_chat(chat.id)
            try:
                await anon.stop(chat.id)
            except Exception:
                pass

        # Determine action title and emoji
        if new_status == enums.ChatMemberStatus.BANNED:
            action_tag = "#BOT_KICKED" if is_bot else "#ASSISTANT_KICKED"
            action_name = "Kicked / Banned"
            emoji = "🚨"
        else:
            action_tag = "#BOT_REMOVED" if is_bot else "#ASSISTANT_REMOVED"
            action_name = "Removed / Left"
            emoji = "⚠️"

        # Performer info
        from_user = chat_member_updated.from_user
        if from_user:
            by_user_mention = from_user.mention
            by_user_id = from_user.id
            by_user_username = f"@{from_user.username}" if from_user.username else "No Username"
        else:
            by_user_mention = "Unknown User / System"
            by_user_id = "N/A"
            by_user_username = "N/A"

        # Chat details
        chat_title = chat.title or "Unknown Chat"
        chat_id = chat.id
        chat_username = f"@{chat.username}" if chat.username else "Private Group"
        chat_type = str(chat.type).replace("ChatType.", "").title()

        # Members count
        try:
            members_count = await app.get_chat_members_count(chat.id)
        except Exception:
            members_count = getattr(chat, "members_count", "N/A")

        # Entity info
        entity_label = "Bot" if is_bot else "Assistant"
        entity_name = target_user.first_name or (app.name if is_bot else "Userbot")
        entity_username = f"@{target_user.username}" if target_user.username else "No Username"
        entity_id = target_user.id

        old_status_str = str(old_status).replace("ChatMemberStatus.", "").title()
        new_status_str = str(new_status).replace("ChatMemberStatus.", "").title()

        log_text = (
            f"{emoji} <b><u>{action_tag} NOTIFICATION</u></b>\n\n"
            f"📌 <b><u>Group Information:</u></b>\n"
            f"<b>• Title:</b> {chat_title}\n"
            f"<b>• Chat ID:</b> <code>{chat_id}</code>\n"
            f"<b>• Username:</b> {chat_username}\n"
            f"<b>• Type:</b> {chat_type}\n"
            f"<b>• Total Members:</b> {members_count}\n\n"
            f"👤 <b><u>Action Performed By:</u></b>\n"
            f"<b>• User:</b> {by_user_mention}\n"
            f"<b>• User ID:</b> <code>{by_user_id}</code>\n"
            f"<b>• Username:</b> {by_user_username}\n\n"
            f"🤖 <b><u>{entity_label} Details:</u></b>\n"
            f"<b>• Name:</b> {entity_name}\n"
            f"<b>• Username:</b> {entity_username}\n"
            f"<b>• ID:</b> <code>{entity_id}</code>\n"
            f"<b>• Old Status:</b> <code>{old_status_str}</code>\n"
            f"<b>• New Status:</b> <code>{new_status_str}</code>\n"
            f"<b>• Action:</b> <b>{action_name}</b>"
        )

        await app.send_message(chat_id=app.logger, text=log_text)

    except Exception as e:
        logger.error(f"Error in bot kick/remove logger: {e}")


@app.on_message(filters.left_chat_member)
async def bot_left_chat_message_handler(_, message: types.Message):
    try:
        left_member = message.left_chat_member
        if not left_member or left_member.id != app.id:
            return

        chat = message.chat
        _clean_recent_cache()
        now = time.time()
        cache_key = f"{chat.id}_{left_member.id}"
        if cache_key in _recently_logged_chats and (now - _recently_logged_chats[cache_key] < 30):
            return
        _recently_logged_chats[cache_key] = now

        # Perform cleanup in DB & active calls
        await db.rm_chat(chat.id)
        try:
            await anon.stop(chat.id)
        except Exception:
            pass

        from_user = message.from_user
        if from_user:
            by_user_mention = from_user.mention
            by_user_id = from_user.id
            by_user_username = f"@{from_user.username}" if from_user.username else "No Username"
        else:
            by_user_mention = "Unknown User / System"
            by_user_id = "N/A"
            by_user_username = "N/A"

        chat_title = chat.title or "Unknown Chat"
        chat_id = chat.id
        chat_username = f"@{chat.username}" if chat.username else "Private Group"
        chat_type = str(chat.type).replace("ChatType.", "").title()

        try:
            members_count = await app.get_chat_members_count(chat.id)
        except Exception:
            members_count = getattr(chat, "members_count", "N/A")

        log_text = (
            f"⚠️ <b><u>#BOT_REMOVED NOTIFICATION</u></b>\n\n"
            f"📌 <b><u>Group Information:</u></b>\n"
            f"<b>• Title:</b> {chat_title}\n"
            f"<b>• Chat ID:</b> <code>{chat_id}</code>\n"
            f"<b>• Username:</b> {chat_username}\n"
            f"<b>• Type:</b> {chat_type}\n"
            f"<b>• Total Members:</b> {members_count}\n\n"
            f"👤 <b><u>Action Performed By:</u></b>\n"
            f"<b>• User:</b> {by_user_mention}\n"
            f"<b>• User ID:</b> <code>{by_user_id}</code>\n"
            f"<b>• Username:</b> {by_user_username}\n\n"
            f"🤖 <b><u>Bot Details:</u></b>\n"
            f"<b>• Name:</b> {app.name}\n"
            f"<b>• Username:</b> @{app.username}\n"
            f"<b>• ID:</b> <code>{app.id}</code>\n"
            f"<b>• Action:</b> <b>Removed / Left</b>"
        )

        await app.send_message(chat_id=app.logger, text=log_text)

    except Exception as e:
        logger.error(f"Error in left_chat_member message handler: {e}")

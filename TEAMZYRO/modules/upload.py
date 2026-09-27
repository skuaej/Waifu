# ==========================================
# Simplified Upload - Only posts to Telegram Channel
# No external hosts (ImgBB/Catbox)
# ==========================================

import os
import asyncio
from pyrogram import filters
from TEAMZYRO import DATABASE_ID, collection, rarity_map, ZYRO, require_power
from TEAMZYRO.unit.zyro_rarity import get_event_display

WRONG_FORMAT_TEXT = """Wrong ❌ format...  
eg. /upload reply muzan-kibutsuji Demon-slayer 3
eg. /upload reply muzan-kibutsuji Demon-slayer 3 erotic

format:- /upload reply character-name anime-name rarity-number [event-type]
"""

async def find_available_id():
    cursor = collection.find().sort('id', 1)
    ids = []
    async for doc in cursor:
        if 'id' in doc:
            ids.append(int(doc['id']))
    ids.sort()
    for i in range(1, len(ids) + 2):
        if i not in ids:
            return str(i).zfill(2)
    return str(len(ids) + 1).zfill(2)


upload_lock = asyncio.Lock()

@ZYRO.on_message(filters.command(["gupload", "u", "upload"]))
@require_power("add")
async def ul_main(client, message):
    if upload_lock.locked():
        return await message.reply_text("Another upload is in progress. Please wait...")

    async with upload_lock:
        reply = message.reply_to_message
        if not reply or not (reply.photo or reply.document or reply.video):
            return await message.reply_text("Please reply to a photo, document, or video.")

        args = message.text.split()
        if len(args) < 4 or len(args) > 5:
            return await message.reply_text(WRONG_FORMAT_TEXT)

        character_name = args[1].replace('-', ' ').title()
        anime = args[2].replace('-', ' ').title()
        rarity = int(args[3])
        event_type = args[4].replace('-', ' ').upper() if len(args) == 5 else None

        if rarity not in rarity_map:
            return await message.reply_text(f"Invalid rarity. Use 1-{len(rarity_map)}")

        rarity_text = rarity_map[rarity]
        available_id = await find_available_id()

        character = {
            'name': character_name,
            'anime': anime,
            'rarity': rarity_text,
            'id': available_id
        }
        if event_type:
            character['event'] = event_type
            character['type'] = event_type

        processing = await message.reply("<ᴘʀᴏᴄᴇꜱꜱɪɴɢ>....")
        path = await reply.download()

        try:
            # Convert DATABASE_ID safely
            actual_chat_id = int(DATABASE_ID) if str(DATABASE_ID).lstrip('-').isdigit() else DATABASE_ID

            caption_lines = [
                f"**Character Name:** {character_name}",
                f"**Anime Name:** {anime}",
                f"**Rarity:** {rarity_text}",
                f"**ID:** {available_id}"
            ]
            if event_type:
                caption_lines.append(f"**Event:** {get_event_display(event_type)}")
            caption = "\n".join(caption_lines)

            # ========== Send local file to Telegram channel ==========
            if reply.photo or reply.document:
                sent = await client.send_photo(
                    chat_id=actual_chat_id,
                    photo=path,
                    caption=caption
                )
                # Optional: save Telegram file_id (works as long as the message exists)
                character['img_url'] = sent.photo.file_id if sent.photo else None

            elif reply.video:
                sent = await client.send_video(
                    chat_id=actual_chat_id,
                    video=path,
                    caption=caption
                )
                character['vid_url'] = sent.video.file_id if sent.video else None
            # ========================================================

            await collection.insert_one(character)
            await processing.delete()

            reply_txt = f"➥ **Character ID:** `{available_id}`\n➥ **Rarity:** {rarity_text}"
            if event_type:
                reply_txt += f"\n➥ **Event:** {get_event_display(event_type)}"
            await message.reply_text(reply_txt)

        except Exception as e:
            await processing.edit_text(f"Character Upload Unsuccessful. Error: {str(e)}")
        finally:
            try:
                os.remove(path)
            except:
                pass

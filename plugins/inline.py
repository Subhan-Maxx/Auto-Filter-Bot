import logging
from pyrogram import Client, emoji, filters
from pyrogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    InlineQueryResultArticle, 
    InputTextMessageContent
)
from pyrogram.enums import ChatType
from database.ia_filterdb import get_search_results  # Aapka db.py file path
from utils import get_size, temp  # get_size function database files ke liye

CACHE_TIME = 300

logger = logging.getLogger(__name__)


@Client.on_inline_query()
async def answer(bot, query):
    """Show search results for given inline query"""
    
    # 1. Chat Type Check: Sirf Bot ke PM (private) me allow karega
    is_private_inline = query.chat_type in (ChatType.PRIVATE, ChatType.SENDER)

    if not is_private_inline:
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text='⚠️ Work only in PM',
            switch_pm_parameter="help"
        )
        return

    results = []
    if '|' in query.query:
        text, file_type = query.query.split('|', maxsplit=1)
        text = text.strip()
        file_type = file_type.strip().lower()
    else:
        text = query.query.strip()
        file_type = None

    offset = int(query.offset or 0)
    
    # 2. Database Compatibility: Naye db.py ke mutabik chat_id pass kiya aur total nikal liya
    # Note: PM query me chat_id None bhej rahe hain taaki default max_results=10 set ho jaye
    files, next_offset, total = await get_search_results(
        chat_id=None, 
        query=text, 
        file_type=file_type, 
        max_results=10, 
        offset=offset
    )

    # Bot username fetch karne ke liye fallback ke sath
    bot_username = getattr(temp, "U_NAME", bot.username)

    for file in files:
        # PM Deep Link generation using file_id (Umongo models return dict or object attribute)
        file_id = getattr(file, "file_id", file.get('file_id') if isinstance(file, dict) else '')
        file_name = getattr(file, "file_name", file.get('file_name') if isinstance(file, dict) else 'Unknown')
        file_size = getattr(file, "file_size", file.get('file_size') if isinstance(file, dict) else 0)
        file_type_str = getattr(file, "file_type", file.get('file_type') if isinstance(file, dict) else 'Unknown')
        caption = getattr(file, "caption", file.get('caption') if isinstance(file, dict) else '')

        pm_link = f"https://t.me{bot_username}?start=file_{file_id}"
        
        # 3. Only Get File & Search Again Buttons
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Get File", url=pm_link)],
            [InlineKeyboardButton("🔍 Search again", switch_inline_query_current_chat=text)]
        ])

        # Message interface format jo user select karega
        input_content = InputTextMessageContent(
            f"<b>📌 Title:</b> <code>{file_name}</code>\n"
            f"<b>📦 Size:</b> {get_size(file_size)}\n\n"
            f"<i>Click below to get your file in Bot PM!</i>"
        )

        results.append(
            InlineQueryResultArticle(
                id=f"file-{file_id}",
                title=f"{file_name}",
                description=f"Size: {get_size(file_size)} | Type: {file_type_str}",
                input_message_content=input_content,
                reply_markup=reply_markup
            )
        )

    if results:
        # Top par result counting ke sath message header update hoga
        switch_pm_text = f"{emoji.FILE_FOLDER} Results - {total}"
        if text:
            switch_pm_text += f" for {text}"

        await query.answer(
            results=results,
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="start",
            next_offset=str(next_offset)
        )
    else:
        switch_pm_text = f'{emoji.CROSS_MARK} No results'
        if text:
            switch_pm_text += f' for "{text}"'

        await query.answer(
            results=[],
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="okay",
        )
        

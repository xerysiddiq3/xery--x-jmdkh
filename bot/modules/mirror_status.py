from psutil import cpu_percent, net_io_counters, virtual_memory, disk_usage
from time import time
from threading import Thread
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import dispatcher, status_reply_dict_lock, download_dict, download_dict_lock, botStartTime, DOWNLOAD_DIR, Interval, DOWNLOAD_STATUS_UPDATE_INTERVAL, status_reply_dict, STORAGE_THRESHOLD
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, auto_delete_message, sendStatusMessage, update_all_messages
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, turn, setInterval, new_thread, MirrorStatus
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands


def mirror_status(update, context):
    with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        currentTime = get_readable_time(time() - botStartTime)
        free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
        message = 'No Active Downloads !\n'
        message += f"\n<b>Free</b>: {free} | <b>Uptime</b>: {currentTime}"
        reply_message = sendMessage(message, context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, reply_message)).start()
    else:
        sendStatusMessage(update.message, context.bot)
        deleteMessage(context.bot, update.message)
        with status_reply_dict_lock:
            try:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
            except:
                pass
            finally:
                Interval.append(setInterval(DOWNLOAD_STATUS_UPDATE_INTERVAL, update_all_messages))

@new_thread
def status_pages(update, context):
    query = update.callback_query
    with download_dict_lock:
        if len(download_dict) != 0:
            with status_reply_dict_lock:
                if not status_reply_dict or not Interval or time() - list(status_reply_dict.values())[0][1] < 2:
                    query.answer(text="Wait One More Second!\n\nI am not your girlfriend", show_alert=True)
                    return
    data = query.data
    data = data.split()
    if data[1] == "ref":
        query.answer()
        update_all_messages(True)
        return
    elif data[1] =='stats':
        stat = bot_sys_stats()
        if stat:
            query.answer(text=stat, show_alert=True)
        else:
            query.answer(text="This status is old now.\n\nI am deleting it.", show_alert=True)
            query.message.delete()
        return
    done = turn(data)
    if done:
        query.answer()
        update_all_messages(True)
    else:
        query.answer(text="This status is old now.\n\nI am deleting it.", show_alert=True)
        query.message.delete()

def bot_sys_stats():
    with download_dict_lock:
        if len(download_dict) == 0:
            return
        active = upload = extract = archive = split = dsize = 0
        for stats in list(download_dict.values()):
            if stats.status() == MirrorStatus.STATUS_DOWNLOADING:
                active += 1
                dsize += stats.processed_bytes()
            if stats.status() == MirrorStatus.STATUS_UPLOADING:
                upload += 1
            if stats.status() == MirrorStatus.STATUS_EXTRACTING:
                extract += 1
            if stats.status() == MirrorStatus.STATUS_ARCHIVING:
                archive += 1
            if stats.status() == MirrorStatus.STATUS_SPLITTING:
                split += 1
        status_ls = f"ZIP: {archive} | UZIP: {extract} | SPLIT: {split}\n" \
                    f"DL: {active} | UP: {upload} | Done: {get_readable_file_size(dsize)}"
        mem = virtual_memory().percent
        recv = get_readable_file_size(net_io_counters().bytes_recv)
        sent = get_readable_file_size(net_io_counters().bytes_sent)
        free = disk_usage(DOWNLOAD_DIR).free
        if STORAGE_THRESHOLD:
            free -= STORAGE_THRESHOLD * 1024**3
        TDlimits = get_readable_file_size(free)
        ZUlimits = get_readable_file_size(free / 2)
        return f"Powered By: xᴇʀʏ sɪᴅᴅɪϙ \n" \
            f"Send: {sent} | Recv: {recv}\n" \
            f"CPU: {cpu_percent()}% | RAM: {mem}%\n\n" \
            f"{status_ls}\n" \
            f"\nLimits: T/D: {TDlimits} | Z/U: {ZUlimits}"

mirror_status_handler = CommandHandler(BotCommands.StatusCommand, mirror_status,
                                       filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

status_pages_handler = CallbackQueryHandler(status_pages, pattern="status", run_async=True)
dispatcher.add_handler(mirror_status_handler)
dispatcher.add_handler(status_pages_handler)

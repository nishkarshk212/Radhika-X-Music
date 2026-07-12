# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import sys
import shutil
import asyncio

from pyrogram import filters, types

from ishu import app, config, db, lang, stop


@app.on_message(filters.command(["logs"]) & app.sudoers)
@lang.language()
async def _logs(_, m: types.Message):
    sent = await m.reply_text(m.lang["log_fetch"])
    if not os.path.exists("log.txt"):
        return await sent.edit_text(m.lang["log_not_found"])
    await sent.edit_media(
        media=types.InputMediaDocument(
            media="log.txt",
            caption=m.lang["log_sent"].format(app.name),
        )
    )


@app.on_message(filters.command(["logger"]) & app.sudoers)
@lang.language()
async def _logger(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))
    if m.command[1] not in ("on", "off"):
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))

    if m.command[1] == "on":
        await db.set_logger(True)
        await m.reply_text(m.lang["logger_on"])
    else:
        await db.set_logger(False)
        await m.reply_text(m.lang["logger_off"])


@app.on_message(filters.command(["restart"]) & app.sudoers)
@lang.language()
async def _restart(_, m: types.Message):
    sent = await m.reply_text(m.lang["restarting"])

    for directory in ["cache", "downloads"]:
        shutil.rmtree(directory, ignore_errors=True)

    await sent.edit_text(m.lang["restarted"])
    task = asyncio.create_task(stop())
    await task

    try: os.remove("log.txt")
    except Exception: pass

    os.execl(sys.executable, sys.executable, "-m", "ishu")


@app.on_message(filters.command(["update"]) & app.sudoers)
@lang.language()
async def _update(_, m: types.Message):
    # Owner only: git pull + auto restart
    if m.from_user.id != config.OWNER_ID:
        return await m.reply_text("This command is restricted to the bot owner.")

    sent = await m.reply_text("Updating from git repository...")
    try:
        proc = await asyncio.create_subprocess_shell(
            "git fetch origin && git reset --hard origin/main",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = (stdout.decode().strip() + "\n" + stderr.decode().strip()).strip()

        if proc.returncode != 0:
            return await sent.edit_text(
                f"Git update failed (exit {proc.returncode}):\n`{output[:1500]}`"
            )

        await sent.edit_text(
            f"Updated from git:\n```{output[-800:]}```\nRestarting bot..."
        )

        for directory in ["cache", "downloads"]:
            shutil.rmtree(directory, ignore_errors=True)

        task = asyncio.create_task(stop())
        await task

        try:
            os.remove("log.txt")
        except Exception:
            pass

        os.execl(sys.executable, sys.executable, "-m", "ishu")
    except Exception as e:
        await sent.edit_text(f"Failed to update or restart:\n`{e}`")

import asyncio
import signal
import importlib
import os
from contextlib import suppress

from ishu import (
    anon,
    app,
    config,
    db,
    logger,
    stop,
    userbot,
    yt,
    thumb,
)

from ishu.plugins import all_modules


async def idle():
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()


async def main():
    await db.connect()

    await app.boot()
    await userbot.boot()
    await anon.boot()

    # Thumbnail initialization
    await thumb.start()

    for module in all_modules:
        importlib.import_module(f"ishu.plugins.{module}")

    logger.info(f"Loaded {len(all_modules)} modules.")

    if config.COOKIES_URL:
        await yt.save_cookies(config.COOKIES_URL)

    # Materialize the base64 cookie (from COOKIE_B64 env) into ishu/cookies/
    if config.COOKIE_B64:
        try:
            import base64
            cookie_dir = os.path.join(os.path.dirname(__file__), "cookies")
            os.makedirs(cookie_dir, exist_ok=True)
            raw = base64.b64decode(config.COOKIE_B64)
            cpath = os.path.join(cookie_dir, "cookie_env.txt")
            with open(cpath, "wb") as _f:
                _f.write(raw)
            logger.info("Decoded COOKIE_B64 → %s", cpath)
        except Exception as exc:
            logger.warning("Failed to decode COOKIE_B64: %s", exc)

    sudoers = await db.get_sudoers()
    app.sudoers.update(sudoers)

    app.bl_users.update(await db.get_blacklisted())

    logger.info(f"Loaded {len(app.sudoers)} sudo users.")

    await idle()
    await stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

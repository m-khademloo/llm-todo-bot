"""Entry point: start bot and scheduler."""
import asyncio

from src.config import Settings
from src.db.database import Database
from src.llm.client import LLMClient
from src.orchestrator.orchestrator import Orchestrator
from src.bot.handlers import create_bot
from src.tools.scheduling_tools import SchedulerService


async def main() -> None:
    """Run setup and bot in the same event loop so Motor (async Mongo) works."""
    settings = Settings()
    db = Database(settings.MONGO_URI, settings.MONGO_DB_NAME)
    await db.setup_indexes()
    llm = LLMClient(model=settings.LLM_MODEL, base_url=settings.LLM_BASE_URL)
    scheduler = SchedulerService(settings.MONGO_URI, settings.MONGO_DB_NAME)
    orchestrator = Orchestrator(db=db, llm=llm, scheduler=scheduler)
    bot = create_bot(settings.TELEGRAM_BOT_TOKEN, orchestrator)
    await scheduler.start(bot)
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

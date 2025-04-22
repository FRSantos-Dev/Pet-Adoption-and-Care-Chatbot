import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import PostgreSQLDatabase
from telegram_bot import (
    start, button, handle_message, error_handler,
    BOT_OWNER_ID, db_config, interview
)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        
        load_dotenv()

        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        if not BOT_OWNER_ID:
            raise ValueError("BOT_OWNER_ID not found in environment variables")
        
        logger.info("Starting bot...")
        
        
        db_manager = PostgreSQLDatabase(db_config)
        
        
        application = Application.builder().token(token).build()

        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_message))
        application.add_error_handler(error_handler)

        
        logger.info("Bot is running...")
        application.run_polling()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
    finally:
        
        db_manager.close()

if __name__ == '__main__':
    main() 
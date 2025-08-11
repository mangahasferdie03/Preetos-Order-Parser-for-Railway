import os
import logging
from telegram.ext import Application
from config import Config
from bot import create_application

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the bot"""
    try:
        # Validate configuration
        Config.validate_config()
        logger.info("Configuration validated successfully")
        
        # Create the application
        application = create_application()
        logger.info("Bot application created successfully")
        
        # Check if we're running on Railway (webhook mode) or locally (polling mode)
        if Config.WEBHOOK_URL:
            # Railway deployment - use webhook
            logger.info(f"Running in webhook mode on port {Config.PORT}")
            
            # Set webhook
            application.run_webhook(
                listen="0.0.0.0",
                port=Config.PORT,
                url_path="/webhook",
                webhook_url=f"{Config.WEBHOOK_URL}/webhook"
            )
        else:
            # Local development - use polling
            logger.info("Running in polling mode (local development)")
            application.run_polling()
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your environment variables in .env file")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == '__main__':
    main()
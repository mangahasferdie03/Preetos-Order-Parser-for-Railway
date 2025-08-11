import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Google Sheets Configuration  
    GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    # Claude AI Configuration
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    
    # Railway Configuration
    PORT = int(os.getenv('PORT', 8000))
    
    # Webhook Configuration (for Railway deployment)
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # e.g., https://your-app.railway.app/webhook
    
    @classmethod
    def validate_config(cls):
        """Validate that all required environment variables are set"""
        missing_vars = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            missing_vars.append('TELEGRAM_BOT_TOKEN')
            
        if not cls.GOOGLE_SHEETS_SPREADSHEET_ID:
            missing_vars.append('GOOGLE_SHEETS_SPREADSHEET_ID')
            
        if not cls.GOOGLE_SERVICE_ACCOUNT_JSON:
            missing_vars.append('GOOGLE_SERVICE_ACCOUNT_JSON')
            
        if not cls.ANTHROPIC_API_KEY:
            missing_vars.append('ANTHROPIC_API_KEY')
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
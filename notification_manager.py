import os
import logging
import smtplib
import telegram
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Configure logger
logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages notifications through email and Telegram."""
    
    def __init__(self, env_file_path):
        """Initialize notification manager.
        
        Args:
            env_file_path: Path to the .env file containing notification settings
        """
        load_dotenv(env_file_path)
        
        # Email settings
        self.enable_email = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'False').lower() == 'true'
        self.email_sender = os.getenv('EMAIL_SENDER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',')
        
        # Telegram settings
        self.enable_telegram = os.getenv('ENABLE_TELEGRAM_NOTIFICATIONS', 'False').lower() == 'true'
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        self._setup_clients()
    
    def _setup_clients(self):
        """Set up notification clients."""
        # Set up Telegram bot if enabled
        if self.enable_telegram:
            try:
                if not self.telegram_bot_token or not self.telegram_chat_id:
                    logger.warning("Telegram notifications enabled but missing credentials.")
                    self.enable_telegram = False
                else:
                    self.telegram_bot = telegram.Bot(token=self.telegram_bot_token)
                    logger.info("Telegram client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram client: {str(e)}")
                self.enable_telegram = False
        
        # Validate email settings if enabled
        if self.enable_email:
            if not self.email_sender or not self.email_password or not self.email_recipients:
                logger.warning("Email notifications enabled but missing credentials.")
                self.enable_email = False
            else:
                logger.info("Email settings validated successfully.")
    
    def send_notification(self, subject, message, notification_type="INFO"):
        """Send notification through configured channels.
        
        Args:
            subject: Notification subject
            message: Notification message
            notification_type: Type of notification (INFO, SUCCESS, ERROR)
        """
        formatted_message = f"[{notification_type}] {subject}\n\n{message}"
        
        if self.enable_email:
            self._send_email(subject, formatted_message)
        
        if self.enable_telegram:
            self._send_telegram(formatted_message)
        
        # Always log the notification
        log_level = logging.ERROR if notification_type == "ERROR" else logging.INFO
        logger.log(log_level, f"Notification: {subject} - {message}")
    
    def _send_email(self, subject, body):
        """Send email notification.
        
        Args:
            subject: Email subject
            body: Email body
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = ', '.join(self.email_recipients)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_sender, self.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
    
    def _send_telegram(self, message):
        """Send Telegram notification.
        
        Args:
            message: Message to send
        """
        try:
            self.telegram_bot.send_message(chat_id=self.telegram_chat_id, text=message)
            logger.info("Telegram notification sent.")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {str(e)}")
    
    def notify_order_placed(self, order_details):
        """Send notification for successful order placement.
        
        Args:
            order_details: Dictionary containing order details
        """
        subject = f"Order Placed: {order_details.get('symbol')}"
        message = f"Order ID: {order_details.get('order_id')}\n"\
                 f"Symbol: {order_details.get('symbol')}\n"\
                 f"Timestamp: {order_details.get('timestamp', 'Not available')}"
        self.send_notification(subject, message, "SUCCESS")
    
    def notify_order_failed(self, order_details, error_message):
        """Send notification for failed order placement.
        
        Args:
            order_details: Dictionary containing order details
            error_message: Error message
        """
        subject = f"Order Failed: {order_details.get('symbol')}"
        message = f"Symbol: {order_details.get('symbol')}\n"\
                 f"Error: {error_message}\n"\
                 f"Timestamp: {order_details.get('timestamp', 'Not available')}"
        self.send_notification(subject, message, "ERROR")
    
    def notify_authentication_failure(self, error_message):
        """Send notification for authentication failure.
        
        Args:
            error_message: Error message
        """
        subject = "Zerodha Authentication Failed"
        message = f"Error: {error_message}\n"\
                 f"Please check your credentials and regenerate access token."
        self.send_notification(subject, message, "ERROR")
import os
import time
import logging
import schedule
import datetime
import pytz
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import custom modules
from auth_manager import ZerodhaAuthManager
from order_manager import ZerodhaOrderManager
from notification_manager import NotificationManager

# Configure logging
def setup_logging(log_dir):
    """Set up logging configuration.
    
    Args:
        log_dir: Directory to store log files
    """
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f"{today}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

class TradeMaster:
    """Main application class for automated trading."""
    
    def __init__(self, config_dir, log_dir):
        """Initialize the application.
        
        Args:
            config_dir: Directory containing configuration files
            log_dir: Directory to store log files
        """
        self.config_dir = config_dir
        self.log_dir = log_dir
        
        # Set up logging
        self.logger = setup_logging(log_dir)
        self.logger.info("Initializing TradeMaster")
        
        # Load configuration
        self.env_file = os.path.join(config_dir, '.env')
        if not os.path.exists(self.env_file):
            self.logger.warning(f"Environment file not found at {self.env_file}")
            self.logger.info(f"Creating .env file from template")
            
            # Create .env file from template if it doesn't exist
            env_template = os.path.join(config_dir, '.env.template')
            if os.path.exists(env_template):
                with open(env_template, 'r') as template_file:
                    template_content = template_file.read()
                with open(self.env_file, 'w') as env_file:
                    env_file.write(template_content)
            else:
                self.logger.error("Environment template file not found")
                raise FileNotFoundError("Environment template file not found")
        
        # Load environment variables
        load_dotenv(self.env_file)
        
        # Initialize components
        self.auth_manager = ZerodhaAuthManager(self.env_file)
        self.notification_manager = NotificationManager(self.env_file)
        
        # Set up Kite client
        try:
            self._setup_kite_client()
        except Exception as e:
            self.logger.error(f"Failed to initialize Kite client: {str(e)}")
            self.notification_manager.notify_authentication_failure(str(e))
            raise
    
    def _setup_kite_client(self):
        """Set up Kite client with valid authentication."""
        if self.auth_manager.is_token_valid():
            self.kite = self.auth_manager.kite
            self.logger.info("Using existing valid access token")
        else:
            self.logger.warning("No valid access token found, regeneration required")
            request_token = os.getenv('REQUEST_TOKEN')
            
            if request_token:
                self.logger.info("Generating access token from saved request token")
                self.auth_manager.generate_access_token_from_request_token(request_token)
                self.kite = self.auth_manager.kite
            else:
                self.logger.error("No request token available. Manual login required")
                self.notification_manager.notify_authentication_failure("No request token available. Manual login required.")
                raise ValueError("No request token available. Manual login required.")
        
        # Initialize order manager with authenticated Kite client
        self.order_manager = ZerodhaOrderManager(self.kite)
    
    def place_scheduled_orders(self):
        """Place orders for all active stocks in the configuration."""
        self.logger.info("Starting scheduled order placement")
        
        # Check if market is open
        ist_timezone = pytz.timezone('Asia/Kolkata')
        current_time = datetime.datetime.now(ist_timezone)
        is_weekday = current_time.weekday() < 5  # Monday to Friday
        
        if not is_weekday:
            self.logger.info("Market closed (weekend). Skipping order placement.")
            return
        
        # Load stock configuration
        stock_config_file = os.path.join(self.config_dir, 'stocks.csv')
        try:
            stock_config = self.order_manager.load_stock_config(stock_config_file)
        except Exception as e:
            error_msg = f"Failed to load stock configuration: {str(e)}"
            self.logger.error(error_msg)
            self.notification_manager.send_notification(
                "Stock Configuration Error", 
                error_msg, 
                "ERROR"
            )
            return
        
        # Place orders for each active stock
        all_results = []
        for index, stock in stock_config.iterrows():
            self.logger.info(f"Processing order for {stock['trading_symbol']}")
            
            # Place the order
            result = self.order_manager.place_order(
                stock,
                retry_attempts=int(os.getenv('RETRY_ATTEMPTS', 3)),
                retry_delay=int(os.getenv('RETRY_DELAY_SECONDS', 2))
            )
            
            # Add timestamp to result
            result['timestamp'] = datetime.datetime.now(ist_timezone).strftime('%Y-%m-%d %H:%M:%S')
            all_results.append(result)
            
            # Send notifications based on order result
            if result['success']:
                self.notification_manager.notify_order_placed(result)
            else:
                self.notification_manager.notify_order_failed(result, result['error'])
        
        self.logger.info(f"Completed scheduled order placement for {len(all_results)} stocks")
        
        # Summary notification
        successful_orders = sum(1 for r in all_results if r['success'])
        failed_orders = len(all_results) - successful_orders
        
        self.notification_manager.send_notification(
            "Order Placement Summary",
            f"Orders placed: {len(all_results)}\n"
            f"Successful: {successful_orders}\n"
            f"Failed: {failed_orders}",
            "INFO"
        )
        
    def start_scheduler(self):
        """Start the scheduler to place orders at specified time."""
        self.logger.info("Starting order scheduler")
        
        # Schedule order placement at 9:30 AM IST
        schedule.every().day.at("09:30").do(self.place_scheduled_orders)
        
        self.logger.info("Scheduler started. Orders will be placed at 09:30 AM IST on trading days")
        self.notification_manager.send_notification(
            "TradeMaster Started", 
            "Order scheduler has been started. Orders will be placed at 09:30 AM IST on trading days.",
            "INFO"
        )
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(1)

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='TradeMaster: Automated trading system for Zerodha')
    parser.add_argument('--config', type=str, default='config',
                        help='Directory containing configuration files')
    parser.add_argument('--logs', type=str, default='logs',
                        help='Directory to store log files')
    parser.add_argument('--run-now', action='store_true',
                        help='Place orders immediately instead of scheduling')
    args = parser.parse_args()
    
    # Resolve paths relative to the script location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, args.config)
    log_dir = os.path.join(base_dir, args.logs)
    
    # Create TradeMaster instance
    trade_master = TradeMaster(config_dir, log_dir)
    
    # Either run immediately or start scheduler
    if args.run_now:
        trade_master.place_scheduled_orders()
    else:
        trade_master.start_scheduler()

if __name__ == "__main__":
    main()
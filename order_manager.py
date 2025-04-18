import os
import logging
import pandas as pd
from datetime import datetime
from kiteconnect import KiteConnect

# Configure logger
logger = logging.getLogger(__name__)

class ZerodhaOrderManager:
    """Manages stock order configuration and placement."""
    
    def __init__(self, kite_client):
        """Initialize order manager.
        
        Args:
            kite_client: Authenticated KiteConnect client
        """
        self.kite = kite_client
        
    def load_stock_config(self, config_file):
        """Load stock configuration from CSV file.
        
        Args:
            config_file: Path to CSV file containing stock configuration
        
        Returns:
            DataFrame: Stock configuration data
        """
        try:
            df = pd.read_csv(config_file)
            required_columns = ['trading_symbol', 'quantity', 'order_type', 'limit_price', 'is_active']
            
            # Validate required columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns in stock config: {missing_columns}")
                raise ValueError(f"Stock config is missing required columns: {missing_columns}")
            
            # Filter out inactive stocks
            active_stocks = df[df['is_active']]
            logger.info(f"Loaded {len(active_stocks)} active stocks from configuration")
            
            return active_stocks
        except Exception as e:
            logger.error(f"Failed to load stock configuration: {str(e)}")
            raise
    
    def place_order(self, stock_entry, retry_attempts=3, retry_delay=2):
        """Place an order for a stock entry.
        
        Args:
            stock_entry: Series containing stock configuration
            retry_attempts: Number of retry attempts if order fails
            retry_delay: Delay in seconds between retry attempts
            
        Returns:
            dict: Order response
        """
        symbol = stock_entry['trading_symbol']
        quantity = int(stock_entry['quantity'])
        order_type = stock_entry['order_type']
        limit_price = float(stock_entry['limit_price']) if order_type == 'LIMIT' else None
        
        logger.info(f"Placing order for {symbol}: {quantity} shares at {order_type}" + 
                   (f" price {limit_price}" if limit_price else ""))
        
        # ESM stocks can only be traded with CNC product type
        try:
            order_params = {
                "tradingsymbol": symbol.split(':')[-1],  # Remove exchange prefix if present
                "exchange": symbol.split(':')[0] if ':' in symbol else "NSE",
                "transaction_type": "BUY",
                "quantity": quantity,
                "product": "CNC",  # ESM stocks allow only CNC
                "order_type": order_type,
            }
            
            # Add price for LIMIT orders
            if order_type == "LIMIT" and limit_price:
                order_params["price"] = limit_price
                
            # Validate margin before placing order
            margin_required = self._check_margin_required(order_params)
            if not self._has_sufficient_margin(margin_required):
                logger.error(f"Insufficient margin for {symbol}. Required: {margin_required}")
                raise ValueError(f"Insufficient margin for {symbol}. Required: {margin_required}")
                
            # Place the order
            order_id = self.kite.place_order(
                variety="regular",
                **order_params
            )
            
            logger.info(f"Order placed successfully for {symbol}. Order ID: {order_id}")
            return {"success": True, "order_id": order_id, "symbol": symbol}
            
        except Exception as e:
            logger.error(f"Failed to place order for {symbol}: {str(e)}")
            
            # Retry logic for order placement
            if retry_attempts > 0:
                import time
                logger.info(f"Retrying order for {symbol}. Attempts left: {retry_attempts}")
                time.sleep(retry_delay)
                return self.place_order(stock_entry, retry_attempts - 1, retry_delay)
            
            return {"success": False, "error": str(e), "symbol": symbol}
    
    def _check_margin_required(self, order_params):
        """Check margin required for an order.
        
        Args:
            order_params: Order parameters
        
        Returns:
            float: Margin required for the order
        """
        try:
            # Use Kite API to check margin required
            margins = self.kite.order_margins([order_params])
            return float(margins[0].get('total', 0))
        except Exception as e:
            logger.warning(f"Failed to check margin requirements: {str(e)}")
            # If margin check fails, estimate based on last price
            symbol = order_params.get('tradingsymbol')
            exchange = order_params.get('exchange')
            quantity = order_params.get('quantity')
            
            try:
                # Get current market price
                ltp = self.kite.ltp(f"{exchange}:{symbol}")
                price = float(ltp[f"{exchange}:{symbol}"]["last_price"])
                return price * quantity
            except:
                # If all fails, return a very large number to be safe
                logger.error(f"Could not estimate margin for {symbol}. Using fallback.")
                return float('inf')
    
    def _has_sufficient_margin(self, margin_required):
        """Check if user has sufficient margin for the order.
        
        Args:
            margin_required: Margin required for the order
            
        Returns:
            bool: True if user has sufficient margin
        """
        try:
            # Get user margins
            margins = self.kite.margins()
            available_margin = float(margins.get('equity', {}).get('available', {}).get('cash', 0))
            
            logger.info(f"Margin check: Required {margin_required}, Available {available_margin}")
            return available_margin >= margin_required
        except Exception as e:
            logger.warning(f"Failed to check user margins: {str(e)}")
            # If margin check fails, assume sufficient margin to avoid blocking orders
            return True
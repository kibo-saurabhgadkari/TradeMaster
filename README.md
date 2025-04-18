# TradeMaster

An automated trading system for Zerodha Kite API that manages authentication, orders, and notifications with focus on ESM stocks.

## Overview

TradeMaster is a Python-based trading automation tool that interfaces with Zerodha's Kite API to facilitate automated trading strategies. The system handles authentication, order management, and sends notifications about trade executions and system status. It is specifically designed to automate the placement of market or limit CNC orders for ESM Stage 1 or 2 stocks exactly at 9:30 AM to improve chances of order execution.

## Features

- **Automated Authentication**: Manages Zerodha Kite API tokens with auto-renewal
- **Order Management**: Places, modifies, and tracks orders
- **Notification System**: Alerts via various channels for trade executions and system events
- **Stock Configuration**: Customizable stock watch list through CSV configuration
- **ESM Stock Order Rules Compliance**: Ensures orders follow ESM stock restrictions
- **Scheduled Execution**: Places orders exactly at 9:30 AM IST
- **Robust Error Handling**: Includes retry logic and comprehensive logging

## System Requirements

- Python 3.7+
- Google Chrome (for automated authentication)
- Windows OS (also supports Linux/Mac)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/kibo-saurabhgadkari/TradeMaster.git
cd TradeMaster
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file in the root directory with your Zerodha API credentials:
```
API_KEY=your_api_key
API_SECRET=your_api_secret
ZERODHA_USER_ID=your_user_id
ZERODHA_PASSWORD=your_password
ZERODHA_PIN=your_pin
EMAIL_SENDER=your_email@example.com
EMAIL_PASSWORD=your_email_password
EMAIL_RECIPIENT=recipient@example.com
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

## Project Structure

- `auth_manager.py` - Handles Zerodha API authentication and token management
- `order_manager.py` - Manages trading orders with ESM stock compliance
- `notification_manager.py` - Sends alerts and notifications
- `main.py` - Main execution script with scheduling
- `config/stocks.csv` - Configuration file for stocks to trade
- `logs/` - Directory containing application logs (daily format: YYYY-MM-DD.log)

## Usage

1. Configure your stock list in `config/stocks.csv` with desired parameters:
```
trading_symbol,quantity,order_type,limit_price,is_active
NSE:INFY,1,LIMIT,1000,True
NSE:TCS,1,MARKET,,True
```

2. Run the application in scheduled mode:
```bash
python main.py --mode scheduled
```

3. Or run immediately for testing:
```bash
python main.py --mode immediate
```

## Authentication Process

TradeMaster supports three authentication methods:

1. **Using Existing Token**: 
   - Uses a valid access token stored in .env

2. **Manual Request Token**:
   - Generates access token from manually obtained request token

3. **Automated Login**:
   - Uses Selenium to automate the login process
   - Requires Zerodha credentials in .env

Example code for authentication:
```python
from auth_manager import ZerodhaAuthManager

# Initialize the authentication manager
auth_manager = ZerodhaAuthManager('.env')

# Check if token is valid
if not auth_manager.is_token_valid():
    # Perform automated login
    auth_manager.automated_login()
```

## ESM Stock Order Rules Compliance

The system ensures compliance with ESM stock trading rules:

- Uses CNC as product type (ESM stocks allow only CNC)
- Defaults to LIMIT orders when market orders aren't allowed
- Validates sufficient funds and proper lot sizes
- Places orders precisely at 9:30 AM IST using scheduling

## Order Management

The system supports various order types with specific handling for ESM stocks:
- Market orders
- Limit orders
- CNC product type

Example for placing an order:
```python
from order_manager import OrderManager

order_mgr = OrderManager(auth_manager.kite)
order_mgr.place_order(
    symbol="NSE:INFY",
    quantity=1,
    order_type="LIMIT",
    price=1000,
    product_type="CNC"
)
```

## Notification System

The notification system alerts you through multiple channels:
- Email
- Telegram
- Console logs

Notifications are sent for:
- Successful order placement
- Order failures
- Authentication/token failures

## Configuration

Stock configuration is managed through `config/stocks.csv` with the following format:
```
trading_symbol,quantity,order_type,limit_price,is_active
NSE:INFY,1,LIMIT,1000,True
NSE:TCS,1,MARKET,,True
```

## Logging

The application generates detailed logs in the `logs/` directory with a daily naming format (YYYY-MM-DD.log), which include:
- Authentication events
- Order placements and executions
- System errors and warnings
- Timestamps for all actions

## Deployment Options

The system can be deployed on:
- Local machine (Windows/Linux/Mac)
- Cloud server (AWS EC2, GCP, DigitalOcean)
- Raspberry Pi

For persistent operation:
- Linux/Mac: Use screen or tmux
- Windows: Create a scheduled task
- Linux Server: Set up as a systemd service

## Troubleshooting

Common issues and their solutions:

1. **Authentication Failures**:
   - Verify your Zerodha credentials
   - Check if Chrome is properly installed
   - Ensure ChromeDriver is compatible with your Chrome version

2. **Order Placement Issues**:
   - Verify you have sufficient funds
   - Check for market hours (orders scheduled for 9:30 AM)
   - Confirm stock configuration is correct

3. **ESM Stock Restrictions**:
   - Ensure you're using CNC as product type
   - Use LIMIT orders when required by ESM restrictions

## Security

- API keys and access tokens are stored securely in `.env`
- Sensitive information is never logged or displayed
- Credentials can be encrypted for additional security

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and informational purposes only. Use at your own risk. The creators are not responsible for any financial losses incurred through the use of this software.
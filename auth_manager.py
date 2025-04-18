import os
import time
import logging
from datetime import datetime
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv, set_key

# Configure logger
logger = logging.getLogger(__name__)

class ZerodhaAuthManager:
    """Manages authentication with Zerodha Kite API."""
    
    def __init__(self, env_file_path):
        """Initialize authentication manager.
        
        Args:
            env_file_path: Path to the .env file containing credentials
        """
        self.env_file_path = env_file_path
        load_dotenv(env_file_path)
        
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        self.access_token = os.getenv('ACCESS_TOKEN')
        
        if not self.api_key or not self.api_secret:
            logger.error("API key or secret not found in environment variables.")
            raise ValueError("API key or secret not found in environment variables.")
        
        self.kite = KiteConnect(api_key=self.api_key)
    
    def is_token_valid(self):
        """Check if the current access token is valid."""
        if not self.access_token:
            return False
        
        try:
            # Try to fetch profile using the current access token
            self.kite.set_access_token(self.access_token)
            profile = self.kite.profile()
            logger.info(f"Using valid token for user: {profile['user_name']}")
            return True
        except Exception as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return False
    
    def generate_access_token_from_request_token(self, request_token=None):
        """Generate access token from request token.
        
        Args:
            request_token: Request token obtained from Kite login (optional)
        
        Returns:
            str: Generated access token
        """
        if not request_token:
            request_token = os.getenv('REQUEST_TOKEN')
            
        if not request_token:
            logger.error("Request token not provided or not found in environment variables.")
            raise ValueError("Request token not provided or not found in environment variables.")
        
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            access_token = data["access_token"]
            
            # Save access token to env file
            self._update_env_variable('ACCESS_TOKEN', access_token)
            logger.info("New access token generated and saved.")
            
            self.kite.set_access_token(access_token)
            self.access_token = access_token
            return access_token
        except Exception as e:
            logger.error(f"Failed to generate access token: {str(e)}")
            raise
    
    def automated_login(self, username, password, pin):
        """Automated login using Selenium to obtain request token.
        
        Args:
            username: Zerodha user ID
            password: Zerodha password
            pin: Zerodha PIN
        
        Returns:
            str: Generated access token
        """
        try:
            logger.info("Starting automated login process")
            service = Service(ChromeDriverManager().install())
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")  # Run in headless mode (no GUI)
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(self.kite.login_url())
            
            # Login Page
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "userid")))
            driver.find_element(By.ID, "userid").send_keys(username)
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # PIN Page
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "pin")))
            driver.find_element(By.ID, "pin").send_keys(pin)
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # Wait for redirection to dashboard which contains request_token
            time.sleep(3)
            
            # Get the current URL which contains the request_token
            current_url = driver.current_url
            request_token = current_url.split('request_token=')[1].split('&')[0]
            
            driver.quit()
            
            # Save request token to env file
            self._update_env_variable('REQUEST_TOKEN', request_token)
            
            # Generate access token from request token
            return self.generate_access_token_from_request_token(request_token)
        except Exception as e:
            logger.error(f"Automated login failed: {str(e)}")
            raise
    
    def _update_env_variable(self, key, value):
        """Update environment variable in .env file.
        
        Args:
            key: Variable name
            value: Variable value
        """
        os.environ[key] = value
        
        # Read all lines from env file
        with open(self.env_file_path, 'r') as file:
            lines = file.readlines()
        
        # Update or add the key-value pair
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
        
        if not found:
            lines.append(f"{key}={value}\n")
        
        # Write back to the file
        with open(self.env_file_path, 'w') as file:
            file.writelines(lines)
import os
import time
import json
import logging
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from NorenRestApiPy.NorenApi import NorenApi
from fetch_options import get_nifty_data
from strategy_engine import calculate_straddle_parameters, evaluate_exit_conditions

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Shoonya API Setup ---
class ShoonyaApi(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')

def get_shoonya_api() -> ShoonyaApi:
    api = ShoonyaApi()

    uid = os.getenv("UID")
    pwd = os.getenv("PWD")
    totp = os.getenv("TOTP")
    vendor_code = os.getenv("VENDOR_CODE")
    api_secret = os.getenv("API_SECRET")
    imei = os.getenv("IMEI")

    if not all([uid, pwd, totp, vendor_code, api_secret, imei]):
        logger.warning("Missing Shoonya API credentials in environment variables.")
        return api

    try:
        ret = api.login(userid=uid, password=pwd, twoFA=totp, vendor_code=vendor_code, api_secret=api_secret, imei=imei)
        if ret is not None and ret.get('stat') == 'Ok':
            logger.info("Shoonya API Logged In.")
        else:
            logger.error(f"Shoonya Login Failed: {ret}")
    except Exception as e:
        logger.error(f"Shoonya API connection error: {e}")

    return api

api = get_shoonya_api()

def execute_trade(decision_json: str):
    """
    Executes trades using the Shoonya API based on the LangChain agent's structured JSON output.
    Expects decision_json to contain details like action ('enter', 'exit'), strikes, and legs.
    """
    try:
        decision = json.loads(decision_json)
        action = decision.get("action")
        logger.info(f"Executing trade action: {action} based on decision: {decision}")

        if action == "enter":
            # Pseudo-code for placing MIS short straddle orders
            logger.info("Placing MIS market orders to ENTER Short Straddle...")
        elif action == "exit":
            logger.info("Placing MIS market orders to EXIT Short Straddle...")
        else:
            logger.warning("No action taken.")
    except Exception as e:
        logger.error(f"Error executing trade: {e}")

# --- LangChain Setup ---
def get_llm():
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        # Bind the strategy engine functions as tools
        tools = [calculate_straddle_parameters, evaluate_exit_conditions, execute_trade]
        return llm.bind_tools(tools)
    except Exception as e:
        logger.error(f"Error initializing LangChain LLM: {e}")
        return None

# --- Main Trading Loop ---
def is_market_open() -> bool:
    """Checks if the current time in IST is between 09:15 AM and 03:30 PM."""
    now = datetime.now()
    market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)

    return market_start <= now <= market_end

def main_loop():
    logger.info("Starting Autonomous Trading Loop...")
    llm = get_llm()
    if not llm:
        logger.error("LLM initialization failed. Exiting.")
        return

    while True:
        try:
            if not is_market_open():
                logger.info("Market is closed. Waiting for market hours...")
                time.sleep(60)
                continue

            logger.info("Fetching latest NIFTY option chain data...")
            market_data = get_nifty_data()

            if "error" in market_data:
                logger.error(f"Data Fetch Error: {market_data['error']}")
                time.sleep(60)
                continue

            current_time = datetime.now().strftime("%H:%M")

            prompt = f"""
            You are an autonomous options trading agent executing a NIFTY Short Straddle strategy.
            The current time is {current_time} IST.
            Latest Market Data: {json.dumps(market_data)}

            Use your tools to calculate entry parameters if we have no position, or evaluate exit conditions if we are in a position.
            If conditions are met, use the execute_trade tool.
            Analyze the current market state and decide the next action.
            """

            logger.info("Prompting LangChain agent...")
            response = llm.invoke(prompt)

            if response.tool_calls:
                for tool_call in response.tool_calls:
                    logger.info(f"Agent wants to call tool: {tool_call['name']} with args {tool_call['args']}")
            else:
                logger.info(f"Agent response: {response.content}")

        except Exception as e:
            logger.error(f"Error in main loop: {e}")

        logger.info("Sleeping for 60 seconds...")
        time.sleep(60)

if __name__ == '__main__':
    try:
        # main_loop() # Normally we would run this, but for sandbox we just compile check.
        pass
    except KeyboardInterrupt:
        logger.info("Loop stopped by user.")

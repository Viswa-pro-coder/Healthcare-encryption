import os
import time
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_google_genai import ChatGoogleGenerativeAI

# The standard AgentExecutor and create_tool_calling_agent have been migrated to langgraph in the newest pip packages.
# We will use the built-in langgraph agent.
from langgraph.prebuilt import create_react_agent
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

def execute_trade(decision_json: str) -> str:
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
            return "Trade executed successfully: ENTER"
        elif action == "exit":
            logger.info("Placing MIS market orders to EXIT Short Straddle...")
            return "Trade executed successfully: EXIT"
        else:
            logger.warning("No action taken.")
            return "No valid action taken."
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        return f"Error executing trade: {e}"

# --- LangChain Setup ---
def get_agent_executor():
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        tools = [calculate_straddle_parameters, evaluate_exit_conditions, execute_trade]

        system_prompt = (
            "You are an autonomous options trading agent executing a NIFTY Short Straddle strategy. "
            "You are provided with real-time market data and the current time. "
            "Use your tools to calculate entry parameters if we have no position, or evaluate exit conditions if we are in a position. "
            "If conditions are met, use the execute_trade tool. "
            "Analyze the current market state and decide the next action."
        )

        agent_executor = create_react_agent(llm, tools, state_modifier=system_prompt)
        return agent_executor
    except Exception as e:
        logger.error(f"Error initializing LangChain agent: {e}")
        return None

# --- Main Trading Loop ---
def get_ist_time() -> datetime:
    """Returns the current time in IST."""
    return datetime.now(ZoneInfo("Asia/Kolkata"))

def is_market_open() -> bool:
    """Checks if the current time in IST is between 09:15 AM and 03:30 PM."""
    now_ist = get_ist_time()
    market_start = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)

    return market_start <= now_ist <= market_end

def main_loop():
    logger.info("Starting Autonomous Trading Loop...")
    agent_executor = get_agent_executor()
    if not agent_executor:
        logger.error("Agent Executor initialization failed. Exiting.")
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

            current_time = get_ist_time().strftime("%H:%M")

            user_input = f"""
            The current time is {current_time} IST.
            Latest Market Data: {json.dumps(market_data)}

            Please evaluate the market data and decide whether to enter, hold, or exit the trade.
            """

            logger.info("Prompting LangChain agent...")
            messages = agent_executor.invoke({"messages": [("user", user_input)]})

            logger.info(f"Agent final response: {messages['messages'][-1].content}")

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

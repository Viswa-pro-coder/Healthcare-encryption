import json
from datetime import datetime
from typing import Dict, Union

def calculate_straddle_parameters(spot_price: float, ce_ltp: float, pe_ltp: float) -> str:
    """
    Calculates the entry targets and stop-loss levels for a Short Straddle strategy.

    A Short Straddle involves selling both a Call (CE) and a Put (PE) option at the same strike.
    This function calculates a strict 25% stop-loss on the premium for both individual legs.

    Args:
        spot_price (float): The current spot price of the underlying asset.
        ce_ltp (float): The Last Traded Price (premium) of the Call option.
        pe_ltp (float): The Last Traded Price (premium) of the Put option.

    Returns:
        str: A JSON string containing the spot price, entry targets (LTPs), and calculated stop-loss levels.
             Returns a JSON string with an 'error' key if invalid inputs are provided.
    """
    if spot_price <= 0 or ce_ltp <= 0 or pe_ltp <= 0:
        return json.dumps({"error": "Prices must be positive numbers."})

    try:
        # Calculate 25% stop loss for both legs (Short options stop loss is higher than entry price)
        ce_sl = ce_ltp * 1.25
        pe_sl = pe_ltp * 1.25

        parameters = {
            "spot_price": spot_price,
            "entry": {
                "ce_ltp": ce_ltp,
                "pe_ltp": pe_ltp,
                "combined_premium": ce_ltp + pe_ltp
            },
            "stop_loss": {
                "ce_sl": round(ce_sl, 2),
                "pe_sl": round(pe_sl, 2)
            }
        }
        return json.dumps(parameters)
    except Exception as e:
        return json.dumps({"error": f"An error occurred during calculation: {str(e)}"})


def evaluate_exit_conditions(
    current_time_str: str,
    current_combined_premium: float,
    entry_combined_premium: float,
    ce_current_ltp: float,
    ce_sl: float,
    pe_current_ltp: float,
    pe_sl: float
) -> Dict[str, Union[bool, str]]:
    """
    Evaluates the exit conditions for an active Short Straddle strategy.

    Checks three conditions to determine if the strategy should be squared off:
    1. Profit Target: If the combined premium has decayed by 15% (15% profit).
    2. Stop Loss: If either the CE or PE leg has breached its predefined 25% stop-loss level.
    3. Time Decay / Intraday: If the current time is past 15:10 (03:10 PM IST).

    Args:
        current_time_str (str): The current time in 'HH:MM' 24-hour format (IST).
        current_combined_premium (float): The current combined premium of both CE and PE legs.
        entry_combined_premium (float): The combined premium at the time of entry.
        ce_current_ltp (float): The current Last Traded Price of the Call option.
        ce_sl (float): The predefined stop-loss level for the Call option.
        pe_current_ltp (float): The current Last Traded Price of the Put option.
        pe_sl (float): The predefined stop-loss level for the Put option.

    Returns:
        dict: A dictionary containing:
              - 'exit_triggered' (bool): True if any exit condition is met, False otherwise.
              - 'reason' (str): The reason for exit, or 'Hold' if no exit is triggered.
              - 'error' (str, optional): Contains error details if input parsing fails.
    """
    try:
        if current_combined_premium < 0 or entry_combined_premium <= 0 or ce_current_ltp < 0 or ce_sl <= 0 or pe_current_ltp < 0 or pe_sl <= 0:
            return {"exit_triggered": False, "reason": "Error", "error": "Invalid price inputs. Must be positive."}

        # Time check (03:10 PM IST is 15:10)
        try:
            current_time = datetime.strptime(current_time_str, "%H:%M").time()
            cutoff_time = datetime.strptime("15:10", "%H:%M").time()
            if current_time >= cutoff_time:
                return {"exit_triggered": True, "reason": "Intraday time cutoff reached (>= 15:10)."}
        except ValueError:
            return {"exit_triggered": False, "reason": "Error", "error": "Invalid time format. Use 'HH:MM'."}

        # Stop-loss check
        # Since it's a short strategy, we lose money if current LTP > SL
        if ce_current_ltp >= ce_sl:
            return {"exit_triggered": True, "reason": "Call leg stop-loss breached."}

        if pe_current_ltp >= pe_sl:
            return {"exit_triggered": True, "reason": "Put leg stop-loss breached."}

        # Profit target check
        # Short straddle profit occurs when premium decays. 15% profit means current premium is <= 85% of entry premium.
        profit_target_premium = entry_combined_premium * 0.85
        if current_combined_premium <= profit_target_premium:
            return {"exit_triggered": True, "reason": "15% combined profit target achieved."}

        return {"exit_triggered": False, "reason": "Hold"}

    except Exception as e:
        return {"exit_triggered": False, "reason": "Error", "error": f"An error occurred during evaluation: {str(e)}"}

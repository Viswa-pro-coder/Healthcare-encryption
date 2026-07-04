import requests
import sys

def fetch_nifty_options():
    # Configure a requests.Session() with standard Mozilla/Chrome browser headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/option-chain'
    }

    session = requests.Session()
    session.headers.update(headers)

    try:
        # Ping the main NSE homepage first to establish the necessary session cookies
        print("Pinging NSE homepage to establish session...")
        session.get('https://www.nseindia.com', timeout=10)
    except requests.exceptions.Timeout:
        print("Error: Timeout while connecting to NSE homepage.")
        return
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to NSE homepage: {e}")
        return

    try:
        # Call the API endpoint
        print("Fetching option chain data from NSE API...")
        url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        print("Error: Timeout while fetching API data.")
        return
    except requests.exceptions.RequestException as e:
        print(f"Error fetching API data: {e}")
        return
    except requests.exceptions.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return
    except ValueError as e: # Catch other JSON decoding failures
        print(f"Error decoding JSON response: {e}")
        return

    try:
        records = data.get('records', {})
        underlying_price = records.get('underlyingValue')

        if underlying_price is None:
            print("Underlying value not found in data.")
            return

        print(f"Underlying Spot Price: {underlying_price}")

        # mathematically determine the nearest At-The-Money (ATM) strike
        # NIFTY strike interval is typically 50
        atm_strike_calculated = round(underlying_price / 50) * 50

        # Verify from strike_prices
        strike_prices = records.get('strikePrices', [])
        if strike_prices:
            atm_strike = min(strike_prices, key=lambda x: abs(x - underlying_price))
        else:
            atm_strike = atm_strike_calculated

        print(f"Nearest ATM Strike: {atm_strike}")

        # Print the Last Traded Price (LTP) and Open Interest (OI) for both the Call (CE) and Put (PE) for that exact ATM strike
        atm_data = next((item for item in records.get('data', []) if item.get('strikePrice') == atm_strike), None)

        if not atm_data:
            print(f"Data for ATM strike {atm_strike} not found.")
            return

        ce_data = atm_data.get('CE', {})
        pe_data = atm_data.get('PE', {})

        ce_ltp = ce_data.get('lastPrice', 'N/A')
        ce_oi = ce_data.get('openInterest', 'N/A')

        pe_ltp = pe_data.get('lastPrice', 'N/A')
        pe_oi = pe_data.get('openInterest', 'N/A')

        print(f"CE - LTP: {ce_ltp}, OI: {ce_oi}")
        print(f"PE - LTP: {pe_ltp}, OI: {pe_oi}")

    except Exception as e:
        print(f"Error processing data: {e}")

if __name__ == '__main__':
    fetch_nifty_options()

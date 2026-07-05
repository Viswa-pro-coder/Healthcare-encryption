import requests
import sys

def get_nifty_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/option-chain'
    }

    session = requests.Session()
    session.headers.update(headers)

    try:
        session.get('https://www.nseindia.com', timeout=10)
    except Exception as e:
        return {"error": f"Error connecting to NSE homepage: {e}"}

    try:
        url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return {"error": f"Error fetching API data: {e}"}

    try:
        records = data.get('records', {})
        underlying_price = records.get('underlyingValue')

        if underlying_price is None:
            return {"error": "Underlying value not found in data."}

        atm_strike_calculated = round(underlying_price / 50) * 50

        strike_prices = records.get('strikePrices', [])
        if strike_prices:
            atm_strike = min(strike_prices, key=lambda x: abs(x - underlying_price))
        else:
            atm_strike = atm_strike_calculated

        atm_data = next((item for item in records.get('data', []) if item.get('strikePrice') == atm_strike), None)

        if not atm_data:
            return {"error": f"Data for ATM strike {atm_strike} not found."}

        ce_data = atm_data.get('CE', {})
        pe_data = atm_data.get('PE', {})

        return {
            "spot_price": underlying_price,
            "atm_strike": atm_strike,
            "ce_ltp": ce_data.get('lastPrice', 'N/A'),
            "ce_oi": ce_data.get('openInterest', 'N/A'),
            "pe_ltp": pe_data.get('lastPrice', 'N/A'),
            "pe_oi": pe_data.get('openInterest', 'N/A')
        }

    except Exception as e:
        return {"error": f"Error processing data: {e}"}

def fetch_nifty_options():
    print("Pinging NSE homepage to establish session...")
    print("Fetching option chain data from NSE API...")
    data = get_nifty_data()

    if "error" in data:
        print(data["error"])
        return

    print(f"Underlying Spot Price: {data['spot_price']}")
    print(f"Nearest ATM Strike: {data['atm_strike']}")
    print(f"CE - LTP: {data['ce_ltp']}, OI: {data['ce_oi']}")
    print(f"PE - LTP: {data['pe_ltp']}, OI: {data['pe_oi']}")

if __name__ == '__main__':
    fetch_nifty_options()

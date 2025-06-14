import requests
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from core.interfaces import ContentProvider
from core.utils import retry_with_backoff, get_env_var

logger = logging.getLogger(__name__)


class ExchangeRateProvider(ContentProvider):
    """Fetch exchange rate data from exchangerate-api.com or similar services."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_currency = config.get('base_currency', 'USD')
        self.target_currencies = config.get('target_currencies', ['EUR', 'GBP', 'CNY', 'JPY'])
        self.api_key = get_env_var('EXCHANGE_RATE_API_KEY') or config.get('api_key')
        self.use_free_api = config.get('use_free_api', True)
    
    def get_prompt(self) -> str:
        """Return the prompt for AI to summarize exchange rate data."""
        currencies_str = ', '.join(self.target_currencies)
        return (
            f"Please provide a brief summary of today's exchange rates for {self.base_currency} "
            f"against {currencies_str}. Mention any significant changes or trends if present. "
            f"Keep it concise and suitable for a daily financial update notification."
        )
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def fetch(self) -> str:
        """Fetch current exchange rates."""
        try:
            if self.use_free_api:
                # Using free API (no key required)
                url = f"https://api.exchangerate-api.com/v4/latest/{self.base_currency}"
                response = requests.get(url, timeout=10)
            else:
                # Using premium API with key
                url = (
                    f"https://v6.exchangerate-api.com/v6/{self.api_key}"
                    f"/latest/{self.base_currency}"
                )
                response = requests.get(url, timeout=10)
            
            response.raise_for_status()
            data = response.json()
            
            # Format the data
            result = self._format_exchange_data(data)
            logger.info(f"Successfully fetched exchange rates for {self.base_currency}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch exchange rate data: {e}")
            raise
    
    def _format_exchange_data(self, data: Dict) -> str:
        """Format exchange rate data into readable text."""
        rates = data.get('rates', {})
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        result = f"Exchange rates for {self.base_currency} on {date}:\n\n"
        
        for currency in self.target_currencies:
            if currency in rates:
                rate = rates[currency]
                result += f"1 {self.base_currency} = {rate:.4f} {currency}\n"
                
                # Add inverse rate for better understanding
                if rate > 0:
                    inverse_rate = 1 / rate
                    result += f"  (1 {currency} = {inverse_rate:.4f} {self.base_currency})\n"
        
        # Add timestamp
        result += f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return result


class CryptoExchangeProvider(ContentProvider):
    """Fetch cryptocurrency exchange rates."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.cryptocurrencies = config.get('cryptocurrencies', ['BTC', 'ETH'])
        self.vs_currency = config.get('vs_currency', 'USD')
    
    def get_prompt(self) -> str:
        """Return the prompt for AI to summarize crypto data."""
        crypto_str = ', '.join(self.cryptocurrencies)
        return (
            f"Please summarize the current cryptocurrency prices for {crypto_str} "
            f"in {self.vs_currency}. Mention any significant price movements if notable. "
            f"Keep it brief and suitable for a daily crypto update."
        )
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def fetch(self) -> str:
        """Fetch cryptocurrency prices from CoinGecko API."""
        try:
            ids = ','.join([self._get_coingecko_id(c) for c in self.cryptocurrencies])
            url = (
                f"https://api.coingecko.com/api/v3/simple/price"
                f"?ids={ids}&vs_currencies={self.vs_currency.lower()}"
                f"&include_24hr_change=true"
            )
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result = self._format_crypto_data(data)
            logger.info("Successfully fetched cryptocurrency data")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch crypto data: {e}")
            raise
    
    def _get_coingecko_id(self, symbol: str) -> str:
        """Map common symbols to CoinGecko IDs."""
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOGE': 'dogecoin'
        }
        return mapping.get(symbol.upper(), symbol.lower())
    
    def _format_crypto_data(self, data: Dict) -> str:
        """Format cryptocurrency data into readable text."""
        result = f"Cryptocurrency prices in {self.vs_currency}:\n\n"
        
        for crypto in self.cryptocurrencies:
            gecko_id = self._get_coingecko_id(crypto)
            if gecko_id in data:
                price_data = data[gecko_id]
                price = price_data.get(self.vs_currency.lower(), 0)
                change_24h = price_data.get(f'{self.vs_currency.lower()}_24h_change', 0)
                
                change_symbol = "↑" if change_24h > 0 else "↓" if change_24h < 0 else "→"
                result += (
                    f"{crypto}: {self.vs_currency} {price:,.2f} "
                    f"({change_symbol} {abs(change_24h):.2f}%)\n"
                )
        
        result += f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return result


def factory(config: Dict[str, Any]) -> ContentProvider:
    """Factory function to create appropriate exchange rate provider."""
    provider_type = config.get('type', 'fiat')
    
    if provider_type == 'crypto':
        return CryptoExchangeProvider(config)
    else:
        return ExchangeRateProvider(config)
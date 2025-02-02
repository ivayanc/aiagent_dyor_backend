import requests


class MoralisConnector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'accept': 'application/json',
            'X-API-Key': self.api_key
        }
        self.base_url = "https://deep-index.moralis.io/api/v2.2/"

    def _make_request(self, url: str, data: dict):
        url = f'{self.base_url}/{url}'
        return requests.get(url, headers=self.headers, params=data).json()
    
    def get_token_top_holders(self, token_address: str, chain: str, limit: int = 11, order: str = "DESC"):
        url = f"erc20/{token_address}/owners"
        data = {
            'chain': chain,
            'limit': limit,
            'order': order
        }
        resp = self._make_request(url, data)
        top_holders = []
        for item in resp['result']:
            if item['is_contract'] is False:
                top_holders.append(item['percentage_relative_to_total_supply'])
        return top_holders

    def get_token_info(self, token_address: str, chain: str):
        url = f'erc20/metadata'
        data = {
            'chain': chain,
            'addresses[]': token_address
        }
        resp = self._make_request(url, data)
        resp = resp[0]
        links = resp.get('links', {})
        return {
            'name': resp['name'],
            'symbol': resp['symbol'],
            'address': resp['address'],
            'twitter': links.get('twitter', ''),
            'telegram': links.get('telegram', ''),
            'website': links.get('website', ''),
            'total_supply_formatted': round(float(resp['total_supply_formatted']), int(resp['decimals']))
        }
    
    def get_token_price_info(self, token_address: str, chain: str):
        url = f'erc20/{token_address}/price'
        data = {
            'chain': chain
        }
        resp = self._make_request(url, data)
        return resp

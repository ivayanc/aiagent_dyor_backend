import requests


class BitqueryConnector:
    BASE_URL = "https://streaming.bitquery.io/graphql"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def get_token_holders_count(self, token_address: str, date: str, network: str) -> int:
        query = f"""
        {{
            EVM(dataset: archive, network: {network}) {{
                TokenHolders(
                    date: "{date}"
                    tokenSmartContract: "{token_address}"
                ) {{
                    uniq(of: Holder_Address)
                }}
            }}
        }}
        """

        payload = {
            "query": query
        }

        response = requests.post(self.BASE_URL, json=payload, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print('Error getting token holders count')
            return 0
        return response.json()['data']['EVM']['TokenHolders'][0]['uniq']
    
    def get_token_max_price(self, token_address: str, date: str, network: str) -> int:
        query = f"""
        {{
            EVM(dataset: combined, network: {network}) {{
                DEXTradeByTokens(
                    orderBy: {{descendingByField: "Trade_high_maximum"}}
                    where: {{
                        Trade: {{
                            Side: {{Amount: {{gt: "0"}}, AmountInUSD: {{gt: "1000"}}}},
                            Currency: {{SmartContract: {{is: "{token_address}"}}}},
                            PriceAsymmetry: {{lt: 0.1}}
                        }},
                        Block: {{Date: {{before: "{date}"}}}}
                    }}
                    limit: {{count: 1}}
                ) {{
                    Trade {{
                        high: PriceInUSD(maximum: Trade_PriceInUSD)
                    }}
                    Block {{
                        Timefield: Time(interval: {{in: hours, count: 1}})
                    }}
                }}
            }}
        }}
        """

        payload = {
            "query": query
        }

        response = requests.post(self.BASE_URL, json=payload, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print('Error getting token holders count')
            return 0
        return response.json()['data']['EVM']['DEXTradeByTokens'][0]['Trade']['high']
    

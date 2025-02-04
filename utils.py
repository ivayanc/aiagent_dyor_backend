from pprint import pprint

from agents.grok import GrokAI
from agents.openai import OpenAI
from agents.dyor_parser import DYORParser

from connectors.moralis import MoralisConnector
from connectors.bitquery_connector import BitqueryConnector

from settings import GROK_API_KEY, MORALIS_API_KEY, OPENAI_API_KEY, BITQUERY_API_KEY
from datetime import datetime, timedelta


grok = GrokAI(GROK_API_KEY)
openai = OpenAI(OPENAI_API_KEY)
moralis_connector = MoralisConnector(MORALIS_API_KEY)
bitquery_connector = BitqueryConnector(BITQUERY_API_KEY)
dyor_parser = DYORParser(OPENAI_API_KEY)


def prepare_token_info_promt(token_info: dict):
    return f"""
    Token name: {token_info['name']}
    Token symbol: {token_info['symbol']}
    Token address: {token_info['address']}
    Token holders count: {token_info['holders_count']}
    Token top holders in format 'percentage_relative_to_total_supply of top holder1;percentage_relative_to_total_supply of top holder2; ...': {token_info['top_holders']}
    Token liquidity in USDT: {token_info['liquidity']}
    Current price in USDT: {token_info['current_price']}
    Max price in USDT: {token_info['max_price']}
    Max price date: {token_info['max_price_date']}
    Total supply: {token_info['total_supply_formatted']}
    """

def prepare_prompt_for_grok(token_info: dict):
    return f"Analyze community of token ${token_info['symbol']}. Contract addres is {token_info['address']}."


def get_token_info(token_address: str, chain: str):
    token_info = moralis_connector.get_token_info(token_address=token_address, chain=chain)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    token_info['holders_count'] = bitquery_connector.get_token_holders_count(token_address=token_address, date=yesterday, network=chain)
    token_info['top_holders'] = ';'.join([str(item) for item in moralis_connector.get_token_top_holders(token_address=token_address, chain=chain)])
    price_info = moralis_connector.get_token_price_info(token_address=token_address, chain=chain)
    token_info['liquidity'] = price_info.get('pairTotalLiquidityUsd', 'Insufficient liquidity in pools to calculate the price')
    token_info['current_price'] = price_info.get('usdPrice', 'Insufficient liquidity in pools to calculate the price')
    max_price_info = bitquery_connector.get_token_max_price(token_address=token_address, date=datetime.now().strftime('%Y-%m-%d'), network=chain)
    token_info['max_price'] = max_price_info.get('Trade', {}).get('high', 'NO AVAILABLE DATA')
    token_info['max_price_date'] = max_price_info.get('Block', {}).get('Timefield', 'NO AVAILABLE DATA')
    token_info['chain'] = chain
    return token_info


def get_community_analysis(prompt: str):
    return grok.chat(prompt)


def get_ticker_info_analysis(prompt: str):
    lore = """
    You are a professional quant trader with 10 years of experience who right now switched to memecoin trading.
    Currently you are analyzing provided token info and answering what future you see for this token leaning on 10 years of experience as quant trader.
    First of all you should take a look at number of holders and top holders.
    Secondly you should take a look at liquidity and current price. If liquidity is low or current price is high, then this token is not a good investment.
    Thirdly you should take a look at max price and max price date.
    Fourthly you should take a look at total supply.
    Fifthly you should take a look at token name and symbol.
    Your response always should contain at the end return confident in procents about confidence in future of that token "Confidence in bright future of that token: your exepctection of confidence in bright future of that token in % ".
    """
    return openai.chat(prompt, lore)


def get_ticker_decision(token_address: str, chain: str):
    token_info = get_token_info(token_address=token_address, chain=chain)
    pprint(token_info)
    ticker_analytic = get_ticker_info_analysis(prepare_token_info_promt(token_info))
    community_analysis = get_community_analysis(prepare_prompt_for_grok(token_info))
    lore = f"""
    You are a General Partner of a hedge fund.
    You got two reports about meme coin token.
    First one from your quant trader who analyze more technical side of this token:
    Second one from your professional psychological who analyze community of this token:
    Your task is to carrefuly read both reports and make decision about investment in this token or not.
    Your company wants to invest in tokens with high probability of success in long term.
    Everything that affects youк decision should be included in final document.
    Your company keeps documents very clearly, so your final report should be in the format shown below:
    1. Token name: TOKEN NAME HERE (Only name)
    2. Token symbol: TOKEN SYMBOL HERE (Only symbol with $)
    3. Token address: TOKEN ADDRESS HERE (Only address)
    4. Token chain: TOKEN CHAIN HERE (Only chain)
    5. Current holders count: CURRENT HOLDERS COUNT HERE (Only number)
    6. Current price: CURRENT PRICE HERE (Only number with $ symbol)
    7. Brief technical side analysis: BRIEF QUANT TRADER ANALYSIS HERE (No longer than 3 sentences)
    8. Brief community side analysis: BRIEF PSYCHOLOGICAL ANALYSIS HERE (No longer than 3 sentences)
    9. Final decision: FINAL DECISION HERE(ONLY HIGH RISK, MEDIUM RISK, LOW RISK)
    10. Final confident level: FINAL CONFIDENT LEVEL HERE (Only number in %)
    11. Explanation: FINAL EXPLANATION HERE(No longer than 4 sentences)
    """
    message = f"""
    Token name: {token_info['name']}
    Token symbol: {token_info['symbol']}
    Token address: {token_info['address']}
    Token chain: {token_info['chain']}
    Quant trader analysis:
    {ticker_analytic}
    Psychological analysis:
    {community_analysis}
    """
    print('--------------------------------MESSAGE--------------------------------')
    print(message)
    print('------------------------------------------------------------------------')
    return openai.chat(message, lore)

def parse_dyor_report(file_path: str):
    return dyor_parser.parse_document_with_openai(file_path)
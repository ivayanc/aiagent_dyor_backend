import json

from pprint import pprint

from agents.grok import GrokAI
from agents.openai import OpenAI
from agents.dyor_parser import DYORParser

from connectors.moralis import MoralisConnector
from connectors.bitquery_connector import BitqueryConnector
from connectors.mongodb import TokenResearchInput, DatabaseManager
from connectors.twitter_connector import TwitterConnector
from connectors.telegram import TelegramConnector
from connectors.github import GitHubConnector
from connectors.discord import DiscordConnector

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

async def parse_dyor_report(file_path: str):
    parsed_dyor = dyor_parser.parse_document_with_openai(file_path)
    db_manager = DatabaseManager()
    input_data = TokenResearchInput(
        token_name=parsed_dyor['general_info']['project_name'],
        token_address=parsed_dyor['general_info']['token_info']['token_address'],
        token_chain=parsed_dyor['general_info']['token_info']['token_chain'],
        data=parsed_dyor,
        metadata=None
    )
    await db_manager.save_research_input(input_data)
    return parsed_dyor


def update_socials_from_dyor_report(platforms: list):
    updated_platforms = []
    for platform in platforms:
        platform_name = platform.get('name').lower()
        if platform_name == 'twitter':
            new_followers = TwitterConnector().get_user_info(platform.get('url').replace('https://x.com/', '').replace('https://twitter.com/', '')).get('result', {}).get('data', {}).get(
                'user',
            {}).get('result', {}).get('legacy', {}).get('followers_count', 0)
        if platform_name == 'telegram':
            new_followers = TelegramConnector().get_channel_followers(platform.get('url').replace('https://t.me/', ''))
        if platform_name == 'discord':
            new_followers = DiscordConnector().get_followers(platform.get('url').replace('https://discord.gg/', '').replace('https://discord.com/invite/', ''))
        updated_platforms.append({
            'name': platform.get('name'),
            'url': platform.get('url'),
            'followers': new_followers
        })
    return updated_platforms


def get_github_repos_info(account_name: str):
    repos = GitHubConnector().get_github_repos_info(account_name)
    formatted_repos = GitHubConnector().format_repo_info(repos)
    return formatted_repos


def convert_token_chain(token_chain: str):
    token_chain = token_chain.lower()
    if token_chain == 'base':
        return 'base'
    if token_chain == 'ethereum':
        return 'eth'
    return token_chain

def update_dyor_report(dyor_report: dict, token_address: str, token_chain: str):
    if token_address and token_chain:
        token_info = get_token_info(token_address=token_address, chain=convert_token_chain(token_chain))
        ticker_analytic = get_ticker_info_analysis(prepare_token_info_promt(token_info))
    else:
        ticker_analytic = 'No token info available.'
    github_account = dyor_report.get('general_info', {}).get('github_url', '').replace('https://github.com/', '')
    updated_development_status, repos_info = update_development_status(github_account)
    platforms = dyor_report.get('social_media', {}).get('platforms', [])
    updated_platforms = update_socials_from_dyor_report(platforms)
    final_conclusion = make_final_conclusion(dyor_report, updated_development_status, updated_platforms, ticker_analytic)
    return {
        'updated_development_status': updated_development_status,
        'updated_platforms': updated_platforms,
        'final_conclusion': final_conclusion,
        'ticker_analytic': ticker_analytic,
        'token_info': token_info,
        'repos_info': repos_info
    }

def make_final_conclusion(dyor_report: dict, updated_development_status: str, updated_platforms: list, ticker_analytic: str):
    lore = f"""
    You are a DYOR (Do Your Own Research) report expert that builds reports for crypto projects.
    You are tasked to make new Conclusion section for DYOR report.
    You'll be provided with previous report in json format and updated development status and updated platforms and ticker analytic if token is realised already.
    You should make new Conclusion section based on provided information.
    You must return result as text always
    """
    message = f"""
    Previous report:
    {json.dumps(dyor_report, indent=4)}
    Updated development status:
    {updated_development_status}
    Updated platforms:
    {json.dumps(updated_platforms, indent=4)}
    Ticker analytic:
    {ticker_analytic}
    """
    return openai.chat(message, lore)


def update_development_status(github_account):
    repos_info = get_github_repos_info(github_account)
    lore = f"""
    You are a DYOR (Do Your Own Research) report expert that builds reports for crypto projects.
    You are specialising on analyzing github repos of projects.
    You are tasked to analyze github repos of projects and provide information about development status of the project in no more than 5 sentences.
    You'll be provided with list of github repos and information about them that includes:
    - repo name
    - repo description
    - repo last commit date
    - repo programming language
    - repo stars
    Current date: {datetime.now().strftime('%Y-%m-%d')}
    """
    return openai.chat(repos_info, lore), repos_info

import json
import logging

import boto3
import requests
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey


# SSMパラメータ取得関数を定義
def get_ssm_parameter(name):
    """SSMパラメータを取得する関数。

    Args:
        name (str): 取得するパラメータの名前。

    Returns:
        str: パラメータの値。
    """
    ssm = boto3.client('ssm')
    return ssm.get_parameter(Name=name, WithDecryption=True)['Parameter']['Value']

# 定数をまとめて定義
PUBLIC_KEY = get_ssm_parameter('/discord/dify/PUBLIC_KEY')
DISCORD_BOT_TOKEN = get_ssm_parameter('/discord/dify/DISCORD_BOT_TOKEN')
DIFY_ENDPOINT = get_ssm_parameter('/dify/ENDPOINT')

# ロガーの設定（名前空間を指定）
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def send_dify_workflow(inputs, user, dify_api_key):
    """DIFYワークフローを実行し、レスポンスを取得する関数。

    Args:
        inputs (dict): DIFYワークフローへの入力データ。
        user (str): ユーザー名。
        dify_api_key (str): DIFYのAPIキー。

    Returns:
        dict: DIFY APIからのレスポンス。
    """
    logger.info(f'inputs: {inputs}')
    headers = {
        'Authorization': f'Bearer {dify_api_key}',
        'Content-Type': 'application/json'
        }
    data = {
        'inputs': inputs,
        'response_mode': 'blocking',
        'user': user
        }

    try:
        response = requests.post(f'{DIFY_ENDPOINT}/v1/workflows/run', headers=headers, data=json.dumps(data), timeout=120)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error('Request timed out')
        return {'error': 'Request timed out'}
    except requests.exceptions.RequestException as e:
        logger.error(f'Request failed: {e}')
        return {'error': f'Request failed: {e}'}

    return response.json()

def handle_ping():
    """DiscordのPINGイベントを処理する関数。

    Returns:
        dict: PINGイベントへの応答データ。
    """
    return {'statusCode': 200, 'body': json.dumps({'type': 1})}

def handle_application_command(body):
    """Discordのアプリケーションコマンドを処理する関数。

    Args:
        body (dict): Discordからのイベントデータ。

    Returns:
        dict: レスポンスデータ。
    """
    command_name = body['data']['name']
    channel_id = body['channel_id']
    command_input = '<Input '

    logger.info(f'command name: {command_name}, channel id: {channel_id}')

    DIFY_API_KEY = get_ssm_parameter(f'/dify/app/{command_name}')

    inputs = {}
    if command_name == 'neko':
        command_input += f'text={body['data']['options'][0]['value']}'
        inputs = {
            'query': body['data']['options'][0]['value']
        }
    elif command_name == 'summary':
        command_input += f'url={body['data']['options'][0]['value']}'
        inputs = {
            'url': body['data']['options'][0]['value']
        }
    # ここに他のコマンドの処理を追加する

    command_input += '>'

    # 3秒以内にレスポンスを返す必要がある
    url = "https://discord.com/api/v10/interactions/{}/{}/callback".format(body['id'], body['token'])
    data = {
        "type": 4,
        "data": {
            "content": command_input
        }
    }
    r = requests.post(url, json=data)

    response = send_dify_workflow(inputs, body['member']['user']['username'], DIFY_API_KEY)
    logger.info(f'dify response: {response}')

    url = f'https://discordapp.com/api/channels/{channel_id}/messages'
    headers = {
        'authorization': f'Bot {DISCORD_BOT_TOKEN}',
        'content-type': 'application/json'
    }
    data = {
        'content': response['data']['outputs']['text'],
    }
    r = requests.post(url, headers=headers, json=data)
    logger.info(f'response: {r.json()}')

    return {'statusCode': 200}

def lambda_handler(event, context):
    """AWS Lambdaのエントリポイント関数。

    Args:
        event (dict): イベントデータ。
        context (LambdaContext): ランタイム情報。

    Returns:
        dict: レスポンスデータ。
    """
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

    signature = event['headers']['x-signature-ed25519']
    timestamp = event['headers']['x-signature-timestamp']
    body = event['body']

    logger.info(f'event: {event}')
    logger.info(f'body: {body}')

    try:
        verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
        body = json.loads(body)

        if body['type'] == 1:
            return handle_ping()
        elif body['type'] == 2:
            return handle_application_command(body)

    except BadSignatureError:
        logger.error('Bad Signature')
        return {'statusCode': 401, 'body': json.dumps('Bad Signature')}
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        return {'statusCode': 500, 'body': json.dumps('Internal Server Error')}

    return {'statusCode': 404}

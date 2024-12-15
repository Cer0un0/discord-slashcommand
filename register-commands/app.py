import json

import boto3
import requests


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

# get parameters
APP_ID = get_ssm_parameter('/discord/dify/DISCORD_APP_ID')
DISCORD_BOT_TOKEN = get_ssm_parameter('/discord/dify/DISCORD_BOT_TOKEN')

def lambda_handler(event, context):
    # Discord API URLを設定
    url = f'https://discord.com/api/v10/applications/{APP_ID}/commands'

    # コマンドのJSONペイロード
    commands = [
        {
            'name': 'neko', 
            'description': 'にゃーん',
            'options': [
                    {
                        "name": "text",
                        "description": "string",
                        "type": 3,
                        "required": True,
                    }
                ]
        },
        {
            'name': 'summary',
            'description': '要約',
            'options': [
                {
                    "name": "url",
                    "description": "string",
                    "type": 3,
                    "required": True,
                }
            ]
        }
    ]

    # HTTPヘッダーを設定
    headers = {'Authorization': f'Bot {DISCORD_BOT_TOKEN}'}

    # Discord APIにリクエストを送信
    try:
        responses = []
        for command in commands:
            response = requests.post(url, json=command, headers=headers)
            response_data = response.json()
            responses.append({'statusCode': response.status_code, 'body': response_data})
        return {'statusCode': 200, 'body': json.dumps(responses)}
    except requests.exceptions.RequestException as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

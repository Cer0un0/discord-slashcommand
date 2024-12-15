import json

import boto3
import requests

# get parameters
ssm = boto3.client('ssm')
# fmt: off
APP_ID = ssm.get_parameter(
    Name='/discord/dify/DISCORD_APP_ID',
    WithDecryption=True)['Parameter']['Value']
DISCORD_BOT_TOKEN = ssm.get_parameter(
    Name='/discord/dify/DISCORD_BOT_TOKEN',
    WithDecryption=True)['Parameter']['Value']
# fmt: on

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

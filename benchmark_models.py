import json
import urllib.request

def get_active_tiers_and_providers():
    try:
        health_response = urllib.request.urlopen('http://127.0.0.1:8000/health')
        health_response.raise_for_status()
    except urllib.error.URLError as e:
        print(f"Error fetching health: {e}")
        return None

    health_json = json.loads(health_response.read().decode('utf-8'))

    try:
        models_response = urllib.request.urlopen('http://127.0.0.1:8000/v1/models')
        models_response.raise_for_status()
    except urllib.error.URLError as e:
        print(f"Error fetching models: {e}")
        return None

    models_json = json.load(models_response)

    active_tiers_and_providers = []
    for model in models_json['data']:
        if model['active']:
            active_tiers_and_providers.append([model['tier'], model['provider']])

    for tier, provider in active_tiers_and_providers:
        print(f"Tier: {tier}, Provider: {provider}")

if __name__ == '__main__':
    get_active_tiers_and_providers()

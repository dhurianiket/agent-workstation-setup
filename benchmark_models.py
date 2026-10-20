import requests
from tabulate import tabulate

def get_active_tiers_and_providers():
    try:
        health_response = requests.get('http://127.0.0.1:8000/health')
        health_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching health: {e}")
        return None

    import json
    import re
    health_json = json.loads(re.search(r'{.*}', health_response.text).group())

    try:
        models_response = requests.get('http://127.0.0.1:8000/v1/models')
        models_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching models: {e}")
        return None

    models_json = models_response.json()

    active_tiers_and_providers = []
    for model in models_json:
        if model['active']:
            active_tiers_and_providers.append([model['tier'], model['provider']])

    print(tabulate(active_tiers_and_providers, headers=['Tier', 'Provider'], tablefmt='grid'))

if __name__ == '__main__':
    get_active_tiers_and_providers()

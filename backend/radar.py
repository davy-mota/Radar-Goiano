import requests

url_catalogo = "https://dadosabertos.go.gov.br/api/3/action/package_show?id=empenhos"
resposta = requests.get(url_catalogo).json()
recursos = resposta.get('result', {}).get('resources', [])

print("🔍 O QUE O GOVERNO REALMENTE ESCONDEU NO PORTAL:\n")

for r in recursos:
    nome = r.get('name', 'Sem Nome')
    formato = r.get('format', 'Vazio')
    # Imprime tudo pra gente investigar!
    print(f"Arquivo: {nome} | Formato cadastrado: '{formato}'")
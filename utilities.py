from Exchange2 import RPCExchange2
import json, requests, re
import re



url = "https://api.sienge.com.br/s8psasistemas/public/api/v1"
username = "s8psasistemas-midd"
password = "fq3LdZzvTJq8u8oeASFhVkYV20NIac41"

def validar_e_limpar_cpf(cpf: str) -> str :
    """
    Recebe um CPF, remove caracteres não numéricos,
    valida o CPF e retorna o CPF limpo.
    Retorna None se o CPF for inválido.
    """

    # Remove tudo que não for número
    cpf_limpo = re.sub(r'\D', '', cpf)

    # Verifica se tem 11 dígitos
    if len(cpf_limpo) != 11:
        return None

    # Elimina CPFs com todos os dígitos iguais
    if cpf_limpo == cpf_limpo[0] * 11:
        return None

    # Primeiro dígito verificador
    soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10) % 11
    digito1 = 0 if digito1 == 10 else digito1

    if digito1 != int(cpf_limpo[9]):
        return None

    # Segundo dígito verificador
    soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10) % 11
    digito2 = 0 if digito2 == 10 else digito2

    if digito2 != int(cpf_limpo[10]):
        return None

    return cpf_limpo
# -----------------------------------------------

def consultarapi(cliente):
    endpoint = f"{url}/customers?cpf={cliente}"
    print(endpoint)
    # Fazendo Requisição GET
    response = requests.get(endpoint, auth=(username, password))

    if response.status_code == 200:
        return True, response.json() # Retorna dados JSON
    else:
        print(response.json().get('msg'), None)
        return False, {"ERRO:" f"Falha ao obter dados {response.status_code}"}
    

# ---------------------------------------------------

def cadastrar_cliente(cliente):
    endpoint = f"{url}/customers?insert={cliente}"

    print("[!] Cliente Recebido para cadastro com Sucesso !.", flush=True)
    
    response = requests.post(
        endpoint,
        json = cliente,
        auth=(username, password)
    )

    print("[!] Modelo de cliente a ser enviado:", cliente)
    print(f'AQUI O TYPE DO CLIENTE', type (cliente), flush= True)
    print("Status:", "Cliente Cadastrado com sucesso" if response.status_code == 201 else "ERRO Ao cadastrar Clinte")
    print("Response:", "201 Criado" if response.status_code == 201 else response.json())

    if response.status_code == 201:
        return "[!] Cliente Cadastrado com Sucesso"
    else:
        return "[!] Erro ao cadastrar cliente"

# -----------------------------------------------

def normalizar_estado_civil(valor: str) -> str:
    chave = valor.strip().lower()

    ESTADO_CIVIL_MAP = {
    "solteiro": "SOLTEIRO",
    "solteira": "SOLTEIRO",
    "casado": "CASADO",
    "casada": "CASADO",
    "divorciado": "DIVORCIADO",
    "divorciada": "DIVORCIADO",
    "viuvo": "VIUVO",
    "viúva": "VIUVO",
    "uniao_estavel": "UNIAO_ESTAVEL",
    "união estável": "UNIAO_ESTAVEL",
    }

    if chave not in ESTADO_CIVIL_MAP:
        raise ValueError(f"Estado civil inválido: {valor}")
    return ESTADO_CIVIL_MAP[chave]


def tratar_conjuge(spouse: dict | None) -> dict | None:
    """
    Trata os dados do cônjuge para o padrão esperado pelo Sienge.
    Retorna None se não houver cônjuge válido.
    """

    if not spouse or not isinstance(spouse, dict):
        return None

    def get(field):
        value = spouse.get(field)
        if value in ("", None):
            return None
        return value

    conjuge = {
        "name": get("name"),
        "cpf": get("cpf"),
        "birthDate": get("birthDate"),
        "sex": get("sex"),
        "civilStatus": get("civilStatus"),
        "nationality": get("nationality"),
        # "profession": get("profession"),
        "numberIdentityCard": get("numberIdentityCard"),
        "issuingBody": get("issuingBody"),
        "issueDateIdentityCard": get("issueDateIdentityCard"),
        "email": get("email"),
    }

    # Remove campos None (Sienge rejeita)
    conjuge = {k: v for k, v in conjuge.items() if v is not None}

    # CPF deve conter apenas números
    if "cpf" in conjuge:
        conjuge["cpf"] = re.sub(r"\D", "", conjuge["cpf"])

    return conjuge if conjuge else None

def consultar_todas_profissoes(profession: str):
    try:
        endpoint = f"{url}/professions?name={profession}"
        print(endpoint)
        response = requests.get(endpoint, auth=(username, password))

        if response.status_code == 200:
            dados = response.json()
            if "results" in dados and len(dados["results"]) > 0:
                profissao = dados["results"][0]
                return profissao["name"]
            else:
                print(f"Profissão '{profession}' não encontrada.")
                
                return None
        else:
            print(f"Erro ao consultar profissões: {response.status_code}")
            return None
    except Exception as err:
        print(f"Erro ao consultar profissões: {err}")
        return None        

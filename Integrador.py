from Exchange2 import RPCExchange2
import json, requests, re
import re

amqps = 'amqps://vlguashe:7MvzDbMfN6oQ2NyAZoDyZw_oKTWhvm43@jackal.rmq.cloudamqp.com/vlguashe'
origin = 'pc-abner'
system = 'cadastro-cliente'
service = 'integrador'
version = 'V1.01 - Integrador De Cliente'
host = 'kuririn'


def validar_e_limpar_cpf(cpf: str) -> str | None:
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


# Consulta API SIEGNE
url = "https://api.sienge.com.br/s8psasistemas/public/api/v1"
username = "s8psasistemas-midd"
password = "fq3LdZzvTJq8u8oeASFhVkYV20NIac41"

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

def cadastrar_cliente(cliente):
    endpoint = f"{url}/customers?insert={cliente}"

    print("[!] Cliente Recebido para cadastro com Sucesso !.", flush=True)
    
    response = requests.post(
        endpoint,
        json = cliente,
        auth=(username, password)
    )
    print("[!] Modelo de cliente a ser enviado:", cliente)
    print("Status:", "Cliente Cadastrado com sucesso" if response.status_code == 201 else "ERRO Ao cadastrar Clinte")
    print("Response:", "201 Criado" if response.status_code == 201 else response.json())

    if response.status_code == 201:
        return "[!] Cliente Cadastrado com Sucesso"
    else:
        return "[!] Erro ao cadastrar cliente"


def tratar_conjuge(civilStatus: str):
    map = {
        "1": "Solteiro",
        "2": "Casado(a)",
        "3": "Divorciado(a)",
        "4": "Viúvo"
    }
    return map.get(civilStatus, "1") # Retorna 1 caso status civil não for informado/encontrado


def callback_RPC(body):
    print('[!] INICIANDO RPC')
    payload = json.loads(body)
    cliente =json.loads(payload.get('msg'))
    naturalPersonData = cliente.get('naturalPersonData')
    print(f'[!] Payload Recebido com sucesso !.')
    # Tratando CPF
    cpf = naturalPersonData.get('cpf')
    cpf_limpo = validar_e_limpar_cpf(cpf)
    # Tratando Status Civil
    civilStatus = naturalPersonData.get('civilStatus')
    print(f'AQUI O STATUS CIVIL {civilStatus}', flush=True)

    response = {"cpf": cpf_limpo}
    
    print(f"> Cliente recebido para verificar no Sienge < {cpf_limpo}")
    status, resultado = consultarapi(cpf_limpo)
    print(f'[!] RESULTADO DO GET: {resultado}')

    if not status:
        print(f"FALHA NA CONSULTA DO SIENGE {resultado}")
        return
    
    if "results" in resultado:
        cadastro = resultado.get('results')
        if cadastro == []:
            print(f'Cliente Não Cadastrado {cpf_limpo}')
    else:
        raise(f"RESULTS NA EXISTE NA RESPOSTA: {cpf_limpo}")
    
    print(f'CADASTRO: {cadastro}')

    if not len(cadastro) == 0:
        print("Cliente Já existe !")

    try:
        cadastrar_cliente(body)
    except ValueError as err:
        print(f'[ERRO] Erro ao cadastrar cliente', err, flush=True)
        return

    return json.dumps(response)

############# MAIN #############
try :
    RPC = RPCExchange2(amqps        = amqps,
                       origin       = host,
                       system       = system,
                       service      = 'integradorcliente',
                       version      = version,
                       workfunction = callback_RPC)
except Exception as ex:
    print("[!] Erro ao receber payload")

try:
    RPC.start_consuming()
except Exception as ex:
    print(f'[ERRO] Erro ao tentar consumir {ex}')
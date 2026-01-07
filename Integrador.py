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


def callback_RPC(body):
    print('[!] INICIANDO RPC')
    payload = json.loads(body)
    cliente =json.loads(payload.get('msg'))
    naturalPersonData = cliente.get('naturalPersonData')
    print(f'ESTÁ CHEGANDO AQUI: {naturalPersonData}')
    cpf = naturalPersonData.get('cpf')
    cpf_limpo = validar_e_limpar_cpf(cpf)
    print(cpf_limpo)
    response = {"cpf": cpf_limpo}
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
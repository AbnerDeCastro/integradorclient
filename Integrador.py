from Exchange2 import RPCExchange2
import json, requests, re
import re
from utilities import*

amqps = 'amqps://vlguashe:7MvzDbMfN6oQ2NyAZoDyZw_oKTWhvm43@jackal.rmq.cloudamqp.com/vlguashe'
origin = 'pc-abner'
system = 'cadastro-cliente'
service = 'integrador'
version = 'V1.01 - Integrador De Cliente'
host = 'kuririn'

# Consulta API SIEGNE

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
    print(f'AQUI O STATUS CIVIL {civilStatus}')

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
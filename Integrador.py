from Exchange2 import RPCExchange2
import json, requests, re

amqps = 'amqps://vlguashe:7MvzDbMfN6oQ2NyAZoDyZw_oKTWhvm43@jackal.rmq.cloudamqp.com/vlguashe'
origin = 'pc-abner'
system = 'cadastro-cliente'
service = 'integrador'
version = 'V1.01 - Integrador De Cliente'
host = 'kuririn'

def callback_RPC(boddy):
    print('[!] INICIANDO RPC')
    payload = json.loads(boddy)
    cliente = json.loads(payload.get('msg'))
    print(cliente)
    cpf = cliente.get('naturalPersonData')
    print(cpf)

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
    print(f'[ERRO] Erro ao tentar consumir: {ex}')
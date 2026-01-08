from Exchange2 import *
import fastapi
from fastapi import FastAPI
import json

app = FastAPI()

version = 'V1.01 - Integrador De Cliente'
service = 'endpoit'
system = 'cadastro-cliente'
host = 'pc-abner'

# CRIANDO CONEXÃO RPC
amps = 'amqps://vlguashe:7MvzDbMfN6oQ2NyAZoDyZw_oKTWhvm43@jackal.rmq.cloudamqp.com/vlguashe'
try:
    RPC = RPCExchange2(amqps    = amps,
                       origin   = host,
                       system   = system,
                       service  = 'integradorcliente',
                       version  = version)
except Exception as ex:
    print(f'[!] RPC Offiline ->', ex)

@app.post("/cadastro-cliente")
def get_idCliente(body: dict):

    print('REQUISIÇÃO RECEBIDA PARA CADASTRO', flush= True)
    print(f'Payload Recebido: {body}')

    response = RPC.callRPC(message=json.dumps(body), timeout=10)
    return {"message": "Integracao Cliente Endpoint is running",
            "menssagem": "Cliete Cadastrado com Sucesso",
            "resposta_rpc": response
            }

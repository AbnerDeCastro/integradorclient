from Exchange2 import *
import fastapi
from fastapi import FastAPI
import json
from pydantic import BaseModel, model_validator
from typing import List, Optional

app = FastAPI()

version = 'V1.01 - Integrador De Cliente'
service = 'endpoit'
system = 'cadastro-cliente'
host = 'pc-abner'

#------CRIANDO OBJETO A SER ENVIADO SIENGE ---------

# -------------------Address------------------------

class Address(BaseModel): 
      type              : str | None = None
      streetName        : str | None = None
      number            : str | None = None
      complement        : str | None = None
      neighborhood      : str | None = None
      cityId            : str | None = None
      city              : str | None = None
      state             : str | None = None
      zipCode           : str | None = None

# ---------- Phone ----------

class Phone(BaseModel): 
      number          : str | None = None
      main            : bool | None = None
      type            : str | None = None
      note            : str | None = None
      idd             : str | None = None

# ---------- Spouse Address ----------

class SpouseAddress(BaseModel): 
      city                    : str | None = None
      complement              : str | None = None
      neighborhood            : str | None = None
      number                  : str | None = None
      streetName              : str | None = None
      zipCode                 : str | None = None

# ---------- Spouse ----------

class Spouse(BaseModel)    : 
      foreigner            : str | None = None
      internationalId      : str | None = None
      cpf                  : str | None = None
      name                 : str | None = None
      email                : str | None = None
      sex                  : str
      civilStatus          : str | None = None
      birthDate            : str | None = None
      numberIdentityCard   : str | None = None
      issueDateIdentityCard: str | None = None
      profession           : str | None = None
      nationality          : str | None = None
      birthPlace           : str | None = None
      fatherName           : str | None = None
      motherName           : str | None = None
      cellphoneNumber      : str | None = None
      businessPhone        : str | None = None
      company              : str | None = None
      addresses            : SpouseAddress | None = None

# ---------- Natural Person Data ----------

class NaturalPersonData(BaseModel): 
      name                        : str
      email                       : str | None = None
      birthDate                   : str | None = None
      birthPlace                  : str | None = None
      civilStatus                 : str | None = None
      cpf                         : str
      mailingAddress              : str | None = None
      licenseNumber               : str | None = None
      licenseIssuingBody          : str | None = None
      licenseIssueDate            : str | None = None
      fatherName                  : str | None = None
      sex                         : str
      issueDateIdentityCard       : str | None = None
      matrimonialRegime           : str | None = None
      marriageDate                : str | None = None
      issuingBody                 : str | None = None
      nationality                 : str | None = None
      numberIdentityCard          : str | None = None
      motherName                  : str | None = None
      profession                  : str | None = None
      spouse                      : Spouse | None = None

# ---------- Root Model ----------
class Person(BaseModel): 
      personType       : str
      addresses        : list[Address] | None = None
      phones           : list[Phone] | None = None
      naturalPersonData: NaturalPersonData | None = None

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
    msg = json.loads(response).get('msg')
    retorno = json.loads(msg)

    return {"message": "Integracao Cliente Endpoint is running",
            "menssagem": "Cliete Cadastrado com Sucesso",
            "resposta_rpc": retorno
            }

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

# Criando Objeto de Cliente para consumo SIENGE

class Address(BaseModel):
    type: Optional[str] = None
    streetName: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    neighborhood: Optional[str] = None
    cityId: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None

class Phone(BaseModel):
    number: str
    main: Optional[bool] = None
    type: Optional[str] = None
    note: Optional[str] = None
    idd: Optional[str] = None

class NaturalPersonData(BaseModel):
    name: str
    email: Optional[str] = None
    birthDate: Optional[str] = None
    birthPlace: Optional[str] = None
    civilStatus: Optional[str] = None
    cpf: str
    mailingAddress: Optional[str] = None
    licenseNumber: Optional[str] = None
    licenseIssuingBody: Optional[str] = None
    licenseIssueDate: Optional[str] = None
    fatherName: Optional[str] = None
    sex: Optional[str] = None
    issueDateIdentityCard: Optional[str] = None
    matrimonialRegime: Optional[str] = None
    marriageDate: Optional[str] = None
    issuingBody: Optional[str] = None
    nationality: Optional[str] = None
    numberIdentityCard: Optional[str] = None
    motherName: Optional[str] = None
    profession: Optional[str] = None
    # spouse: Optional[Spouse] = None

class Agent(BaseModel):
    id: int

class LegalPersonData(BaseModel):
    name: str
    email: Optional[str] = None
    cityRegistrationNumber: Optional[str] = None
    cnaeNumber: Optional[str] = None
    cnpj: str
    contactName: Optional[str] = None
    creaNumber: Optional[str] = None
    establishmentDate: Optional[str] = None
    fantasyName: Optional[str] = None
    note: Optional[str] = None
    site: Optional[str] = None
    shareCapital: Optional[float] = None
    stateRegistrationNumber: Optional[str] = None
    technicalManager: Optional[str] = None
    agents: Optional[List[Agent]] = None


class Spouse(BaseModel):
    foreigner: Optional[str] = None
    internationalId: Optional[str] = None
    cpf: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    sex: Optional[str] = None
    civilStatus: Optional[str] = None
    birthDate: Optional[str] = None
    numberIdentityCard: Optional[str] = None
    issueDateIdentityCard: Optional[str] = None
    profession: Optional[str] = None
    nationality: Optional[str] = None
    birthPlace: Optional[str] = None
    fatherName: Optional[str] = None
    motherName: Optional[str] = None
    cellphoneNumber: Optional[str] = None
    businessPhone: Optional[str] = None
    company: Optional[str] = None
    addresses: Optional[Address] = None


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

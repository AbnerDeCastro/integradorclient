from Exchange2 import RPCExchange2
import json, requests, re
import re
from utilities import*
from pydantic import BaseModel, ValidationError
from Main import Person, NaturalPersonData, Phone, Address
from BrasilAPI import *

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
    zipCode = cliente.get('addresses')[0].get('zipCode')
    print(f'AQUI O TYPE DO CEP {type(zipCode)}', flush= True)
    print(f'[!] Payload Recebido com sucesso !.')
    # Tratando CPF
    cpf = naturalPersonData.get('cpf')
    cpf_limpo = validar_e_limpar_cpf(cpf)
    print(f"AQUI O CPF: {cpf}")
    print(f"AQUI O CPF LIMPO: {cpf_limpo}")
    print(f'AQUI O ZIPCODE {zipCode}')
    print(f'AQUI O CEP COM A API {get_cep(zipCode)}')
    # Tratando Status Civil
    civilStatus = naturalPersonData.get('civilStatus')
    # print(f'AQUI O STATUS CIVIL {civilStatus}', flush=True)

    response = {"cpf": cpf_limpo}
    
    print(f"> Cliente recebido para verificar no Sienge < {cpf_limpo}")
    status, resultado = consultarapi(cpf_limpo)
    # print(f'[!] RESULTADO DO GET: {resultado}')

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
        # print(f"Cliente Já existe ! {cadastro}")
        id_cliente = cadastro[0]['id'] # ID do cliente caso já tenha CADASTRADO
        print(f'AQUI O ID DO CLIENTE {id_cliente}')

        return json.dumps({"id": id_cliente})
    
    # VALIDANDO ENDECO
    try:
        print("VALIDANDO ENDERECO",flush=True)
        if 'addresses' not in cliente:
            print("SEM ENDEREÇO", flush=True)
            return
        endereco = cliente['addresses'][0]
        # Descobre cidade e estado pelo CEP
        cidade, estado = get_city_state_by_cep(zipCode)

        # Busca o cityId correto no Sienge
        city_id = get_city_id_sienge(cidade, estado)

        # Monta endereço válido para o Sienge
        addresses = Address(
            type         = endereco['type'],
            streetName   = endereco['streetName'],
            number       = endereco['number'],
            complement   = endereco.get('complement'),
            neighborhood = endereco['neighborhood'],
            cityId       = city_id,
            city         = cidade,
            state        = estado,
            zipCode      = endereco['zipCode']
        )
    except ValidationError as err:
        print(f"ERRO DE VALIDAÇÃO: ", err, flush=True)
        return
    
    try:
        print("VALIDANDO TELEFONE", flush=True)
        if 'phones' not in cliente:
            print("SEM TELEFONE", err, flsuh=True)
            return
        telefone = cliente['phones'][0]
        phone = Phone(
                number = telefone['number'],
                main   = telefone['main'],
                type   = telefone['type'],
                note   = telefone['note'],
                idd    = telefone['idd']
            )
    except ValidationError as err:
        print(f"ERRO DE VALIDAÇÃO: ", err, flush=True)
        return

    try:
        print("MONTANDO MODELO DE CLIENTE", flush= True)
        if 'naturalPersonData' not in cliente:
            print("SEM INFORMAÇÕES DE PESSOA FÍSICA", flsuh = True)
            return 
        naturalPersonData = NaturalPersonData(
            name                  = cliente['naturalPersonData']['name'],
            email                 = cliente['naturalPersonData']['email'],
            birthDate             = cliente['naturalPersonData']['birthDate'],
            birthPlace            = cliente['naturalPersonData']['birthPlace'],
            civilStatus           = normalizar_estado_civil(cliente['naturalPersonData']['civilStatus']),
            cpf                   = cpf_limpo,
            mailingAddress        = cliente['naturalPersonData']['mailingAddress'],
            licenseNumber         = cliente['naturalPersonData']['licenseNumber'],
            licenseIssuingBody    = cliente['naturalPersonData']['licenseIssuingBody'],
            licenseIssueDate      = cliente['naturalPersonData']['licenseIssueDate'],
            fatherName            = cliente['naturalPersonData']['fatherName'],
            sex                   = cliente['naturalPersonData']['sex'],
            issueDateIdentityCard = cliente['naturalPersonData']['issueDateIdentityCard'],
            matrimonialRegime     = cliente['naturalPersonData']['matrimonialRegime'],
            marriageDate          = cliente['naturalPersonData']['marriageDate'],
            issuingBody           = cliente['naturalPersonData']['issuingBody'],
            nationality           = cliente['naturalPersonData']['nationality'],
            numberIdentityCard    = cliente['naturalPersonData']['numberIdentityCard'],
            motherName            = cliente['naturalPersonData']['motherName'],
            profession            = consultar_todas_profissoes(cliente['naturalPersonData']['profession']),
            spouse                = tratar_conjuge(cliente['naturalPersonData']['spouse'])
        )

    except ValidationError as err:
        print(f"ERRO NATURALPERSONDATA", err, flush=True)
        return
    print("NATURALPERSONDATA VALIDADO COM SUCESSO", flush=True)

    # VALIDANDO PERSONTYPE
    try:
        print("VALIDANDO PERSONTYPE", flush=True)
        if 'personType' not in cliente:
            print("SEM PERSONTYPE", err, flush=True)
            return
        personType = cliente['personType']
    except ValidationError as err:
        print(f"ERRO DE VALIDAÇÃO:", err, flush=True)
        return


    # MONTANDO MODELO DE CLIENTE PARA ENVIO      
    try:
        print("MONTANDO MODELO DE CLIENTE PARA ENVIO", flush=True)
        insert_cliente = Person (
            personType=cliente['personType'],
            addresses = [addresses],
            phones = [phone],
            naturalPersonData = naturalPersonData
        )
        print(f'MODELO DE CLIENTE PARA ENVIO SENDO PRINTADO AQUI {insert_cliente}', flush=True)
        print(type(insert_cliente), flush = True)
        
    except ValidationError as err:
        print(f"[ ! ] ERRO DE FROMACAO DE MODELO CLIENTE: ", err, flush=True)
        return
    except Exception as ex:
        print(f"[ ! ] ERRO INESPERADO: ", ex, flush=True)
        return
    print("MODELO DE CLIENTE MONTADO COM SUCESSO", flush=True)
    
    # CADASTRANDO CLIENTE
    try:
        cadastrar_cliente(insert_cliente.model_dump())
    except ValidationError as err:
        print(f"[ ! ] ERRO AO CADASTRAR CLIENTE:", err, flush=True)
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
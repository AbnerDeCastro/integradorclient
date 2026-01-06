import json, time, sys, inspect, os
import hmac, hashlib, uuid, re

import pika, pprint
from datetime import datetime
from pytz import timezone
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

versao = "v1.0.0 14/12/2023 - Baltazar - Prefetch count"
versao = "v1.1.0 06/02/2024 - MJ. - Detecta Serviço rabbitmq ausente no inicio"
versao = "v1.2.0 20/02/2024 - MJ. - Possibilita uma taksqueue por serviço"
versao = "v1.3.0 06/03/2024 - MJ. - Verboso apenas nos erros"
versao = "v1.5.0 07/03/2024 - MJ. - External Rabbitmq Connection"
versao = "v1.6.0 26/06/2024 - MJ. - Conversao dos parametros host, service e client para lowercase"
versao = "v1.7.0 26/07/2024 - MJ. - Prepacao para utilizar Cloudamqp ou Rabbitmq local amqps/system"
versao = "v2.0.0 16/08/2024 - MJ. - Nova classe RPC e restruturação de Exchange2 e Tasks"
versao = "v2.1.0 21/11/2024 - MJ. - Clareza no log e tratamento de erros"
versao = "v2.2.0 31/01/2025 - MJ. - Remoção de alguns logs e melhorias de performance"
versao = "v2.3.0 12/02/2025 - MJ. - Melhorias na conexão com o Rabbitmq"
versao = "v2.4.0 14/02/2025 - MJ. - Check amqp url parameters"
versao = "v2.4.1 19/02/2025 - MJ. - Correcao prefetch_count=1"
versao = "v2.5.1 13/05/2025 - MJ. - Payload até 128kb - ajuste documentação e visual"

def is_amqp_url(url):
    pattern = r"^amqps?:\/\/([a-zA-Z0-9_\-\.]+):([^@]+)@([a-zA-Z0-9_\-\.]+)(:[0-9]+)?(\/[a-zA-Z0-9_\-\.]*)?$"
 
    return bool(re.match(pattern, url))

# QUEUE EXCHANGE - Apoia no comunicação inter-serviços de um sistema
# EXCHANGE TIPO DIRECT 
# NAO DURAVEL - EXCLUSIVO - AUTODELETE
# SE NAO HOUVER QUEM RECEBA A MSG A MSG SERÁ PERDIDA -> O ENVIO FUNCIONA MESMO QUE NINGUEM EXISTA PARA RECEBER 
class QueueExchange2:
    def __init__(   self, 
                    amqps:str, 
                    origin:str, 
                    system:str, 
                    service:str, 
                    version:str, 
                    client:str = '#', 
                    callback: object = None, 
                    delivery_mode = 1):

        paramOK = len(service) and len(system) and len(amqps) and len(origin) and len(version)            
        if not (paramOK) or not is_amqp_url(amqps):
            if not is_amqp_url(amqps):
                msg = f"NOT A VALID AMQP URL: {amqps}"
            else:
                msg = f"VERIFY PARAMETERS: is_amqp_url: {is_amqp_url(amqps)}\n amqps[{amqps}]\n origin[{origin}]\n system[{system}]\n service[{service}]\n version[{version}]"
            raise Exception(msg)

        self.delivery  = delivery_mode
        self.payload   = ""
        self.hmac      = ""
        self.version   = version
        self.serviceid = ""
        self.type      = "msg"
        self.origin    = origin.lower()
        self.client    = client.lower()
        self.service   = service.lower()
        self.system    = system.lower()
        self.client    = client
        self.params    = pika.URLParameters(amqps)
        self.callback  = callback
        self.queue     = f"{self.system}_{service}_{self.client}" if client != '#' else f"{self.system}_{service}"
        if callback is not None:
            try:
                self.connection = pika.BlockingConnection(self.params)
                self.channelIn  = self.connection.channel() # start main channel
                self.channelIn.exchange_declare (exchange   = f"{self.system}.direct", exchange_type = 'direct')
                self.channelIn.queue_declare    (queue      = self.queue,  durable       = True)
                self.channelIn.queue_bind       (queue      = self.queue,  exchange      = f"{self.system}.direct", routing_key= self.queue)
                self.channelIn.basic_qos        (prefetch_count=1)
                self.consumerTag = self.channelIn.basic_consume (queue    = self.queue, 
                                                                 auto_ack = False,
                                                                on_message_callback = self.callback)
            except Exception as error:
                raise(error)
        else: 
            conexao = pika.BlockingConnection(self.params) #testa conexao
            conexao.close()                

    def cancel(self):
        self.channelIn.basic_cancel(self.consumerTag)

    # METODOS INTERNOS _
    # MODELO MSG QUE TRAFEGA ENTRE SERVIÇOS E CONTROLLER
    """
    MSG JSON CONTROLADOR
    data:
    {
    "salesContractId": <int>,
    "client":       "bambui",
    "service":    "SALES_CONTRACT_CREATED"
    }

    message:
    { ...,
    "serviceid": <registred uuid within controller>,
    "payload":   aes-256 <data>,
    "hmac":      hmac <payload>,
    "type":      "work",
    ...
    }
    """
    def _setMsg(self, msg:str, caller:str):
        now = datetime.now(timezone('America/Sao_Paulo'))
        message =msg.strip('"')

        self.Msg = {
            "system":    self.system,
            "target":    self.target, 
            "service":   self.service,
            "serviceid": self.serviceid,
            "payload":   self.payload,
            "hmac":      self.hmac,
            "type":      self.type,
            "version":   self.version,
            "origin":    self.origin,
            "client":    self.client,      
            "caller":    caller,            
            "logDate":   f"{now}",          
            "msg":       f"{message}"                      
        }

    # Envia uma mensagem para um serviço associado ao sistema
    # controller é o nome padrão do serviço, caso nao seja informado
    def sendMsg(self, message: str, service:str = 'controller'):
        trials      = 5
        waitTime    = 12
        messageSent = False
        caller      = inspect.stack()[1].function
        if caller == '<module>': caller = 'main'

        self.target = service
        self._setMsg(message, caller)
        targetQueue = f"{self.system}_{self.target}_{self.client}" if self.client != '#' else f"{self.system}_{self.target}"
        while not messageSent and trials:
            try:
                connection = pika.BlockingConnection(self.params)
                channelOut = connection.channel()                  # start a channel
                #channelOut.exchange_declare(exchange = f"{self.system}.direct", exchange_type = 'direct')
                #channelOut.queue_declare   (queue= targetQueue, durable= True)
                #channelOut.queue_bind      (queue= targetQueue, exchange= f"{self.system}.direct", routing_key= targetQueue)
                channelOut.basic_publish(
                    exchange    = f"{self.system}.direct", 
                    routing_key = targetQueue, 
                    body        = json.dumps(self.Msg), 
                    properties  = pika.BasicProperties(content_type = 'text/plain', delivery_mode= self.delivery))
                messageSent = True
                connection.close()
            except Exception as ex:
                print(f"EXCH2: TROUBLE CNX RABBITMQ REMAIN ATTEMPT: {trials}")
                print(ex, flush=True)
                sys.stdout.flush()
                time.sleep(waitTime)
                trials -= 1
        if messageSent:
            self.payload = ""
            self.hmac    = ""
        else:
            print(f"EXCH2: ERROR MESSAGE NOT SENT TO [{targetQueue}]", flush=True)

    def start_consuming(self):
        if self.callback is not None:
            self.consumerTag = self.channelIn.start_consuming()

    def setCrypto(self, serviceid:str, servicekey:str):
        self.serviceid  = serviceid
        self.servicekey = servicekey
        self.Crypto     = Payload(serviceid, servicekey) 

    def setPayload(self, data:str):
        try:
            self.hmac    = ""
            self.payload = ""
            self.hmac, self.payload = self.Crypto.setPayload(data)
        except Exception as ex:
            print(f"EXCH2: CRYPTO ERROR: {ex}", flush=True)

    def getPayload(self, hmac:str, safeData:str):
        try:
            self.hmac    = ""
            self.payload = ""
            self.hmac, self.payload = self.Crypto.getPayload(safeData)
        except Exception as ex:
            print(ex)
            return False

        return hmac == self.hmac

# CRIPTOGRAFIA DO PAYLOAD
class Payload:
    def __init__(self, serviceid:str, servicekey:str):
        self.serviceid  = serviceid
        self.servicekey = servicekey
        
    
    def setPayload(self, data:str):
        data     = data.encode('utf-8')
        tamanho  = len(data)
        if tamanho > 65536 * 2 or tamanho <= 0:
            raise Exception("EXCHANGE2 Payload setPayload: Invalid Payload size")

        hmacData= hmac.new(self.serviceid.encode('utf-8'), data, 'sha256').hexdigest()
        iv       = os.urandom(16)
        padder   = padding.PKCS7(128).padder()
        datarw   = padder.update(data) + padder.finalize()
        cipher   = Cipher(algorithms.AES(self.servicekey.encode('utf-8')), modes.CBC(iv))
        encrypt  = cipher.encryptor()
        safeData = encrypt.update(datarw) + encrypt.finalize()
        payload  = (iv + safeData)

        return (hmacData, payload.hex())

    def getPayload(self, safeData:str):
        safeData = bytes.fromhex(safeData)
        iv       = safeData[:16]
        cipher   = Cipher(algorithms.AES(self.servicekey.encode('utf-8')), modes.CBC(iv))
        decrypt  = cipher.decryptor()
        rawdata  = decrypt.update(safeData[16:]) + decrypt.finalize()
        if len(rawdata)%16 != 0:
             raise Exception("EXCHANGE2 Payload getPayload: Invalid Payload size block {0}".format(len(rawdata)))

        unpadder = padding.PKCS7(128).unpadder()
        data     = unpadder.update(rawdata) + unpadder.finalize()
        hmacData = hmac.new(self.serviceid.encode('utf-8'), data, 'sha256').hexdigest()
   
        return (hmacData, data.decode('utf-8'))

# TASK EXCHANGE
# PERMITE CRIAR UM DISTRIBUIDOR DE TAREFAS
# O DISTRIBUIDOR DEVE RECEBER UMA FUNCAO DE CALLBACK
class TaskExchange2:
    def __init__(self, 
                amqps:str, 
                origin:str, 
                system:str, 
                service:str, 
                version:str, 
                client:str = '#', callback: object = None, delivery_mode:int = 2):
        paramOK = len(service) and len(system) and len(amqps) and len(origin) and len(version)            
        if not (paramOK) or not is_amqp_url(amqps):
            if not is_amqp_url(amqps):
                msg = f"NOT A VALID AMQP URL {amqps}"
            else:
                msg = f"VERIFY PARAMETERS: is_amqp_url: {is_amqp_url(amqps)}\n amqps[{amqps}]\n origin[{origin}]\n system[{system}]\n service[{service}]\n version[{version}]"
            raise Exception(msg)

        self.delivery  = delivery_mode
        self.payload   = ""
        self.hmac      = ""
        self.version   = version
        self.serviceid = ""
        self.type      = "task"
        self.origin    = origin.lower()
        self.service   = service.lower()
        self.system    = system.lower()
        self.client    = client.lower()
        self.params    = pika.URLParameters(amqps)
        self.callback  = callback
        self.queue     = f'{self.system}_{self.service}_tasks_{client}' if client != '#' else f'{self.system}_{self.service}_tasks'
        if callback is not None:
            self.connection = pika.BlockingConnection(self.params)
            self.channelIn  = self.connection.channel() # start main channel
            self.channelIn.exchange_declare (exchange   = f"{self.system}.direct", exchange_type = 'direct')
            self.channelIn.queue_declare    (queue      = self.queue,  durable       = True)
            self.channelIn.queue_bind       (queue      = self.queue,  exchange      = f"{self.system}.direct", routing_key= self.queue)
            self.channelIn.basic_qos        (prefetch_count=1)
            self.consumerTag = self.channelIn.basic_consume (queue = self.queue, 
                                                             auto_ack = False,
                                                             on_message_callback = self.callback)
        else: 
            conexao = pika.BlockingConnection(self.params) #testa conexao
            conexao.close()
    def _setTask(self, msg:str, caller:str):
        now = datetime.now(timezone('America/Sao_Paulo'))
        message =msg.strip('"')

        self.Msg = {
            "system":    self.system,
            "target":    self.target, 
            "service":   self.service,
            "serviceid": self.serviceid,
            "payload":   self.payload,
            "hmac":      self.hmac,
            "type":      self.type,
            "version":   self.version,
            "origin":    self.origin,
            "client":    self.client,      
            "caller":    caller,            
            "logDate":   f"{now}",          
            "msg":       f"{message}"                      
        }

    def cancel(self):
        self.channelIn.basic_cancel(self.consumerTag)

    def sendTask(self, message:str):
        trials      = 5
        waitTime    = 12
        messageSent = False
        caller      = 'TaskExchange2'
        self.target = 'workers'
        self._setTask(message, caller)

        while not messageSent and trials:
            try:
                connection = pika.BlockingConnection(self.params)
                channelOut = connection.channel()                      # start a channel
                channelOut.exchange_declare(exchange   = f"{self.system}.direct", exchange_type = 'direct')
                channelOut.queue_declare   (queue      = self.queue,  durable  = True)
                channelOut.queue_bind      (queue      = self.queue,  exchange = f"{self.system}.direct", routing_key= self.queue)

                channelOut.basic_publish   (exchange    = f"{self.system}.direct", 
                                            routing_key = self.queue, 
                                            body        = json.dumps(self.Msg), 
                                            properties  = pika.BasicProperties(content_type = 'text/plain', 
                                                                               delivery_mode= self.delivery))
                messageSent = True
                connection.close()
            except Exception as ex:
                print(f"EXCH2: TROUBLE CNX RABBITMQ REMAIN ATTEMPT: {trials}")
                print(ex, flush=True)
                time.sleep(waitTime)
                trials -= 1
        if not messageSent:
            print(f"EXCH2: ERROR TASK NOT SENT TO: {self.queue}", flush=True)

    def start_consuming(self):
        if self.callback is not None:
            print(f"EXCH2: SEND TASKS TO: [{self.queue}]", flush=True)
            self.consumerTag = self.channelIn.start_consuming()

    def setCrypto(self, serviceid:str, servicekey:str):
        self.serviceid  = serviceid
        self.servicekey = servicekey
        self.Crypto     = Payload(serviceid, servicekey) 

    def setPayload(self, data:str):
        try:
            self.hmac    = ""
            self.payload = ""
            self.hmac, self.payload = self.Crypto.setPayload(data)
        except Exception as ex:
            print(f"EXCH2: CRYPTO ERROR: {ex}", flush=True)

    def getPayload(self, hmac:str, safeData:str):
        try:
            self.hmac    = ""
            self.payload = ""
            self.hmac, self.payload = self.Crypto.getPayload(safeData)
        except Exception as ex:
            print(f"EXCH2: CRYPTO ERROR: {ex}", flush=True)
            return False

        return hmac == self.hmac

# RPC - QUANDO FOR UTILIZAR COMO ENDPOINT
# FORNECER FUNCAO DE TRABALHO NA INICIALIZACAO
# COMO RPC Server: FILA ONDE RECEBERA AS TAREFAS => SISTEM_SERVICE_RPC ou SISTEM_SERVICE_RPC_CLIENT
# COMO RPC Client: UTILIZA callRPC
class RPCExchange2:
    def __init__(self, 
                 amqps:str,                # ENDERECO URL RABBITMQ - CLOUDAMQP
                 origin:str,               # NOME DO HOST ONDE O SCRIPT ESTÁ RODANDO
                 system:str,               # NOME DO SISTEMA QUE O SERVIÇO FAZ PARTE
                 service:str,              # NOME DO SERVIÇO DENTRO DO SISTEMA
                 version:str,              # VERSÃO DO SERVIÇO
                 client:str = '#',         # CASO ESPECIFICO A UM CLIENTE, COMO NO CASO DO SG_ETL
                 workfunction=None,        # FUNCAO DE TRABALHO PARA O USO COMO RCP Server, i.e. para substituir um endpoint fastapi
                 delivery_mode=2           # VAI PERSISTIR AS MENSAGENS NO MODO 2
                ):
        paramOK = len(service) and len(system) and len(amqps) and len(origin) and len(version)            
        
        if not (paramOK) or not is_amqp_url(amqps):
            if not is_amqp_url(amqps):
                msg = f"RPCExchange2: NOT A VALID AMQP URL: {amqps}"
            else:
                msg = f"RPCExchange2: VERIFY PARAMETERS: is_amqp_url: {is_amqp_url(amqps)}\n amqps[{amqps}]\n origin[{origin}]\n system[{system}]\n service[{service}]\n version[{version}]"
            raise Exception(msg)
        
        self.callback       = workfunction
        self.delivery       = delivery_mode
        self.payload        = ""
        self.hmac           = ""
        self.version        = version
        self.serviceid      = ""
        self.servicekey     = ""
        self.correlation_id = ""
        self.consumerTag    = None
        self.type           = "rpc"
        self.origin         = origin.lower()
        self.service        = service.lower()
        self.system         = system.lower()
        self.client         = client.lower()
        self.params         = pika.URLParameters(amqps)
        # Server ouve nessa fila - Cliente publica nesta fila
        self.queue          = f'{self.system}_{self.service}_rpc_{client}' if client != '#' else f'{self.system}_{self.service}_rpc'
        self.connection     = pika.BlockingConnection(self.params)
        self.channel        = self.connection.channel() # start main channel
        self.channel.exchange_declare (exchange = f"{self.system}.direct", exchange_type = 'direct')

        if (workfunction is not None):   # FUNCIONAMENTO COMO RPC SERVER
            self.target = 'rpcclt'       # SINALIZA O DESTINO DA MSG SER UM RPC CLIENT
            self.channel.queue_declare (queue          = self.queue, exclusive = False, durable=True, auto_delete = True)  
            self.channel.queue_bind    (exchange       = f"{self.system}.direct", queue = self.queue, routing_key = self.queue)
            self.channel.basic_qos     (prefetch_count = 1)
            self.consumerTag = self.channel.basic_consume(queue               = self.queue, 
                                                          auto_ack            = True,
                                                          on_message_callback = self._RPCResp) # de lá chamamos self.callback
        else:                            # FUNCIONAMENTO COMO RPC CLIENT
            self.target = 'rpcsrv'       # SINALIZA O DESTINO DA MSG SER UM RPC SERVER

            # PREPARA QUEUE DE RETORNO
            result              = self.channel.queue_declare(queue='', exclusive=True, auto_delete=True)
            self.callback_queue = result.method.queue
            self.channel.queue_bind(exchange    = f"{self.system}.direct", 
                                    queue       = self.callback_queue, 
                                    routing_key = self.callback_queue)

            self.channel.basic_consume(
                queue               = self.callback_queue,
                on_message_callback = self._on_response,
                auto_ack            = True
            )
            #print("EXCH2: RPC CLT - QUEUE:", self.callback_queue, flush=True)

    # RPC - QUANDO FOR UTILIZAR COMO ENDPOINT  
    def _RPCResp(self, ch, method, props, body):
        #ch.basic_ack(delivery_tag = method.delivery_tag)
        message        = body.decode("utf-8")
        reply_to       = getattr(props, 'reply_to', None)
        correlation_id = getattr(props, 'correlation_id', None)
        resposta       = "{}" # SEM WORKFUNCTION
        # ENVIA A MENSAGEM AO CALLBACK
        try:
            if self.callback is not None:
                resposta = self.callback(message)
                rspObj   = json.loads(resposta)
                # para enviar um payload criptografado na resposta ao caller
                # retorne um objeto contendo serviceid, servicekey e payload
                # essas chaves serao retiradas do objeto e o restante da informacao
                # irá no chave msg
                if 'payload' in rspObj and 'serviceid' in rspObj and 'servicekey' in rspObj:
                    self.setCrypto(rspObj['serviceid'], rspObj['servicekey'])
                    self.setPayload(json.dumps(rspObj['payload']))
                    rspObj.pop('payload',    None)
                    rspObj.pop('serviceid',  None)
                    rspObj.pop('servicekey', None)
                    resposta = json.dumps(rspObj)

                
        except Exception as ex:
            erro = f"ERROR CALLBACK: {str(ex)}"
            print(erro, flush=True)
            raise Exception(erro)

        # ENVIA RESPOSTA AO CALLER
        msg = json.loads(message)
        msg = msg['msg']
        #print(f"RPC <== {msg}", flush=True)
        #print(f"RPC ==> {resposta}", flush=True)
        try:        
            if reply_to:
                self.target = "rpcclt"
                self._setJSON(resposta, 'RPCResp')

                ch.basic_publish(exchange   = f"{self.system}.direct", 
                                routing_key = reply_to, 
                                body        = json.dumps(self.Msg), 
                                properties  = pika.BasicProperties(content_type   = 'application/json', 
                                                                   delivery_mode  = self.delivery,
                                                                   correlation_id = correlation_id))
            else:
                print(f"RPCExchange2: NO TARGET FOUND: {resposta}", props, flush=True)

        except Exception as ex:
            print(ex)
            resposta = f"RPCExchange2: ERRO MSG CALLER: {str(ex)}"
            raise Exception(resposta)


    def _setJSON(self, msg:str, caller:str):
        now = datetime.now(timezone('America/Sao_Paulo'))
        message =msg.strip('"')

        self.Msg = {
            "system":           self.system,
            "target":           self.target, 
            "service":          self.service,
            "serviceid":        self.serviceid,
            "payload":          self.payload,
            "hmac":             self.hmac,
            "type":             self.type,
            "correlation_id":   self.correlation_id,
            "version":          self.version,
            "origin":           self.origin,
            "client":           self.client,      
            "caller":           caller,            
            "logDate":          f"{now}",          
            "msg":              f"{message}"                      
        }
        self.hmac    = ""
        self.payload = ""


    def _on_response(self, ch, method, properties, body):
        try:
            if self.correlation_id == properties.correlation_id:
                self.response = body.decode("utf-8")
        except Exception as ex:
            print(f"RPCExchange2: RPC ERROR: {ex}", flush=True)
            sys.exit(0)

        return self.response

    # ENVIA A MENSAGEM AO CALLBACK
    # RPC CLIENT CHAMA O RPC SERVER
    def callRPC(self, message:str, timeout:int=10):
        # ENVIA A MENSAGEM
        self.response       = None
        self.correlation_id = str(uuid.uuid4())
        self._setJSON(message, 'callRPC')        # COLOCA A message DENTRO DA CHAVE msg em self.Msg

        self.channel.exchange_declare(exchange = f"{self.system}.direct", exchange_type = 'direct')
        self.channel.queue_declare   (queue= self.queue, durable=True, exclusive=False, auto_delete=True)
        self.channel.queue_bind      (queue= self.queue, exchange= f"{self.system}.direct", routing_key= self.queue)

        self.channel.basic_publish (exchange    = f"{self.system}.direct", 
                                    routing_key = self.queue, 
                                    body        = json.dumps(self.Msg), 
                                    properties  = pika.BasicProperties(content_type  = 'application/json',
                                                                       delivery_mode = self.delivery,
                                                                       reply_to      = self.callback_queue,
                                                                       correlation_id= self.correlation_id))
        # AGUARDA O RETORNO
        while self.response is None:
            self.connection.process_data_events(time_limit=timeout)
        return self.response

    def cancel(self):
        print(f"RPCExchange2: CONSUMER TAG CANCELED: {self.consumerTag}", flush=True)
        self.channel.basic_cancel(self.consumerTag)

    def start_consuming(self):
        if self.callback is not None:
            print(f"RPCExchange2: {self.service.upper()} RPC SRV QUEUE: [{self.queue}]", flush=True)
            self.channel.start_consuming()

    def setCrypto(self, serviceid:str, servicekey:str):
        self.serviceid  = serviceid
        self.servicekey = servicekey
        self.Crypto     = Payload(serviceid, servicekey) 

    def setPayload(self, data:str):
        print(f"RPCExchange2: SET PAYLOAD", flush=True)
        try:
            self.hmac    = ""
            self.payload = ""
            self.hmac, self.payload = self.Crypto.setPayload(data)
        except Exception as ex:
            print(ex)

    def getPayload(self, hmac:str, safeData:str):
        print(f"RPCExchange2: GET PAYLOAD", flush=True)
        try:
            self.hmac    = ""
            self.payload = ""
            self.hmac, self.payload = self.Crypto.getPayload(safeData)
        except Exception as ex:
            print(ex)
            return False

        return hmac == self.hmac
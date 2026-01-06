import json,time, os, sys
from datetime import datetime

from pytz import timezone
import pprint
import inspect
import pika
from pika.exceptions import StreamLostError
from pydantic import BaseModel, ValidationError
import logging

versao = "v1.0 Fecha a conexao apos envio da mensagem"
versao = "v1.1 Prioriza log local antes de envio para messageria"
versao = "v1.2 Deleta explicitamente a conexao com a messageria"
versao = "v1.21 bug {trial}"
versao = "v1.3 Melhora o arquivo de logs removendo info dos modulos importados"
versao = "v1.31 Aceita a key setup para colaborar com a configuração das chaves"
versao = "v1.32 09/01/24 MJ. Bug Duplicação do handler logging.info"
versao = "v1.40 06/02/24 MJ. String de conexao (amqps) para messageria"
versao = "v1.41 09/02/24 MJ. Retirada de sys.stdout.flush()"
versao = "v1.42 11/02/24 MJ. Controle de sys.stdout.flush()"
versao = "v1.43 13/02/24 MJ. Guarda amqps em variavel"
versao = "v1.44 14/03/24 MJ. Flush True"
versao = "v1.51 20/06/24 MJ. Campos origem, versao, restricao messageria, remocao de logTypeList"
versao = "v1.52 24/06/24 MJ. logger.exchange.setLogType 25 caracteres maximo"
versao = "v1.53 21/11/24 MJ. Log para saida padrão menos verboso"
versao = "v1.54 19/03/25 MJ. Ajuste do log no momento de conexão ao serviço amqp"
versao = "v2.00 30/09/25 MJ. Logs passam a ser enviados para uma unica conta cloudampq"

# CONFIGURACAO DO EXCHANGE
# SERVICO DE ENVIO DE LOGS
# EXCHANGE TIPO TOPIC
# ROUTEKEY logType:service:system:client  - client é opcional
class Exchange:
    def __init__(self, amqps: str, system: str, service: str, logType: str):
        # Sistema SG_ETL - Tough Tiger - 10M msg/month, 100 conn, 1500 queues w 100k msgs
        self.params     = pika.URLParameters(amqps)
        self.exchange   = 'topic_softgo' 
        self.system     = system
        self.service    = service
        self.logType    = logType
        self.logTypeSvd = logType         
        self.routeKey   = f"{self.logType}.{self.service}.{self.system}" # logs.hash.sg_etl.crescer, status.hash.sg_etl
        self.params.socket_timeout = 5 
        print(f"params: {self.params} amqps: {amqps}", flush=True)

    # Para quando desejar trocar o header do topico
    # Salva o tópico padrão especificado no momento da inicialização
    def setLogType(self, logType:str):
        if len(logType) > 0 and len(logType) <= 25:
            self.logType  = logType
            self.routeKey = f"{self.logType}.{self.service}.{self.system}" 
    
    # Volta ao header topico padrao
    def clrLogType(self):
        self.logType = self.logTypeSvd
        self.routeKey   = f"{self.logType}.{self.service}.{self.system}" # logs.hash.sg_etl.crescer, status.hash.sg_etl
              
    # Funcionamento: caso nao seja possivel enviar a msg, tentar nova conexao
    # e envio da msg original mais uma vez    
    def sendMsg(self, message:str, client:str = ""):
        messageSent = False
        trials      = 5
        waitTime    = 60
        while not messageSent and trials:
            routeKey = self.routeKey
            if len(client) > 0:
                routeKey = f"{self.routeKey}.{client}"

            try:
                connection = pika.BlockingConnection(self.params)
                channel    = connection.channel() # start a channel
                channel.exchange_declare(exchange     = self.exchange, 
                                        exchange_type = 'topic',
                                        auto_delete   = True)
                channel.basic_publish(
                    exchange   = self.exchange, 
                    routing_key= routeKey, 
                    body       = message, 
                    properties = pika.BasicProperties(
                                    content_type = 'text/plain',
                                    delivery_mode= pika.DeliveryMode.Transient))
                messageSent = True
                connection.close()
                del channel, connection 
            except Exception as ex:
                print(f"TROUBLE CNX LOGGER REMAIN ATTEMPT: {trials}", flush=True)
                print(ex, flush=True)
                print(self.params, flush=True)
                time.sleep(waitTime)
                trials -= 1
            
         
class LogService():
    exchange:       Exchange # Servico para envio de logs
    logLocalName:   str      # Nome do arquivo de log em disco
    logLocal:       bool     # Grava ou não em /app/logs, volume do host em docker_compose.yml
    Msg:            object   # Objeto representando a mensagem enviada - customizado pelo usuario
    system:         str      # NOME DO SISTEMA (diretorio/docker-compose) E DO EXCHANGE
    service:        str      # NOME DO SERVIÇO (docker-compose/services)
    client:         str      # NOME DO CLIENTE NO ATENDIMENTO
    erroMsg:        str      # MSG DE ERRO PARA RETORNO CLIENTE
    system:         str      # ID FORNECIDO PELA INSTANCIA
    
    def __str__(self):
        estado = {
            "logLocalName":   self.logLocalName,
            "logLocal":       self.logLocal,
            "system" :        self.system,
            "service":        self.service,
            "version":        self.version,
            "origin":         self.origin,
            "client":         self.client, 
            "erroMsg":        self.erroMsg
        }

        return self.pp.pformat(estado)
    
    def __init__(   self, 
                    system:str, 
                    service:str, 
                    version:str = "",
                    origin:str = "",
                    client:str = "", 
                    logType:str = 'logs', 
                    logLocal:bool = False):
        if not os.path.exists('logs'): os.mkdir('logs')
    
        dt                 = datetime
        self.amqps         = "amqps://sg_ic2:z3Lvt3usa0fRdYd82ZjL69yuR61Mg2@tall-cyan-dog.rmq4.cloudamqp.com/info_connector_host"
        self.system        = system.lower()      
        self.service       = service.lower()
        self.version       = version
        self.origin        = origin
        self.client        = client.lower()
        self.logType       = logType
        self.logLocal      = logLocal
        self.flush         = True
        self.pp            = pprint.PrettyPrinter(indent=4)

        self.logLocalName  = 'logs/'+ self.system.split()[0] + '_' + dt.now().strftime("%d")
        self.logging       = logging.getLogger(system)
        self.logging.setLevel(logging.INFO)
        formatter          = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fhandler           = logging.FileHandler(self.logLocalName)
        fhandler.setLevel(logging.INFO)
        fhandler.setFormatter(formatter)
        if (self.logging.hasHandlers()):
            self.logging.handlers.clear()
        self.logging.addHandler(fhandler)

        self.exchange      = Exchange(amqps=self.amqps, system=self.system, service=self.service, logType= logType) #logs.hash.sg_etl
        self.erroMsg       = "ERRO"            # MSG DE ERRO PARA RETORNO CLIENTE
    
    # PERMITE ALTERAR PARAMETROS DE FLUSH
    # ALTERA A VELOCIDADE DE OPERACAO
    def setFlush(self,  flush: bool):    
        self.flush = flush
        
    # METODOS INTERNOS _
    # Configura informacoes basicas da msg
    def _setMsg(self, msg:str, caller:str):
        now = datetime.now(timezone('America/Sao_Paulo'))  # melhoria: acrescentar timezone info no system_config
        self.Msg = {
            "system":  self.system,      
            "service": self.service,
            "version": self.version,
            "origin":  self.origin,
            "client":  self.client,      
            "caller":  caller,            
            "logDate": f"{now}",          
            "msg":     msg                
        }

    # Envia para LogMessage Msg formatada para messageria
    def _sendMsg (self, msg:str, caller: str, *args):
        message = msg.strip()
        try:
            # outros objetos alem da msg
            arg = args[0]
            if len(arg) > 0:
                for item in arg:
                    msgArg  = pprint.pformat(item).replace("'", "").strip()
                    message = f"{message}, {msgArg}" 

            # prepara msg
            self._setMsg(message, caller)
            # output docker logs ou console    
            self.pp.pprint(f"{self.Msg['logDate'][0:21]} {self.Msg['msg']}")
            # output diretorio de logs
            if self.logLocal: 
                self.logging.info(self.pp.pformat(self.Msg))
            # output para messageria
            self.exchange.sendMsg(json.dumps(self.Msg), self.client)
            # forca atualizacao output
            if self.flush:    
                sys.stdout.flush()
        except Exception as e:
            self.logging.info(self.pp.pformat(e))

    # METODOS DISPONIBILIZADOS #############################################################
    # SINALIZAR SE OS SISTEMAS/SERVICOS ESTAO OPERACIONAIS
    ## INFORM  status.<service>.<system>.# 
    # envia OK para sinalizar serviço ON-LINE
    def heartBeat(self):
        self.exchange.setLogType('status')
        self.logMsg("OK")
        self.exchange.clrLogType()

    # PAINEIS OPERACIONAIS DE SERVICO ACEITAM STATUS DE INICIO, SUCESSO E FALHA
    # INFORM  operational.<service>.<system>.# 
    # envia sucess, start ou failure
    def operational(self, status):
        if not status in ['success', 'start', 'failure']: return
        self.exchange.setLogType('operational')
        self.logMsg(status)
        self.exchange.clrLogType()
        
    # ERROS DE VALIDACAO DE MODELO - PYDANTIC
    # INFORM  error.logs.<service>.<system>.# 
    # Usar quando except ValidationError as e
    # Loga e atualiza errMsg
    def logMsgValidationError(self, msg: str, e):
        self.exchange.setLogType("error.logs")
        # relaciona os erros encontrados na validacao do modelo
        erros = json.loads(e.json())
        erroLst = []
        for err in erros:
            localErro = '_'.join(err['loc'])
            errMsg    = f"{localErro} => {err['msg']}"
            erroLst.append(errMsg)
            
        self.erroMsg = f"{msg} " + ','.join(erroLst)
        bodyMsg      = f"{self.erroMsg}"
        caller       = inspect.stack()[1].function
        if caller == '<module>': caller = 'main'
        
        self._sendMsg(bodyMsg, caller)
        self.exchange.clrLogType()

    # ERROS DE OPERAÇÃO GENÉRICOS
    # INFORM  error.logs.<service>.<system>.#
    # Loga e atualiza errMsg
    def logMsgError(self, msg:str, *args):
        self.exchange.setLogType('error.logs')
        self.erroMsg = msg
        caller       = inspect.stack()[1].function
        if caller == '<module>': caller = 'main'

        Msg          = f"{self.erroMsg}"
        self._sendMsg(Msg, caller, args)
        self.exchange.clrLogType()

    # LOGS GERAIS
    # INFORM  logs.<service>.<system>.#
    # Log geral de acordo com o valor logType
    def logMsg (self, msg: str, *args):
        now = datetime.now()
        caller      = inspect.stack()[1].function
        if caller == '<module>': caller = 'main'
        Msg         = f"{msg}"
        self._sendMsg(Msg, caller, args)


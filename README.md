# 🔗 Integrador de Cliente - Sistema de Integração RPC

Um sistema robusto de integração de clientes que utiliza **RPC (Remote Procedure Call)** com **RabbitMQ** para comunicação assíncrona, desenvolvido em **Python**. Este projeto conecta sistemas de cadastro de clientes através de mensageria, permitindo a sincronização de dados com validações automatizadas.

## 📋 Características

- ✅ **RPC com RabbitMQ**: Comunicação assíncrona entre microsserviços
- 🔍 **Validação de Dados**: Validação automática de CPF, CEP e endereços
- 🌐 **Integração com APIs**: Integração com BrasilAPI e Sienge
- 📝 **Sistema de Logs**: Logging estruturado com rastreamento de requisições
- ⚡ **Processamento Assíncrono**: Callbacks para processamento em tempo real
- 🛡️ **Tratamento de Erros**: Validação robusta com Pydantic

## 🏗️ Arquitetura

### Componentes Principais

```
├── Integrador.py          # Lógica principal de integração e RPC
├── Main.py               # Modelos Pydantic e API endpoints
├── Exchange2.py          # Cliente RPC do RabbitMQ
├── Logger.py             # Sistema de logging centralizado
├── utilities.py          # Funções utilitárias (validações)
├── BrasilAPI.py          # Integração com BrasilAPI
└── exemplo.js            # Exemplo de utilização (frontend)
```

### Fluxo de Dados

```
Cliente → API FastAPI → RabbitMQ (RPC) → Integrador → Sienge API
                                      ↓
                              Callbacks & Logs
```

## 🚀 Instalação

### Pré-requisitos

- Python 3.8+
- RabbitMQ (ou CloudAMQP)
- pip (gerenciador de pacotes Python)

### Passos

1. **Clone o repositório**
   ```bash
   git clone https://github.com/AbnerDeCastro/integradorclient.git
   cd integradorclient
   ```

2. **Crie um ambiente virtual**
   ```bash
   python -m venv env
   ```

3. **Ative o ambiente virtual**
   
   **Windows:**
   ```bash
   .\env\Scripts\Activate.ps1
   ```
   
   **Linux/macOS:**
   ```bash
   source env/bin/activate
   ```

4. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

   Dependências principais:
   - `fastapi` - Framework web
   - `pika` - Cliente RabbitMQ
   - `pydantic` - Validação de dados
   - `requests` - Requisições HTTP
   - `python-dotenv` - Variáveis de ambiente

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# RabbitMQ
AMQP_URL=amqps://usuario:senha@host/vhost

# API Sienge
SIENGE_URL=https://api.sienge.com.br/s8psasistemas/public/api/v1
SIENGE_USERNAME=seu_usuario
SIENGE_PASSWORD=sua_senha

# Configuração da Aplicação
ORIGIN=pc-seu-host
SYSTEM=cadastro-cliente
SERVICE=integrador
VERSION=V1.01
```

### Estrutura de Configuração

O projeto utiliza as seguintes configurações:
- **AMQP**: CloudAMQP para mensageria
- **Exchange**: `topic_softgo` (tipo TOPIC)
- **Routing Key**: `{logType}.{service}.{system}`

## 📖 Uso

### 1. Iniciar o Servidor

```bash
python Main.py
```

O servidor FastAPI estará disponível em `http://localhost:8000`

### 2. Enviar Dados via RPC

O sistema aguarda mensagens no RabbitMQ através da fila RPC. Exemplo de payload:

```json
{
  "msg": {
    "personType": "NATURAL",
    "naturalPersonData": {
      "name": "João Silva",
      "cpf": "123.456.789-00",
      "email": "joao@example.com",
      "sex": "M",
      "birthDate": "1990-01-15",
      "birthPlace": "São Paulo"
    },
    "addresses": [
      {
        "type": "RESIDENTIAL",
        "streetName": "Rua das Flores",
        "number": "123",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "state": "SP",
        "zipCode": "01310-100"
      }
    ],
    "phones": [
      {
        "number": "11999999999",
        "main": true,
        "type": "MOBILE"
      }
    ]
  }
}
```

### 3. Fluxo de Integração

1. **Recebimento**: Sistema recebe mensagem RPC com dados do cliente
2. **Validação**: 
   - Valida CPF (algoritmo verificador)
   - Valida CEP e obtém dados de localização
   - Consulta BrasilAPI para dados complementares
3. **Consulta**: Verifica se cliente já existe no Sienge
4. **Cadastro**: Se novo, realiza cadastro automaticamente
5. **Resposta**: Retorna ID do cliente via callback RPC

## 🔑 Funções Principais

### `callback_RPC(body)`
Callback executado ao receber mensagem RPC. Processa dados do cliente, valida informações e integra com Sienge.

### `validar_e_limpar_cpf(cpf)`
Valida e limpa CPF removendo caracteres especiais. Verifica algoritmo de verificação.

### `consultarapi(cliente)`
Consulta API Sienge para verificar se cliente já está cadastrado.

### `cadastrar_cliente(cliente)`
Realiza cadastro do cliente na API Sienge com validação de resposta.

### `get_cep(zipCode)`
Integração com BrasilAPI para obtenção de dados de localização.

## 📊 Modelos de Dados (Pydantic)

### Address
```python
- type: Tipo de endereço (RESIDENTIAL, COMMERCIAL, etc)
- streetName: Nome da rua
- number: Número
- complement: Complemento
- neighborhood: Bairro
- cityId: ID da cidade no Sienge
- city: Nome da cidade
- state: UF (SP, RJ, etc)
- zipCode: CEP
```

### Phone
```python
- number: Número do telefone
- main: Se é telefone principal
- type: MOBILE, LANDLINE, etc
- idd: Código internacional
```

### NaturalPersonData
```python
- name: Nome completo
- cpf: CPF
- email: Email
- birthDate: Data de nascimento
- sex: M ou F
- civilStatus: SOLTEIRO, CASADO, etc
- [... outros campos opcionais]
```

### Person (Root Model)
```python
- personType: NATURAL ou LEGAL
- addresses: Lista de endereços
- phones: Lista de telefones
- naturalPersonData: Dados da pessoa física
```

## 🧪 Exemplo de Uso (JavaScript/Frontend)

Veja `exemplo.js` para exemplo de como enviar dados para o sistema.

## 📝 Logging

O sistema implementa logging em múltiplos níveis:

- **INFO**: Informações gerais de processamento
- **ERROR**: Erros de validação ou integração
- **DEBUG**: Detalhes de execução

Logs são enviados para:
1. **Local**: Arquivo de log na máquina
2. **Remoto**: RabbitMQ (CloudAMQP) para monitoramento centralizado

## 🔐 Segurança

- Credenciais da API Sienge protegidas em variáveis de ambiente
- Validação de dados de entrada com Pydantic
- RabbitMQ com autenticação AMQPS
- Tratamento de exceções para dados inválidos

## 🐛 Troubleshooting

### Erro de conexão RabbitMQ
```
StreamLostError: Connection lost
```
**Solução**: Verifique credenciais AMQP e conectividade com CloudAMQP

### Erro de validação de CPF
```
CPF inválido: None
```
**Solução**: Envie CPF no formato correto (apenas dígitos ou formatado)

### Erro de CEP não encontrado
```
CEP inválido na API
```
**Solução**: Verifique se o CEP está correto na BrasilAPI

## 📚 Dependências Principais

| Pacote | Versão | Descrição |
|--------|--------|-----------|
| fastapi | 0.128.0+ | Framework web moderna |
| pika | 1.3.2+ | Cliente RabbitMQ |
| pydantic | 2.12.5+ | Validação de dados |
| requests | latest | Requisições HTTP |
| python-dotenv | 1.2.1+ | Variáveis de ambiente |

## 🤝 Contribuindo

1. Faça um Fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👨‍💻 Autor

**Abner de Castro**
- GitHub: [@AbnerDeCastro](https://github.com/AbnerDeCastro)
- Email: abner.decastro@email.com

## 📞 Suporte

Para dúvidas ou problemas, abra uma [Issue](https://github.com/AbnerDeCastro/integradorclient/issues) no repositório.

---

**Versão**: V1.01 - Integrador De Cliente  
**Data**: 2025  
**Última atualização**: Janeiro de 2026

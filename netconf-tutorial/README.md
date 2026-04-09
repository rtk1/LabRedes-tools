## Instalando dependências
#### Usando `uv`:
```
uv sync
```
#### Usando `pip`
```
pip install -r requirements.txt
```

## Testando com o containerlab

O arquivo de topologia do containerlab, `simple-lab.yaml`, pode ser usado para testar as funcionalidades mencionadas anteriormente. Use o `vrnetlab` [doc](https://containerlab.dev/manual/vrnetlab/#vrnetlab) para gerar as imagens VSRX 20.1R1.13 e Huawei NE40E V800R011C00SPC607B607. Então utilize o containerlab para montar o laboratório:
```
containerlab deploy -t simple-lab.yaml
```

O Containerlab exibirá os IPs alocados para cada instância, necessários para a configuração dos testes.

## Testando NETCONF

Espera-se que os dispositivos já estejam configurados com o serviço de NETCONF habilitado.

Altere os arquivos `huawei_device_config.yaml`, `junos_device_config.yaml` e `cisco_device_config.yaml` de acordo com a sua necessidade. Execute o script `netconf_test.py` da seguitne maneira:
```
usage: netconf_test.py [-h] -c CONFIG -p PAYLOAD
argumentos: 
-c CONFIG, --config CONFIG Caminho para o arquivo de configuração YAML 
-p PAYLOAD, --payload PAYLOAD Caminho para o arquivo XML de payload
ex:
python netconf_test.py -c huawei_device_config.yaml -p xml/openconfig-huawei-interface-ip.xml
```

Os payloads de configuração estão na pasta `xml`. A configuração para Huawei foi validada com um Huawei NE40E (Version 8.180 - V800R011C00SPC607B607) emulado. Configuração para JunOS foi validada com um Juniper VSRX (20.1R1.13).

## Obtendo o modelo YANG de dispositivo HUAWEI

Para obter o modelo YANG de um dispositivo Huawei, execute o script `huawei_get_schema.py` da seguinte maneira:
```
usage: huawei_get_schema.py [-h] host username password [output_dir]
argumentos:
  host          Endereço IP ou hostname do dispositivo Huawei
  username      Nome de usuário para autenticação no dispositivo
  password      Senha para autenticação no dispositivo
  output_dir    (Opcional) Caminho para o diretório onde os arquivos YANG serão salvos - default=huawei-schema
ex:
python huawei_get_schema.py 192.168.1.1 admin admin yang_models
```

Os arquivos YANG serão baixados e salvos no diretório especificado.

## Obtendo o modelo YANG de dispositivos Juniper
Nos dispositivos Juniper, podemos gerar o modelo a partir da cli e salvá-lo no armazenamento local do dispositivo e depois fazer o download via `scp`, por exemplo.

Siga as orientações no site da Juniper:
https://www.juniper.net/documentation/us/en/software/junos/netconf/topics/task/netconf-yang-module-obtaining-and-importing.html

Apesar de ser possível obter os modelos por meio de NETCONF, como é feito com o Huawei acima, o JunOS, por padrão, não mostra todos os módulos suportados na mensagem `<hello>`, impedindo-nos de utilizarmos a mesma técnica que foi utilizada com o Huawei.

## Obtendo o modelo YANG de dispositivos Cisco

Para obter o modelo YANG de um dispositivo Cisco, execute o script `cisco_get_schema.py` da seguinte maneira:
```
usage: cisco_get_schema.py [-h] [--port PORT] host username password [output_dir]
argumentos:
  host          Endereço IP ou hostname do dispositivo Cisco
  username      Nome de usuário para autenticação no dispositivo
  password      Senha para autenticação no dispositivo
  output_dir    (Opcional) Caminho para o diretório onde os arquivos YANG serão salvos - default=cisco-schema
  --port        (Opcional) Porta NETCONF - default=830
ex:
python cisco_get_schema.py 192.168.1.2 admin 'senha' cisco-schema --port 830
```

Os arquivos YANG serão baixados e salvos no diretório especificado (quando disponível, o nome seguirá o padrão `<modulo>@<revision>.yang`).

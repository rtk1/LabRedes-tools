# Configuração Transacional Simulada para Dispositivos de Rede

A configuração de múltiplos dispositivos de rede de forma automatizada apresenta um desafio significativo, especialmente quando os sistemas operacionais desses dispositivos não oferecem suporte nativo a um mecanismo de `commit`. Este documento explora como o script `device_configurator.py` aborda esse problema, simulando um comportamento transacional para garantir a integridade e a consistência da rede.

## O Problema: Ausência de Atomicidade

Em muitos dispositivos de rede, cada comando de configuração é aplicado imediatamente e de forma individual. Isso significa que não há uma "área de preparação" (ou *candidate configuration*) onde as alterações possam ser agrupadas e depois aplicadas em um único passo.

Essa abordagem "comando a comando" é problemática em automações complexas:
- **Estado Inconsistente:** Se um script de automação falhar no meio de sua execução, o dispositivo ficará em um estado de configuração parcial, podendo causar instabilidade ou comportamento inesperado na rede.
- **Rollback Complexo:** Reverter as alterações aplicadas exige uma lógica manual para executar o comando inverso de cada passo que foi bem-sucedido, o que é complexo e propenso a erros.
- **Falta de Atomicidade:** Não há garantia de que um conjunto de alterações será aplicado como uma unidade indivisível (tudo ou nada).

## O Conceito de "Transacional"

No contexto de gerenciamento de redes, uma abordagem **transacional** (ou atômica) garante que uma série de operações de configuração seja tratada como uma única transação. Isso significa que:
1.  Todas as operações no conjunto são aplicadas com sucesso.
2.  Se qualquer uma das operações falhar, nenhuma das outras alterações é permanentemente aplicada. O sistema retorna ao estado anterior ao início da transação.

Dispositivos como os que rodam Junos (Juniper) ou SR OS (Nokia) implementam este princípio nativamente. O engenheiro de rede modifica uma configuração candidata e, somente após a validação, utiliza o comando `commit` para aplicá-la de forma atômica à configuração ativa. Se ocorrer um erro ou a mudança for indesejada, a configuração candidata pode ser simplesmente descartada.

## A Solução do `device_configurator.py`

O script `device_configurator.py` implementa uma solução inteligente para simular esse comportamento transacional em dispositivos que não o possuem. Ele garante que, se a configuração de um ou mais dispositivos falhar, o sistema tentará reverter *todas* as alterações já realizadas em *todos* os dispositivos para o estado original.

A lógica funciona da seguinte maneira:

1.  **Lista de Passos:** As configurações são definidas como uma lista de `DeviceStep`, que representam ações individuais (ex: criar uma VLAN, configurar um IP).
2.  **Execução Sequencial:** A função `apply_configurations` itera sobre cada dispositivo e aplica seus respectivos passos sequencialmente.
3.  **Rastreamento Global:** Um registro central (`applied_steps`) armazena cada passo que foi concluído com sucesso, juntamente com o dispositivo em que foi aplicado.
4.  **Mecanismo de Rollback:**
    - Se qualquer passo falhar em qualquer dispositivo, uma exceção é capturada.
    - O processo de configuração é interrompido imediatamente.
    - O script inicia um **rollback global**, iterando sobre a lista `applied_steps` em **ordem inversa**.
    - Para cada passo bem-sucedido, ele chama o método correspondente com um parâmetro `undo=True`, efetivamente executando a operação inversa (ex: deletar a VLAN que acabou de ser criada).

Essa abordagem garante que o conjunto de dispositivos não permaneça em um estado semi-configurado, simulando o princípio de "tudo ou nada" de uma transação real.

## Código Equivalente com Suporte a `commit`

Para ilustrar a complexidade que o `device_configurator.py` resolve, veja como o código seria drasticamente simplificado se todos os dispositivos tivessem suporte nativo a `commit`. A lógica de rollback seria gerenciada pelo próprio dispositivo, não pelo script.

```python
# Exemplo de como seria a configuração com suporte nativo a "commit"

def apply_configs_with_commit(device_configs):
    """
    Aplica configurações em dispositivos com suporte a commit.
    A lógica de rollback é tratada pelo próprio dispositivo.
    """
    for device_config in device_configs:
        try:
            # Conecta ao dispositivo
            with connect_to_device(device_config) as manager:
                
                # Entra no modo de configuração, travando a config candidata
                manager.lock_config()

                # Envia todos os comandos para a configuração candidata
                # Nenhum comando é aplicado ainda
                for step in device_config.steps:
                    manager.configure(step.command)

                # Valida a sintaxe e a lógica da configuração candidata
                manager.validate()

                # Aplica todas as alterações de uma vez. Este é o ponto atômico.
                print(f"Aplicando configurações em {device_config.name}...")
                manager.commit()
                print(f"Configuração de {device_config.name} bem-sucedida.")

                # Libera a trava da configuração
                manager.unlock_config()

        except Exception as e:
            print(f"ERRO ao configurar {device_config.name}: {e}")
            print("Iniciando rollback (descartando alterações)...")
            # Se o commit falhou ou qualquer passo anterior,
            # basta descartar a configuração candidata.
            # A conexão pode ser fechada ou um comando "rollback" explícito pode ser usado.
            if 'manager' in locals() and manager.is_connected():
                manager.rollback()
            # O script pode então decidir parar ou continuar com os outros dispositivos.
```

A comparação deixa claro o valor do `device_configurator.py`: ele introduz uma camada de abstração que traz a robustez das configurações transacionais para ambientes de rede heterogêneos e legados.

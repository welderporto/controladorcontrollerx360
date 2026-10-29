# DIRETRIZES DE PROMPT PARA ADICIONAR NOVOS CONTROLES

Este arquivo serve como instrucao para usuarios e Inteligencias Artificiais (IAs) que forem modificar ou adicionar compatibilidade para novos controles neste projeto.

---

## 1. COMO O USUARIO DEVE PEDIR PARA A IA ADICIONAR UM CONTROLE

Copie e cole o texto abaixo para a IA quando quiser adicionar suporte a um controle que ainda nao funciona automaticamente:

```text
Por favor, adicione suporte ao controle [NOME DO CONTROLE] no projeto controladorcontrollerx360.
Dados do controle:
- Fabricante e Modelo: [Ex: Gamesir T4 Pro / Redragon Harrow / etc.]
- Vendor ID (VID): [Ex: 0x045e ou 1118]
- Product ID (PID): [Ex: 0x028e ou 654]
- Tipo de conexao: [Cabo USB ou Dongle 2.4G sem fio]
- Modo de operacao: [HID padrao / D-Input / PS3 / etc.]

REGRAS OBRIGATORIAS:
Siga estritamente as regras de seguranca contidas no arquivo PROMPT_ADICIONAR_CONTROLE.md deste repositorio. Nao altere rotinas sensiveis de kernel, nem reative resets de USB que possam travar o Xbox 360 no ABadAvatar.
```

---

## 2. REGRAS OBRIGATORIAS PARA A INTELIGENCIA ARTIFICIAL (IA)

Se voce e uma IA lendo este arquivo para realizar alteracoes no codigo, voce DEVE seguir com rigor absoluto as instrucoes abaixo. Elas garantem que o console do usuario nao congele nem sofra corrupcao de memoria.

### [!] ZONAS PROIBIDAS (NUNCA ALTERAR)

1. **NUNCA reativar o Reset do Driver USB:**
   - As diretivas `XBOXINPUT_NO_USB_RESET` e `UsbdPowerDownNotification` NUNCA devem ser religadas.
   - O reset forçado da pilha USB corrompe a memoria de consoles com o exploit ABadAvatar (softmod) e trava o videogame no boot.

2. **NUNCA reativar Patches invasivos na XAM:**
   - Mantenha `XBOXINPUT_NO_NOTIFY_PATCH` ativo.
   - Nao recrie o tipo de notificacao 80 com branch patches no codigo da XAM. Utilize apenas `XNOTIFYUI_TYPE_CONSOLEMESSAGE` ou equivalentes nativos.

3. **NUNCA colocar DbgPrint ou chamadas de log em caminhos rapidos:**
   - Nao adicione impressoes de tela ou `DbgPrint` dentro de `interruptHandler`, rotinas DPC ou callbacks USB.
   - No Xbox 360 de varejo sem placa xbdm, chamadas repetidas de debug saturam o buffer do kernel e travam o console imediatamente.

4. **NUNCA usar variaveis globais compartilhadas entre controles:**
   - Toda estrutura de estado de controle (`initState`, `reportData`, `hidDescriptorBuffer`) DEVE residir no slot individual correspondente (`connectedControllers[index]`).
   - Globais compartilhadas causam condicoes de corrida quando dois controles sao plugados ao mesmo tempo.

5. **NUNCA alterar a rotina de limpeza de memoria sem liberar buffers antes do memset:**
   - Ao desconectar um dispositivo em `HidRemoveDeviceHook`, sempre execute `free()` nos ponteiros alocados (`reportData`, `reportDescriptorBuffer`) ANTES de zerar a estrutura com `memset`.

---

### [*] ZONA PERMITIDA E RECOMENDADA PARA ADICIONAR CONTROLES

Para adicionar novos modelos com segurança, atue EXCLUSIVAMENTE nas seguintes áreas:

1. **Adicionar mapeamento estatico no arquivo `source/mapping.cpp`:**
   - Se o controle for um dispositivo USB HID comum (PC/PS3/Android):
     - Defina a tabela de mapeamento de botoes (`HidButtonMapEntry kSeuControleMapping[]`).
     - Insira a entrada na lista `kStaticDeviceMappings[]` com o `vendorId` e `productId` correspondentes.
     - Use o mapa padrao de eixos `kDefaultAxisMap` ou defina as inversoes necessárias na estrutura `{invertX, invertY, invertZ, invertRX, invertRY, invertRZ}`.

2. **Handshakes especiais (se o controle exigir pacote de ativacao):**
   - Se o controle necessitar de um comando de inicializacao especifico para comecar a enviar dados (como acontece no DualShock 3 e Switch Pro):
     - Declare a funcao de verificacao `NeedsSeuControleHandshake(uint16_t vid, uint16_t pid)` em `source/main.cpp`.
     - Envie o comando via `SendControlRequest` no estagio `InitState::INIT_GET_REPORT_DESCRIPTOR` em `setConfigurationComplete`.

3. **Controles com protocolo GIP (familia Xbox One/Series):**
   - Caso o controle use protocolo proprietario GIP em vez de HID:
     - Adicione a identificacao de interface e produto no arquivo `source/controller_backend.cpp`.
     - Nao mexa no despachador de pacotes `GipHandleTransfer` nem na fila assincrona `gip_output_queue.h`.

---

## 3. CHECKLIST DE VERIFICACAO ANTES DE CONCLUIR

- [x] O codigo compila sem erros ou avisos graves?
- [x] Nenhuma funcao de kernel fora das declaradas em `xkelib` foi chamada?
- [x] O arquivo `hiddriver.json` mantem compatibilidade de leitura e gravacao?
- [x] As mensagens exibidas ao usuario permanecem em Portugues e claras?
- [x] O console continua seguro para inicializar via ABadAvatar na dashboard 17559?

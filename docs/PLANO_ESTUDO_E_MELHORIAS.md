# PLANO DE ESTUDO, ARQUITETURA E MELHORIAS TÉCNICAS: XBOXINPUT-UNIFIED
## Driver Unificado de Periféricos USB para Xbox 360 (Kernel 17559 / Devkit / ABadAvatar)

---

**Autor:** Equipe de Engenharia de Sistemas e Arquitetura de Drivers (`XboxInput-Unified Team`)  
**Data:** 29 de Outubro de 2026  
**Versão do Documento:** 1.0.0-PROPOSAL  
**Classificação:** Estudo de Engenharia de Baixo Nível & Especificação de Implementação  
**Ambiente Alvo:** Xbox 360 (Kernel Retail 17559, Devkit 17489, Softmod ABadAvatar, RGH 1.2/3.0, JTAG)

---

## Sumário Executivo

O presente documento estabelece o estudo técnico aprofundado, a análise de integridade de kernel e o plano mestre de engenharia para o projeto **XboxInput-Unified**. O objetivo principal é consolidar, estabilizar e expandir a camada de drivers USB de controles no ecossistema Xbox 360, unificando os dois ecossistemas até então fragmentados:
1. O protocolo proprietário **GIP (Game Input Protocol)**, utilizado pelos controles de Xbox One e Xbox Series X|S (derivado do projeto de referência `XboxInput-1.4.2` de bloxmaster0811).
2. O subsistema genérico e estendido **USB HID (Human Interface Device)**, utilizado por controles clássicos, DualShock 3, Nintendo Switch Pro e dispositivos DirectInput (derivado de `hiddriver360-0.6-beta` de EinTim23 e aprimorado por Welder Porto no `XboxInput-Unified`).

Além da análise comparativa, este estudo endereça as causas-raiz de instabilidade e congelamentos (*kernel panics* e *watchdog hangs*) no Kernel 17559, formaliza as especificações de protocolo binário para a inclusão nativa dos controles **Sony DualShock 4** e **Sony DualSense (PS5)** com suporte completo a vibração (*rumble*) e barra de luz (*lightbar* RGB), detalha a topologia de hubs e dongles sem fio (Sony, 8BitDo, Mayflash) e estabelece uma arquitetura em 4 camadas com pool de sessões pré-alocado (Zero-Allocation em tempo de execução), garantindo imunidade a colisões de contexto e violações de IRQL.

---

## 1. Introdução e Objetivos

### 1.1 Contexto da Plataforma Xbox 360 (Kernel 17559)
O console Xbox 360 é fundamentado na arquitetura de processamento **Xenon** (três núcleos PowerPC de 64 bits operando a 3.2 GHz, com suporte a SMT de duas vias, totalizando seis threads de hardware) e no subsistema de E/S integrado à Southbridge **XeSBA/B/C**.

No ambiente de varejo modificado (RGH/JTAG com dashlaunch) e em cenários de softmod moderno (como a exploração **ABadAvatar** no Kernel 17559, que executa *shadowbooting* através de vetores de payload em avatares do sistema sem necessitar de chips de glitch físicos), a integridade do espaço de memória do kernel (`xboxkrnl.exe`) e do gerenciador de autenticação e sistema (`xam.xex`) é extremamente sensível. 

Qualquer módulo em nível de kernel (`.xex` injetado como plugin de dashboard) opera com privilégios de anel zero (Ring 0 / Supervisor Mode). Consequentemente:
- Erros de desalinhamento de memória ou desreferenciação de ponteiros inválidos provocam imediatamente uma interrupção fatal por Machine Check (`0xC0000005 - STATUS_ACCESS_VIOLATION`) ou travamento da CPU.
- Operações de espera síncrona ou loops não limitados no nível de requisição de interrupção **`DISPATCH_LEVEL` (IRQL 2)** congelam os escalonadores de hardware das threads do Xenon, disparando o watchdog interno do hardware.

### 1.2 Histórico do Projeto e Motivação da Unificação
Historicamente, os usuários e desenvolvedores de homebrew na plataforma Xbox 360 dependiam de soluções isoladas:
- O **`hiddriver360`** permitia a conexão de controles USB HID genéricos e DualShock 3, porém sofria de instabilidade crônica na desconexão de dispositivos, vazamentos contínuos de memória no heap do kernel, travamentos durante o boot e ausência total de suporte a atuadores de vibração (*force feedback / rumble*).
- O **`XboxInput` (v1.4.2)** implementou com maestria o suporte robusto a controles Xbox One e Series X|S via GIP, introduzindo comunicação DPC serializada no núcleo 2, contenção de erros de leitura e suporte a quatro motores de vibração independentes. No entanto, sua arquitetura era estritamente dedicada ao protocolo GIP proprietário.
- O **`XboxInput-Unified`** (mantido por Welder Porto) realizou a fusão preliminar dessas duas bases em uma única base de código, resolvendo condições de corrida críticas na inicialização de múltiplos controles HID simultâneos. Contudo, essa fusão inicial manteve as duas pilhas de driver operando como silos paralelos, compartilhando recursos globais do XAM de forma concorrente e sem abstração centralizada, gerando colisões de identificador de dispositivo e impedindo o envio de vibração para controles HID.

### 1.3 Visão de um Driver Unificado Modular
A visão do projeto `XboxInput-Unified` reorganizado é transformar o plugin em uma **Camada de Abstração de Barramento e Dispositivos de Entrada (Universal Input HAL)** para o Xbox 360, com os seguintes pilares de engenharia:
1. **Pilha de Memória com Zero Alocação Dinâmica:** Eliminação de todas as chamadas de heap (`malloc`, `calloc`, `new`, `free`, `delete`) em caminhos críticos de DPC e callbacks USB.
2. **Isolamento de Slots Determinístico:** Criação de um pool estático centralizado de 4 slots virtuais de controle, impedindo matematicamente qualquer sobreposição de contexto XAM entre GIP e HID.
3. **Suporte Completo a Periféricos Sony (DS4 e DualSense):** Decodificação direta de relatórios de entrada sem sobrecarga do analisador genérico LUFA e transmissão de relatórios de saída (*Output Reports*) com vibração háptica/clássica e indicação de cor por jogador na barra de luz.
4. **Resiliência a Desconexões e Ciclos Rápidos:** Teardown limpo e seguro de endpoints e estruturas de extensão de driver, eliminando o congelamento da CPU e tornando o uso de hubs USB passivos ou ativos 100% seguro.

---

## 2. Estudo Comparativo e Arquitetura Atual

### 2.1 Análise Comparativa: `XboxInput-Unified` vs `XboxInput-1.4.2`

Uma análise comparativa direta entre `XboxInput-Unified\source\main.cpp` (5.642 linhas), `XboxInput-1.4.2\source\main.cpp` (5.618 linhas) e `source\mapping.cpp` evidencia as melhorias de engenharia introduzidas por Welder Porto para mitigar gargalos da versão original:

```
+---------------------------------------------------------------------------------------------------+
| COMPARATIVO DE IMPLEMENTAÇÃO: XboxInput-1.4.2 vs XboxInput-Unified                                |
+------------------------------------+---------------------------------+----------------------------+
| Componente / Subsistema            | XboxInput-1.4.2 (Upstream)      | XboxInput-Unified (Porto)  |
+------------------------------------+---------------------------------+----------------------------+
| Gestão de Inicialização HID        | Variáveis Globais Únicas:       | Estrutura Isolada por Slot:|
|                                    | g_InitState,                    | Controller[4].initState,   |
|                                    | hidDescriptorBuffer,            | hidDescriptorBuffer,       |
|                                    | reportDescriptorBuffer          | reportDescriptorBuffer     |
|                                    | (Race condition com 2+ controles)| (Total isolamento multi-slot)|
+------------------------------------+---------------------------------+----------------------------+
| Identificação do Slot em Callbacks | Ausente no driver extension     | Adicionado slotIndex em    |
|                                    | (conflito de ponteiros)         | HidControllerExtension    |
+------------------------------------+---------------------------------+----------------------------+
| Notificações Customizadas no HUD   | XNOTIFYQUEUEUI_TYPE (80 fixo)   | Macro condicional          |
|                                    | (Incompatível se patch falhar)  | XBOXINPUT_NO_NOTIFY_PATCH  |
|                                    |                                 | com fallback para console  |
+------------------------------------+---------------------------------+----------------------------+
| Carregamento de Mapeamento JSON    | Exclusivo de HDD:\hiddriver.json| Fallback sequencial:       |
|                                    | (Falha em consoles sem disco)   | HDD:\ -> Usb:\hiddriver.json|
+------------------------------------+---------------------------------+----------------------------+
| Suporte Nativo a Dongles Ipega     | Não suportado                   | Adicionado VID 0x2563/     |
| (PG-9076 / ShanWan 2.4G)           |                                 | PID 0x0575 e 0x1949:0x0402 |
+------------------------------------+---------------------------------+----------------------------+
| Testes de Fila de Saída GIP        | Testes base de transporte       | 100% de conformidade       |
|                                    |                                 | em check_output_integration|
+------------------------------------+---------------------------------+----------------------------+
```

#### Detalhe Técnico da Correção Multi-Slot de Welder Porto:
Na versão upstream `XboxInput-1.4.2`, a obtenção de descritores HID durante o handshake USB utilizava buffers estáticos compartilhados globalmente (`main.cpp:1436-1438`):
```cpp
// VULNERABILIDADE ORIGINAL (XboxInput-1.4.2):
InitState g_InitState = INIT_SET_CONFIGURATION;
usb_hid_descriptor hidDescriptorBuffer;
void* reportDescriptorBuffer = NULL;
```
Se dois controles HID fossem conectados em portas USB simultâneas (ou via hub), a requisição assíncrona do controle 2 sobrescrevia os descritores e o ponteiro de relatório do controle 1 em pleno trânsito, levando a ponteiros corrompidos e travamentos.

No `XboxInput-Unified`, essa vulnerabilidade foi eliminada ao alocar o estado no contexto estruturado de cada slot:
```cpp
// CORREÇÃO INTRODUZIDA EM XboxInput-Unified:
struct Controller {
    ...
    InitState initState;
    usb_hid_descriptor hidDescriptorBuffer;
    void* reportDescriptorBuffer;
    ...
};
Controller connectedControllers[4];
```

### 2.2 Análise do Estado de Integração com `hiddriver360-0.6-beta`
O subsistema HID presente no `XboxInput-Unified` descende diretamente do `hiddriver360-0.6-beta`. A integração atual herdou três componentes fundamentais:
1. O analisador de descritores USB HID derivado da biblioteca LUFA (`USB_ProcessHIDReport`, `hid_parser.cpp`).
2. A interceptação de funções do driver de classe HID nativo do kernel (`HidAddDevice` e `HidRemoveDevice`).
3. O mecanismo de injeção direta de estado em `XInputdReadState`.

No entanto, diversos vícios estruturais do código de 2011 do `hiddriver360` ainda persistem nessa integração, tais como desalocação imprópria de memória na desconexão e chamadas diretas a rotinas de heap em contexto de interrupção.

### 2.3 Dualismo Arquitetural: GIP vs HID
Atualmente, o arquivo `source\main.cpp` opera duas pilhas paralelas, com ciclos de vida e garantias de segurança completamente assimétricas:

```
+----------------------------------------------------------------------------------------------------+
| MATRIZ DE DUALISMO ARQUITETURAL NO ESTADO ATUAL DO CÓDIGO                                          |
+-----------------------------------+--------------------------------+-------------------------------+
| Atributo                          | Caminho GIP (Xbox One / Series)| Caminho HID (Genérico / PS3)  |
+-----------------------------------+--------------------------------+-------------------------------+
| Hook de Reivindicação USB         | UsbdAddDeviceCompleteHook      | HidAddDeviceHook              |
| Tipo de Dispositivo Filtrado      | Classe 0xFF / Sub 0x47 / 0xD0  | Classe 0x03 / Sub 0x00 / 0x00 |
| Modelo de Sessão                  | GipSessionSlot g_sessions[32]  | Controller connected[4]       |
| Alocação de Memória               | Zero Heap (Pool Estático)      | new, malloc, calloc no IRQL 2 |
| Tratamento de Desconexão          | Anula driver pointer e consome | Desaloca heap com transfer in-|
|                                   | retorno sem chamar kernel      | flight e desalinhamento       |
| Resiliência a Erros de Leitura    | Limite de 4 erros consecutivos | Loop de rearmamento infinito  |
| Envio de Vibração (Rumble)        | Fila com DPC no Processador 2  | Completamente nulo (Descartado|
| Sincronização de Estado           | Cópia com barreira e lock      | Torn Reads em currentState    |
+-----------------------------------+--------------------------------+-------------------------------+
```

### 2.4 Tabela de Exportações do Kernel e Offsets Internos (Kernel 17559 & Devkit 17489)
O correto funcionamento do driver depende da resolução precisa de chamadas de sistema, divididas entre exportações oficiais resolvidas via ordinal (`XexGetProcedureAddress`) e rotinas internas privadas resolvidas via endereçamento fixo ou varredura de assinatura de opcodes PowerPC.

#### Tabela de Exportações Resolvidas por Ordinal:
```
+---------------+---------+----------------------------------+-----------------------------------------------+
| Módulo Origem | Ordinal | Nome da Função                   | Função no Driver / Propósito                  |
+---------------+---------+----------------------------------+-----------------------------------------------+
| xboxkrnl.exe  | 189     | MmFreePhysicalMemory             | Liberação de páginas físicas do kernel        |
| xboxkrnl.exe  | 486     | XInputdReadState                 | Despachante interno de estado dos controles   |
| xboxkrnl.exe  | 740     | UsbdAddDeviceComplete            | Notificação de conclusão de adição de periférico|
| xboxkrnl.exe  | 742     | UsbdGetDeviceSpeed               | Consulta de velocidade USB (Low/Full/High)    |
| xboxkrnl.exe  | 744     | UsbdGetEndpointDescriptor        | Extração de descritores de endpoint USB       |
| xboxkrnl.exe  | 746     | UsbdOpenDefaultEndpoint          | Abertura do Endpoint de Controle 0            |
| xboxkrnl.exe  | 747     | UsbdOpenEndpoint                 | Abertura de Endpoints de Interrupção/Bulk     |
| xboxkrnl.exe  | 748     | UsbdQueueAsyncTransfer           | Enfileiramento de pacotes USB via TRB         |
| xboxkrnl.exe  | 749     | UsbdQueueCloseDefaultEndpoint    | Encerramento assíncrono do endpoint 0         |
| xboxkrnl.exe  | 750     | UsbdQueueCloseEndpoint           | Encerramento assíncrono de endpoint comum     |
| xboxkrnl.exe  | 751     | UsbdRemoveDeviceComplete         | Notificação de conclusão de remoção de periférico|
| xboxkrnl.exe  | 759     | UsbdGetDeviceDescriptor          | Obtenção do descritor de dispositivo USB      |
| xboxkrnl.exe  | 886     | KeCallAndWaitForDpcRoutine       | Execução síncrona de DPC em núcleo específico |
| xam.xex       | 400     | XamInputGetCapabilities          | Consulta básica de capacidades do controle    |
| xam.xex       | 401     | XamInputGetState                 | Consulta de estado do controle pelo XAM       |
| xam.xex       | 402     | XamInputSetState                 | Envio de comandos de atuador de vibração      |
| xam.xex       | 463     | XamGetCurrentTitleId             | Consulta do TitleID do jogo em execução       |
| xam.xex       | 685     | XamInputGetCapabilitiesEx        | Consulta estendida de capacidades XInput      |
| xam.xex       | 746     | XamIsSysUiInvokedByXenonButton   | Verificação de invocação do Guide Menu        |
| xam.xex       | 1183    | NotificationPatchPtr             | Ponteiro para patching de fila de notificação |
+---------------+---------+----------------------------------+-----------------------------------------------+
```

#### Tabela de Offsets Internos e Assinaturas (Não Exportadas):
```
+------------------------------+--------------------+--------------------+---------------------------------------+
| Símbolo / Ponto de Patch     | Retail (17559)     | Devkit (17489)     | Assinatura PPC / Descrição            |
+------------------------------+--------------------+--------------------+---------------------------------------+
| UsbdGetInterfaceDescriptor   | 0x800D8500         | 0x8010D2D0         | 89 43 ? ? 3D 60 ? ? 39 6B             |
| XamUserBindDeviceCallback    | 0x816D9060         | 0x817A34B8         | 7C 8B 23 78 7C A4 2B 78 54 CA 06 3F   |
| HidAddDevice                 | 0x800E4D68         | 0x8011AE38         | Rotina interna de bind de periférico  |
| HidRemoveDevice              | 0x800E4D28         | 0x8011ADF8         | Rotina interna de teardown de HID     |
| UsbdPowerDownNotification    | 0x800D8FC8         | 0x8010E140         | Notificação de suspensão do host USB  |
| UsbdDriverEntry              | 0x800D8D08         | 0x8010DE48         | Ponto de reentrada da pilha USB       |
| UsbPhysicalPage              | 0x801A8098         | 0x8020A9B8         | Ponteiro para página física de USBD   |
| USB Bugcheck Patch 1         | 0x800E05E4         | 0x80116298         | Patch 0x48000018 (b +0x18) pula assert|
| USB Bugcheck Patch 2         | 0x800DD8E0         | 0x801132A4         | Patch 0x48000018 (b +0x18) pula assert|
| NOP Registro Duplo 1         | 0x800D8F00         | 0x8010E04C         | Patch 0x60000000 (nop)                |
| NOP Registro Duplo 2         | 0x800D8EF0         | 0x8010E05C         | Patch 0x60000000 (nop)                |
| Patch Temporizador XNotify   | 0x816AB7A6 (=80)   | 0x8176A7C6 (=80)   | Configuração do tipo de notificação   |
|                              | 0x816AB7AA (=1500) | 0x8176A7CA (=1500) | Duração de exibição do pop-up (ms)    |
+------------------------------+--------------------+--------------------+---------------------------------------+
```

---

## 3. Gargalos Críticos de Integração e Riscos de Estabilidade no Kernel 17559

A investigação forense da base de código revelou cinco gargalos arquiteturais graves que comprometem a estabilidade do sistema sob o Kernel 17559 e causam falhas catastróficas em cenários de uso prolongado ou desconexão a quente:

### 3.1 Colisão de Contexto de Dispositivo e Sobreposição de Slots XAM
O mecanismo de injeção do XAM associa cada controle físico registrado a um identificador único de hardware (`dwDeviceId`) e a um contexto de 32 bits (`dwDeviceContext`).
No código atual do `XboxInput-Unified`:
- O GIP calcula o contexto em `main.cpp:3017` como:  
  `context = 0x10000005 + idx;` (onde `idx` é o índice de 0 a 3).
- O HID calcula o contexto em `main.cpp:1631` exatamente como:  
  `context = 0x0000000010000005 + index;` (onde `index` é o índice no array `connectedControllers[4]`).

#### O Cenário de Colisão Crítica:
1. Um controle Xbox One (GIP) é conectado na porta frontal e reivindicado no slot 0:
   - Registrado no XAM com `deviceId = 0xa7553952`, `context = 0x10000005`.
   - O array `connectedControllers[0].controllerDriver` permanece `NULL` (pois GIP utiliza o array separado `g_gipSessions`).
2. O usuário conecta um controle DualShock 4 na porta USB traseira:
   - O gancho `HidAddDeviceHook` busca o primeiro slot livre em `connectedControllers` e seleciona o **slot 0** (visto que `connectedControllers[0].controllerDriver == NULL`).
   - O HID invoca `XamUserBindDeviceCallback` com `deviceId = 0xa7553952` e `context = 0x10000005`!
   - O registro do XAM é sobrescrito, corrompendo a tabela de roteamento interna do kernel.
3. No despacho de entrada em `XInputdReadStateHook` (`main.cpp:5091`):
   ```cpp
   if (GipControllerFromContext(dwDeviceContext, &controller))
       return GipControllerReadState(&controller, pdwPacketNumber, pInputData, unk);
   ```
   Como o contexto `0x10000005` é verificado prioritariamente pelo GIP, a busca encontra a sessão GIP do controle Xbox One e retorna `STATUS_SUCCESS`. **O código HID correspondente nunca é executado.** O controle DualShock 4 torna-se um controle fantasma (*ghost device*), incapaz de registrar comandos no jogo.

### 3.2 Assimetria no Subsistema de Vibração (Rumble Truncation)
Enquanto a pilha GIP possui uma esteira completa de enfileiramento assíncrono com limitação de taxa de atualização (10 Hz) e serialização no núcleo 2 (`XboxInputOutputQueue`), a pilha HID encontra-se completamente inoperante:
- Em `XamInputSetStateHook` (`main.cpp:4802-4815`), quando o jogo solicita vibração para um controle HID:
  ```cpp
  if (status == ERROR_DEVICE_NOT_CONNECTED) {
      Controller* c = nullptr;
      for (int i = 0; i < (sizeof(connectedControllers) / sizeof(Controller)); i++) {
          if (connectedControllers[i].controllerDriver && connectedControllers[i].userIndex == user) {
              c = &connectedControllers[i];
              break;
          }
      }
      if (!c) return status;
      return ERROR_SUCCESS; // <--- O VALOR É DESCARTADO SILENCIOSAMENTE!
  }
  ```
- Em `XamInputGetCapabilitiesExHook` (`main.cpp:4837` e `4862`):
  ```cpp
  capabilities->Vibration.wLeftMotorSpeed = 0;
  capabilities->Vibration.wRightMotorSpeed = 0;
  ```
O driver deliberadamente mente para os títulos, informando que os periféricos HID não possuem capacidade motora, impedindo o funcionamento do force-feedback mesmo em controles que suportam nativamente relatórios de saída USB como o DualShock 4 e o DualSense.

### 3.3 Violações de Alocação de Memória em Nível de Interrupção (`DISPATCH_LEVEL`)
O subsistema de E/S do USBD executa todas as rotinas de conclusão de transferência assíncrona (`CompletionRoutines`) em **`DISPATCH_LEVEL` (IRQL 2)**. Nesse nível de execução de hardware no PowerPC Xenon:
- É expressamente proibido alocar memória do heap padrão da CRT (`malloc`, `calloc`, `new`, `free`, `delete`). O heap depende de travas e semáforos que exigem `PASSIVE_LEVEL` (IRQL 0).
- No entanto, a implementação herdada do `hiddriver360` executa:
  * `main.cpp:4690`: `new HidControllerExtension()` em pleno `HidAddDeviceHook`.
  * `main.cpp:1560`: `ctrl->reportDescriptorBuffer = calloc(1, ...)` dentro de `setConfigurationComplete`.
  * `main.cpp:1620`: `ctrl->reportData = malloc(pktSize * 2)` dentro da conclusão assíncrona de configuração.
  * `main.cpp:2345-2353`: `free()` e `delete` dentro de `HidRemoveDeviceHook`.

Essa violação das regras de IRQL é a causa direta de corrupção silenciosa da pool do kernel (`KeBugCheckEx: IRQL_NOT_LESS_OR_EQUAL`), travando títulos durante a tela de carregamento ou quando múltiplos controles são conectados concomitantemente.

### 3.4 Leituras Incompletas e Condições de Corrida (*Torn Reads*)
No processamento de entrada HID, os dados recebidos da interrupção USB são convertidos para a estrutura `ButtonsReport` (28 bytes não alinhados).
- A thread de interrupção USB (DPC) grava diretamente em `connectedControllers[index].currentState = buttonReport;` (`main.cpp:2300`).
- A thread de renderização do jogo lê concorrentemente através de `XInputdReadStateHook` (`main.cpp:5109`): `b = connectedControllers[index].currentState;`.
Essa operação envolve múltiplos ciclos de máquina de carga e armazenamento em registradores PowerPC de 32 bits sem nenhuma primitiva atômica, barreira de sincronização de memória (`sync` / `lwsync`) ou trava de leitura. Consequentemente, o jogo frequentemente lê metades de relatórios concorrentes, resultando em desvios momentâneos (*flickering*) nos direcionais analógicos e cliques fantasmas de botões.

### 3.5 Causas-Raiz de Travamentos Críticos no Kernel 17559

#### A. O Loop Infinito de Rearmamento de Interrupção na Desconexão
Quando um cabo de controle USB é desconectado abruptamente durante o gameplay:
- A transferência de interrupção ativa falha com status de erro de hardware (ex.: `0xC000000D` - `STATUS_INVALID_PARAMETER` ou `0xC0000001` - `STATUS_UNSUCCESSFUL`).
- No caminho GIP, bloxmaster0811 mitigou isso com um contador estrito (`g_gipReadErrors` limitado a 4 falhas consecutivas).
- **No caminho HID (`main.cpp:2303`)**, a função `interruptHandler` re-enfileira a transferência incondicionalmente:
  ```cpp
  return UsbdQueueAsyncTransfer(driverExtension->deviceHandle, &driverExtension->interruptTrb);
  ```
  Como o descritor de dispositivo do kernel já foi invalidado, `UsbdQueueAsyncTransfer` falha e invoca a própria rotina de conclusão de forma síncrona imediata. Isso gera uma **recursão infinita a 100% de CPU no núcleo do Xenon em `DISPATCH_LEVEL`**. A thread gráfica é estrangulada, o pipeline do chip de vídeo Xenos esvazia e o console congela por completo em menos de 5 segundos.

#### B. Desreferenciação de Extensão de Driver Fabricada no Teardown
Ao reivindicar periféricos no gancho `UsbdAddDeviceCompleteHook`, o plugin atribui o ponteiro `deviceHandle->driver = &g_gipExt;`. No momento da desconexão física, a rotina padrão `UsbdRemoveDeviceComplete` do kernel assume que esse ponteiro é um objeto alocado na pool do kernel e tenta percorrer e liberar suas listas encadeadas. Isso resulta em um `STATUS_ACCESS_VIOLATION` imediato dentro de `xboxkrnl.exe`. A correção exige anular `deviceHandle->driver = 0;` e retornar `0` interceptando o encerramento do driver.

#### C. O Perigo Mortal do "Dirty USB Reset"
O `hiddriver360` original tentava forçar a re-enumeração de controles ao iniciar o plugin invocando uma reinicialização forçada do host USB:
```cpp
UsbdPowerDownNotification();
MmFreePhysicalMemory(0, *(DWORD*)UsbPhysicalPage);
UsbdDriverEntry();
```
Essa sequência causa estragos devastadores no Kernel 17559:
1. Interrompe a alimentação dos controladores de rede Wi-Fi internos dos modelos Xbox 360 Slim (Trinity e Corona) e Super Slim (Winchester/Stingray), derrubando a rede permanentemente até o desligamento elétrico do console.
2. Exige a aplicação de patches destrutivos em duas rotinas de bugcheck do kernel (`0x800E05E4` e `0x800DD8E0`) para ignorar asserções da pilha USB.
3. Se o console estiver inicializando um jogo armazenado em pendrive USB ou HD externo configurado como `Usb:\`, a redefinição do driver corrompe os buffers de leitura do sistema de arquivos FATX, travando o console na tela de abertura do jogo.
**Diretriz Arquitetural Inegociável:** O reset forçado da pilha USB deve permanecer **permanentemente desativado** (`XBOXINPUT_NO_USB_RESET = 1`).

#### D. Condição de Corrida no Teardown com Transferência de Saída em Voo (Rumble Hot-Unplug)
Quando um controle é desconectado abruptamente durante uma vibração ativa ou envio de relatório de LED (comum durante explosões em jogos):
- A transferência de saída (`interruptOutTrb`) está em trânsito no controlador EHCI com a flag `outTransferInFlight == true`.
- Se a rotina de tratamento de desconexão (`HidRemoveDeviceHook` ou `UsbdRemoveDeviceComplete`) zerar prematuramente a memória do slot via `memset` ou liberar extensões antes da conclusão dessa transferência pendente:
- O controlador USB conclui a transação física com erro de desconexão e invoca o callback de conclusão assíncrona em nível de interrupção (`DISPATCH_LEVEL` / IRQL 2).
- Em `DISPATCH_LEVEL`, o callback tenta acessar o contexto do slot (que foi limpo com zeros), provocando uma desreferenciação fatal de ponteiro nulo (`NULL pointer dereference`) sem suporte a tratamento de exceções, resultando em travamento instantâneo (*kernel panic / hard freeze*) do console.
- **Mitigação Mandatória:** No `HidRemoveDeviceHook`, o driver deve checar explicitamente a flag `outTransferInFlight` (e `inTransferInFlight`), cancelar transferências em voo via `UsbdCancelTransfer` ou aguardar ativamente o retorno do callback de encerramento antes de zerar o slot com `memset` ou liberar recursos.

---

## 4. Nova Arquitetura Proposta: Driver Unificado Modular

Para resolver definitivamente todos os gargalos diagnosticados, propõe-se uma reestruturação completa da arquitetura do `XboxInput-Unified`, organizada em um modelo de **4 Camadas Desacopladas**.

### 4.1 Diagrama Estrutural da Nova Arquitetura

```
+===================================================================================================+
|                               CAMADA 4: APRESENTAÇÃO VIRTUAL XAM                                  |
|   - Hook XInputdReadState: Despacho ultra-rápido por Slot Index (0..3) sem colisões               |
|   - Hook XamInputSetState: Roteamento de Rumble para Fila Unificada do Slot                       |
|   - Hook XamInputGetCapabilitiesEx: Anúncio real de capacidades e motores                         |
|   - Sincronização do Ring of Light (RoL) e LED do Botão Guide via XamUserBindDeviceCallback       |
+===================================================================================================+
                                                  ▲
                                                  │  Estado Normalizado (XboxInputNormalizedState)
                                                  │  Comandos de Rumble (ScaleRumble / OutputQueue)
                                                  ▼
+===================================================================================================+
|                        CAMADA 3: BACKENDS DE PROTOCOLO PLUGGÁVEIS                                 |
|  +--------------------+  +--------------------+  +--------------------+  +---------------------+  |
|  |   Backend GIP      |  |   Backend Sony DS4 |  | Backend DualSense  |  | Backend Genérico    |  |
|  | (Xbox One/Series)  |  | (CUH-ZCT1 / ZCT2)  |  | (PS5 CFI-ZCT1W)    |  | (Switch Pro, DInput)|  |
|  | - Varint GIP Frame |  | - Input Report 0x01|  | - Input Report 0x01|  | - Descritor LUFA    |  |
|  | - Auth Bypass      |  | - Output Rep. 0x05 |  | - Output Rep. 0x02 |  | - Calibração Eixos  |  |
|  | - 4 Motores Impulso|  | - Rumble & Lightbar|  | - Haptics & Lightbar|  | - Mapeamento JSON   |  |
|  +--------------------+  +--------------------+  +--------------------+  +---------------------+  |
+===================================================================================================+
                                                  ▲
                                                  │  Transmissão / Recepção de Buffers Brutos
                                                  │  Despacho em Core 2 / Bounded Retry Loop
                                                  ▼
+===================================================================================================+
|                 CAMADA 2: BARRAMENTO UNIFICADO & POOL DE SESSÕES ZERO-ALLOCATION                  |
|   - Tabela Estática Central: struct UnifiedControllerSlot g_slots[4]                              |
|   - Alocador Determinístico de Slots Virtuais (Slots 0..3 vinculados aos Jogadores 1..4)          |
|   - Sequenciador Atômico de Estado (Double-Buffering com Sequence Counter - Sem Torn Reads)       |
|   - Fila de Saída Serializada via DPC em Processador 2 (KeCallAndWaitForDpcRoutine Ordinal 886)   |
|   - Watchdog de Erros Bounded: Interrupção estrita após 4 falhas consecutivas na desconexão       |
+===================================================================================================+
                                                  ▲
                                                  │  Intercepção de Eventos USBD / Dispatch IRP
                                                  │  Gerenciamento de Handles Físicos
                                                  ▼
+===================================================================================================+
|                       CAMADA 1: KERNEL 17559 HAL & HOOKS CORE                                     |
|   - Detour em UsbdAddDeviceComplete (Reivindicação de GIP Classe 0xFF e Fallbacks)                |
|   - Detour em HidAddDevice (Reivindicação Segura de Periféricos USB HID Classe 0x03)              |
|   - Teardown Seguro em UsbdRemoveDeviceComplete / HidRemoveDevice (Sem vazamento nem deref crash)|
|   - Gestão de Endpoints: UsbdOpenDefaultEndpoint, UsbdOpenEndpoint (Interrupt IN / Interrupt OUT) |
|   - Supressão de Dirty USB Reset (Preservação de Wi-Fi interno Slim/E e integridade USB Storage)  |
+===================================================================================================+
```

### 4.2 Definição da Estrutura `UnifiedControllerSlot` (Pool Zero-Allocation)

A eliminação definitiva de condições de corrida e violações de IRQL reside na pré-alocação de todas as estruturas em tempo de inicialização do plugin. Nenhuma memória do kernel será alocada ou liberada dinamicamente quando um controle for plugado ou desplugado:

```cpp
#pragma once
#include <xtl.h>
#include <stdint.h>

// Tipo de backend de transporte associado ao slot
enum ControllerTransportType : uint8_t {
    TRANSPORT_NONE = 0,
    TRANSPORT_GIP,            // Xbox One, Xbox One S, Xbox Series X|S
    TRANSPORT_SONY_DS4,       // Sony DualShock 4 (V1 / V2 / Dongle Oficial)
    TRANSPORT_SONY_DUALSENSE, // Sony DualSense (PS5 / Edge)
    TRANSPORT_GENERIC_HID     // Switch Pro, DirectInput, Ipega, ShanWan
};

// Estado da máquina de conexão do slot
enum SlotConnectionState : uint8_t {
    SLOT_DISCONNECTED = 0,
    SLOT_INITIALIZING,
    SLOT_AUTHENTICATING,
    SLOT_CONNECTED,
    SLOT_TEARDOWN_PENDING
};

// Estrutura de relatório normalizado para eliminação de Torn Reads
struct __declspec(align(8)) AtomicGamepadState {
    uint32_t sequence;          // 4 bytes: Even = valid/stable, Odd = write in progress
    XINPUT_GAMEPAD gamepad;     // 12 bytes: wButtons (2B), bLeftTrigger (1B), bRightTrigger (1B), sThumbLX (2B), sThumbLY (2B), sThumbRX (2B), sThumbRY (2B)
};                              // Total: 16 bytes (perfectly 8-byte and 16-byte aligned for Xenon 64-bit ld/std instructions, preventing Exception 0x600 alignment traps)

// Estrutura do Slot Unificado (100% estático, pré-alocado na BSS)
struct UnifiedControllerSlot {
    // Identificação de Slot e XAM
    bool                     active;
    uint8_t                  slotIndex;     // Índice físico do slot: 0, 1, 2, 3
    uint8_t                  userIndex;     // Jogador atribuído pelo XAM: 0, 1, 2, 3
    SlotConnectionState      state;
    ControllerTransportType  transportType;
    
    // Identificadores de Hardware
    uint16_t                 vendorId;
    uint16_t                 productId;
    uint16_t                 bcdDevice;
    uint32_t                 deviceContext; // 0x10000005 + slotIndex (Garantia de Não-Colisão)
    uint32_t                 controllerId;  // 0xa7553952 + slotIndex
    
    // Handles de Hardware do Host USB (xboxkrnl.exe)
    void*                    deviceHandle;
    DWORD                    endpointIn;
    DWORD                    endpointOut;
    bool                     hasInterruptOut;
    uint8_t                  interfaceNumber;
    uint16_t                 maxPacketSizeIn;
    uint16_t                 maxPacketSizeOut;

    // Blocos de Requisição de Transferência USB (TRB) pré-alocados
    UsbControlTrb            controlTrb;        // TRB de controle com UsbPacket embutido (obrigatório para USBD setup)
    UsbTrb                   interruptInTrb;
    UsbTrb                   interruptOutTrb;

    // Buffers DMA estáticos alinhados para Recepção e Envio (Isolamento de Linha de Cache Xenon 128 bytes)
    __declspec(align(128)) uint8_t inBuffer[64];
    uint8_t                  pad_in[64];        // ensure 128-byte cache line isolation
    __declspec(align(128)) uint8_t outBuffer[64];
    uint8_t                  pad_out[64];       // ensure 128-byte cache line isolation

    // Resiliência de Interrupção e Controle de Concorrência
    volatile uint32_t        consecutiveErrors; // Watchdog: Limite de 4 falhas consecutivas
    volatile bool            inTransferInFlight;  // Evita re-enfileiramento concorrente no TRB de entrada (IN)
    volatile bool            outTransferInFlight; // Evita re-enfileiramento concorrente no TRB de saída (OUT)

    // Sincronização de Estado sem Travas (Double-Buffering)
    AtomicGamepadState       stateBuffers[2];
    volatile uint32_t        activeBufferIndex; // 0 ou 1

    // Fila e Estado de Vibração (Rumble & LEDs)
    uint8_t                  rumbleLeftMotor;   // Motor Pesado (Baixa frequência)
    uint8_t                  rumbleRightMotor;  // Motor Leve (Alta frequência)
    uint8_t                  rumbleLeftTrigger; // Impulso Gatilho Esquerdo (GIP)
    uint8_t                  rumbleRightTrigger;// Impulso Gatilho Direito (GIP)
    uint8_t                  ledRed;            // Barra de luz RGB / LED
    uint8_t                  ledGreen;
    uint8_t                  ledBlue;
    volatile bool            outputDirty;       // Sinaliza necessidade de despacho assíncrono

    // Contexto específico de protocolo (Union estática - Zero Heap)
    union {
        struct {
            uint8_t sequenceOut;
            uint8_t sequenceIn;
            bool    announced;
            bool    authenticated;
        } gip;

        struct {
            bool    isWirelessDongle;
            bool    dongleControllerConnected;
            uint8_t batteryLevel;
        } sony;

        struct {
            uint8_t handshakeStep;
            bool    isSwitchPro;
        } hid;
    } proto;
};

// Declaração do Pool Global Centralizado
extern UnifiedControllerSlot g_unifiedSlots[4];
```

#### Diretrizes Críticas de Alinhamento e Endianness no PowerPC Xenon:
1. **Alinhamento Estrito de 64 bits (`AtomicGamepadState`):** A estrutura `AtomicGamepadState` utiliza `__declspec(align(8))` e totaliza exatamente 16 bytes (4 bytes de `sequence` + 12 bytes de `XINPUT_GAMEPAD`). Esse dimensionamento estrito assegura que ambos os elementos do array `stateBuffers[2]` fiquem alinhados em múltiplos de 8 e 16 bytes, prevenindo exceções de desalinhamento de hardware (*Alignment Trap Exception 0x600*) durante instruções PowerPC Xenon de 64 bits (`ld`/`std`).
2. **Conversão de Endianness em Pacotes de Setup USB (`UsbPacket`):** O processador PowerPC Xenon opera nativamente em Big-Endian, enquanto os barramentos USB transmitem dados estritamente em Little-Endian. Ao montar a estrutura `UsbControlTrb controlTrb` para requisições no Endpoint de Controle 0, os campos de 16 bits (`wValue = 0x0205` / `0x0202`, `wIndex`, `wLength`) DEVEM ser convertidos para Little-Endian utilizando `_byteswap_ushort()` ou `__builtin_bswap16()`. A submissão sem swap resulta em inversão de bytes na via física USB e falha imediata com código `STALL` (`USBD_STATUS_STALL_PID`).

### 4.3 Algoritmo de Leitura e Escrita Atômica (Eliminação de Torn Reads)
Para garantir que a thread de renderização dos jogos leia sempre uma estrutura consistente de botões e direcionais sem a sobrecarga de travas de exclusão mútua (`CRITICAL_SECTION`) que não podem ser adquiridas em IRQL 2:

```cpp
// 1. Thread de Interrupção USB (DISPATCH_LEVEL / DPC) - Produtor
void UpdateSlotGamepadState(UnifiedControllerSlot* slot, const XINPUT_GAMEPAD* newState) {
    uint32_t writeIndex = 1 - slot->activeBufferIndex;
    AtomicGamepadState* target = &slot->stateBuffers[writeIndex];
    
    // Incrementa a sequência para número ímpar (sinalizando início de escrita)
    target->sequence++;
    __lwsync(); // Barreira de memória de sincronização de store PowerPC
    
    target->gamepad = *newState;
    
    __lwsync();
    // Incrementa para número par (sinalizando dado estável)
    target->sequence++;
    
    __lwsync(); // Barreira de memória store-store: garante que sequence++ par atinja a L2 antes da troca de activeBufferIndex
    // Troca o buffer ativo de forma atômica
    slot->activeBufferIndex = writeIndex;
}

// 2. Thread do Jogo (PASSIVE_LEVEL / XInputdReadState) - Consumidor
bool ReadSlotGamepadState(const UnifiedControllerSlot* slot, XINPUT_GAMEPAD* outState) {
    const AtomicGamepadState* source;
    uint32_t seq1, seq2;
    int retries = 0;

    do {
        source = &slot->stateBuffers[slot->activeBufferIndex];
        seq1 = source->sequence;
        __lwsync(); // Força leitura da sequência antes dos dados
        
        *outState = source->gamepad;
        
        __lwsync(); // Força leitura dos dados antes de re-verificar sequência
        seq2 = source->sequence;
        
        // Se a sequência for par e não mudou durante a cópia, a leitura foi perfeitamente atômica
        if (seq1 == seq2 && (seq1 & 1) == 0) {
            return true;
        }
    } while (++retries < 3);

    return false; // Fallback seguro
}
```

### 4.4 Máquina de Estados de Teardown Limpo (Anti-Freeze na Desconexão)
Quando um controle é desconectado, o encerramento do periférico deve obedecer à seguinte sequência determinística para evitar *kernel panic*:

```
Desconexão Física Detectada na Porta USB
                   │
                   ▼
[1] Marcar slot->state = SLOT_TEARDOWN_PENDING imediatamente.
                   │
                   ▼
[2] Anular slot->deviceHandle = NULL.
    (Garante que qualquer callback assíncrono atrasado não tente rearmar transferências).
                   │
                   ▼
[3] Informar o XAM sobre a desconexão do controle:
    XamUserBindDeviceCallback(slot->controllerId, slot->deviceContext, 0, true, &slot->userIndex);
                   │
                   ▼
[4] Interceptar rotina de desconexão (HidRemoveDeviceHook / UsbdRemoveDeviceComplete):
    - Identificar se deadHandle corresponde a um de nossos slots ativos.
    - Se sim: desvincular deadHandle->driver = NULL.
    - Consumir a notificação sem permitir que a rotina padrão do kernel tente liberar memória estática.
                   │
                   ▼
[4.1] Barreira de Sincronização de TRBs em Voo (Anti-Race Condition):
    - Checar explicitamente `slot->outTransferInFlight` e `slot->inTransferInFlight`.
    - Se houver transferência ativa (vibração/LEDs ou leitura em voo), cancelar via UsbdCancelTransfer
      ou aguardar a conclusão assíncrona gerada pelo EHCI.
    - É TERMINANTEMENTE PROIBIDO executar memset ou liberar recursos enquanto outTransferInFlight == true,
      prevenindo desreferenciação de ponteiro nulo (NULL Pointer Dereference) em DISPATCH_LEVEL.
                   │
                   ▼
[5] Resetar os campos da estrutura g_unifiedSlots[slotIndex] via memset estático (apenas após drenagem dos TRBs).
                   │
                   ▼
Slot marcado como SLOT_DISCONNECTED (Livre para próxima conexão sem vazamento de RAM).
```

#### Protocolo de Drenagem de Transferências em Voo (`HidRemoveDeviceHook`):
Durante a desconexão em tempo real, se uma rajada de rumble estiver em trânsito no controlador EHCI (`outTransferInFlight == true`), a interrupção física falhará e o hardware invocará a rotina de conclusão do TRB (`InterruptOutCompletionRoutine`) em IRQL 2 (`DISPATCH_LEVEL`). O manipulador do gancho de remoção (`HidRemoveDeviceHook`) deve executar cancelamento explícito através de `UsbdCancelTransfer(slot->deviceHandle, &slot->interruptOutTrb)` ou sincronizar/aguardar o retorno do callback. Apenas quando `outTransferInFlight == false` e `inTransferInFlight == false` o driver pode proceder para o passo [5] e executar o `memset(&g_unifiedSlots[slotIndex], 0, sizeof(UnifiedControllerSlot))`. Esse protocolo elimina 100% dos congelamentos intermitentes de console causados por *hot-unplug* durante eventos com rumble contínuo.

---

## 5. Especificação de Protocolo: Sony DualShock 4

O Sony DualShock 4 (gerações V1 CUH-ZCT1, V2 CUH-ZCT2 e o adaptador sem fio oficial CUH-ZWA1E) é um dispositivo padrão USB HID (Classe `0x03`, Subclasse `0x00`, Protocolo `0x00`). No entanto, ao ser conectado via cabo USB, ele expõe simultaneamente endpoints de entrada e saída por interrupção, além de relatórios de dados estendidos.

### 5.1 Identificadores de Hardware (VID & PID)
- **DualShock 4 Versão 1:** VID `0x054C`, PID `0x05C4`
- **DualShock 4 Versão 2:** VID `0x054C`, PID `0x09CC`
- **DualShock 4 Wireless USB Adapter Oficial:** VID `0x054C`, PID `0x0BA0`

### 5.2 Relatório de Entrada USB (Input Report 0x01)
O controle transmite relatórios de entrada fixos de **64 bytes** através do endpoint Interrupt IN (normalmente EP `0x81` ou `0x84`, intervalo de amostragem de 4ms).

#### Tabela de Mapeamento Byte-a-Byte (Relatório de Entrada 0x01):
```
+-------------+--------------------+-----------+-------------------------------------------------------------+
| Byte Offset | Campo              | Tipo      | Descrição / Faixa de Valores                                |
+-------------+--------------------+-----------+-------------------------------------------------------------+
| 0           | report_id          | uint8_t   | Constante 0x01 (Identificador do relatório de entrada USB)   |
| 1           | stick_left_x       | uint8_t   | Analógico Esquerdo X: 0 (Esquerda) .. 128 (Centro) .. 255   |
| 2           | stick_left_y       | uint8_t   | Analógico Esquerdo Y: 0 (Cima) .. 128 (Centro) .. 255 (Baixo)|
| 3           | stick_right_x      | uint8_t   | Analógico Direito X: 0 (Esquerda) .. 128 (Centro) .. 255    |
| 4           | stick_right_y      | uint8_t   | Analógico Direito Y: 0 (Cima) .. 128 (Centro) .. 255 (Baixo) |
| 5           | buttons[0]         | uint8_t   | D-Pad (Bits 0..3) e Botões de Ação (Bits 4..7)              |
| 6           | buttons[1]         | uint8_t   | Bumpers, Triggers Digitais, Clicks dos Sticks, Share/Options|
| 7           | buttons[2]         | uint8_t   | Botão PS (Bit 0), Click do Touchpad (Bit 1), Contador Seq.  |
| 8           | trigger_left       | uint8_t   | Gatilho Analógico L2: 0 (Solto) a 255 (Pressionado Total)   |
| 9           | trigger_right      | uint8_t   | Gatilho Analógico R2: 0 (Solto) a 255 (Pressionado Total)   |
| 10 - 11     | timestamp          | uint16_t  | Timestamp do sensor interno (Little Endian, passos de 5.3µs)|
| 12          | temperature        | uint8_t   | Sensor de temperatura interna                               |
| 13 - 18     | gyro[3]            | int16_t[3]| Velocidade angular nos eixos X, Y e Z (Giroscópio)          |
| 19 - 24     | accel[3]           | int16_t[3]| Aceleração nos eixos X, Y e Z (Acelerômetro)                |
| 25 - 29     | reserved           | uint8_t[5]| Reservado pelo firmware da Sony                             |
| 30          | status[0]          | uint8_t   | Status de bateria (Bits 0..3: Nível 0-10, Bit 4: Carregando)|
| 31          | status[1]          | uint8_t   | Status de Conexão (Bit 2: 1 = Dongle Sem Controle, 0 = OK)  |
| 32          | reserved2          | uint8_t   | Reservado                                                   |
| 33          | num_touch_reports  | uint8_t   | Quantidade de pacotes do touchpad presentes no frame        |
| 34 - 63     | touch_data[30]     | uint8_t   | Dados de rastreamento capacitivo multi-touch (dedos 1 e 2)  |
+-------------+--------------------+-----------+-------------------------------------------------------------+
```

#### Decodificação de Máscaras de Bits (DualShock 4):
- **Byte 5 (`buttons[0]`):**
  * **Bits 0..3 (`byte & 0x0F`): Hat Switch (D-Pad):**  
    `0x0`: Cima | `0x1`: Cima-Direita | `0x2`: Direita | `0x3`: Baixo-Direita | `0x4`: Baixo | `0x5`: Baixo-Esquerda | `0x6`: Esquerda | `0x7`: Cima-Esquerda | `0x8`: Neutro (Solto).
  * **Bit 4 (`0x10`):** Quadrado $\rightarrow$ Mapear para `XINPUT_GAMEPAD_X`.
  * **Bit 5 (`0x20`):** Cruz $\rightarrow$ Mapear para `XINPUT_GAMEPAD_A`.
  * **Bit 6 (`0x40`):** Círculo $\rightarrow$ Mapear para `XINPUT_GAMEPAD_B`.
  * **Bit 7 (`0x80`):** Triângulo $\rightarrow$ Mapear para `XINPUT_GAMEPAD_Y`.
- **Byte 6 (`buttons[1]`):**
  * **Bit 0 (`0x01`):** L1 Bumper $\rightarrow$ Mapear para `XINPUT_GAMEPAD_LEFT_SHOULDER`.
  * **Bit 1 (`0x02`):** R1 Bumper $\rightarrow$ Mapear para `XINPUT_GAMEPAD_RIGHT_SHOULDER`.
  * **Bit 4 (`0x10`):** Share $\rightarrow$ Mapear para `XINPUT_GAMEPAD_BACK`.
  * **Bit 5 (`0x20`):** Options $\rightarrow$ Mapear para `XINPUT_GAMEPAD_START`.
  * **Bit 6 (`0x40`):** L3 Click $\rightarrow$ Mapear para `XINPUT_GAMEPAD_LEFT_THUMB`.
  * **Bit 7 (`0x80`):** R3 Click $\rightarrow$ Mapear para `XINPUT_GAMEPAD_RIGHT_THUMB`.
- **Byte 7 (`buttons[2]`):**
  * **Bit 0 (`0x01`):** Botão PS $\rightarrow$ Mapear para Botão Guide (invoca `XamInputSendXenonButtonPress`).
  * **Bit 1 (`0x02`):** Click Mecânico do Touchpad $\rightarrow$ Mapeamento opcional como Back secundário.

#### Estrutura em C/C++ (`struct Ds4InputReportUsb`):
```cpp
#pragma pack(push, 1)
struct Ds4InputReportUsb {
    uint8_t  report_id;          // Constante 0x01
    uint8_t  stick_lx;           // 0..255 (Centro = 128)
    uint8_t  stick_ly;           // 0..255 (Centro = 128, Topo = 0)
    uint8_t  stick_rx;           // 0..255 (Centro = 128)
    uint8_t  stick_ry;           // 0..255 (Centro = 128, Topo = 0)
    uint8_t  buttons[3];         // buttons[0]=dpad+shapes, buttons[1]=bumpers+opt, buttons[2]=ps+touch
    uint8_t  trigger_l2;         // 0..255
    uint8_t  trigger_r2;         // 0..255
    uint16_t timestamp;
    uint8_t  temperature;
    int16_t  gyro_x;
    int16_t  gyro_y;
    int16_t  gyro_z;
    int16_t  accel_x;
    int16_t  accel_y;
    int16_t  accel_z;
    uint8_t  reserved[5];
    uint8_t  status[2];          // status[0]=bateria, status[1]=status do dongle
    uint8_t  reserved2;
    uint8_t  num_touch_reports;
    uint8_t  touch_reports[30];
};
#pragma pack(pop)
static_assert(sizeof(Ds4InputReportUsb) == 64, "Ds4InputReportUsb deve possuir exatamente 64 bytes");
```

### 5.3 Relatório de Saída USB: Vibração e Barra de Luz (Output Report 0x05)
Para acionar os atuadores de vibração e definir a cor da barra de luz no DualShock 4 conectado via cabo USB, deve-se emitir o relatório de saída **`0x05`**, com tamanho estrito de **32 bytes**.
*Nota de Endianness no PowerPC Xenon:* Enquanto os campos do payload do relatório são de 8 bits (`uint8_t`), qualquer emissão através do Endpoint de Controle 0 exige que os campos de 16 bits do setup packet (`wValue = 0x0205`, `wIndex`, `wLength = 32`) sejam convertidos para Little-Endian via `_byteswap_ushort()` ou `__builtin_bswap16()`.

#### Tabela do Relatório de Saída (Output Report 0x05):
```
+-------------+--------------------+---------+---------------------------------------------------------------+
| Byte Offset | Campo              | Tipo    | Descrição e Regras de Configuração                            |
+-------------+--------------------+---------+---------------------------------------------------------------+
| 0           | report_id          | uint8_t | Constante 0x05 (Identificador do relatório de saída USB)      |
| 1           | valid_flag0        | uint8_t | Flags de Habilitação:                                         |
|             |                    |         | • Bit 0 (0x01) = Atualizar Motores de Rumble                  |
|             |                    |         | • Bit 1 (0x02) = Atualizar LED da Barra de Luz (RGB)          |
|             |                    |         | • Bit 2 (0x04) = Atualizar Piscar da Barra de Luz             |
| 2           | valid_flag1        | uint8_t | Flags Secundárias (Normalmente 0x00)                          |
| 3           | reserved           | uint8_t | Constante 0x00                                                |
| 4           | motor_right        | uint8_t | Motor Leve (Alta Frequência / Right Rumble): 0 a 255          |
| 5           | motor_left         | uint8_t | Motor Pesado (Baixa Frequência / Left Rumble): 0 a 255        |
| 6           | lightbar_red       | uint8_t | Intensidade do Canal Vermelho (Red): 0 a 255                  |
| 7           | lightbar_green     | uint8_t | Intensidade do Canal Verde (Green): 0 a 255                   |
| 8           | lightbar_blue      | uint8_t | Intensidade do Canal Azul (Blue): 0 a 255                     |
| 9           | lightbar_blink_on  | uint8_t | Tempo do LED aceso no modo piscar (Passos de 10ms; 0 = Fixo)  |
| 10          | lightbar_blink_off | uint8_t | Tempo do LED apagado no modo piscar (Passos de 10ms; 0 = Fixo)|
| 11 - 31     | padding            | uint8_t | Preenchimento obrigatório com zeros (21 bytes de padding)     |
+-------------+--------------------+---------+---------------------------------------------------------------+
```

#### Estrutura em C/C++ (`struct Ds4OutputReportUsb`):
```cpp
#pragma pack(push, 1)
struct Ds4OutputReportUsb {
    uint8_t report_id;           // Constante 0x05
    uint8_t valid_flag0;         // 0x01 (Rumble) | 0x02 (LED) = 0x03
    uint8_t valid_flag1;         // 0x00
    uint8_t reserved;            // 0x00
    uint8_t motor_right;         // Motor leve de alta frequência (0..255)
    uint8_t motor_left;          // Motor pesado de baixa frequência (0..255)
    uint8_t lightbar_red;        // Canal R (0..255)
    uint8_t lightbar_green;      // Canal G (0..255)
    uint8_t lightbar_blue;       // Canal B (0..255)
    uint8_t lightbar_blink_on;   // Duração aceso (0 = sem piscar)
    uint8_t lightbar_blink_off;  // Duração apagado (0 = sem piscar)
    uint8_t padding[21];         // Padding para completar exatamente 32 bytes
};
#pragma pack(pop)
static_assert(sizeof(Ds4OutputReportUsb) == 32, "Ds4OutputReportUsb deve possuir exatamente 32 bytes");
```

### 5.4 Mecânica de Transmissão no Kernel 17559
A transmissão do relatório de saída deve priorizar a via de interrupção dedicada e possuir fallback para a via de controle:
1. **Via Primária: Interrupt OUT Endpoint:**
   - Durante a enumeração, localizar o endpoint de saída com tipo `USB_ENDPOINT_TYPE_INTERRUPT` e direção `USB_DIRECTION_OUT`.
   - Abrir o endpoint via `UsbdOpenEndpoint(slot->deviceHandle, 3, epAddress, maxPacketSize, interval, &slot->endpointOut)`.
   - Enviar de forma assíncrona com `UsbdQueueAsyncTransfer` utilizando o buffer pré-alocado `slot->outBuffer` e `slot->interruptOutTrb`.
2. **Via Secundária: Fallback por Control Transfer (`SET_REPORT`):**
   - Caso o endpoint de interrupção de saída não esteja disponível, submeter uma requisição de classe no Endpoint de Controle 0 utilizando `slot->controlTrb`:
     * `bmRequestType = 0x21` (`Host-to-Device | Class | Interface`)
     * `bRequest = 0x09` (`HID_SET_REPORT`)
     * `wValue = 0x0205` (`(HID_REPORT_TYPE_OUTPUT << 8) | 0x05`) — **Atenção Big-Endian:** Deve ser convertido para Little-Endian via `_byteswap_ushort(0x0205)` ou `__builtin_bswap16(0x0205)` ao montar `slot->controlTrb.packet.wValue`.
     * `wIndex = slot->interfaceNumber` (Normalmente `0x0000`, convertido via `_byteswap_ushort(slot->interfaceNumber)`)
     * `wLength = 32` (convertido via `_byteswap_ushort(32)`)
   - **Nota de Compatibilidade PowerPC Xenon (Big-Endian):**  
     O Xbox 360 USBD espera que a estrutura `UsbPacket` embutida em `UsbControlTrb` contenha os campos de 16 bits (`wValue = 0x0205` no DS4 ou `0x0202` no DualSense, `wIndex` e `wLength`) em ordem de bytes física do barramento (Little-Endian). Conforme verificado no driver (`main.cpp:1508-1510`), a ausência de byte-swap resulta em STALL imediato (`USBD_STATUS_STALL_PID`) pelo periférico, impedindo a inicialização ou atualização de vibração.

---

## 6. Especificação de Protocolo: Sony DualSense (PS5)

O controle Sony DualSense (modelo padrão CFI-ZCT1W e modelo DualSense Edge CFI-ZCP1) representa uma evolução da arquitetura HID da Sony. Ele introduz atuadores de voz para resposta háptica (*voice-coil voice haptics*), gatilhos adaptáveis resistivos e um arranjo de bytes de entrada substancialmente diferente do DualShock 4.

### 6.1 Identificadores de Hardware (VID & PID)
- **DualSense Padrão (PS5):** VID `0x054C`, PID `0x0CE6`
- **DualSense Edge:** VID `0x054C`, PID `0x0DF2`

### 6.2 Relatório de Entrada USB (Input Report 0x01)
O DualSense transmite relatórios de entrada fixos de **64 bytes** através do endpoint Interrupt IN.

**Diferença Arquitetural Crítica em Relação ao DS4:**  
No DualSense, a posição dos gatilhos analógicos (`trigger_left` e `trigger_right`) e o contador de sequência situam-se nos bytes 5, 6 e 7, posicionados **antes** dos bytes de botões digitais (bytes 8, 9 e 10). Tentar interpretar um pacote de DualSense com a estrutura do DualShock 4 faz com que a pressão dos gatilhos acione botões fantasmas de ação.

#### Tabela de Mapeamento Byte-a-Byte (Relatório de Entrada DualSense 0x01):
```
+-------------+--------------------+-----------+-------------------------------------------------------------+
| Byte Offset | Campo              | Tipo      | Descrição / Faixa de Valores                                |
+-------------+--------------------+-----------+-------------------------------------------------------------+
| 0           | report_id          | uint8_t   | Constante 0x01 (Identificador do relatório de entrada USB)   |
| 1           | stick_left_x       | uint8_t   | Analógico Esquerdo X: 0 (Esquerda) .. 128 (Centro) .. 255   |
| 2           | stick_left_y       | uint8_t   | Analógico Esquerdo Y: 0 (Cima) .. 128 (Centro) .. 255 (Baixo)|
| 3           | stick_right_x      | uint8_t   | Analógico Direito X: 0 (Esquerda) .. 128 (Centro) .. 255    |
| 4           | stick_right_y      | uint8_t   | Analógico Direito Y: 0 (Cima) .. 128 (Centro) .. 255 (Baixo) |
| 5           | trigger_left       | uint8_t   | Gatilho Analógico L2: 0 (Solto) a 255 (Pressionado Total)   |
| 6           | trigger_right      | uint8_t   | Gatilho Analógico R2: 0 (Solto) a 255 (Pressionado Total)   |
| 7           | seq_number         | uint8_t   | Contador de sequência de pacotes (Incrementa a cada frame)  |
| 8           | buttons[0]         | uint8_t   | D-Pad (Bits 0..3) e Botões de Ação (Bits 4..7)              |
| 9           | buttons[1]         | uint8_t   | Bumpers (L1/R1), Gatilhos Digitais, Create, Options, L3/R3  |
| 10          | buttons[2]         | uint8_t   | Botão PS (Bit 0), Touch Click (Bit 1), Mic Mute (Bit 2), FN |
| 11          | buttons[3]         | uint8_t   | Botões de Paddles traseiros do DualSense Edge / Reservado   |
| 12 - 15     | reserved           | uint8_t[4]| Reservado pelo firmware da Sony                             |
| 16 - 21     | gyro[3]            | int16_t[3]| Giroscópio X, Y e Z (Little Endian, signed)                 |
| 22 - 27     | accel[3]           | int16_t[3]| Acelerômetro X, Y e Z (Little Endian, signed)               |
| 28 - 31     | sensor_timestamp   | uint32_t  | Timestamp do sensor de 32 bits (Little Endian)              |
| 32          | reserved2          | uint8_t   | Reservado                                                   |
| 33 - 40     | touch_points[8]    | uint8_t[8]| 2 pontos de toque Sony x 4 bytes: contact_id/active bit 7 + X/Y 12-bit pack |
| 41 - 52     | motion_data[12]    | uint8_t[12]| Giroscópio/Acelerômetro 6 eixos x 16-bit LE                |
| 53 - 55     | status[3]          | uint8_t[3]| Status de conexão, nível de bateria e telemetria oficial Sony / hid-playstation |
| 56 - 63     | reserved4[8]       | uint8_t[8]| Padding de hardware USB (Total do relatório = exatamente 64 bytes) |
+-------------+--------------------+-----------+-------------------------------------------------------------+
```

#### Decodificação de Máscaras de Bits (DualSense):
- **Byte 8 (`buttons[0]`):**
  * **Bits 0..3 (`byte & 0x0F`): Hat Switch (D-Pad):**  
    `0x0`: Cima | `0x1`: Cima-Direita | `0x2`: Direita | `0x3`: Baixo-Direita | `0x4`: Baixo | `0x5`: Baixo-Esquerda | `0x6`: Esquerda | `0x7`: Cima-Esquerda | `0x8`: Neutro (Solto).
  * **Bit 4 (`0x10`):** Quadrado $\rightarrow$ `XINPUT_GAMEPAD_X`.
  * **Bit 5 (`0x20`):** Cruz $\rightarrow$ `XINPUT_GAMEPAD_A`.
  * **Bit 6 (`0x40`):** Círculo $\rightarrow$ `XINPUT_GAMEPAD_B`.
  * **Bit 7 (`0x80`):** Triângulo $\rightarrow$ `XINPUT_GAMEPAD_Y`.
- **Byte 9 (`buttons[1]`):**
  * **Bit 0 (`0x01`):** L1 Bumper $\rightarrow$ `XINPUT_GAMEPAD_LEFT_SHOULDER`.
  * **Bit 1 (`0x02`):** R1 Bumper $\rightarrow$ `XINPUT_GAMEPAD_RIGHT_SHOULDER`.
  * **Bit 4 (`0x10`):** Create (Share) $\rightarrow$ `XINPUT_GAMEPAD_BACK`.
  * **Bit 5 (`0x20`):** Options $\rightarrow$ `XINPUT_GAMEPAD_START`.
  * **Bit 6 (`0x40`):** L3 Click $\rightarrow$ `XINPUT_GAMEPAD_LEFT_THUMB`.
  * **Bit 7 (`0x80`):** R3 Click $\rightarrow$ `XINPUT_GAMEPAD_RIGHT_THUMB`.
- **Byte 10 (`buttons[2]`):**
  * **Bit 0 (`0x01`):** Botão PS $\rightarrow$ Invoca Guia do Xbox (`XamInputSendXenonButtonPress`).
  * **Bit 1 (`0x02`):** Click do Touchpad.
  * **Bit 2 (`0x04`):** Botão **Mic Mute** (Pode ser configurado para mutar chat ou atalho rápido de HUD).

#### Estrutura em C/C++ (`struct DualSenseInputReportUsb`):
```cpp
#pragma pack(push, 1)
struct DualSenseInputReportUsb {
    uint8_t  report_id;          // Constante 0x01
    uint8_t  stick_lx;           // 0..255 (Centro = 128)
    uint8_t  stick_ly;           // 0..255 (Centro = 128, Topo = 0)
    uint8_t  stick_rx;           // 0..255 (Centro = 128)
    uint8_t  stick_ry;           // 0..255 (Centro = 128, Topo = 0)
    uint8_t  trigger_l2;         // 0..255
    uint8_t  trigger_r2;         // 0..255
    uint8_t  seq_number;         // Contador de pacotes
    uint8_t  buttons[4];         // buttons[0]=dpad+shapes, buttons[1]=bumpers+create, buttons[2]=ps+mute
    uint8_t  reserved[4];
    int16_t  gyro_x;
    int16_t  gyro_y;
    int16_t  gyro_z;
    int16_t  accel_x;
    int16_t  accel_y;
    int16_t  accel_z;
    uint32_t sensor_timestamp;
    uint8_t  reserved2;
    uint8_t  touch_points[8];    // Bytes 33-40: 2 touch points x 4 bytes
    uint8_t  motion_data[12];    // Bytes 41-52: Gyro / Accel (6 axes x 16-bit LE)
    uint8_t  status[3];          // Bytes 53-55: Status, battery level, connection state
    uint8_t  reserved4[8];       // Bytes 56-63: Hardware padding (total = 64 bytes)
};
#pragma pack(pop)
static_assert(sizeof(DualSenseInputReportUsb) == 64, "DualSenseInputReportUsb deve possuir exatamente 64 bytes");
```

### 6.3 Relatório de Saída USB: Vibração Compatível, LEDs e Barra de Luz (Output Report 0x02)
O relatório de saída via USB do DualSense utiliza o Report ID **`0x02`** e possui tamanho total de **63 bytes** (sendo 1 byte de ID, 47 bytes de payload comum e 15 bytes de padding de preenchimento).

#### Modo de Emulação de Vibração Clássica (*Compatible Rumble Mode*):
O DualSense suporta internamente um modo de emulação de motores excêntricos clássicos (ERM), sintetizando comandos de vibração tradicionais nos transdutores de voz hápticos sem exigir sinais complexos de áudio PCM.
Para acionar esse modo:
- `valid_flag0` deve conter o bit `0x01` (`DS_OUTPUT_FLAG_COMPAT_RUMBLE`).
- O bit `0x02` de `valid_flag0` deve ser mantido em `0` (sinalizando emulação de rumble clássico e não áudio háptico).

#### Tabela do Relatório de Saída (Output Report 0x02):
```
+-------------+--------------------+---------+---------------------------------------------------------------+
| Byte Offset | Campo              | Tipo    | Descrição e Regras de Configuração                            |
+-------------+--------------------+---------+---------------------------------------------------------------+
| 0           | report_id          | uint8_t | Constante 0x02 (Identificador de saída USB do DualSense)      |
| 1           | valid_flag0        | uint8_t | • Bit 0 (0x01) = Habilitar Emulação de Rumble Compatível      |
|             |                    |         | • Bit 1 (0x02) = Seleção de Háptico (0 = Rumble Clássico)     |
| 2           | valid_flag1        | uint8_t | • Bit 0 (0x01) = Controle do LED do Microfone                 |
|             |                    |         | • Bit 2 (0x04) = Controle da Barra de Luz (RGB)               |
|             |                    |         | • Bit 4 (0x10) = Controle dos LEDs Indicadores de Jogador     |
| 3           | motor_right        | uint8_t | Motor Leve (Alta Frequência / Right Rumble): 0 a 255          |
| 4           | motor_left         | uint8_t | Motor Pesado (Baixa Frequência / Left Rumble): 0 a 255        |
| 5 - 8       | audio_volume_ctrl  | uint8_t | Volumes e roteamentos de áudio (Fixar em 0x00)                |
| 9           | mute_button_led    | uint8_t | LED do Botão Mute: 0 = Desligado, 1 = Laranja Sólido, 2 = Pulso|
| 10          | power_save_control | uint8_t | Gerenciamento de energia (0x00)                               |
| 11 - 37     | trigger_effects    | uint8_t | Efeitos de Resistência dos Gatilhos Adaptáveis (Fixar em 0x00)|
| 38          | audio_control2     | uint8_t | Controle secundário de áudio (0x00)                           |
| 39          | valid_flag2        | uint8_t | Bit 1 (0x02) = Habilitar Setup da Barra de Luz                |
| 40 - 41     | reserved           | uint8_t | Reservado (0x00)                                              |
| 42          | lightbar_setup     | uint8_t | Comportamento da Barra: 0 = Padrão, 1 = Fade In, 2 = Fade Out |
| 43          | led_brightness     | uint8_t | Brilho dos LEDs: 0 = Alto, 1 = Médio, 2 = Baixo               |
| 44          | player_leds        | uint8_t | Padrão dos 5 LEDs Brancos de Jogador (Abaixo do Touchpad)    |
| 45          | lightbar_red       | uint8_t | Barra de Luz Canal Vermelho: 0 a 255                          |
| 46          | lightbar_green     | uint8_t | Barra de Luz Canal Verde: 0 a 255                             |
| 47          | lightbar_blue      | uint8_t | Barra de Luz Canal Azul: 0 a 255                              |
| 48 - 62     | padding            | uint8_t | Padding com zeros para atingir exatamente 63 bytes            |
+-------------+--------------------+---------+---------------------------------------------------------------+
```

#### Padrão de Bits para os 5 LEDs de Jogador do DualSense (Byte 44):
O DualSense possui cinco micro-LEDs brancos posicionados abaixo da superfície do touchpad para indicar visualmente o número do jogador:
- **Jogador 1 (`userIndex == 0`):** `0x04` (`0b00000100`) $\rightarrow$ LED Central aceso (`--x--`).
- **Jogador 2 (`userIndex == 1`):** `0x0A` (`0b00001010`) $\rightarrow$ Dois LEDs intermediários acesos (`-x-x-`).
- **Jogador 3 (`userIndex == 2`):** `0x15` (`0b00010101`) $\rightarrow$ Três LEDs alternados acesos (`x-x-x`).
- **Jogador 4 (`userIndex == 3`):** `0x1B` (`0b00011011`) $\rightarrow$ Quatro LEDs externos acesos (`xx-xx`).

#### Estrutura em C/C++ (`struct DualSenseOutputReportUsb`):
```cpp
#pragma pack(push, 1)
struct DualSenseOutputReportUsb {
    uint8_t report_id;           // Constante 0x02
    
    // Bloco comum de 47 bytes
    uint8_t valid_flag0;         // 0x01 = compatible rumble
    uint8_t valid_flag1;         // 0x04 = lightbar, 0x10 = player leds, 0x01 = mute led
    uint8_t motor_right;         // Motor leve / alta frequência (0..255)
    uint8_t motor_left;          // Motor pesado / baixa frequência (0..255)
    uint8_t headphone_volume;    // 0x00
    uint8_t speaker_volume;      // 0x00
    uint8_t mic_volume;          // 0x00
    uint8_t audio_control;       // 0x00
    uint8_t mute_button_led;     // 0 = desligado, 1 = aceso
    uint8_t power_save_control;  // 0x00
    uint8_t trigger_effects[27]; // 27 bytes zerados (efeito de gatilho desligado)
    uint8_t audio_control2;      // 0x00
    uint8_t valid_flag2;         // 0x02 = habilita setup da barra de luz
    uint8_t reserved[2];         // 0x00, 0x00
    uint8_t lightbar_setup;      // 0x00
    uint8_t led_brightness;      // 0x00
    uint8_t player_leds;         // 0x04, 0x0A, 0x15, 0x1B
    uint8_t lightbar_red;        // 0..255
    uint8_t lightbar_green;      // 0..255
    uint8_t lightbar_blue;       // 0..255

    // Padding de 15 bytes
    uint8_t padding[15];         // Completa 63 bytes
};
#pragma pack(pop)
static_assert(sizeof(DualSenseOutputReportUsb) == 63, "DualSenseOutputReportUsb deve possuir exatamente 63 bytes");
```

---

## 7. Dongles Sem Fio, Adaptadores e Enumeração Multi-Controle via Hub USB

### 7.1 Sony DualShock 4 Wireless USB Adapter Oficial (`0x054C:0x0BA0`)
O dongle oficial da Sony (CUH-ZWA1E) é um conversor de hardware USB-Bluetooth proprietário que possui uma característica crítica de funcionamento:
- **Enumeração Persistente:** Ao ser inserido no console Xbox 360, o dongle inicializa seus descritores USB e endpoints imediatamente, **mesmo que nenhum controle DualShock 4 físico esteja ligado ou emparelhado**.
- Ele transmite continuamente o Relatório de Entrada `0x01` preenchido com zeros.

#### Detecção do Estado Real de Conexão Física:
Para evitar que o Xbox 360 reserve permanentemente o Slot 1 para um dongle sem controle ativo (bloqueando a conexão de outros controles):
- O driver deve inspecionar o **byte 31 (`status[1]`)** do relatório de entrada.
- O **Bit 2 (`0x04`)** é a flag indicadora de desconexão sem fio:
  ```cpp
  bool isControllerConnected = ((inputReport[31] & 0x04) == 0);
  ```
- **Lógica de Vinculação com o XAM:**
  * Se `isControllerConnected == false`: O driver mantém o dispositivo em estado dormente (`SLOT_INITIALIZING`), não invoca `XamUserBindDeviceCallback` e não consome nenhum slot de jogador (1 a 4).
  * Se `isControllerConnected == true`: O driver transiciona imediatamente para `SLOT_CONNECTED`, liga o Ring of Light e vincula o usuário. Quando o usuário desliga o controle pelo botão PS, o bit volta para `1` e o driver envia o evento de desconexão para o XAM automaticamente.

### 7.2 Adaptadores Sem Fio 8BitDo (Adapter 1 e Adapter 2)
Os adaptadores USB sem fio da 8BitDo (família V1 Laranja/Marrom e V2 Preto) possuem múltiplos modos de firmware selecionados via atalhos de botões mantidos pressionados por 3 segundos:
- `SELECT + UP`: **Modo XInput** (VID `0x045E`, PID `0x028E` - Emula Controle Xbox 360 com Fio).
- `SELECT + LEFT`: **Modo DInput** (VID `0x2DC8`, PID `0x3100`/`0x3105` - USB HID Padrão).
- `SELECT + L`: **Modo Nintendo Switch** (VID `0x057E`, PID `0x2009`).
- `SELECT + DOWN`: **Modo Sony PS3** (VID `0x054C`, PID `0x0268`).

#### Mecanismo de Intercepção e Bypass de Autenticação do Xbox 360:
Em consoles Xbox 360 travados de fábrica, ao utilizar o adaptador 8BitDo no modo XInput (`0x045E:0x028E`), o kernel rejeita o controle após alguns segundos porque o dongle não possui o chip criptográfico da Microsoft para responder ao desafio de segurança do barramento USB.
No entanto, no ecossistema `XboxInput-Unified`:
- Como o driver intercepta `XamUserBindDeviceCallback` e manipula o contexto em `XInputdReadState`, qualquer dispositivo XInput conectado tem sua autenticação de segurança bypassada de forma transparente, operando com total compatibilidade no modo XInput com vibração nativa.
- Caso o usuário utilize o modo DInput ou Switch, o subsistema HID do `XboxInput-Unified` decodifica os eixos e botões diretamente via tabela pré-calibrada.

### 7.3 Adaptadores Mayflash Magic Series (Magic-NS, Magic-X, Magic-S Pro)
Os adaptadores Mayflash utilizam um botão físico com LED multicolorido para alternar entre perfis:
- **LED Verde:** Modo PC XInput (`0x045E:0x028E`). Recomendado para máxima fidelidade e rumble nativo.
- **LED Azul:** Modo DInput / PS3 (`0x0079:0x18D2` ou `0x054C:0x0268`). Processado como periférico HID.
- **LED Vermelho / Roxo:** Modos Nintendo Switch. Processados via decodificação de eixos calibrados.

### 7.4 Topologia de Hubs USB no Hardware do Xbox 360
A Southbridge do Xbox 360 integra dois controladores de host USB 2.0 independentes (controlador EHCI para 480 Mbps com controlador companheiro OHCI para 1.5/12 Mbps):
- **Host Controller 0:** Gerencia as portas USB frontais.
- **Host Controller 1:** Gerencia as portas USB traseiras e as linhas internas do módulo de rede Wi-Fi.

#### 1. Limite de Camadas de Hub (Hub Tier Depth):
A pilha USBD do Xbox 360 implementa a especificação USB 2.0 padrão, suportando até **5 camadas externas de hubs em cascata** (profundidade máxima de 7 nós de árvore a partir do host raiz). Um hub comercial convencional de 4 ou 7 portas utiliza apenas 1 ou 2 tiers internos e é 100% suportado pelo kernel.

#### 2. Orçamento Elétrico e a Regra do Hub com Alimentação Ativa (Imperativo):
- Cada porta USB física do Xbox 360 fornece no máximo **500 mA a 5V** (2.5 Watts).
- Consumo elétrico típico de periféricos modernos:
  * Controle DualShock 4: Consome **250 mA a 500 mA** durante a recarga da bateria interna.
  * Controle DualSense (PS5): Consome **500 mA a 1500 mA** (1.5A) se a bateria estiver esgotada.
- **Alerta Crítico de Engenharia:**  
  Conectar dois ou mais controles modernos (DS4, DualSense ou Xbox One) utilizando um **Hub USB Passivo (sem fonte de tomada externa)** excede imediatamente o limite de 500 mA da porta raiz do Xbox 360. Isso provoca queda de tensão no barramento USB (*bus voltage sag*), congelamento de comunicação nos endpoints e pode disparar a proteção de sobrecorrente da Southbridge, resetando a porta USB.
- **Diretriz Obrigatória:** Para topologias com 3 ou 4 controles em uma única porta, é mandatório o uso de um **Hub USB Ativo com Fonte Externa Dedicada** (mínimo de 5V 2A).

#### 3. Largura de Banda de Barramento e Orçamento de Endpoints:
- Taxa de transferência de entrada por controle: 64 bytes a cada 4 ms = **16 KB/s por controle**.
- Quatro controles simultâneos consumindo dados e vibração a 100% utilizam aproximadamente **100 KB/s** de tráfego agregado.
- O barramento USB 2.0 High-Speed oferece 480 Mbps (capacidade real líquida de ~40 MB/s). Logo, quatro controles representam **menos de 0,3% da largura de banda total do barramento**.
- O controlador EHCI suporta até 32 endpoints por host. Quatro controles alocam 8 endpoints no total, operando com margem de segurança de hardware superior a 75%.

---

## 8. Roteiro de Implementação Faseado (Roadmap)

A modernização do `XboxInput-Unified` deve ser executada em quatro fases sequenciais, com critérios de aceitação rígidos e sem quebra de compatibilidade com versões anteriores:

```
+----------------------------------------------------------------------------------------------------+
| CRONOGRAMA DE IMPLEMENTAÇÃO EM 4 FASES (ROADMAP)                                                   |
+----------------------------------------------------------------------------------------------------+
| FASE 1: REFATORAÇÃO ARQUITETURAL E POOL UNIFICADO ZERO-ALLOCATION                                  |
| - Implementação da estrutura UnifiedControllerSlot g_unifiedSlots[4] estática.                     |
| - Desacoplamento da atribuição de contextos: slotIndex determina contexto e ID exclusivos.         |
| - Remoção completa de new/malloc/calloc nos callbacks de USBD e HID.                               |
| - Implementação do watchdog de desconexão (máximo de 4 erros consecutivos no interruptHandler).     |
| - Blindagem do teardown: desvinculação dead->driver = NULL e anulação de deviceHandle.             |
| Critério de Conclusão: Console não trava em desconexões rápidas de HID e sem colisões GIP/HID.     |
+----------------------------------------------------------------------------------------------------+
| FASE 2: INTEGRAÇÃO DOS PROTOCOLOS SONY DUALSHOCK 4 E DUALSENSE COM RUMBLE                          |
| - Implementação dos decodificadores diretos Ds4InputReportUsb e DualSenseInputReportUsb.           |
| - Criação dos construtores de relatórios de saída: Relatório 0x05 (DS4) e Relatório 0x02 (DualSense).|
| - Roteamento da vibração do XamInputSetStateHook para a fila de saída do slot correspondente.       |
| - Atualização das cores da Lightbar RGB e dos LEDs indicadores de jogador (1 a 4).                 |
| - Atualização do XamInputGetCapabilitiesExHook para reportar suporte a vibração em HID.             |
| Critério de Conclusão: Jogos disparam vibração física e iluminação de jogador no DS4 e DualSense.  |
+----------------------------------------------------------------------------------------------------+
| FASE 3: SUPORTE A DONGLES SEM FIO E TOPOLOGIA MULTI-CONTROLE VIA HUB USB                           |
| - Detecção dinâmica de conexão sem fio no Dongle Oficial DS4 via byte 31 (status[1] & 0x04).       |
| - Suporte e autodetecção de adaptadores 8BitDo e Mayflash em portas USB expandidas.                |
| - Validação da enumeração de até 4 controles conectados simultaneamente em Hub USB.                |
| - Sincronização automática das cores dos LEDs de acordo com o quadrante atribuído pelo XAM.        |
| Critério de Conclusão: 4 jogadores simultâneos via hub operando em partidas de esportes/luta.      |
+----------------------------------------------------------------------------------------------------+
| FASE 4: TESTES DE ESTRESSE, HARDENING DE KERNEL E VALIDAÇÃO EM HARDWARE REAL                       |
| - Bateria de testes de estresse com conexão e desconexão a quente contínua (100 ciclos).           |
| - Validação em jogos com vibração intensa (ex.: Forza Horizon, Gears of War, Halo).                |
| - Testes de compatibilidade em Kernel Retail 17559 (RGH), Devkit 17489 e exploit ABadAvatar.       |
| - Verificação de não-regressão nos controles Xbox One e Series X|S via GIP.                        |
| Critério de Conclusão: Zero travamentos, logs de debug limpos e estabilidade de longo prazo.       |
+----------------------------------------------------------------------------------------------------+
```

---

## 9. Metodologia de Verificação e Testes

Para auditar e certificar a implementação técnica sem depender exclusivamente de telemetria empírica, estabelece-se o seguinte protocolo de testes de laboratório:

### 9.1 Casos de Teste Estruturados (Test Matrix)

```
+-------+-----------------------------+------------------------------------+---------------------------------+
| ID    | Caso de Teste               | Procedimento de Estresse           | Resultado Esperado              |
+-------+-----------------------------+------------------------------------+---------------------------------+
| TC-01 | Rejeição de Alocação no DPC | Varredura estática de símbolos e   | Zero ocorrências de chamadas    |
|       |                             | ganchos de heap em IRQL 2          | a malloc/new dentro de callbacks|
+-------+-----------------------------+------------------------------------+---------------------------------+
| TC-02 | Coexistência GIP + HID      | 1. Plugar Controle Xbox Series (GIP)| Ambos os controles respondem    |
|       | (Anti-Collision Test)       | 2. Plugar DualSense no Slot 2 (HID)| simultaneamente em XInput sem   |
|       |                             | 3. Iniciar jogo de 2 jogadores     | sobreposição de contexto ou dead|
+-------+-----------------------------+------------------------------------+---------------------------------+
| TC-03 | Desconexão Abrupta HID      | Puxar o cabo USB do DualShock 4    | O jogo pausa; sem travamento ou |
|       | (Hot-Unplug Stress)         | durante vibração pesada contínua   | congelamento do console (100%). |
+-------+-----------------------------+------------------------------------+---------------------------------+
| TC-04 | Ciclo Rápido de Conexão     | Inserir e remover o periférico 20  | Reconexão limpa em todas as     |
|       | (Rapid Reconnect Test)      | vezes seguidas em menos de 30s     | tentativas; sem vazamento de RAM|
+-------+-----------------------------+------------------------------------+---------------------------------+
| TC-05 | Rumble DualShock 4          | Executar teste de vibração no HUD  | Motores leve e pesado vibram;   |
|       |                             | ou título com tiro/impacto         | barra de luz mantém azul/verde. |
+-------+-----------------------------+------------------------------------+---------------------------------+
| TC-06 | Rumble DualSense (PS5)      | Executar aceleração em jogo de     | Motores hápticos reproduzem     |
|       |                             | corrida (ex.: Forza Motorsport)    | o rumble perfeitamente; LEDs OK.|
+-------+-----------------------------+------------------------------------+---------------------------------+
| TC-07 | Dongle Oficial DS4 Dormente | Plugar dongle CUH-ZWA1E desligado  | Nenhum slot de jogador alocado  |
|       |                             | e ligar controle sem fio depois    | até o controle parear de fato.  |
+-------+-----------------------------+------------------------------------+---------------------------------+
| TC-08 | 4 Controles em Hub USB      | Conectar 4 controles em Hub ativo  | 4 quadrantes do Ring of Light   |
|       | (Multi-Player Enumeration)  | (2x Xbox One + 1x DS4 + 1x DualS.) | atribuídos perfeitamente (P1-P4)|
+-------+-----------------------------+------------------------------------+---------------------------------+
```

### 9.2 Métodos de Captura de Pacotes USB (Análise Forense)
Caso ocorra discrepância no comportamento de novas revisões de controles da Sony ou adaptadores sem fio:
1. Conectar o dispositivo a uma estação de trabalho Windows com o software **Wireshark** e o driver **USBPcap** instalados.
2. Iniciar a captura na interface correspondente da raiz USB (`USBPcap1`).
3. Filtrar por tráfego de interrupção: `usb.transfer_type == 0x01`.
4. Comparar os bytes de deslocamento de eixos e botões em relação às tabelas das Seções 5 e 6 deste documento.

### 9.3 Comandos de Validação Local e Não-Regressão
A integridade da base de código e os testes unitários do subsistema de saída GIP existentes devem ser validados via console PowerShell:

```powershell
# 1. Validação dos invariantes de transporte assíncrono e fila de saída DPC
powershell -ExecutionPolicy Bypass -File ".\tests\check_output_integration.ps1"

# 2. Confirmação de integridade não-destrutiva (Working tree clean)
& "C:\Users\Welder\AppData\Local\MinGit\cmd\git.exe" status
```

---

## 10. Considerações Finais e Próximos Passos

O presente plano de melhorias estabelece pela primeira vez um diagnóstico abrangente e definitivo das causas de falha do driver USB no ecossistema Xbox 360 Kernel 17559. A eliminação das alocações de heap em rotinas de interrupção, o desacoplamento em 4 camadas e a padronização dos relatórios de saída para controles da Sony transformam o `XboxInput-Unified` em uma solução com nível de confiabilidade e qualidade técnica comercial.

Com a aprovação deste planejamento, o desenvolvimento deve prosseguir de acordo com a **Fase 1 do Roadmap**, implementando a matriz estática `g_unifiedSlots[4]` e blindando o subsistema contra congelamentos de desconexão.

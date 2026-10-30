# controladorcontrollerx360 🎮 (Xbox 360)

[![GitHub Release](https://img.shields.io/badge/Release-v0.1--beta-blue.svg)](https://github.com/welderporto/controladorcontrollerx360/releases/tag/v0.1-beta)
[![Plataforma](https://img.shields.io/badge/Plataforma-Xbox%20360%20(RGH%20%7C%20JTAG%20%7C%20ABadAvatar)-green.svg)]()
[![Licença](https://img.shields.io/badge/Licen%C3%A7a-GPL--3.0-orange.svg)](LICENSE)
[![Dashboard](https://img.shields.io/badge/Kernel-17559%20%7C%2017489-purple.svg)]()

> **O driver definitivo e unificado de controles para o Xbox 360.**  
> Uma fusão arquitetural e otimizada entre o [XboxInput](https://github.com/bloxmaster0811/XboxInput) (protocolo GIP para controles Xbox One e Series) e o [hiddriver360](https://github.com/EinTim23/hiddriver360) (protocolo USB HID para controles de terceiros e outras marcas), reescrito com foco em **zero travamentos**, **preservação do Wi-Fi**, **blindagem contra bugs no ABadAvatar** e **assistente na tela 100% em Português (PT-BR)**.

---

## 📥 Downloads Prontos (Releases)

Você pode baixar os arquivos compilados prontos para uso diretamente na página de **[Releases v0.1-beta](https://github.com/welderporto/controladorcontrollerx360/releases/tag/v0.1-beta)**:

* 📦 **[controladorcontrollerx360-v0.1-beta.zip](https://github.com/welderporto/controladorcontrollerx360/releases/download/v0.1-beta/controladorcontrollerx360-v0.1-beta.zip)** - Pacote completo com o executável (`hiddriver.xex`), arquivo de configuração (`hiddriver.json`), exemplo de `launch.ini` e instruções.
* 🕹️ **[hiddriver.xex](https://github.com/welderporto/controladorcontrollerx360/releases/download/v0.1-beta/hiddriver.xex)** - Executável retail pronto para o DashLaunch.
* ⚙️ **[hiddriver.json](https://github.com/welderporto/controladorcontrollerx360/releases/download/v0.1-beta/hiddriver.json)** - Configuração de botões e mapeamento para pendrive ou HD.
* 🗜️ **[Código Fonte (.zip)](https://github.com/welderporto/controladorcontrollerx360/archive/refs/tags/v0.1-beta.zip)** | **[Código Fonte (.tar.gz)](https://github.com/welderporto/controladorcontrollerx360/archive/refs/tags/v0.1-beta.tar.gz)**

---

## 🌟 Principais Recursos e Diferenciais

- 🎮 **Dois Motores em 1 Único Plugin (`.xex`):** Suporta controles de Xbox One / Series (com vibração) E controles de PlayStation (DS3, DS4, DualSense), Nintendo Switch Pro e genéricos USB no mesmo arquivo.
- 📶 **Preservação Total do Wi-Fi (Xbox 360 Slim / E):** O reset bruto de USB foi eliminado. Placas Wi-Fi internas não perdem energia e não caem após o boot.
- 🛡️ **Blindagem contra Travamentos no ABadAvatar (17559):** Inicialização segura sem quebra de página de memória física, sem hooks intrusivos na XAM e sem congelamentos na transição de jogos.
- 🇧🇷 **Interface e Assistente 100% em Português:** Notificações de pareamento e mapeamento exibidas diretamente na TV em Português do Brasil com nomes dos botões traduzidos.
- 💾 **Salvamento Flexível (Sem Travar no HDD):** Carrega e salva perfis de controle tanto no disco rígido (`Hdd:\`) quanto em pendrives USB (`Usb:\`) e memórias internas (`FlashMu:\`).
- 🤖 **Prompt Inteligente para Adicionar Qualquer Controle:** Acompanha um prompt interativo completo para você usar qualquer Inteligência Artificial (ChatGPT, Claude, Gemini) para deixar controles não suportados funcionais sem tocar em código sensível.

---

## 🎯 Comparativo Técnico: Por que este driver é superior?

| Recurso | hiddriver360 Original | XboxInput Original | controladorcontrollerx360 |
|---|:---:|:---:|:---:|
| **Controles Xbox One / Series** | ❌ Não | ✅ Sim (Com vibração) | ✅ **Sim (GIP Nativo)** |
| **Controles PS3 / PS4 / DualSense / Switch** | ✅ Sim | ❌ Não | ✅ **Sim (HID Nativo)** |
| **Controles Genéricos USB / Fliperamas** | ✅ Com mapeamento | ❌ Não | ✅ **Sim (Com assistente PT-BR)** |
| **Compatível com ABadAvatar / Softmod** | ❌ Trava no boot | ✅ Sim | ✅ **100% Blindado** |
| **Preservação de Wi-Fi no Slim / E** | ❌ Desconecta Wi-Fi | ✅ Preserva | ✅ **Preservação Total** |
| **Notificações na Tela** | ⚠️ Exige patch XAM | ⚠️ Só diagnóstico | ✅ **Nativas do Console (PT-BR)** |
| **Isolamento de Memória por Controle** | ❌ Globais compartilhadas | ✅ Sessões isoladas | ✅ **Isolamento Total por Slot** |

---

## 🚀 Como Funciona a Tecnologia

### 1. 🎮 Arquitetura Dual-Engine (GIP + HID)
O driver monitora o barramento USB do Xbox 360. Quando um dispositivo é conectado:
* Se for identificado com classe proprietária `FF/47/D0` (GIP), ele ativa o manipulador de baixa latência do Xbox One / Series com suporte total a rumble.
* Se for classe `03/00/00` (Padrão USB HID), ativa o analisador de relatórios HID, verificando descritores de eixo, botões analógicos e gatilhos.

### 2. 📶 Eliminação do Reset Forçado de USB
No código legado, uma chamada forçada a `UsbdPowerDownNotification` e `MmFreePhysicalMemory` era usada para recontar portas USB. Nos consoles Slim/E e no exploit ABadAvatar, isso desenergizava a placa de rede sem fio interna e causava kernel panic.  
Este driver removeu o reset destrutivo: **o console liga suavemente, o Wi-Fi continua estável e os controles funcionam ao serem plugados**.

### 3. 🇧🇷 Assistente Interativo de Mapeamento (PT-BR)
Se você conectar um controle USB que não possua uma assinatura pré-cadastrada, o driver aciona automaticamente um assistente passo a passo direto nas notificações do console:
* 🔔 *"Novo controle conectado! Iniciando mapeamento..."*
* 🔔 *"Pressione [A (ou X no PS)] (segure 3s p/ pular)"*
* 🔔 *"Pressione [Gatilho Esquerdo (LT)]..."*
* 🔔 *"Configuração concluída! Controle pronto para jogar."*
O arquivo de configuração é salvo automaticamente para que você nunca mais precise calibrar novamente.

---

## 📦 Como Instalar no Xbox 360

1. **Baixe o arquivo compilado:**
   * Acesse a aba **[Releases](https://github.com/welderporto/controladorcontrollerx360/releases/tag/v0.1-beta)** e baixe o `controladorcontrollerx360-v0.1-beta.zip` ou o `hiddriver.xex`.
2. **Copie para o Xbox 360:**
   * Coloque os arquivos `hiddriver.xex` e `hiddriver.json` na raiz do seu HD ou Pendrive (ex: `Hdd:\hiddriver.xex` ou `Usb:\hiddriver.xex`).
3. **Configure o DashLaunch:**
   * Abra o arquivo `launch.ini` e adicione o driver na seção `[Plugins]`:
   ```ini
   [Plugins]
   plugin1 = Usb:\hiddriver.xex
   ```
   *(Caso o arquivo esteja no HD interno, configure `plugin1 = Hdd:\hiddriver.xex`).*
4. **Reinicie o console:**
   * Ligue o Xbox 360.
   * Quando a Dashboard carregar, plugue o cabo USB ou o receptor sem fio 2.4G.
   * O console vinculará o dispositivo ao anel de luz (Player 1 a 4) instantaneamente.

---

## 🤖 Como Adicionar Novos Controles Incompatíveis com IA

Criamos um prompt mestre de Inteligência Artificial para tornar qualquer controle genérico ou raro compatível de forma **rápida, segura e sem demora**:

👉 **Arquivo de Instruções:** [PROMPT_ADICIONAR_CONTROLE.md](PROMPT_ADICIONAR_CONTROLE.md)

- ⚡ **Resposta Instantânea:** A IA responde em poucos segundos em texto direto, sem ficar executando comandos demorados em segundo plano.
- 🛑 **Pergunta Antes de Qualquer Alteração:** A IA é terminantemente proibida de editar arquivos (`launch.ini`, etc.) ou rodar scripts sem pedir e receber sua permissão prévia.
- 📋 **Entrega Direta do Mapeamento:** A IA gera o bloco pronto para você colar em `hiddriver.json` ou pergunta se deseja que ela mesma salve para você.

### Como Usar:
1. Abra o arquivo [PROMPT_ADICIONAR_CONTROLE.md](PROMPT_ADICIONAR_CONTROLE.md), copie o texto e cole na sua IA favorita (ChatGPT, Claude, Gemini, DeepSeek, Antigravity, etc.).
2. A IA fará 3 perguntas rápidas de triagem (marca, modelo e conexão).
3. Ela entregará o bloco de mapeamento pronto para o `hiddriver.json` na raiz do seu pendrive (`Usb:\hiddriver.json`).

---

## 🎮 Controles Sony, Adaptadores e Hubs (v0.2 em desenvolvimento, não testado em hardware)

| Dispositivo | Entrada | Vibração / LEDs | Observação |
|---|:---:|:---:|---|
| DualShock 4 (`054C:05C4`, `09CC`) | ✅ | ✅ lightbar por jogador | Via cabo USB |
| DualSense / Edge (`054C:0CE6`, `0DF2`) | ✅ | ✅ LEDs de jogador | Via cabo USB |
| Adaptador USB oficial DS4 (`054C:0BA0`) | ✅ | ✅ | Sem controle ligado, envia estado neutro; o slot do jogador continua reservado |
| 8BitDo / Mayflash em modo DInput ou Switch | ⚙️ | ❌ | Use o assistente de mapeamento ou o `hiddriver.json` |
| 8BitDo / Mayflash em modo XInput (`045E:028E`) | ❌ | ❌ | Protocolo diferente de HID, ainda não suportado |

> ⚠️ **Hubs USB:** com 2 ou mais controles modernos (DS4, DualSense), use um hub **com fonte externa** (5V 2A). Hubs passivos podem derrubar a porta USB do console.

---

## 🛠️ Como Compilar o Código-Fonte

Caso queira compilar alterações por conta própria:

### Pré-requisitos:
* Visual Studio 2010 SP1
* Microsoft Xbox 360 SDK (XDK) instalado
* XexTool no PATH

### Compilação em 1 Clique:
Execute o script incluído na raiz do projeto:
```cmd
build.bat
```
O script chamará o MSBuild com os parâmetros de arquitetura PowerPC, compilará em modo `Release Retail` e converterá o `.xex` automaticamente com o `XexTool`.

---

## 🏆 Créditos e Reconhecimentos

* **[bloxmaster0811](https://github.com/bloxmaster0811)**: Criador do [XboxInput](https://github.com/bloxmaster0811/XboxInput), pioneiro no protocolo GIP e na arquitetura de sessões seguras no Xbox 360.
* **[EinTim23](https://github.com/EinTim23)**: Criador do [hiddriver360](https://github.com/EinTim23/hiddriver360), responsável pela engenharia reversa do driver USB HID e injeção na XAM.
* **[Durg5](https://github.com/Durg5)**: Projeto [riffmaster-rgh360](https://github.com/Durg5/riffmaster-rgh360), fundamental para o transporte USB do GIP.
* **[iMoD1998](https://github.com/iMoD1998)**: Biblioteca Detours utilizada para a interceptação de funções do kernel do Xbox 360.
* **[Tencent RapidJSON](https://github.com/Tencent/rapidjson)**: Analisador leve de JSON utilizado no salvamento de mapeamentos.
* **[Welder Porto](https://github.com/welderporto)**: Unificação dos drivers, blindagem para ABadAvatar/Wi-Fi, tradução PT-BR, eliminação de bugs de memória e criação do ecossistema de diagnóstico via IA.

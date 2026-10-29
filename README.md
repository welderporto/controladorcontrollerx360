# controladorcontrollerx360

Driver unificado de controles para Xbox 360 (RGH / JTAG / ABadAvatar).
Combina o suporte a controles modernos da familia Xbox One / Series (via protocolo GIP) com controles USB HID de outras marcas (PlayStation, Nintendo Switch, Ipega e genericos) em um unico plugin nativo (.xex).

---

## [*] RECURSOS PRINCIPAIS

- [x] Suporte unificado em um unico arquivo .xex:
  - Controles oficiais com fio: Xbox One, Xbox One S, Xbox Elite, Xbox Elite Series 2 e Xbox Series X|S.
  - Controles USB HID de terceiros: DualShock 3 (PS3), DualShock 4 (PS4), DualSense / Edge (PS5) e Nintendo Switch Pro.
  - Perfil pré-configurado para Ipega PG-9076 (modo cabo USB ou dongle sem fio 2.4G).
- [x] Assistente de configuracao na tela totalmente em Portugues (PT-BR).
- [x] Blindado contra travamentos no exploit ABadAvatar e na dashboard 17559:
  - Sem reset forçado do barramento USB (elimina congelamentos no boot).
  - Sem patches destrutivos na memoria da XAM.
  - Sem chamadas de depuracao lentas em tempo real no kernel.
- [x] Correcao de vazamentos de memoria e conflitos de portas quando mais de um controle e conectado.
- [x] Suporte a salvar as configuracoes tanto no disco interno (HDD:\) quanto em pendrive (Usb:\).

---

## [GUIA] COMO CONECTAR O IPEGA PG-9076

1. Conexao via Cabo USB ou Dongle 2.4GHz:
   - Ligue o controle no modo D-Input / PS3 ou Android HID (pressione HOME + X ou HOME + R1 dependendo da revisao).
   - Conecte o cabo ou o receptor USB na porta do console.
2. Reconhecimento:
   - Se o controle ja estiver mapeado, as luzes indicadoras atribuirao o slot do jogador e ele respondera imediatamente.
   - Caso seja um modelo novo ou generico, o assistente em Portugues aparecera na tela orientando o mapeamento de cada botao.

---

## [GUIA] INSTALACAO NO CONSOLE (XBOX 360)

1. Copie o arquivo gerado `XboxInput.xex` para a raiz do seu armazenamento:
   - Exemplo: `Hdd:\XboxInput.xex` ou `Usb:\XboxInput.xex`
2. No seu arquivo `launch.ini` do DashLaunch, adicione a linha:
   ```ini
   [Plugins]
   plugin1 = Hdd:\XboxInput.xex
   ```
   *(Substitua `Hdd:\` por `Usb:\` se o seu console rodar sem HD interno).*
3. Reinicie o console com o controle desconectado.
4. Apos o carregamento completo da Dashboard, plugue o controle na USB.

---

## [AVISO] ADICIONAR NOVOS CONTROLES VIA INTELIGENCIA ARTIFICIAL

Consulte o arquivo [PROMPT_ADICIONAR_CONTROLE.md](PROMPT_ADICIONAR_CONTROLE.md) para ver como pedir para uma IA adicionar novos modelos de controle sem colocar em risco a estabilidade do sistema nem alterar rotinas sensíveis de kernel.

---

## [DEV] COMPILACAO DO CODIGO-FONTE

Requisitos:
- Microsoft Xbox 360 SDK (XDK) com o toolset Visual C++ para Xbox 360.
- Visual Studio 2010 SP1.
- XexTool (para conversao Retail).

Como compilar:
- Execute o arquivo `build.bat` para iniciar a compilacao automatica via MSBuild.

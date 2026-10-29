# controladorcontrollerx360 - Documentacao em Portugues

Versao unificada e otimizada que combina o suporte a controles de Xbox One / Series com controles de terceiros (PlayStation, Switch, Ipega e genericos USB) em um unico plugin nativo (.xex) para o Xbox 360.

---

## [*] PRINCIPAIS MELHORIAS

1. Unificacao Total em 1 Plugin:
   - Suporte a controles oficiais com fio: Xbox One, One S, Elite, Elite 2 e Series X|S.
   - Suporte a controles USB HID de terceiros: PlayStation 3 (DS3), PlayStation 4 (DS4), PlayStation 5 (DualSense) e Nintendo Switch Pro.
   - Perfil nativo para Ipega PG-9076 (cabo USB ou dongle 2.4G sem fio).
2. Totalmente em Portugues (PT-BR):
   - Notificacoes de sistema e assistente de mapeamento de botoes com legendas em Portugues na TV.
3. Blindado para ABadAvatar / Softmod (Dashboard 17559):
   - Removido o reset destrutivo do driver USB que congelava o console no boot.
   - Removidos os patches invasivos de notificacao da XAM (utiliza notificacoes padrao do sistema).
   - Sem travamentos (DbgPrint removido dos caminhos de interrupcao USB).
   - Suporte a salvar as configuracoes em pendrive (Usb:\), memoria interna (FlashMu:\) ou HD (Hdd:\).
4. Correcao de Bugs Criticos de Memoria:
   - Corrigido o bug onde plugar dois controles juntos corrompia a inicializacao.
   - Corrigido o vazamento de memoria e ponteiros soltos ao desplug/re-plugar controles.

---

## [GUIA] COMO CONECTAR O IPEGA PG-9076

1. Cabo USB ou Dongle 2.4GHz:
   - Ligue o controle no modo D-Input / PS3 ou Android HID (segure HOME + X ou HOME + R1 ao ligar).
   - Conecte o cabo ou o receptor USB na porta do Xbox 360.
   - O plugin reconhecera o controle imediatamente.
   - Se for necessaria calibracao, o assistente aparecera na tela em Portugues guiando cada botao.

---

## [GUIA] COMO INSTALAR NO XBOX 360

1. Copie o arquivo gerado `XboxInput.xex` para a raiz do seu pendrive ou disco rigido (ex: `Hdd:\XboxInput.xex` ou `Usb:\XboxInput.xex`).
2. Abra o arquivo `launch.ini` do DashLaunch e adicione na secao `[Plugins]`:
   ```ini
   [Plugins]
   plugin1 = Hdd:\XboxInput.xex
   ```
3. Reinicie o console com os controles desligados.
4. Apos entrar na dashboard, plugue o controle na USB.

---

## [AVISO] ADICIONANDO NOVOS CONTROLES COM IA

Consulte o arquivo `PROMPT_ADICIONAR_CONTROLE.md` para instrucoes completas e seguras sobre como usar IA para adicionar outros controles sem danificar a estabilidade do sistema.

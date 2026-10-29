#!/usr/bin/env python3
"""
tools/identificar_controle.py - Diagnosticador de Controles USB / 2.4G para Xbox 360
Compativel com Windows 10/11.

Recursos:
1. Leitura completa com hidapi (Report Descriptors e pacotes brutos).
2. Pergunta autorizacao antes de qualquer instalacao.
3. Desinstalacao automatica apos a leitura para manter o PC limpo.
4. Modo alternativo 100% nativo (PowerShell) sem instalar nenhuma biblioteca externa.
"""

import sys
import time
import subprocess
import os

def native_windows_scan():
    """Realiza uma varredura nativa usando PowerShell sem instalar nada no sistema."""
    print("\n[+] Executando varredura nativa via PowerShell (sem instalacoes)...")
    cmd = (
        "Get-PnpDevice -PresentOnly | "
        "Where-Object { $_.InstanceId -match 'VID_' -and ($_.Class -eq 'HIDClass' -or $_.Class -eq 'USB') } | "
        "Select-Object FriendlyName, InstanceId | Format-List"
    )
    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
        print(proc.stdout)
        print("Dica: Os 4 digitos apos 'VID_' sao o Vendor ID, e apos 'PID_' sao o Product ID.")
    except Exception as e:
        print(f"[!] Erro ao executar PowerShell: {e}")

def ask_user_permission(package_name):
    print(f"\n=======================================================")
    print(f"  SOLICITACAO DE PERMISSAO DE INSTALACAO")
    print(f"=======================================================")
    print(f"Para extrair a estrutura completa dos botoes e o HID")
    print(f"Report Descriptor, e necessario o pacote Python '{package_name}'.")
    print(f"Assim que a leitura terminar, o pacote sera completamente")
    print(f"desinstalado do seu computador, garantindo seguranca e limpeza.\n")
    print(f"[1] Sim, autorizo a instalacao temporaria do '{package_name}'")
    print(f"[2] Nao, prefiro usar a varredura nativa do Windows (sem instalar nada)")
    print(f"[3] Cancelar e sair\n")
    resp = input("Escolha uma opcao (1/2/3) [Padrao: 1]: ").strip()
    return resp

def check_requirements():
    try:
        import hid
        return hid, False
    except ImportError:
        choice = ask_user_permission("hidapi")
        if choice in ('', '1', 's', 'sim', 'y'):
            print("\n[+] Instalando biblioteca 'hidapi' temporariamente...")
            subprocess.run([sys.executable, "-m", "pip", "install", "hidapi"], check=True)
            import hid
            return hid, True
        elif choice == '2':
            native_windows_scan()
            sys.exit(0)
        else:
            print("\n[!] Operacao cancelada. Nenhuma alteracao foi feita no seu sistema.")
            sys.exit(0)

def cleanup(installed_temporarily):
    if installed_temporarily:
        print("\n" + "=" * 65)
        print("  LIMPEZA DO SISTEMA (DESINSTALACAO)")
        print("=" * 65)
        resp = input("Deseja desinstalar a biblioteca 'hidapi' agora? (s/n) [Padrao: s]: ").strip().lower()
        if resp in ('', 's', 'sim', 'y', 'yes'):
            print("[+] Removendo 'hidapi' do seu sistema...")
            subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "hidapi"], check=True)
            print("[OK] Seu computador esta 100% limpo, sem pacotes residuais!")
        else:
            print("[*] 'hidapi' mantida conforme sua solicitacao.")

def main():
    installed_temporarily = False
    try:
        hid, installed_temporarily = check_requirements()
        print("\n" + "=" * 65)
        print("  controladorcontrollerx360 - Diagnosticador de Controles USB")
        print("=" * 65)
        print("Procurando dispositivos de controle conectados...")

        devices = hid.enumerate()
        gamepads = []

        for d in devices:
            usage_page = d.get('usage_page', 0)
            usage = d.get('usage', 0)
            prod = d.get('product_string') or "Desconhecido"
            if usage_page == 1 and usage in (4, 5):
                gamepads.append(d)
            elif any(k in prod.lower() for k in ['gamepad', 'controller', 'joystick', 'pad', 'shanwan', 'ipega', 'wireless', '8bitdo', 'gamesir']):
                gamepads.append(d)

        unique_pads = {}
        for g in gamepads:
            key = (g['vendor_id'], g['product_id'])
            if key not in unique_pads:
                unique_pads[key] = g

        if not unique_pads:
            print("\n[!] Nenhum controle USB ou receptor sem fio foi detectado.")
            print("    Dicas:")
            print("    1. Certifique-se de que o controle esta ligado e pareado.")
            print("    2. Conecte o cabo USB ou receptor em outra porta.")
            native_windows_scan()
            return

        print(f"\n[+] Encontrado(s) {len(unique_pads)} dispositivo(s):\n")
        pads_list = list(unique_pads.values())
        for i, p in enumerate(pads_list):
            vid = p['vendor_id']
            pid = p['product_id']
            mfg = p.get('manufacturer_string') or "Padrao"
            prod = p.get('product_string') or "Controle de Jogo"
            print(f"  [{i+1}] {prod} ({mfg}) -> VID: 0x{vid:04X} ({vid}), PID: 0x{pid:04X} ({pid})")

        target = pads_list[0]
        if len(pads_list) > 1:
            choice = input(f"\nEscolha o numero do controle a testar (1-{len(pads_list)}) [Padrao: 1]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(pads_list):
                target = pads_list[int(choice)-1]

        vid = target['vendor_id']
        pid = target['product_id']
        prod = target.get('product_string') or "Game Controller"
        mfg = target.get('manufacturer_string') or "Standard"

        print(f"\n[-] Lendo descritores do dispositivo 0x{vid:04X}:0x{pid:04X}...")
        dev = hid.device()
        try:
            dev.open(vid, pid)
        except Exception as e:
            print(f"[!] Erro ao abrir dispositivo: {e}")
            print("Tentando leitura basica...")
            return

        desc_hex = ""
        try:
            desc = dev.get_report_descriptor()
            desc_hex = bytes(desc).hex()
        except Exception:
            pass

        print("[+] Lendo amostra de dados por 2 segundos (mantenha o controle ligado)...")
        sample_packet = []
        for _ in range(40):
            data = dev.read(64, 50)
            if data:
                sample_packet = list(data)
                break

        dev.close()

        print("\n" + "=" * 65)
        print("  COPIE O TEXTO ABAIXO E ENVIE PARA A SUA IA DE PREFERENCIA:")
        print("=" * 65)
        prompt_text = f"""Ola! Preciso da sua ajuda para adicionar compatibilidade para o meu controle no Xbox 360 com o driver 'controladorcontrollerx360'.

Informacoes tecnicas coletadas no PC:
- Nome do Dispositivo: {prod}
- Fabricante: {mfg}
- Vendor ID (VID): 0x{vid:04X} ({vid} em decimal)
- Product ID (PID): 0x{pid:04X} ({pid} em decimal)
- Pacote de Entrada de Amostra (Neutro): {sample_packet}
- HID Report Descriptor (Hex): {desc_hex if desc_hex else "N/A"}

Por favor, siga rigorosamente as diretrizes de seguranca do arquivo PROMPT_ADICIONAR_CONTROLE.md e me forneca:
1. O bloco de mapeamento JSON para adicionar no 'hiddriver.json'.
2. Se necessario, a estrutura estatica em C++ para 'source/mapping.cpp'.
"""
        print(prompt_text)
        print("=" * 65)

    finally:
        cleanup(installed_temporarily)

if __name__ == "__main__":
    main()

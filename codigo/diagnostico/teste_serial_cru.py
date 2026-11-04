"""Teste cru da serial da ADICUP3029 (sem libiio).
Abre a porta a 230400, manda o comando PRINT do protocolo IIO e mostra o que
a placa responde em ate 5 segundos. So LE/ESCREVE na serial, nao altera nada na placa.
Uso: python teste_serial_cru.py"""
import glob, os, termios, time, select, sys

portas = sorted(glob.glob("/dev/cu.usbmodem*"))
if not portas:
    print("Nenhuma porta /dev/cu.usbmodem* encontrada.")
    sys.exit(1)
porta = portas[0]
print("Porta:", porta)

fd = os.open(porta, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
attrs = termios.tcgetattr(fd)
# modo cru, 8N1, 230400
attrs[0] = 0                      # iflag
attrs[1] = 0                      # oflag
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL   # cflag
attrs[3] = 0                      # lflag
attrs[4] = attrs[5] = termios.B230400
attrs[6][termios.VMIN] = 0
attrs[6][termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, attrs)
termios.tcflush(fd, termios.TCIOFLUSH)

def ler(segundos):
    fim = time.time() + segundos
    dados = b""
    while time.time() < fim:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                dados += os.read(fd, 4096)
            except BlockingIOError:
                pass
    return dados

print("Ouvindo 2 s sem enviar nada...")
d0 = ler(2)
print("  recebido sem enviar:", len(d0), "bytes", d0[:80])

print("Enviando PRINT...")
os.write(fd, b"\r\nPRINT\r\n")
d1 = ler(5)
print("  recebido apos PRINT:", len(d1), "bytes")
print("  inicio:", d1[:200])
os.close(fd)
if len(d1) == 0:
    print("RESULTADO: a placa NAO respondeu na serial.")
else:
    print("RESULTADO: a placa respondeu. O firmware esta rodando.")

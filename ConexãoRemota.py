import sys
import socket
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, QFrame, QHBoxLayout, QDesktopWidget


class ConnectionChecker(QThread):
    connection_status = pyqtSignal(bool, bool)  # Sinal para emitir status dos servidores
    finished = pyqtSignal()  # Sinal para indicar que a verificação terminou

    def __init__(self, primary_server, primary_port, secondary_server, secondary_port):
        super().__init__()
        self.primary_server = primary_server
        self.primary_port = primary_port
        self.secondary_server = secondary_server
        self.secondary_port = secondary_port

    def run(self):
        primary_status = self.check_connection(self.primary_server, self.primary_port)
        secondary_status = self.check_connection(self.secondary_server, self.secondary_port)
        self.connection_status.emit(primary_status, secondary_status)
        self.finished.emit()  # Emite sinal indicando que a verificação terminou

    def check_connection(self, server, port):
        try:
            with socket.create_connection((server, port), timeout=5):
                return True
        except Exception as e:
            print(f"Erro ao verificar conexão com {server}:{port} - {str(e)}")
            return False


class ConnectionWindow(QWidget):
    def __init__(self):
        super().__init__()


        self.primary_server = "soollar.ddns.net"
        self.primary_port = 8574
        self.secondary_server = "soollar11.ddns.net"
        self.secondary_port = 8575

        self.connection_checker = ConnectionChecker(self.primary_server, self.primary_port, self.secondary_server,
                                                    self.secondary_port)
        self.connection_checker.connection_status.connect(self.update_status)
        self.connection_checker.finished.connect(self.update_connect_button_text)

        self.primary_status = False
        self.secondary_status = False
        self.checking_status = False  # Flag para indicar se está verificando status
        self.connect_after_check = False  # Flag para indicar se deve conectar após a verificação

        self.initUI()


    def initUI(self):


        self.setWindowTitle('Status dos Servidores')
        self.setWindowIcon(QIcon('acesso-remoto.ico'))
        self.setGeometry(0, 0, 700, 550)  # Definindo o tamanho da janela

        # Estilo para arredondar a borda da janela principal
        self.setStyleSheet("QMainWindow {border-radius: 10px;}")

        # Centralizando a janela na tela
        self.center()

        # Configurando o layout principal
        main_layout = QHBoxLayout(self)

        # Parte esquerda com o status da conexão
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        left_widget.setStyleSheet("background-color: #005CC7; color: white;border-radius: 10px;")  # Estilo azul

        status_title_label = QLabel('Status da Conexão')
        status_title_label.setAlignment(Qt.AlignCenter)
        status_title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        left_layout.addWidget(status_title_label)

        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.Box)
        self.status_frame.setFrameShadow(QFrame.Sunken)
        self.status_frame.setLineWidth(2)
        self.status_frame.setStyleSheet("""
            background-color: #f0f0f0; /* Cor de fundo do painel */
            border: 1px solid #555555; /* Borda do painel */
            border-radius: 5px; /* Cantos arredondados */
            padding: 10px; /* Espaçamento interno */
        """)

        self.status_layout = QVBoxLayout()

        self.status_label_primary = QLabel('Conexão server: Verificando...')
        self.status_label_primary.setAlignment(Qt.AlignCenter)  # Centraliza o texto
        self.status_label_primary.setStyleSheet("font-size: 12px; color: white;font-weight: bold;")
        self.status_label_primary_color = QLabel()
        self.status_label_primary_color.setFixedSize(12, 12)
        self.status_label_primary.setStyleSheet("font-size: 17px; color: white; font-weight: bold;")  # Tamanho maior da fonte

        self.status_label_secondary = QLabel('Conexão server1: Verificando...')
        self.status_label_secondary.setAlignment(Qt.AlignCenter)  # Centraliza o texto
        self.status_label_secondary.setStyleSheet("font-size: 17px; color: white; font-weight: bold;")  # Tamanho maior da fonte
        self.status_label_secondary_color = QLabel()
        self.status_label_secondary_color.setFixedSize(12, 12)
        self.status_label_secondary_color.setStyleSheet("background-color: white; border-radius: 17px;font-weight: bold;")
        # Adicione margens para empurrar os labels para baixo
        self.status_layout.setContentsMargins(0, 200, 0, 0)  # Adiciona margem superior de 20 pixels

        # Adiciona os labels e as cores ao layout
        status_primary_layout = QHBoxLayout()
        status_primary_layout.addWidget(self.status_label_primary)
        status_primary_layout.addWidget(self.status_label_primary_color)

        status_secondary_layout = QHBoxLayout()
        status_secondary_layout.addWidget(self.status_label_secondary)
        status_secondary_layout.addWidget(self.status_label_secondary_color)

        # Adicione os layouts horizontais ao layout principal de status
        self.status_layout.addLayout(status_primary_layout)
        # Adiciona um espaço entre os labels
        self.status_layout.addSpacing(30)  # Espaçamento de 20 pixels entre os dois labels
        self.status_layout.addLayout(status_secondary_layout)

        left_layout.addLayout(self.status_layout)
        left_layout.addStretch(1)  # Adiciona espaço para empurrar os status para o topo
        # Adicione os layouts horizontais ao layout principal de status
        self.status_layout.addLayout(status_primary_layout)

        main_layout.addWidget(left_widget)

        # Parte direita com a imagem e botões
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        right_widget.setStyleSheet("background-color: white;")  # Estilo cinza claro

        # Adicionando o texto "Acesso Remoto" com fonte aumentada
        self.remote_access_label = QLabel('Acesso Remoto')
        self.remote_access_label.setAlignment(Qt.AlignCenter)
        self.remote_access_label.setStyleSheet("font-size: 24px; font-weight: bold; color: black;")  # Azul escuro
        right_layout.addWidget(self.remote_access_label)

        # Adicionando a imagem

        pixmap = QPixmap('img_acesso_remoto.PNG')  # Caminho para a imagem
        scaled_pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio,Qt.SmoothTransformation)  # Redimensiona a imagem mantendo a proporção
        self.image_label = QLabel()
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.image_label)

        # Layout horizontal para os botões de conexão manual
        manual_buttons_layout = QHBoxLayout()

        # Botão de conexão remota
        self.remote_access_button = QPushButton('Conectar')
        self.remote_access_button.setStyleSheet("""
            font-size: 20px; 
            padding: 15px 30px;
            background-color: #005CC7; 
            color: white;
            border-radius: 5px;
            font-weight: bold; /* Negrito */
        """)
        right_layout.addWidget(self.remote_access_button)

        # Botões de conexão manual
        self.connect_primary_button = QPushButton('Conexão Primária')
        self.connect_secondary_button = QPushButton('Conexão Secundária')

        # Estilo dos botões de conexão manual em azul escuro
        self.connect_primary_button.setStyleSheet("""
            background-color: #717471; 
            color: white; 
            border: none; 
            border-radius: 5px;
            padding: 10px;
            font-size: 14px;
        """)
        self.connect_secondary_button.setStyleSheet("""
            background-color: #717471; 
            color: white; 
            border: none; 
            border-radius: 5px;
            padding: 10px;
            font-size: 14px;
        """)

        manual_buttons_layout.addWidget(self.connect_primary_button)
        manual_buttons_layout.addWidget(self.connect_secondary_button)
        right_layout.addLayout(manual_buttons_layout)

        main_layout.addWidget(right_widget)

        # Conectando os sinais aos slots
        self.connect_primary_button.clicked.connect(self.connect_to_primary)
        self.connect_secondary_button.clicked.connect(self.connect_to_secondary)
        self.remote_access_button.clicked.connect(self.check_and_connect_remote)

        # Adiciona feedback visual ao clicar no botão de acesso remoto
        self.remote_access_button.pressed.connect(self.on_button_pressed)
        self.remote_access_button.released.connect(self.on_button_released)

        # Inicia a verificação de status dos servidores ao iniciar o programa
        self.check_connection_status()

        # Definindo tamanho fixo e removendo a capacidade de redimensionamento
        self.setFixedSize(self.size())  # Define o tamanho fixo da janela





    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def check_connection_status(self):
        if self.checking_status:
            return  # Evita iniciar outra verificação se já está em andamento
        self.checking_status = True  # Define flag para indicar que está verificando
        self.disable_buttons()  # Desativa os botões enquanto verifica o status

        # Define o texto e limpa a cor da bolinha enquanto verifica
        self.status_label_primary.setText('Conexão server: Verificando...')
        self.status_label_primary_color.setStyleSheet("background-color: white; border-radius: 6px;")
        self.status_label_secondary.setText('Conexão soollar1: Verificando...')
        self.status_label_secondary_color.setStyleSheet("background-color: white; border-radius: 6px;")


        self.connection_checker.start()
    def disable_buttons(self):
        self.remote_access_button.setEnabled(False)
        self.connect_primary_button.setEnabled(False)
        self.connect_secondary_button.setEnabled(False)

    def enable_buttons(self):
        self.remote_access_button.setEnabled(True)
        self.connect_primary_button.setEnabled(True)
        self.connect_secondary_button.setEnabled(True)

    def update_status(self, primary_status, secondary_status):
        self.primary_status = primary_status
        self.secondary_status = secondary_status

        # Atualiza o texto e a cor da bolinha para a conexão soollar
        if primary_status:
            self.status_label_primary.setText('Conexão server: Online')
            self.status_label_primary_color.setStyleSheet("background-color: green; border-radius: 6px;")
        else:
            self.status_label_primary.setText('Conexão server: Offline')
            self.status_label_primary_color.setStyleSheet("background-color: red; border-radius: 6px;")

        # Atualiza o texto e a cor da bolinha para a conexão soollar1
        if secondary_status:
            self.status_label_secondary.setText('Conexão server1: Online')
            self.status_label_secondary_color.setStyleSheet("background-color: green; border-radius: 6px;")
        else:
            self.status_label_secondary.setText('Conexão server1: Offline')
            self.status_label_secondary_color.setStyleSheet("background-color: red; border-radius: 6px;")

    def update_connect_button_text(self):
        if self.primary_status or self.secondary_status:
            self.remote_access_button.setText('Conectar')
        else:
            self.remote_access_button.setText('Conectar')
        self.checking_status = False  # Reseta a flag após a verificação
        self.enable_buttons()  # Reativa os botões após a verificação

        if self.connect_after_check:
            self.connect_after_check = False  # Reseta a flag
            self.check_and_connect_remote()  # Tenta conectar após a verificação

    def check_and_connect_remote(self):
        if self.checking_status:
            self.connect_after_check = True  # Define a flag para conectar após a verificação
            return  # Sai da função se ainda está verificando

        if self.primary_status:
            self.connect_to_primary()
        elif self.secondary_status:
            self.connect_to_secondary()
        else:
            QMessageBox.warning(self, 'Erro na Conexão', 'Ambos os servidores estão offline.')

    def connect_to_primary(self):
        rdp_file = self.get_rdp_file(self.primary_server)
        if rdp_file:
            self.start_rdp_session(rdp_file)
        else:
            QMessageBox.warning(self, 'Erro de Arquivo', 'Arquivo RDP para o servidor primário não encontrado.')

    def connect_to_secondary(self):
        rdp_file = self.get_rdp_file(self.secondary_server)
        if rdp_file:
            self.start_rdp_session(rdp_file)
        else:
            QMessageBox.warning(self, 'Erro de Arquivo', 'Arquivo RDP para o servidor secundário não encontrado.')

    def get_rdp_file(self, server):
        # Implemente a lógica para determinar qual arquivo .rdp utilizar com base no servidor
        if server == self.primary_server:
            return r'C:\server1.rdp'  # Substitua pelo caminho correto do arquivo .rdp do servidor primário
        elif server == self.secondary_server:
            return r'C:\server2.rdp'  # Substitua pelo caminho correto do arquivo .rdp do servidor secundário
        else:
            return None  # Retorne o caminho do arquivo .rdp correspondente ao servidor

    def start_rdp_session(self, rdp_file):
        # Comando para iniciar a conexão RDP utilizando o aplicativo mstsc.exe do Windows
        command = f'mstsc.exe "{rdp_file}"'

        try:
            subprocess.Popen(command, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            QApplication.quit()  # Fecha o aplicativo após iniciar a sessão RDP
        except Exception as e:
            QMessageBox.warning(self, 'Erro na Conexão', f'Falha ao iniciar a sessão RDP: {str(e)}')

    def on_button_pressed(self):
        self.remote_access_button.setStyleSheet("""
            font-size: 20px; 
            padding: 15px 30px;
            background-color: #005CC7; 
            color: white; 
            border-radius: 5px;
            font-weight: bold; /* Negrito */
        """)

    def on_button_released(self):
        self.remote_access_button.setStyleSheet("""
            font-size: 20px; 
            padding: 15px 30px;
            background-color: #005CC7; 
            color: white;
            border-radius: 5px;
            font-weight: bold; /* Negrito */ 
        """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ConnectionWindow()
    window.show()
    sys.exit(app.exec_())

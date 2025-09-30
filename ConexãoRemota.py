import sys
import socket
import subprocess
import win32cred
import json
import os
import binascii
import base64
import datetime
import webbrowser
import win32gui
import win32con
import pywintypes
import requests
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox,
    QHBoxLayout, QDesktopWidget, QDialog, QLineEdit, QFormLayout, QDialogButtonBox,
    QListWidget, QInputDialog, QScrollArea,
)
import sys, os

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class ConnectionChecker(QThread):
    connection_status = pyqtSignal(bool, bool)
    finished = pyqtSignal()


class ConfiguracaoDialog(QDialog):
    def __init__(self, servers):
        super().__init__()
        self.setWindowTitle("Gerenciar Acesso a Servidores")
        self.setFixedSize(400, 400)

        self.servers = servers.copy()
        self.layout = QVBoxLayout()

        # Título
        title = QLabel("Acessos Cadastrados")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #EEF4FC;")
        self.layout.addWidget(title)

        # Lista
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
             QListWidget {
                 background-color: white;
                 border: 1px solid #ccc;
                 border-radius: 6px;
                 padding: 4px;
             }
         """)
        self.update_list()
        self.layout.addWidget(self.list_widget)

        # Botões
        add_btn = QPushButton("Adicionar")
        remove_btn = QPushButton("Remover Selecionado")
        user_btn = QPushButton("Definir Usuário Global")

        for btn in [add_btn, remove_btn, user_btn]:
            btn.setStyleSheet(self.button_style())

        add_btn.clicked.connect(self.add_server)
        remove_btn.clicked.connect(self.remove_selected)
        user_btn.clicked.connect(self.solicitar_credenciais_e_salvar)

        self.layout.addSpacing(10)
        self.layout.addWidget(add_btn)
        self.layout.addWidget(remove_btn)
        #self.layout.addWidget(user_btn)

        # Botões OK / Cancelar
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:!enabled {
                background-color: #cccccc;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #aaaaaa;
            }
        """)
        self.layout.addSpacing(10)
        self.layout.addWidget(buttons)

        self.setLayout(self.layout)
        self.setStyleSheet("""
             QDialog {
                 background-color: #EEEFF0;
                 font-family: 'Segoe UI';
                 font-size: 13px;
             }
         """)

    def button_style(self):
        return """
             QPushButton {
                 background-color: #005CC7;
                 color: white;
                 font-weight: bold;
                 border: none;
                 border-radius: 6px;
                 padding: 6px 12px;
             }
             QPushButton:hover {
                 background-color: #004b9a;
             }
         """

    def update_list(self):
        self.list_widget.clear()
        for server in self.servers:
            self.list_widget.addItem(f"{server['name']} - {server['address']}")

    def add_server(self):
        name, ok1 = QInputDialog.getText(self, "Nome do Servidor", "Nome:")
        if not ok1 or not name:
            return
        address, ok2 = QInputDialog.getText(self, "Endereço", "Endereço (ex: host.ddns.net):")
        if not ok2 or not address:
            return
        self.servers.append({"name": name, "address": address})
        self.update_list()

    def remove_selected(self):
        selected = self.list_widget.currentRow()
        if selected >= 0:
            del self.servers[selected]
            self.update_list()

    def get_servers(self):
        return self.servers

    def solicitar_credenciais_e_salvar(self):
        usuario, ok1 = QInputDialog.getText(self, "Usuário", "Digite o usuário:")
        if not ok1 or not usuario:
            return
        senha, ok2 = QInputDialog.getText(self, "Senha", "Digite a senha:", QLineEdit.Password)
        if not ok2 or not senha:
            return

        for server in self.servers:
            self.salvar_credenciais(server["address"], usuario, senha)


    def salvar_credenciais(self, hostname, usuario, senha):
        try:
            host_sanitizado = hostname.split(":")[0]

            cred_blob = senha.encode('utf-16le')  # RDP exige UTF-16LE

            cred = {
                'Type': win32cred.CRED_TYPE_DOMAIN_PASSWORD,
                'TargetName': f"TERMSRV/{host_sanitizado}",
                'UserName': usuario,
                'CredentialBlob': cred_blob,
                'Comment': "Credencial RDP automática",
                'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE
            }

            win32cred.CredWrite(cred, 0)

            print(f"✅ Credencial do Windows salva para {host_sanitizado}")
        except pywintypes.error as e:
            print(f"❌ Erro do Windows ao salvar credencial: {e}")
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")


class ConnectionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.servers = self.load_servers()
        self.button_list = []
        self.verificar_validade()
        self.initUI()

    def verificar_validade(self):
        import re

        data_limite = datetime.date(2025, 8, 19)
        hoje = datetime.date.today()

        if hoje >= data_limite:
            # 1. Remove o JSON de servidores
            if os.path.exists("servidores.json"):
                os.remove("servidores.json")

            # 2. Limpa credenciais de RDP apenas dos servidores listados
            for server in self.servers:
                try:
                    endereco = server.get("address")
                    if endereco:
                        # Remove a porta, se existir
                        host_only = re.split(r":", endereco)[0]
                        subprocess.run([f"cmdkey /delete:TERMSRV/{host_only}"],
                                       shell=True, capture_output=True, text=True)
                        print(f"Credenciais removidas para: {host_only}")
                except Exception as e:
                    print(f"Erro limpando credenciais de {endereco}: {e}")

            # 3. Mostra aviso e fecha o programa
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Acesso Expirado")
            msg.setText("O acesso ao sistema expirou.\nContate o TI.")
            msg.exec_()
            sys.exit()

    def abrir_link(self, event):
        webbrowser.open("https://www.linkedin.com/in/weslley-larroza-b8bb57213")  # ou LinkedIn

    def initUI(self):
        self.setWindowTitle('Acesso Servidor')
        self.setWindowIcon(QIcon('acesso-remoto.ico'))
        self.setGeometry(0, 0, 700, 550)
        self.setFixedSize(self.size())
        self.center()


        main_layout = QHBoxLayout(self)
        self.setStyleSheet("background-color: #EEEFF0;")  # Azul escuro profundo

        # Lado esquerdo
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        left_widget.setStyleSheet("background-color: #0B4D9B; color: white; border-radius: 10px;")

        status_title_label = QLabel('Acessos Remoto')
        status_title_label.setAlignment(Qt.AlignHCenter)  # Alinha horizontalmente ao centro
        status_title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        left_layout.addWidget(status_title_label)


        # Área de rolagem para os botões
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")


        # Widget e layout interno para os botões
        scroll_content = QWidget()
        # Criar o layout para os botões e armazenar na instância
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)


        scroll_area.setWidget(scroll_content)
        scroll_area.setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: #005CC7;  /* Azul #005CC7 para o fundo da barra de rolagem */
                width: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background: #003366;  /* Cor para o 'handle', escolha de um verde para contraste */
                min-height: 20px;
                border-radius: 6px;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Adiciona a área de rolagem ao layout principal do lado esquerdo
        left_layout.addWidget(scroll_area)

        # Criar os botões e adicioná-los no layout de rolagem
        self.create_connection_buttons(self.scroll_layout)

        self.config_button = QPushButton()
        self.config_button.setFixedSize(40, 40)  # Define o tamanho do botão
        self.config_button.setIcon(QIcon('settings.svg'))  # Substitua pelo caminho do seu ícone
        self.config_button.setIconSize(QSize(24, 24))  # Define o tamanho do ícone

        self.config_button.setStyleSheet("""
            QPushButton {
                background-color: #0B4D9B;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        # Botão do GitHub
        self.github_button = QPushButton()
        self.github_button.setFixedSize(40, 40)
        self.github_button.setIcon(QIcon('icons8-github.svg'))  # Ícone do GitHub
        self.github_button.setIconSize(QSize(24, 24))
        self.github_button.setStyleSheet("""
            QPushButton {
                background-color: #0B4D9B;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)

        # Ao clicar no botão, abre o link do GitHub
        self.github_button.clicked.connect(self.abrir_link)

        self.config_button.clicked.connect(self.open_config_dialog)
        # Container para os dois botões
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(2)  # Espaço entre os botões

        buttons_layout.addWidget(self.config_button)
        buttons_layout.addWidget(self.github_button)

        buttons_container.setLayout(buttons_layout)

        # Adiciona o container ao layout principal, alinhado à esquerda
        left_layout.addWidget(buttons_container, alignment=Qt.AlignLeft)

        main_layout.addWidget(left_widget)

        # Lado direito
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        right_widget.setStyleSheet("background-color: #EEEFF0;")

        self.remote_access_label = QLabel()#'Acesso Remoto')
        self.remote_access_label.setAlignment(Qt.AlignCenter)
        self.remote_access_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #003366;")
        right_layout.addWidget(self.remote_access_label)

        self.setWindowIcon(QIcon(resource_path('acesso-remoto.ico')))
        pixmap = QPixmap(resource_path('img_acesso_remoto.png'))
        scaled_pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label = QLabel()
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)

        # Criar um layout auxiliar para manter a imagem no topo
        image_layout = QVBoxLayout()
        image_layout.addSpacing(90)  # espaço extra no topo (ajuste esse valor como quiser)
        image_layout.addWidget(self.image_label, alignment=Qt.AlignTop | Qt.AlignHCenter)
        image_layout.addStretch()  # empurra o conteúdo para cima

        # Widget contêiner para a imagem
        image_container = QWidget()
        image_container.setLayout(image_layout)
        right_layout.addWidget(image_container)

        # Obter IP público
        try:
            ip = requests.get("https://api.ipify.org").text
            botao_texto = f"IP Público: {ip}"
        except Exception as e:
            botao_texto = "IP Público: Erro"
        self.image_label.setPixmap(scaled_pixmap)

        self.setLayout(main_layout)

        self.remote_access_button = QPushButton(botao_texto)
        self.remote_access_button.setStyleSheet("""
            font-size: 20px; 
            padding: 15px 30px;
            background-color: #0B4D9B; 
            color: white;
            border-radius: 5px;
            font-weight: bold;
        """)
        right_layout.addWidget(self.remote_access_button)

        main_layout.addWidget(right_widget)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def open_rdp_config(self, address):
        subprocess.Popen(
            ["mstsc", f"/v:{address}"],
            creationflags=subprocess.CREATE_NO_WINDOW
        )


    def verificar_e_abrir_rdp(self, server_name, address):
        def carregar_enderecos():
            try:
                with open("servidores.json", "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    return [srv["address"].lower() for srv in dados if "address" in srv]
            except Exception as e:
                print(f"Erro ao carregar servidores.json: {e}")
                return []

        def enum_window_callback(hwnd, result):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                for addr in enderecos_configurados:
                    # Usa apenas o host ou porta para identificar no título
                    if addr in title:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(hwnd)
                        result.append(hwnd)
                        print(f"Já existe uma sessão RDP ativa para: {addr}")
                        return
            return True

        enderecos_configurados = carregar_enderecos()
        encontrados = []
        win32gui.EnumWindows(enum_window_callback, encontrados)

        if not encontrados:
            print(f"Abrindo nova conexão RDP: {server_name} ({address})")
            self.open_rdp_config(address)
        else:
            print("Sessão já aberta foi maximizada.")

    def create_connection_buttons(self, layout):
        for server in self.servers:
            btn = QPushButton(server["name"])
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #00A010;
                    color: white;
                    font-weight: bold;
                    font-size: 17px;
                    border-radius: 10px;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #105617;
                }
            """)
            btn.clicked.connect(lambda _, addr=server["address"], name=server["name"]: self.verificar_e_abrir_rdp(name, addr))
            layout.addWidget(btn)
            self.button_list.append(btn)

    def open_config_dialog(self):
        dialog = ConfiguracaoDialog(self.servers)
        if dialog.exec_() == QDialog.Accepted:
            self.servers = dialog.get_servers()
            self.save_servers()

            for btn in self.button_list:
                btn.setParent(None)
            self.button_list.clear()

            # Atualiza os botões no layout correto
            self.create_connection_buttons(self.scroll_layout)

    def load_servers(self):
        if os.path.exists("servidores.json"):
            with open("servidores.json", "r") as f:
                return json.load(f)
        return [

        ]

    def save_servers(self):
        with open("servidores.json", "w") as f:
            json.dump(self.servers, f, indent=4)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ConnectionWindow()
    window.show()
    sys.exit(app.exec_())

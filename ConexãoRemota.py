import sys
import socket
import subprocess
import win32cred
import json
import os
import binascii
import base64
import pywintypes
import requests
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox,
    QHBoxLayout, QDesktopWidget, QDialog, QLineEdit, QFormLayout, QDialogButtonBox,
    QListWidget, QInputDialog, QScrollArea
)

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
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #005CC7;")
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
             QPushButton:hover {
                 background-color: #218838;
             }
         """)
        self.layout.addSpacing(10)
        self.layout.addWidget(buttons)

        self.setLayout(self.layout)
        self.setStyleSheet("""
             QDialog {
                 background-color: #f4f8fb;
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
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Status dos Servidores')
        self.setWindowIcon(QIcon('acesso-remoto.ico'))
        self.setGeometry(0, 0, 700, 550)
        self.setFixedSize(self.size())
        self.center()

        main_layout = QHBoxLayout(self)

        # Lado esquerdo
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        left_widget.setStyleSheet("background-color: #005CC7; color: white; border-radius: 10px;")

        status_title_label = QLabel('Acessos RDP')
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

        self.config_button = QPushButton('Configurar')
        self.config_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #e0a800;
                color: white;
            }
        """)

        self.config_button.clicked.connect(self.open_config_dialog)
        left_layout.addWidget(self.config_button)

        main_layout.addWidget(left_widget)

        # Lado direito
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        right_widget.setStyleSheet("background-color: white;")

        self.remote_access_label = QLabel('Acesso Remoto')
        self.remote_access_label.setAlignment(Qt.AlignCenter)
        self.remote_access_label.setStyleSheet("font-size: 24px; font-weight: bold; color: black;")
        right_layout.addWidget(self.remote_access_label)

        pixmap = QPixmap('img_acesso_remoto.png')
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

        self.remote_access_button = QPushButton(botao_texto)
        self.remote_access_button.setStyleSheet("""
            font-size: 20px; 
            padding: 15px 30px;
            background-color: #005CC7; 
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
        # Exemplo básico para Windows
        os.system(f"mstsc /v:{address}")

    def create_connection_buttons(self, layout):
        for server in self.servers:
            btn = QPushButton(server["name"])
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                    border-radius: 5px;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            btn.clicked.connect(lambda _, addr=server["address"]: self.open_rdp_config(addr))
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

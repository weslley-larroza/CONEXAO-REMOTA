from cx_Freeze import setup, Executable
import sys
import os

# Caminho relativo para empacotamento
def resource_path(relative_path):
    return os.path.join(os.path.abspath("."), relative_path)

# Arquivos extras (ícones, imagens, SVGs etc.)
includefiles = [
    ("acesso-remoto.ico", "acesso-remoto.ico"),
    ("img_acesso_remoto.png", "img_acesso_remoto.png"),
    ("logo.png", "logo.png"),
    ("settings.svg", "settings.svg"),
    ("icons8-github.svg", "icons8-github.svg"),
]

# Opções de build
build_exe_options = {
    "packages": ["os", "sys", "requests", "PyQt5.QtWidgets", "PyQt5.QtGui", "PyQt5.QtCore"],
    "excludes": ["tkinter", "PyQt5.QtQml"],  # evitar dependências desnecessárias
    "include_files": includefiles,
    "include_msvcr": True,
    "optimize": 1,
}

# Define base para ocultar terminal no Windows
base = "Win32GUI" if sys.platform == "win32" else None

# Configuração final
setup(
    name="AcessoRemoto",
    version="1.0",
    description="Status dos Servidores RDP",
    options={"build_exe": build_exe_options},
    executables=[
        Executable("ConexãoRemota.py", base=base, icon="acesso-remoto.ico")
    ]
)

"""
Helpers compartilhados pelas telas.
"""
from tkinter import messagebox


def mostrar_erro(parent, mensagem_amigavel: str, excecao: Exception = None,
                 titulo: str = "Erro"):
    """
    Mostra mensagem amigavel ao usuario e loga detalhes tecnicos no stdout.
    Usa em vez de `messagebox.showerror("Erro", str(e))` para evitar vazar
    schema MySQL ou caminhos em screenshots/prints.
    """
    if excecao is not None:
        print("[erro]", type(excecao).__name__, "-", str(excecao))
    messagebox.showerror(titulo, mensagem_amigavel, parent=parent)

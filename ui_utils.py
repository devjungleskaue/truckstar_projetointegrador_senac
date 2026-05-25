"""
Helpers de UI: redimensionamento, fullscreen, atalhos de tela.
"""


def habilitar_resize_e_fullscreen(janela, min_w=600, min_h=400):
    """
    Permite redimensionar a janela com o mouse, define tamanho mínimo
    e adiciona atalhos:
      F11   -> alterna tela cheia
      Esc   -> sai da tela cheia
      Ctrl+M-> maximiza (modo 'zoomed' no Windows)
    """
    try:
        janela.resizable(True, True)
    except Exception:
        pass
    try:
        janela.minsize(min_w, min_h)
    except Exception:
        pass

    estado = {'fullscreen': False}

    def alternar_fullscreen(event=None):
        estado['fullscreen'] = not estado['fullscreen']
        try:
            janela.attributes('-fullscreen', estado['fullscreen'])
        except Exception:
            pass
        return "break"

    def sair_fullscreen(event=None):
        if estado['fullscreen']:
            estado['fullscreen'] = False
            try:
                janela.attributes('-fullscreen', False)
            except Exception:
                pass
        return "break"

    def maximizar(event=None):
        try:
            if janela.state() == 'zoomed':
                janela.state('normal')
            else:
                janela.state('zoomed')
        except Exception:
            pass
        return "break"

    janela.bind('<F11>', alternar_fullscreen)
    janela.bind('<Escape>', sair_fullscreen)
    janela.bind('<Control-m>', maximizar)
    janela.bind('<Control-M>', maximizar)


def botao_tela_cheia(parent_bar, janela):
    """Retorna um CTkButton que maximiza/restaura a janela."""
    import customtkinter as ctk

    def toggle():
        try:
            if janela.state() == 'zoomed':
                janela.state('normal')
            else:
                janela.state('zoomed')
        except Exception:
            try:
                janela.attributes('-fullscreen',
                                  not janela.attributes('-fullscreen'))
            except Exception:
                pass

    return ctk.CTkButton(parent_bar, text="⛶ Tela cheia", width=110, height=28,
                         fg_color="gray35", hover_color="gray45", command=toggle)

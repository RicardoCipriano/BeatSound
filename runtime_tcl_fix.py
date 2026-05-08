import os
import sys

# Força o caminho do Tcl no executável
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    
    # Busca por _tcl_data e _tk_data dentro de _internal/ ou na raiz MEIPASS
    tcl_dir = os.path.join(base_path, '_internal', '_tcl_data')
    if not os.path.exists(tcl_dir):
        tcl_dir = os.path.join(base_path, '_tcl_data')
        
    tk_dir = os.path.join(base_path, '_internal', '_tk_data')
    if not os.path.exists(tk_dir):
        tk_dir = os.path.join(base_path, '_tk_data')

    if os.path.exists(tcl_dir):
        os.environ['TCL_LIBRARY'] = tcl_dir
        print(f"[FIX] TCL_LIBRARY set to: {tcl_dir}")
    if os.path.exists(tk_dir):
        os.environ['TK_LIBRARY'] = tk_dir
        print(f"[FIX] TK_LIBRARY set to: {tk_dir}")

    # Adiciona caminhos ao sys.path para garantir que módulos internos sejam achados
    internal_path = os.path.join(base_path, '_internal')
    if os.path.exists(internal_path) and internal_path not in sys.path:
        sys.path.insert(0, internal_path)

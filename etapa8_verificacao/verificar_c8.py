"""Atalho: o c8 agora roda pelo script geral.  python verificar_c8.py [opções]  =  python verificar.py casos/c8.json [opções]"""
import os, subprocess, sys
aqui = os.path.dirname(os.path.abspath(__file__))
sys.exit(subprocess.run([sys.executable, os.path.join(aqui, "verificar.py"), os.path.join(aqui, "casos", "c8.json")] + sys.argv[1:]).returncode)

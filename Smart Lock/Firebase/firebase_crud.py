import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
from config import DATABASE_URL

# Inicialização da app Firebase
cred = credentials.Certificate("Firebase/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': DATABASE_URL  
})

# Referência principal
ref = db.reference('smarlock')

# === FUNÇÕES DE AUTORIZAÇÃO ===
def criar_autorizacao(entrada, tipo, autorizado):
    chave = f"{tipo}_{entrada}"
    ref = db.reference(f"autorizacoes/{chave}")
    ref.set({
        "tipo": tipo,
        "autorizado": autorizado
    })

def atualizar_autorizacao(entrada, tipo, autorizado):
    chave = f"{tipo}_{entrada}"
    ref = db.reference(f"autorizacoes/{chave}")
    ref.update({
        "autorizado": autorizado
    })

def apagar_autorizacao(entrada, tipo):
    chave = f"{tipo}_{entrada}"
    ref = db.reference(f"autorizacoes/{chave}")
    ref.delete()

def ler_autorizacoes():
    ref = db.reference("autorizacoes")
    return ref.get() or {}

def verificar_autorizacao(entrada, tipo):
    chave = f"{tipo}_{entrada}"
    ref = db.reference(f"autorizacoes/{chave}")
    dados = ref.get()
    if dados and dados.get("autorizado"):
        registar_log(entrada, tipo, "autorizado")
        return True
    else:
        registar_log(entrada, tipo, "negado")
        return False



# === FUNÇÃO PARA REGISTAR LOGS ===
def registar_log(entrada, tipo, resultado):
    timestamp = datetime.now().isoformat()
    log_ref = db.reference("logs")
    log_ref.push({
        "entrada": f"{tipo}_{entrada}",
        "tipo": tipo,
        "resultado": resultado,
        "data": timestamp
    })

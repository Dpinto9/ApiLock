import time
from datetime import datetime, timedelta

def criar_qr_temporario(qr_data, tempo_validade_minutos):
    """Create a temporary QR code authorization"""
    agora = datetime.now()
    expiracao = agora + timedelta(minutes=tempo_validade_minutos)
    
    ref = base_ref.child(f"autorizacoes/qr_{qr_data}")
    ref.set({
        "tipo": "qr",
        "autorizado": True,
        "entrada": qr_data,
        "criado_em": agora.isoformat(),
        "expira_em": expiracao.isoformat()
    })
    return qr_data

def verificar_e_limpar_autorizacoes():
    """Check and clean expired authorizations"""
    autorizacoes = base_ref.child("autorizacoes").get() or {}
    agora = datetime.now()
    
    for key, auth in autorizacoes.items():
        if "expira_em" in auth:
            expiracao = datetime.fromisoformat(auth["expira_em"])
            if agora > expiracao:
                base_ref.child(f"autorizacoes/{key}").delete()
                print(f"Removido QR expirado: {auth['entrada']}")

def verificar_autorizacao(entrada, tipo):
    """Modified to check expiration"""
    chave = f"{tipo}_{entrada}"
    ref = base_ref.child(f"autorizacoes/{chave}")
    dados = ref.get()
    
    if not dados:
        registar_log(entrada, tipo, "negado")
        return False
    
    # Check expiration if it exists
    if "expira_em" in dados:
        expiracao = datetime.fromisoformat(dados["expira_em"])
        if datetime.now() > expiracao:
            ref.delete()  # Remove expired code
            registar_log(entrada, tipo, "negado (expirado)")
            return False
    
    if dados.get("autorizado"):
        registar_log(entrada, tipo, "autorizado")
        return True
    else:
        registar_log(entrada, tipo, "negado")
        return False
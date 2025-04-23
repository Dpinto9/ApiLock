from flask import Flask, render_template, request, redirect, session, jsonify
from config import SECRET_KEY, TOKEN_ADMIN
import Firebase.firebase_crud as db

app = Flask(__name__)
app.secret_key = SECRET_KEY

# === AUTENTICAÇÃO ===
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        token = request.form.get('token')
        if token == TOKEN_ADMIN:
            session['logado'] = True
            return redirect('/painel')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# === PAINEL PRINCIPAL ===
@app.route('/painel')
def painel():
    if 'logado' not in session:
        return redirect('/')
    
    # Get all PINs for display
    autorizacoes = db.ler_autorizacoes()
    pins = [
        {
            "entrada": key,
            "autorizado": value["autorizado"]
        }
        for key, value in autorizacoes.items()
        if value["tipo"] == "pin"
    ]
    
    return render_template('painel.html', pins=pins)

# === API ENDPOINTS ===
@app.route('/api/pins', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_pins():
    if 'logado' not in session:
        return jsonify({"error": "Não autorizado"}), 401

    if request.method == 'GET':
        autorizacoes = db.ler_autorizacoes()
        pins = [
            {
                "entrada": key,
                "autorizado": value["autorizado"]
            }
            for key, value in autorizacoes.items()
            if value["tipo"] == "pin"
        ]
        return jsonify(pins)

    elif request.method == 'POST':
        data = request.json
        pin = data.get('pin')
        autorizado = data.get('autorizado', True)
        
        if not pin:
            return jsonify({"error": "PIN é obrigatório"}), 400
        
        try:
            db.criar_autorizacao(pin, 'pin', autorizado)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'PUT':
        data = request.json
        entrada_original = data.get('entrada_original')
        nova_entrada = data.get('nova_entrada')
        autorizado = data.get('autorizado')
        
        if not all([entrada_original, nova_entrada]):
            return jsonify({"error": "Dados incompletos"}), 400
        
        try:
            db.atualizar_autorizacao(entrada_original, nova_entrada, 'pin', autorizado)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'DELETE':
        data = request.json
        pin = data.get('pin')
        
        if not pin:
            return jsonify({"error": "PIN é obrigatório"}), 400
        
        try:
            db.apagar_autorizacao(pin, 'pin')
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# === API PARA O ESP32 ===
@app.route('/verificar', methods=['POST'])
def verificar():
    dados = request.json
    entrada = dados.get('entrada')
    tipo = dados.get('tipo')

    if not all([entrada, tipo]):
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        autorizado = db.verificar_autorizacao(entrada, tipo)
        return jsonify({"autorizado": autorizado})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

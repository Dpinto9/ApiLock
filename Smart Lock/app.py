from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from functools import wraps
from config import SECRET_KEY, TOKEN_ADMIN
import Firebase.firebase_crud as db
from datetime import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ===== DECORATOR PARA LOGIN REQUERIDO =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logado' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ===== FILTRO PARA FORMATAR DATA =====
@app.template_filter('format_datetime')
def format_datetime(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return value

# ===== ROTAS DE AUTENTICAÇÃO =====
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'logado' in session:
        return redirect(url_for('painel'))
    
    if request.method == 'POST':
        token = request.form.get('token')
        if token == TOKEN_ADMIN:
            session['logado'] = True
            next_page = request.args.get('next')
            return redirect(next_page or url_for('painel'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== PAINEL PRINCIPAL =====
@app.route('/painel')
@login_required
def painel():
    autorizacoes = db.ler_autorizacoes()
    pins = [
        {"entrada": key, "autorizado": value["autorizado"]}
        for key, value in autorizacoes.items()
        if value["tipo"] == "pin"
    ]
    return render_template('painel.html', pins=pins)

# ===== API PARA GERENCIAMENTO DE PINS =====
@app.route('/api/pins', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def manage_pins():
    if request.method == 'GET':
        autorizacoes = db.ler_autorizacoes()
        pins = [
            {"entrada": key, "autorizado": value["autorizado"]}
            for key, value in autorizacoes.items()
            if value["tipo"] == "pin"
        ]
        return jsonify(pins)

    data = request.get_json()
    
    if request.method == 'POST':
        pin = data.get('pin')
        if not pin:
            return jsonify({"error": "PIN é obrigatório"}), 400
        db.criar_autorizacao(pin, 'pin', data.get('autorizado', True))
        return jsonify({"success": True})

    elif request.method == 'PUT':
        entrada_original = data.get('entrada_original')
        nova_entrada = data.get('nova_entrada')
        if not all([entrada_original, nova_entrada]):
            return jsonify({"error": "Dados incompletos"}), 400
        db.atualizar_autorizacao(entrada_original, nova_entrada, 'pin', data.get('autorizado', True))
        return jsonify({"success": True})

    elif request.method == 'DELETE':
        pin = data.get('pin')
        if not pin:
            return jsonify({"error": "PIN é obrigatório"}), 400
        db.apagar_autorizacao(pin, 'pin')
        return jsonify({"success": True})

# ===== API PARA O ESP32 =====
@app.route('/verificar', methods=['POST'])
def verificar():
    dados = request.json
    entrada = dados.get('entrada')
    tipo = dados.get('tipo')

    if not all([entrada, tipo]):
        return jsonify({"error": "Dados incompletos"}), 400
    
    autorizado = db.verificar_autorizacao(entrada, tipo)
    return jsonify({"autorizado": autorizado})

# ===== HISTÓRICO DE ACESSOS =====
@app.route('/historico')
@login_required
def historico():
    if 'logado' not in session:
        return redirect('/')
    
    # Read logs from Firebase
    logs = db.ler_logs()
    
    # Convert logs dictionary to list and sort by date (newest first)
    logs_list = []
    for log_id, log_data in logs.items():
        log_data['id'] = log_id
        logs_list.append(log_data)
    
    # Sort logs by date in descending order
    logs_list.sort(key=lambda x: x['data'], reverse=True)
    
    def format_datetime(timestamp):
        # Convert string timestamp to datetime object
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        # Format datetime to a more readable string
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    
    return render_template('historico.html', 
                         logs=logs_list, 
                         format_datetime=format_datetime)

if __name__ == '__main__':
    app.run(debug=True)
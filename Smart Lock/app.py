from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from functools import wraps
from config import SECRET_KEY, TOKEN_ADMIN
import Firebase.firebase_crud as db
from datetime import datetime
from QRcode.qrcode_manager import QRCodeManager 

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ===== DECORATOR PARA LOGIN REQUERIDO =====
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logado' not in session:
            return redirect('/')
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
    
    logs = db.ler_logs()
    
    logs_list = []
    for log_id, log_data in logs.items():
        log_data['id'] = log_id
        logs_list.append(log_data)
    
    logs_list.sort(key=lambda x: x['data'], reverse=True)
    
    def format_datetime(timestamp):
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    
    return render_template('historico.html', 
                         logs=logs_list, 
                         format_datetime=format_datetime)

# ===== QRCode =====
qr_manager = QRCodeManager()

@app.route('/qrcode', methods=['GET', 'POST'])
@login_required
def handle_qrcode():
    if request.method == 'GET':
        qr_manager.clean_resources()  
        return render_template('qrcode.html')
    
    try:
        validity = int(request.form.get('validade', 5))
        if not 1 <= validity <= 60:
            return jsonify({'error': 'Validade deve ser entre 1-60 minutos'}), 400
            
        qr_info = qr_manager.generate_qr_code(validity)
        return jsonify({
            'success': True,
            'qr_image': f'/static/temp_qr/{qr_info["qr_data"]}.png',
            'qr_data': qr_info['qr_data'],
            'valid_until': qr_info['valid_until']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/qrcode/delete', methods=['POST'])
@login_required
def delete_qrcode():
    data = request.json
    qr_data = data.get('qr_data')
    
    if not qr_data:
        return jsonify({'error': 'QR data missing'}), 400
        
    if qr_manager.force_delete(qr_data):
        return jsonify({
            'success': True,
            'reset': True 
        })
    return jsonify({'error': 'Failed to delete QR code'}), 500

@app.route('/qrcode/status')
@login_required
def qrcode_status():
    try:
        active_qr = qr_manager.get_active_qr()
        if active_qr:
            return jsonify({
                'active': True,
                'qr_data': active_qr['qr_data'],
                'remaining': active_qr['remaining'],
                'valid_until': active_qr['valid_until'],
                'qr_image': f'/static/temp_qr/{active_qr["qr_data"]}.png'
            })
        return jsonify({'active': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


if __name__ == '__main__':
    app.run(debug=True)
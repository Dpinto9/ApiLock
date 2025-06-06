from flask import Flask, render_template, request, redirect, session, jsonify, url_for, session
from functools import wraps
from config import SECRET_KEY, TOKEN_ADMIN, API_KEY
from datetime import datetime, timedelta
from QRcode.qrcode_manager import QRCodeManager
from functools import wraps
import Firebase.firebase_crud as db
import os
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.secret_key = SECRET_KEY
csrf = CSRFProtect(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logado' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY') or request.args.get('api_key')
        if api_key != API_KEY:  
            return jsonify({"error": "Acesso não autorizado"}), 401
        return view_function(*args, **kwargs)
    return decorated_function

@app.template_filter('format_datetime')
def format_datetime(value):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return value


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

@app.route('/api/pins', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def manage_pins():
    try:
        if request.method == 'GET':
            autorizacoes = db.ler_autorizacoes()
            pins = [
                {"entrada": key, "autorizado": value["autorizado"]}
                for key, value in autorizacoes.items()
                if value["tipo"] == "pin"
            ]
            return jsonify({"success": True, "data": pins})

        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados não recebidos"}), 400

        if request.method == 'POST':
            pin = data.get('pin')
            if not pin:
                return jsonify({"error": "PIN é obrigatório"}), 400
                
            db.criar_autorizacao(pin, 'pin', data.get('autorizado', True))
            return jsonify({"success": True, "message": "PIN adicionado com sucesso"})
        
        elif request.method == 'PUT':
            entrada_original = data.get('entrada_original')
            nova_entrada = data.get('nova_entrada')
            if not all([entrada_original, nova_entrada]):
                return jsonify({"error": "Dados incompletos"}), 400
                
            db.atualizar_autorizacao(
                entrada_original, 
                nova_entrada, 
                'pin', 
                data.get('autorizado', True)
            )
            return jsonify({"success": True, "message": "PIN atualizado com sucesso"})

        elif request.method == 'DELETE':
            pin = data.get('pin')
            if not pin:
                return jsonify({"error": "PIN é obrigatório"}), 400
                
            db.apagar_autorizacao(pin, 'pin')
            return jsonify({"success": True, "message": "PIN removido com sucesso"})

    except Exception as e:
        return jsonify({
            "error": "Erro no servidor",
            "details": str(e)
        }), 500

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

@app.route('/api/logs/clear', methods=['POST'])
@login_required
def clear_logs():
    try:
        db.limpar_logs()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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

# ===== ANALITICA =====
@app.route('/analitica')
@login_required
def analytics():
    initial_data = {
        'total_acessos': 0,
        'taxa_sucesso': 0,
        'horario_pico': '00:00',
        'tentativas_negadas': 0,
        'dias': [],
        'acessos_por_dia': [],
        'tipos_acesso': [0, 0, 0],  
        'ultimos_acessos': []
    }
    return render_template('analiticas.html', **initial_data)

@app.route('/analitica/dados')
@login_required
def get_analytics_data():
    try:
        logs = db.ler_logs()
        current_time = datetime.now()
        
        # Initialize data structures
        total_acessos = 0
        acessos_autorizados = 0
        acessos_por_hora = [0] * 24
        acessos_por_dia = {}
        tipos_acesso = {'pin': 0, 'qr': 0, 'outros': 0}
        
        # Process last 30 days
        for log_id, log in logs.items():
            log_date = datetime.fromisoformat(log['data'])
            days_diff = (current_time - log_date).days
            
            if days_diff <= 30:
                total_acessos += 1
                
                # Count authorized access
                if log['resultado'] == 'autorizado':
                    acessos_autorizados += 1
                
                # Count by type
                tipo = log['tipo']
                if tipo == 'pin':
                    tipos_acesso['pin'] += 1
                elif tipo == 'qr':
                    tipos_acesso['qr'] += 1
                else:
                    tipos_acesso['outros'] += 1
                
                # Track hourly access
                acessos_por_hora[log_date.hour] += 1
                
                # Track daily access
                dia = log_date.strftime('%Y-%m-%d')
                acessos_por_dia[dia] = acessos_por_dia.get(dia, 0) + 1
        
        # Calculate peak hour
        hora_pico = acessos_por_hora.index(max(acessos_por_hora))
        hora_pico_fmt = f"{hora_pico:02d}:00"
        
        # Calculate success rate
        taxa_sucesso = round((acessos_autorizados / total_acessos * 100) if total_acessos > 0 else 0, 1)
        
        # Get last 7 days for chart
        dias = []
        valores = []
        for i in range(7):
            dia = (current_time - timedelta(days=i)).strftime('%Y-%m-%d')
            dias.insert(0, dia)
            valores.insert(0, acessos_por_dia.get(dia, 0))
        
        # Get last 10 access attempts for table
        ultimos_acessos = []
        sorted_logs = sorted(logs.items(), key=lambda x: x[1]['data'], reverse=True)
        for _, log in sorted_logs[:10]:
            ultimos_acessos.append({
                'data': datetime.fromisoformat(log['data']).strftime('%d/%m/%Y %H:%M'),
                'tipo': log['tipo'].upper(),
                'status': log['resultado'],
                'metodo': 'Normal' if log['tipo'] != '2fa' else '2FA'
            })
        
        return jsonify({
            'total_acessos': total_acessos,
            'taxa_sucesso': taxa_sucesso,
            'horario_pico': hora_pico_fmt,
            'tentativas_negadas': total_acessos - acessos_autorizados,
            'dias': dias,
            'acessos_por_dia': valores,
            'tipos_acesso': [tipos_acesso['pin'], tipos_acesso['qr'], tipos_acesso['outros']],
            'ultimos_acessos': ultimos_acessos
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== DEFINICOES =====  
@app.route('/definicoes')
@login_required
def definicoes():
    settings = db.ler_configuracoes()
    return render_template('definicoes.html', settings=settings)

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings_api():
    try:
        data = request.get_json()
        settings = {
            'two_factor_enabled': data.get('two_factor_enabled', False),
            'pin_enabled': data.get('pin_enabled', False)
        }
        
        db.atualizar_configuracoes(settings)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400



# ===== API PARA O ESP32 =====
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address, 
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/verificar', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
@csrf.exempt
def verificar():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"error": "No data received"}), 400
            
        entrada = dados.get('entrada')
        tipo = dados.get('tipo')

        if not all([entrada, tipo]):
            return jsonify({"error": "Missing required fields"}), 400
        
        if tipo not in ['pin', 'qr', 'rfid']:
            return jsonify({"error": "Invalid authentication type"}), 400
        
        config = db.ler_configuracoes()
        
        if tipo == 'pin' and not config.get('pin_enabled', True):
            return jsonify({
                "autorizado": False,
                "motivo": "PINs desativados",
                "tentativa_registada": True
            })
        
        # Special handling for QR codes 
        if tipo == 'qr':
            autorizado = db.ler_qrcode(entrada)
            db.registar_log(entrada, tipo, "autorizado" if autorizado else "negado")
        else:
            autorizado = db.verificar_autorizacao(entrada, tipo)
        
        if config.get('two_factor_enabled', False):
            return jsonify({
                "autorizado": False,
                "2fa_requerido": True,
                "passo_autenticado": tipo,
                # "proximo_passo": "qr" if tipo == "pin" else "pin"
            })
        
        return jsonify({
            "autorizado": autorizado,
            "tentativa_registada": True
        })
        
    except Exception as e:
        if tipo == 'qr':
            db.registar_log(entrada, tipo, "erro")
        return jsonify({
            "error": "Server error",
            "details": str(e)
        }), 500



@app.route('/verificar-2fa', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
@csrf.exempt
def verificar_2fa():
    dados = request.json
    pin = dados.get('pin')
    qr = dados.get('qr')
    
    if not all([pin, qr]):
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        # Verify credentials without logging individual attempts
        pin_ok = db.verificar_autorizacao(pin, 'pin', registrar_log=False)
        qr_ok = db.ler_qrcode(qr)
        
        # Only log the final 2FA result
        if pin_ok and qr_ok:
            db.registar_log(f"{pin}+{qr}", '2fa', "autorizado")
            return jsonify({
                "autorizado": True,
                "tentativa_registada": True
            })
        
        db.registar_log(f"{pin}+{qr}", '2fa', "negado")
        return jsonify({
            "autorizado": False,
            "motivo": "Credenciais 2FA inválidas",
            "tentativa_registada": True
        })
        
    except Exception as e:
        db.registar_log(f"{pin}+{qr}", '2fa', "erro")
        return jsonify({
            "error": "Erro no servidor",
            "detalhes": str(e)
        }), 500


# ESP VERIFICATION CONNECTION
@app.route('/status', methods=['GET'])
@require_api_key
def status():
    try:
        return jsonify({
            "status": "online",
            "message": "ESP conectado com sucesso"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "offline",
            "message": "Erro ao conectar",
            "error": str(e)
        }), 500

@app.route('/2factor/status', methods=['GET'])
@require_api_key
@csrf.exempt
def check_2fa_status():
    try:
        config = db.ler_configuracoes()
        two_factor_enabled = config.get('two_factor_enabled', False)
        pin_enabled = config.get('pin_enabled', True)
        
        return jsonify({
            "2fa_enabled": two_factor_enabled,
            "pin_enabled": pin_enabled,
            "status": {
                "2fa": "active" if two_factor_enabled else "inactive",
                "pin": "active" if pin_enabled else "inactive"
            },
        })
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "details": str(e),
            "status": {
                "2fa": "error",
                "pin": "error"
            }
        }), 500





if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
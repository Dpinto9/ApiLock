from flask import Flask, render_template, request, redirect, session, jsonify
import Firebase.firebase_crud as db
import qrcode
import base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = "smarlocksupersegredo"

TOKEN_ADMIN = "admin123"

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

# === PAINEL CRUD ===
@app.route('/painel', methods=['GET', 'POST'])
def painel():
    if not session.get('logado'):
        return redirect('/')
    
    mensagem = ""
    qr_code = None
    
    if request.method == 'POST':
        entrada = request.form['entrada']
        tipo = request.form['tipo']
        autorizado = 'autorizado' in request.form
        acao = request.form['acao']

        if acao == 'criar':
            db.criar_autorizacao(entrada, tipo, autorizado)
            mensagem = "Autorização criada."
            
            # Generate QR code if type is 'qr'
            if tipo == 'qr':
                # Create QR code
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(entrada)
                qr.make(fit=True)
                
                # Create image
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Convert to base64 for display
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                qr_code = base64.b64encode(buffered.getvalue()).decode()

        elif acao == 'atualizar':
            db.atualizar_autorizacao(entrada, tipo, autorizado)
            mensagem = "Autorização atualizada."
        elif acao == 'apagar':
            db.apagar_autorizacao(entrada, tipo)
            mensagem = "Autorização apagada."

    registos = db.ler_autorizacoes()
    return render_template('painel.html', mensagem=mensagem, registos=registos, qr_code=qr_code)

# === API PARA O ESP32 ===
@app.route('/verificar', methods=['POST'])
def verificar():
    dados = request.json
    entrada = dados.get('entrada')
    tipo = dados.get('tipo')

    if entrada and tipo:
        autorizado = db.verificar_autorizacao(entrada, tipo)
        return jsonify({"autorizado": autorizado})
    
    return jsonify({"erro": "dados inválidos"}), 400

if __name__ == '__main__':
    app.run(debug=True)

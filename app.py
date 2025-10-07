#!/usr/bin/env python3
"""
Aplicação Web Flask para Validação de Arquivos CNAB400 Bradesco
"""
from flask import Flask, render_template, request, jsonify, send_file
import os
import tempfile
import json
from validator import validate_file
from layouts.bradesco_cnab400 import set_current_century, set_validate_nosso_numero

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

ALLOWED_EXTENSIONS = {'REM', 'rem', 'txt', 'TXT'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/validar', methods=['POST'])
def validar():
    if 'arquivo' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['arquivo']
    
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Tipo de arquivo não permitido. Use .REM ou .txt'}), 400
    
    # Salvar arquivo temporário
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(temp_path)
    
    try:
        # Parâmetros opcionais
        seculo_base = int(request.form.get('seculo_base', 2000))
        tolerancia = int(request.form.get('tolerancia_centavos', 0))
        validar_dv = request.form.get('validar_nosso_numero', 'false').lower() == 'true'
        min_severity = request.form.get('min_severidade', 'field')
        
        # Configurar validação
        set_current_century(seculo_base)
        set_validate_nosso_numero(validar_dv)
        
        # Executar validação
        result = validate_file(temp_path, tolerancia_centavos=tolerancia)
        
        # Filtrar por severidade
        severity_order = {'fatal': 0, 'business': 1, 'field': 2}
        min_level = severity_order.get(min_severity, 2)
        
        errors_filtered = [
            e for e in result.errors 
            if severity_order.get(e.get('severity', 'field'), 2) <= min_level
        ]
        
        # Calcular estatísticas do arquivo
        with open(temp_path, 'r', encoding='latin-1') as f:
            lines = f.readlines()
            total_linhas = len(lines)
            total_titulos = 0
            valor_total = 0
            
            for line in lines:
                if line.startswith('1'):  # Registro tipo 1 (detalhe/título)
                    total_titulos += 1
                    # Valor do título está nas posições 127-139 (13 dígitos, 2 decimais)
                    if len(line) >= 139:
                        valor_str = line[126:139].strip()
                        if valor_str.isdigit():
                            valor_total += int(valor_str) / 100  # Converter centavos para reais
        
        # Preparar resposta
        response = {
            'valid': result.valid and len(errors_filtered) == 0,
            'filename': file.filename,
            'total_linhas': total_linhas,
            'total_erros': len(errors_filtered),
            'erros': errors_filtered,
            'resumo': {
                'header_ok': lines[0].startswith('0') if lines else False,
                'trailer_ok': lines[-1].startswith('9') if lines else False,
                'total_titulos': total_titulos,
                'valor_total': valor_total,
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500
    
    finally:
        # Limpar arquivo temporário
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/download-exemplo')
def download_exemplo():
    """Download de arquivo CNAB de exemplo (se existir)"""
    exemplo = 'CB14081.REM'
    if os.path.exists(exemplo):
        return send_file(exemplo, as_attachment=True)
    return jsonify({'error': 'Arquivo de exemplo não encontrado'}), 404

if __name__ == '__main__':
    # Rodar em modo desenvolvimento
    # Para produção use: gunicorn -w 4 -b 0.0.0.0:5000 app:app
    app.run(host='0.0.0.0', port=5000, debug=True)

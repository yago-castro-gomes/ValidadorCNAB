#!/bin/bash
# Script para rodar o validador CNAB via web

echo "🚀 Iniciando Validador CNAB400 Web..."
echo ""

# Verificar se Flask está instalado
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Instalando dependências..."
    pip3 install -r requirements.txt
    echo ""
fi

# Rodar aplicação
echo "✅ Servidor rodando em: http://localhost:5000"
echo "   Acesse pelo navegador ou compartilhe na rede local"
echo ""
echo "   Pressione Ctrl+C para parar o servidor"
echo ""

python3 app.py

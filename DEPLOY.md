# 🚀 Como Hospedar Gratuitamente

## Opção 1: Render.com (Recomendado - Mais Fácil)

### Passo a Passo:

1. **Criar conta no GitHub** (se não tiver)

   - Acesse: https://github.com/signup

2. **Criar repositório no GitHub**

   ```bash
   cd /home/yago/Documentos/ValidadorCNAB
   git init
   git add .
   git commit -m "Initial commit - Validador CNAB400"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/validador-cnab.git
   git push -u origin main
   ```

3. **Criar conta no Render**

   - Acesse: https://render.com/
   - Faça login com GitHub

4. **Deploy no Render**

   - Clique em "New +" → "Web Service"
   - Conecte seu repositório GitHub
   - Configure:
     - **Name:** validador-cnab
     - **Environment:** Python 3
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn app:app`
   - Clique em "Create Web Service"

5. **Aguarde deploy (2-3 minutos)**
   - URL ficará: `https://validador-cnab.onrender.com`

### ⚠️ Limitação Gratuita:

- App "dorme" após 15min sem uso
- Primeiro acesso após sleep demora ~30s para "acordar"

---

## Opção 2: Railway.app

### Passo a Passo:

1. **Criar conta no Railway**

   - Acesse: https://railway.app/
   - Login com GitHub

2. **Deploy**

   - "New Project" → "Deploy from GitHub repo"
   - Selecione seu repositório
   - Railway detecta Python automaticamente
   - Deploy automático!

3. **Gerar domínio público**
   - Settings → "Generate Domain"
   - URL: `https://validador-cnab-production.up.railway.app`

### 💰 Custo:

- $5 crédito grátis/mês
- Suficiente para uso leve
- Precisa cartão (não cobra se não exceder)

---

## Opção 3: PythonAnywhere

### Passo a Passo:

1. **Criar conta**

   - https://www.pythonanywhere.com/registration/register/beginner/

2. **Upload do código**

   - Dashboard → Files → Upload
   - Ou clonar do GitHub via Bash

3. **Configurar Web App**

   - Web → "Add a new web app"
   - Framework: Flask
   - Python version: 3.10
   - Configurar WSGI file apontando para `app.py`

4. **Reload**
   - URL: `https://SEU_USUARIO.pythonanywhere.com`

### ⚠️ Limitação:

- CPU limitada
- 512MB storage
- Não pode usar scheduled tasks no free tier

---

## Opção 4: Fly.io

### Passo a Passo:

1. **Instalar Fly CLI**

   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**

   ```bash
   flyctl auth login
   ```

3. **Deploy**
   ```bash
   cd /home/yago/Documentos/ValidadorCNAB
   flyctl launch
   flyctl deploy
   ```

---

## 🎯 Recomendação Final:

**Para simplicidade:** Use **Render.com**

- Zero configuração complexa
- Deploy em 5 minutos
- Gratuito permanente

**Para performance:** Use **Railway.app**

- Não dorme
- Mais rápido
- $5/mês grátis (suficiente)

---

## 📝 Checklist Antes de Subir:

✅ Remover arquivos sensíveis (.REM de clientes)
✅ Verificar .gitignore
✅ Testar localmente: `gunicorn app:app`
✅ Commit e push para GitHub
✅ Escolher plataforma e seguir passos

---

## 🔧 Comandos Úteis:

### Testar localmente com Gunicorn:

```bash
gunicorn app:app
# Acesse: http://localhost:8000
```

### Inicializar Git:

```bash
git init
git add .
git commit -m "Initial commit"
```

### Criar repositório GitHub:

```bash
# No GitHub: criar repositório "validador-cnab"
git remote add origin https://github.com/SEU_USUARIO/validador-cnab.git
git push -u origin main
```

@echo off
title TITAN GLOBAL SUITE - Push to GitHub
echo ==========================================================
echo    PERFECT LIFE TITAN SUITE - AUTOMATIC GITHUB SYNC
echo ==========================================================
echo.
cd /d "%~dp0"

:: Check if git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] O Git nao esta instalado neste computador ou nao esta no PATH.
    echo Por favor, instale o Git e tente novamente.
    pause
    exit /b
)

:: Initialize git repository if not exists
if not exist .git (
    echo [SISTEMA] Inicializando repositorio Git local...
    git init
    git branch -M main
)

:: Create a basic .gitignore to keep cache and large dynamic data separate
if not exist .gitignore (
    echo [SISTEMA] Criando arquivo .gitignore...
    echo __pycache__/ > .gitignore
    echo *.pyc >> .gitignore
    echo .stfolder >> .gitignore
    echo .streamlit/ >> .gitignore
)

:: Stage all files
echo [SISTEMA] Adicionando arquivos ao commit...
git add .

:: Commit
echo [SISTEMA] Salvando commit local de implantacao...
git commit -m "Deploy: Ultimate Real-Time Market Integration & Fixes"

echo.
echo ==========================================================
echo    PASSO 2: CONEXÃO COM O REPOSITÓRIO REMOTO
echo ==========================================================
echo.
echo Por favor, crie um repositorio VAZIO no seu GitHub (ex: "titan-suite")
echo e cole a URL do repositorio abaixo (ex: https://github.com/usuario/titan-suite.git)
echo.
set /p giturl="URL do Repositorio GitHub: "

if "%giturl%"=="" (
    echo [ERRO] Nenhuma URL foi inserida. Operacao cancelada.
    pause
    exit /b
)

:: Link remote and push
git remote remove origin >nul 2>nul
git remote add origin %giturl%
echo.
echo [SISTEMA] Enviando codigo para o GitHub...
git push -u origin main --force

if %errorlevel% eq 0 (
    echo.
    echo ==========================================================
    echo    [SUCESSO] CODIGO DISPONIVEL NO GITHUB!
    echo ==========================================================
    echo.
    echo Agora siga estes 3 passos simples para colocar online gratis:
    echo 1. Acesse o site https://render.com ou https://railway.app e crie uma conta gratuita.
    echo 2. Clique em "New Web Service" (no Render) ou "New Project" (no Railway).
    echo 3. Selecione o seu repositorio do GitHub e clique em "Deploy".
    echo.
    echo O servidor instalara as dependencias e gerara seu Link de Staging em 60 segundos!
) else (
    echo.
    echo [ERRO] Houve uma falha ao enviar o codigo para o GitHub.
    echo Verifique suas credenciais de login ou se o repositorio no GitHub foi criado.
)

pause

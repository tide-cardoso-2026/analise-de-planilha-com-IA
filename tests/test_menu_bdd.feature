# language: pt
Funcionalidade: Menu Interativo do Dashboard IA
  Como um usuário do sistema
  Quero ter um menu com opções claras
  Para poder controlar o comportamento do aplicativo

  Cenário: Opção 1 - Apenas Rodar Análise
    Quando escolho a opção "1"
    Então o sistema deve rodar a análise dos dados
    E deve gerar arquivo JSON em outputs/insights.json
    E deve gerar arquivo Markdown em outputs/dashboard.md
    E deve gerar arquivo PDF em outputs/analise_completa.pdf
    E o programa deve encerrar sem abrir dashboard
    E nenhuma página web deve ser aberta

  Cenário: Opção 2 - Rodar Análise + Dashboard
    Quando escolho a opção "2"
    Então o sistema deve rodar a análise dos dados
    E deve gerar todos os arquivos (JSON, Markdown, PDF)
    E deve iniciar o dashboard Streamlit
    E deve abrir a página http://localhost:8501 no navegador
    E o programa deve ficar rodando até eu pressionar Ctrl+C
    Quando pressiono Ctrl+C
    Então o programa deve encerrar o dashboard e sair

  Cenário: Opção 3 - Apenas Abrir Dashboard
    Quando arquivos de análise já existem em outputs/
    E escolho a opção "3"
    Então o sistema NOT deve rodar a análise novamente
    E deve iniciar apenas o dashboard Streamlit
    E deve abrir a página http://localhost:8501 no navegador
    Quando pressiono Ctrl+C
    Então o programa deve encerrar o dashboard e sair

  Cenário: Opção 4 - Sair
    Quando escolho a opção "4"
    Então o programa deve exibir "👋 Até logo!"
    E deve encerrar imediatamente
    E nenhum arquivo deve ser criado
    E nenhum dashboard deve ser aberto

  Cenário: Entrada Inválida
    Quando escolho uma opção inválida como "5"
    Então deve exibir mensagem "❌ Opção inválida. Digite 1, 2, 3 ou 4."
    E deve pedir novamente para escolher uma opção

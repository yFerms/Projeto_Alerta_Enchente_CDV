import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def enviar_email_alerta(caminhos_imagens, nivel, tendencia):
    remetente = os.getenv("EMAIL_REMETENTE")
    senha = os.getenv("EMAIL_SENHA")
    destinatario = os.getenv("EMAIL_DESTINATARIO")

    if not remetente or not senha or not destinatario:
        print("⚠️ Configurações de e-mail não encontradas no .env")
        return

    print("\n--- 📧 PREPARANDO ENVIO DE E-MAIL ---")

    # 1. Configura o Assunto e Cabeçalhos
    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = destinatario
    
    # Assunto dinâmico com emojis para chamar atenção
    emoji = "🟢"
    if nivel > 650: emoji = "🟠"
    if nivel > 786: emoji = "🔴"
    
    msg['Subject'] = f"{emoji} ALERTA RIO PIRACICABA: {nivel:.0f}cm ({tendencia})"

    # 2. Corpo do E-mail (HTML para ficar bonito)
    corpo_html = f"""
    <html>
      <body>
        <h2 style="color: #2c3e50;">Monitoramento Cachoeira do Vale</h2>
        <p>Seguem os dados atualizados da estação <strong>Mário de Carvalho</strong>:</p>
        <ul>
            <li><strong>Nível Atual:</strong> {nivel:.0f} cm</li>
            <li><strong>Tendência:</strong> {tendencia}</li>
            <li><strong>Data/Hora:</strong> {os.getenv('COMPUTERNAME', 'Servidor')}</li>
        </ul>
        <p><em>As imagens detalhadas do monitoramento estão em anexo.</em></p>
        <hr>
        <p style="font-size: 10px; color: gray;">Sistema Automático de Alerta de Enchentes - TCC Engenharia de Software</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(corpo_html, 'html'))

    # 3. Anexar as Imagens
    for caminho in caminhos_imagens:
        path = Path(caminho)
        if path.exists():
            try:
                # Abre a imagem em modo binário
                with open(path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                
                # Codifica para envio
                encoders.encode_base64(part)
                
                # Adiciona cabeçalho do anexo
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {path.name}",
                )
                msg.attach(part)
                print(f"   📎 Anexado: {path.name}")
            except Exception as e:
                print(f"   ⚠️ Erro ao anexar {path.name}: {e}")

    # 4. Conecta no Gmail e Envia
    try:
        # Servidor SMTP do Gmail (se for Outlook é smtp-mail.outlook.com porta 587)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # Criptografia
        server.login(remetente, senha)
        text = msg.as_string()
        server.sendmail(remetente, destinatario, text)
        server.quit()
        print("   ✅ E-mail enviado com sucesso!")
    except Exception as e:
        print(f"   ❌ Erro ao enviar e-mail: {e}")
#!/usr/bin/env python3
"""
Script para buscar NF-e usando SOAP direto (sem WSDL)
Mais estável e funciona mesmo quando o WSDL está indisponível
"""
import base64
import os
import argparse
import gzip
from datetime import datetime, timedelta
import requests_pkcs12
from lxml import etree

# === CONFIGURAÇÕES ===
CERT_PATH = "via_palhoca.pfx"
CERT_PASS = "Via2025#"
CNPJ = "49091246000105"
UF_COD = "42"  # Santa Catarina

# URL do serviço
URL = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"


def criar_envelope_soap(ult_nsu="000000000000000"):
    """Cria envelope SOAP para consulta de DFe"""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <nfeDadosMsg>
        <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
          <tpAmb>1</tpAmb>
          <cUFAutor>{UF_COD}</cUFAutor>
          <CNPJ>{CNPJ}</CNPJ>
          <distNSU>
            <ultNSU>{ult_nsu}</ultNSU>
          </distNSU>
        </distDFeInt>
      </nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""


def consultar_dfe(ult_nsu="000000000000000"):
    """Consulta documentos fiscais via SOAP"""
    envelope = criar_envelope_soap(ult_nsu)

    headers = {
        "Content-Type": "application/soap+xml; charset=utf-8",
    }

    try:
        response = requests_pkcs12.post(
            URL,
            data=envelope.encode("utf-8"),
            headers=headers,
            pkcs12_filename=CERT_PATH,
            pkcs12_password=CERT_PASS,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")

        return etree.fromstring(response.content)

    except Exception as e:
        raise Exception(f"Erro na consulta SOAP: {e}")


def extrair_documentos(resposta_xml):
    """Extrai e decodifica documentos do XML de resposta"""
    documentos = []

    # Namespace SOAP
    ns = {
        'soap': 'http://www.w3.org/2003/05/soap-envelope',
        'nfe': 'http://www.portalfiscal.inf.br/nfe'
    }

    # Busca código de status
    cStat = resposta_xml.findtext('.//nfe:cStat', namespaces=ns)
    xMotivo = resposta_xml.findtext('.//nfe:xMotivo', namespaces=ns)

    if cStat != "138":  # 138 = sucesso
        status_msg = f"Status {cStat}: {xMotivo}" if cStat else "Resposta inválida"
        if cStat == "656":  # Nenhum documento encontrado
            return [], None, None, status_msg
        raise Exception(status_msg)

    # Extrai NSUs
    ultNSU = resposta_xml.findtext('.//nfe:ultNSU', namespaces=ns)
    maxNSU = resposta_xml.findtext('.//nfe:maxNSU', namespaces=ns)

    # Extrai documentos
    docs_zip = resposta_xml.findall('.//nfe:docZip', namespaces=ns)

    for doc_zip in docs_zip:
        try:
            # O conteúdo está em Base64
            conteudo_b64 = doc_zip.text
            if not conteudo_b64:
                continue

            # Decodifica Base64
            conteudo_comprimido = base64.b64decode(conteudo_b64)

            # Descomprime GZIP
            try:
                conteudo_xml = gzip.decompress(conteudo_comprimido)
            except:
                # Se não estiver comprimido, usa direto
                conteudo_xml = conteudo_comprimido

            # Parse XML
            xml = etree.fromstring(conteudo_xml)
            documentos.append(xml)

        except Exception as e:
            print(f"⚠️  Erro ao processar documento: {e}")
            continue

    return documentos, ultNSU, maxNSU, xMotivo


def extrair_data(xml):
    """Extrai data de emissão da NF-e"""
    # Tenta diferentes formatos de data
    dhEmi = xml.findtext(".//{*}dhEmi")
    if dhEmi:
        try:
            return datetime.fromisoformat(dhEmi.replace("Z", "+00:00"))
        except:
            # Tenta apenas a parte da data
            return datetime.strptime(dhEmi[:10], "%Y-%m-%d")
    return None


def buscar_todos_documentos():
    """Busca todos os documentos disponíveis"""
    ult_nsu = "000000000000000"
    docs_todos = []
    iteracao = 0

    print("🔍 Consultando SEFAZ...")

    while True:
        iteracao += 1
        print(f"   Lote {iteracao} (NSU: {ult_nsu})...", end=" ", flush=True)

        try:
            resposta_xml = consultar_dfe(ult_nsu)
            novos, novo_nsu, max_nsu, mensagem = extrair_documentos(resposta_xml)

            if not novos:
                print(f"✓ {mensagem}")
                break

            docs_todos.extend(novos)
            print(f"✓ ({len(novos)} docs)")

            # Atualiza NSU
            if novo_nsu:
                ult_nsu = novo_nsu

            # Se chegou no final
            if novo_nsu == max_nsu:
                print("✓ Todos os documentos foram recuperados")
                break

        except Exception as e:
            print(f"\n❌ Erro: {e}")
            break

    print(f"\n📦 Total de documentos encontrados: {len(docs_todos)}")
    return docs_todos


def filtrar_por_periodo(documentos, data_inicio, data_fim):
    """Filtra documentos por período"""
    filtradas = []

    for xml in documentos:
        data_emissao = extrair_data(xml)
        if data_emissao:
            if data_inicio <= data_emissao.date() <= data_fim:
                filtradas.append(xml)

    return filtradas


def salvar_xmls(documentos, pasta_destino="nfes"):
    """Salva XMLs em pasta"""
    if not documentos:
        print("⚠️  Nenhum documento para salvar")
        return

    os.makedirs(pasta_destino, exist_ok=True)

    salvos = 0
    for xml in documentos:
        chave = xml.findtext(".//{*}chNFe")
        if chave:
            caminho = os.path.join(pasta_destino, f"nfe_{chave}.xml")
            with open(caminho, "wb") as f:
                f.write(etree.tostring(xml, encoding="utf-8", pretty_print=True))
            salvos += 1
            print(f"✓ {caminho}")

    print(f"\n✅ {salvos} XMLs salvos em '{pasta_destino}/'")


def obter_periodo_interativo():
    """Menu interativo para seleção de período"""
    print("\n" + "="*60)
    print("  BUSCA DE NOTAS FISCAIS - SEFAZ SC")
    print("="*60)
    print("\nSelecione o período de busca:")
    print("  1 - Hoje")
    print("  2 - Ontem")
    print("  3 - Últimos 7 dias")
    print("  4 - Mês atual")
    print("  5 - Mês passado")
    print("  6 - Ano atual (2025)")
    print("  7 - Período personalizado")

    while True:
        try:
            opcao = input("\nOpção [1-7]: ").strip()
            hoje = datetime.now().date()

            if opcao == "1":
                return hoje, hoje
            elif opcao == "2":
                ontem = hoje - timedelta(days=1)
                return ontem, ontem
            elif opcao == "3":
                inicio = hoje - timedelta(days=7)
                return inicio, hoje
            elif opcao == "4":
                inicio = hoje.replace(day=1)
                return inicio, hoje
            elif opcao == "5":
                primeiro_dia_mes_atual = hoje.replace(day=1)
                ultimo_dia_mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
                primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)
                return primeiro_dia_mes_passado, ultimo_dia_mes_passado
            elif opcao == "6":
                inicio = datetime(2025, 1, 1).date()
                return inicio, hoje
            elif opcao == "7":
                print("\nFormato: AAAA-MM-DD (ex: 2025-10-01)")
                data_ini = input("Data início: ").strip()
                data_fim = input("Data fim: ").strip()
                inicio = datetime.strptime(data_ini, "%Y-%m-%d").date()
                fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
                return inicio, fim
            else:
                print("❌ Opção inválida. Tente novamente.")
        except ValueError as e:
            print(f"❌ Erro: {e}")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelado")
            exit(0)


def main():
    parser = argparse.ArgumentParser(description="Buscar NF-e via SOAP direto")
    parser.add_argument("--data-inicio", help="Data início (AAAA-MM-DD)")
    parser.add_argument("--data-fim", help="Data fim (AAAA-MM-DD)")
    parser.add_argument("--pasta", default="nfes", help="Pasta destino")

    args = parser.parse_args()

    # Define período
    if args.data_inicio and args.data_fim:
        data_inicio = datetime.strptime(args.data_inicio, "%Y-%m-%d").date()
        data_fim = datetime.strptime(args.data_fim, "%Y-%m-%d").date()
    else:
        data_inicio, data_fim = obter_periodo_interativo()

    print(f"\n📅 Período: {data_inicio} até {data_fim}")
    print(f"🏢 CNPJ: {CNPJ}")
    print(f"📁 Destino: {args.pasta}/")
    print()

    # Autenticação
    print("🔐 Autenticando com certificado...")
    try:
        # Testa certificado
        import requests
        session = requests.Session()
        adapter = requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=CERT_PATH,
            pkcs12_password=CERT_PASS
        )
        session.mount("https://", adapter)
        print("✓ Certificado carregado\n")
    except Exception as e:
        print(f"❌ Erro: {e}")
        return

    # Busca documentos
    documentos = buscar_todos_documentos()

    if not documentos:
        print("\n⚠️  Nenhum documento encontrado")
        return

    # Filtra por período
    print(f"\n🔍 Filtrando período {data_inicio} a {data_fim}...")
    filtradas = filtrar_por_periodo(documentos, data_inicio, data_fim)
    print(f"✓ {len(filtradas)} NF-e(s) no período\n")

    if not filtradas:
        print("⚠️  Nenhuma nota no período selecionado")
        return

    # Salva
    print("💾 Salvando XMLs...")
    salvar_xmls(filtradas, args.pasta)


if __name__ == "__main__":
    main()

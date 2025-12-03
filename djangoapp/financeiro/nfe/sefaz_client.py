"""
Cliente para consulta de NF-e na SEFAZ usando SOAP.
Adaptado do script original para uso no Django.
"""
import base64
import gzip
import os
from datetime import datetime
from typing import List, Tuple, Optional
from decimal import Decimal

import requests_pkcs12
from lxml import etree
from django.core.files.base import ContentFile


class SefazClient:
    """Cliente para consulta de documentos fiscais na SEFAZ"""

    # URLs por UF
    URLS_SEFAZ = {
        # Nacional (para a maioria dos estados)
        'nacional': 'https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx',
        # Específicos (se houver)
        '35': 'https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx',  # SP
        '42': 'https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx',  # SC
    }

    def __init__(self, certificado_path: str, certificado_senha: str, cnpj: str, uf_cod: str):
        """
        Inicializa o cliente SEFAZ.

        Args:
            certificado_path: Caminho para o arquivo .pfx
            certificado_senha: Senha do certificado
            cnpj: CNPJ para consulta (14 dígitos, sem formatação)
            uf_cod: Código da UF (2 dígitos)
        """
        self.certificado_path = certificado_path
        self.certificado_senha = certificado_senha
        self.cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
        self.uf_cod = uf_cod
        self.url = self.URLS_SEFAZ.get(uf_cod, self.URLS_SEFAZ['nacional'])

    def _criar_envelope_soap(self, ult_nsu: str = "000000000000000", chave_nfe: str = None) -> str:
        """Cria envelope SOAP para consulta de DFe"""

        # Se for consulta por chave de acesso
        if chave_nfe:
            dist_content = f"""<consChNFe>
            <chNFe>{chave_nfe}</chNFe>
          </consChNFe>"""
        else:
            # Consulta por NSU
            dist_content = f"""<distNSU>
            <ultNSU>{ult_nsu}</ultNSU>
          </distNSU>"""

        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <nfeDadosMsg>
        <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
          <tpAmb>1</tpAmb>
          <cUFAutor>{self.uf_cod}</cUFAutor>
          <CNPJ>{self.cnpj}</CNPJ>
          {dist_content}
        </distDFeInt>
      </nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""

    def consultar_dfe(self, ult_nsu: str = "000000000000000", chave_nfe: str = None) -> etree._Element:
        """
        Consulta documentos fiscais via SOAP.

        Args:
            ult_nsu: Último NSU consultado
            chave_nfe: Chave de acesso da NF-e (para buscar XML completo)

        Returns:
            XML da resposta

        Raises:
            Exception: Em caso de erro na consulta
        """
        envelope = self._criar_envelope_soap(ult_nsu, chave_nfe)

        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8",
        }

        try:
            response = requests_pkcs12.post(
                self.url,
                data=envelope.encode("utf-8"),
                headers=headers,
                pkcs12_filename=self.certificado_path,
                pkcs12_password=self.certificado_senha,
                timeout=60
            )

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")

            return etree.fromstring(response.content)

        except Exception as e:
            raise Exception(f"Erro na consulta SOAP: {e}")

    def buscar_xml_completo(self, chave_acesso: str) -> Optional[etree._Element]:
        """
        Busca o XML completo de uma NF-e pela chave de acesso.

        Args:
            chave_acesso: Chave de 44 dígitos da NF-e

        Returns:
            XML completo da NF-e ou None se não encontrado
        """
        try:
            resposta_xml = self.consultar_dfe(chave_nfe=chave_acesso)
            documentos, _, _, _ = self.extrair_documentos(resposta_xml)

            if documentos:
                return documentos[0]

            return None

        except Exception as e:
            print(f"Erro ao buscar XML completo da chave {chave_acesso}: {e}")
            return None

    def extrair_documentos(self, resposta_xml: etree._Element) -> Tuple[List[etree._Element], str, str, str]:
        """
        Extrai e decodifica documentos do XML de resposta.

        Args:
            resposta_xml: XML da resposta SOAP

        Returns:
            Tupla (documentos, ultNSU, maxNSU, mensagem)

        Raises:
            Exception: Em caso de erro não recuperável
        """
        documentos = []

        # Namespace SOAP
        ns = {
            'soap': 'http://www.w3.org/2003/05/soap-envelope',
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }

        # Busca código de status
        cStat = resposta_xml.findtext('.//nfe:cStat', namespaces=ns)
        xMotivo = resposta_xml.findtext('.//nfe:xMotivo', namespaces=ns)

        # Debug
        print(f"Status SEFAZ: {cStat} - {xMotivo}")

        # Extrai NSUs (mesmo em caso de erro, podem estar presentes)
        ultNSU = resposta_xml.findtext('.//nfe:ultNSU', namespaces=ns)
        maxNSU = resposta_xml.findtext('.//nfe:maxNSU', namespaces=ns)

        if cStat != "138":  # 138 = sucesso
            status_msg = f"Status {cStat}: {xMotivo}" if cStat else "Resposta inválida"

            if cStat == "656":
                # 656 pode ser "nenhum documento" OU "consumo indevido"
                if "Consumo Indevido" in (xMotivo or ""):
                    # Retorna os NSUs para atualizar o certificado
                    print(f"SEFAZ - Consumo Indevido: {status_msg}")
                    return [], ultNSU, maxNSU, status_msg
                else:
                    # Nenhum documento encontrado (normal)
                    print(f"SEFAZ - Sem documentos: {status_msg}")
                    return [], ultNSU, maxNSU, status_msg

            print(f"Erro SEFAZ: {status_msg}")
            raise Exception(status_msg)

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
                # Log do erro, mas continua processando outros documentos
                print(f"⚠️  Erro ao processar documento: {e}")
                continue

        return documentos, ultNSU, maxNSU, xMotivo

    def sincronizar_nsu(self) -> Tuple[str, str, str]:
        """
        Sincroniza o NSU atual com a SEFAZ sem buscar documentos.
        Útil para recuperar o ultNSU após erro 656 ou resetar o NSU.

        Returns:
            Tupla (ultNSU, maxNSU, mensagem)

        Raises:
            Exception: Em caso de erro na consulta
        """
        try:
            # Faz uma consulta com NSU zero para obter os NSUs atuais
            resposta_xml = self.consultar_dfe("000000000000000")
            _, ult_nsu, max_nsu, mensagem = self.extrair_documentos(resposta_xml)

            return ult_nsu or "000000000000000", max_nsu or "000000000000000", mensagem

        except Exception as e:
            # Mesmo em caso de erro, tenta extrair os NSUs da resposta
            print(f"Erro ao sincronizar NSU: {e}")
            raise

    def buscar_todos_documentos(self, nsu_inicial: str = "000000000000000") -> List[etree._Element]:
        """
        Busca todos os documentos disponíveis a partir de um NSU.

        Args:
            nsu_inicial: NSU inicial para busca

        Returns:
            Lista de XMLs dos documentos
        """
        ult_nsu = nsu_inicial
        docs_todos = []
        iteracao = 0
        max_iteracoes = 100  # Limite de segurança

        while iteracao < max_iteracoes:
            iteracao += 1

            try:
                resposta_xml = self.consultar_dfe(ult_nsu)
                novos, novo_nsu, max_nsu, mensagem = self.extrair_documentos(resposta_xml)

                if not novos:
                    break

                docs_todos.extend(novos)

                # Atualiza NSU
                if novo_nsu:
                    ult_nsu = novo_nsu

                # Se chegou no final
                if novo_nsu == max_nsu:
                    break

            except Exception as e:
                print(f"❌ Erro na iteração {iteracao}: {e}")
                break

        return docs_todos

    @staticmethod
    def extrair_data_emissao(xml: etree._Element) -> Optional[datetime]:
        """
        Extrai data de emissão da NF-e.

        Args:
            xml: XML do documento

        Returns:
            Data de emissão ou None
        """
        dhEmi = xml.findtext(".//{*}dhEmi")
        if dhEmi:
            try:
                return datetime.fromisoformat(dhEmi.replace("Z", "+00:00"))
            except:
                try:
                    # Tenta apenas a parte da data
                    return datetime.strptime(dhEmi[:10], "%Y-%m-%d")
                except:
                    pass
        return None

    @staticmethod
    def eh_resumo_nfe(xml: etree._Element) -> bool:
        """
        Verifica se o XML é um resumo (resNFe) ou documento completo.

        Args:
            xml: XML do documento

        Returns:
            True se for resumo, False se for completo
        """
        # Verifica se é resNFe (resumo)
        if xml.tag.endswith('resNFe'):
            return True

        # Verifica se é procNFe ou NFe (completo)
        if xml.tag.endswith('procNFe') or xml.tag.endswith('NFe'):
            return False

        # Se não identificar, assume que é resumo
        return True

    @staticmethod
    def extrair_chave_resumo(xml: etree._Element) -> Optional[str]:
        """
        Extrai a chave de acesso de um resumo de NF-e.

        Args:
            xml: XML do resumo (resNFe)

        Returns:
            Chave de acesso ou None
        """
        return xml.findtext('.//{*}chNFe')

    @staticmethod
    def extrair_metadados_nfe(xml: etree._Element) -> dict:
        """
        Extrai metadados principais da NF-e.

        Args:
            xml: XML do documento

        Returns:
            Dicionário com metadados
        """
        # Namespace NFe
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        # Tenta com namespace e sem namespace (usando {*})
        def buscar_texto(xpath_com_ns, xpath_sem_ns):
            valor = xml.findtext(xpath_com_ns, namespaces=ns)
            if valor is None:
                valor = xml.findtext(xpath_sem_ns)
            return valor

        chave = buscar_texto('.//nfe:chNFe', './/{*}chNFe')
        numero = buscar_texto('.//nfe:nNF', './/{*}nNF')
        serie = buscar_texto('.//nfe:serie', './/{*}serie')
        dhEmi = buscar_texto('.//nfe:dhEmi', './/{*}dhEmi')

        # Emitente
        emit_cnpj = buscar_texto('.//nfe:emit/nfe:CNPJ', './/{*}emit/{*}CNPJ')
        emit_nome = buscar_texto('.//nfe:emit/nfe:xNome', './/{*}emit/{*}xNome')

        # Valores
        valor_total_str = buscar_texto('.//nfe:total/nfe:ICMSTot/nfe:vNF', './/{*}total/{*}ICMSTot/{*}vNF')
        valor_desconto_str = buscar_texto('.//nfe:total/nfe:ICMSTot/nfe:vDesc', './/{*}total/{*}ICMSTot/{*}vDesc')

        # NSU
        nsu = xml.get('NSU', '')

        # Converte valores
        try:
            valor_total = Decimal(valor_total_str) if valor_total_str else Decimal('0.00')
        except:
            valor_total = Decimal('0.00')

        try:
            valor_desconto = Decimal(valor_desconto_str) if valor_desconto_str else Decimal('0.00')
        except:
            valor_desconto = Decimal('0.00')

        valor_liquido = valor_total - valor_desconto

        # Data de emissão
        data_emissao = None
        if dhEmi:
            try:
                data_emissao = datetime.fromisoformat(dhEmi.replace("Z", "+00:00"))
            except:
                try:
                    data_emissao = datetime.strptime(dhEmi[:10], "%Y-%m-%d")
                except:
                    pass

        return {
            'chave_acesso': chave or '',
            'numero': numero or '',
            'serie': serie or '',
            'data_emissao': data_emissao,
            'emitente_cnpj': emit_cnpj or '',
            'emitente_nome': emit_nome or '',
            'valor_total': valor_total,
            'valor_desconto': valor_desconto,
            'valor_liquido': valor_liquido,
            'nsu': nsu,
        }

    @staticmethod
    def xml_to_string(xml: etree._Element) -> bytes:
        """
        Converte XML Element para string formatada.

        Args:
            xml: XML Element

        Returns:
            bytes: XML formatado
        """
        return etree.tostring(xml, encoding='utf-8', pretty_print=True)

    def filtrar_por_periodo(self, documentos: List[etree._Element],
                           data_inicio: datetime, data_fim: datetime) -> List[etree._Element]:
        """
        Filtra documentos por período.

        Args:
            documentos: Lista de XMLs
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Lista filtrada de XMLs
        """
        filtradas = []

        for xml in documentos:
            data_emissao = self.extrair_data_emissao(xml)
            if data_emissao:
                # Converte para date se necessário
                data_check = data_emissao.date() if hasattr(data_emissao, 'date') else data_emissao
                data_ini_check = data_inicio.date() if hasattr(data_inicio, 'date') else data_inicio
                data_fim_check = data_fim.date() if hasattr(data_fim, 'date') else data_fim

                if data_ini_check <= data_check <= data_fim_check:
                    filtradas.append(xml)

        return filtradas

from dataclasses import dataclass
from typing import Callable, Optional, Any
import re
from datetime import datetime

# ================= Utilitários Globais =================
CURRENT_CENTURY = 2000  # poderá ser ajustado dinamicamente pelo validador
VALIDATE_NOSSO_NUMERO = False  # configuração para validar DV do Nosso Número

DATE_RE = re.compile(r'\d{6}')
NUM_RE = re.compile(r'\d+')
AMOUNT_13_2_RE = re.compile(r'\d{13}')

def amount_13_2_optional_digits(v: str):
    v=v.strip()
    if v and v.isdigit():
        return int(v)/100
    return 0.0

# Transforms seguros -----------------------------------------------------------

def parse_date_ddmmaa(v: str) -> datetime:
    d = int(v[0:2]); m = int(v[2:4]); a = int(v[4:6]) + CURRENT_CENTURY
    return datetime(a, m, d)

def parse_date_optional(v: str):
    v = v.strip()
    if not v or v == '000000':
        return None
    return parse_date_ddmmaa(v)

def amount_13_2_safe(v: str):
    if not v.strip():
        return 0.0
    if not v.isdigit():
        raise ValueError('non_digit_characters')
    return int(v) / 100

def set_current_century(century_base: int):
    """Define o século base (ex: 1900 ou 2000) usado nas datas de 2 dígitos."""
    global CURRENT_CENTURY
    if century_base not in (1900, 2000):
        # permitir qualquer valor entre 1800 e 2099 para flexibilidade
        if not (1800 <= century_base <= 2099):
            raise ValueError('século base inválido')
    CURRENT_CENTURY = century_base

def set_validate_nosso_numero(flag: bool):
    """Ativa/desativa validação de DV do Nosso Número Bradesco."""
    global VALIDATE_NOSSO_NUMERO
    VALIDATE_NOSSO_NUMERO = bool(flag)

# ================= Especificação de Campo =================
@dataclass
class FieldSpec:
    name: str
    start: int
    end: int
    description: str
    required: bool = True
    pattern: Optional[re.Pattern] = None
    allowed: Optional[set[str]] = None
    transform: Optional[Callable[[str], Any]] = None
    conditional: Optional[Callable[[str, dict], bool]] = None
    validator: Optional[Callable[[str, dict], Optional[str]]] = None
    severity: str = 'field'  # 'field' | 'business'

    def extract(self, line: str) -> str:
        return line[self.start-1:self.end]

    def validate(self, line: str, context: dict):
        raw = self.extract(line)
        errors = []
        expected_len = self.end - self.start + 1
        if len(raw) != expected_len:
            errors.append({'field': self.name, 'position': f"{self.start:03}-{self.end:03}", 'error': 'invalid_length', 'expected_length': expected_len, 'found_length': len(raw), 'severity': 'fatal'})
            return errors
        # Condicional
        if self.conditional and not self.conditional(raw, context):
            return errors
        if self.required and raw.strip() == '':
            errors.append({'field': self.name, 'position': f"{self.start:03}-{self.end:03}", 'error': 'required_blank', 'severity': self.severity})
            return errors
        if self.allowed and raw not in self.allowed:
            errors.append({'field': self.name, 'position': f"{self.start:03}-{self.end:03}", 'error': 'unexpected_value', 'expected': sorted(self.allowed), 'found': raw, 'severity': self.severity})
        if self.pattern and raw.strip() and not self.pattern.fullmatch(raw):
            errors.append({'field': self.name, 'position': f"{self.start:03}-{self.end:03}", 'error': 'pattern_mismatch', 'pattern': self.pattern.pattern, 'found': raw, 'severity': self.severity})
        # Transform
        if self.transform:
            try:
                context[self.name] = self.transform(raw)
            except Exception as e:
                errors.append({'field': self.name, 'position': f"{self.start:03}-{self.end:03}", 'error': 'transform_error', 'detail': str(e), 'raw': raw, 'severity': self.severity})
        else:
            context[self.name] = raw
        context[f"__raw__{self.name}"] = raw
        if self.validator and raw.strip():
            msg = self.validator(raw, context)
            if msg:
                errors.append({'field': self.name, 'position': f"{self.start:03}-{self.end:03}", 'error': 'business_rule', 'detail': msg, 'found': raw, 'severity': 'business'})
        return errors

# ================= HEADER (Tipo 0) =================
# Layout conforme padrão Bradesco CNAB400 (ajustado para reduzir falsos positivos)
HEADER_FIELDS = [
    FieldSpec('identificacao_registro', 1, 1, 'Identificação do Registro', allowed={'0'}),
    FieldSpec('tipo_operacao', 2, 2, 'Tipo de Operação', allowed={'1'}),
    FieldSpec('literal_remessa', 3, 9, 'Literal REMESSA', allowed={'REMESSA'}),  # aceitar sem espaço final
    FieldSpec('codigo_servico', 10, 11, 'Código do Serviço', pattern=re.compile(r'\d{2}')),
    FieldSpec('literal_servico', 12, 26, 'Literal do Serviço (COBRANCA)', required=True),
    FieldSpec('codigo_empresa', 27, 46, 'Código Empresa (20)'),
    FieldSpec('nome_empresa', 47, 76, 'Nome da Empresa (30)'),
    # Aceita 237 (Bradesco) e 463 (Banco moderno / configuração solicitada)
    FieldSpec('codigo_banco', 77, 79, 'Código Banco', allowed={'237','463'}),
    FieldSpec('nome_banco', 80, 94, 'Nome Banco'),
    FieldSpec('data_gravacao', 95, 100, 'Data Gravação (DDMMAA)', pattern=DATE_RE, transform=parse_date_ddmmaa),
    FieldSpec('filler_1', 101, 108, 'Brancos', required=False),
    FieldSpec('filler_2', 109, 110, 'Brancos', required=False),
    FieldSpec('sequencial_remessa', 111, 117, 'Número Sequencial Remessa', pattern=re.compile(r'\d{7}'), transform=lambda v: int(v)),
    FieldSpec('filler_3', 118, 394, 'Brancos', required=False),
    FieldSpec('sequencial_registro', 395, 400, 'Sequencial do Registro', pattern=re.compile(r'\d{6}'), transform=lambda v: int(v)),
]

# ================= REGISTRO TIPO 1 (Detalhe) =================
# Inserção de fillers para preservar alinhamento; campos chave mantidos
REGISTRO1_FIELDS = [
    FieldSpec('identificacao_registro', 1, 1, 'Identificação', allowed={'1'}),
    FieldSpec('ident_debito_automatico', 2, 20, 'Ident. Débito Automático', required=False),
    FieldSpec('ident_empresa_banco', 21, 37, 'Identificação Empresa'),
    FieldSpec('controle_participante', 38, 62, 'Controle Participante', required=False),
    FieldSpec('codigo_banco_debito', 63, 65, 'Código Banco Débito', required=False, pattern=re.compile(r'\d{3}')),
    FieldSpec('indicador_multa', 66, 66, 'Indicador Multa', allowed={'0', '2', ' '}, required=False),
    FieldSpec('percentual_multa', 67, 70, 'Percentual Multa (4,2)', pattern=re.compile(r'\d{4}'), required=False, transform=lambda v: int(v)/100 if v.strip() else 0.0),
    FieldSpec('nosso_numero', 71, 82, 'Nosso Número', pattern=re.compile(r'\d{12}')),
    FieldSpec('data_segundo_desconto', 83, 88, 'Data 2º Desconto', pattern=DATE_RE, required=False, transform=parse_date_optional),
    FieldSpec('filler_a', 89, 92, 'Brancos', required=False),
    FieldSpec('cond_emissao_boleto', 93, 93, 'Condição Emissão', required=False),
    FieldSpec('cond_registro_debito', 94, 94, 'Condição Débito Automático', required=False),
    FieldSpec('filler_b', 95, 104, 'Brancos', required=False),
    FieldSpec('indicador_rateio', 105, 105, 'Indicador Rateio', required=False),
    FieldSpec('end_aviso_debito', 106, 106, 'Endereço Aviso Débito', required=False),
    FieldSpec('pagamento_parcial', 107, 108, 'Pagamento Parcial', required=False),
    FieldSpec('ocorrencia', 109, 110, 'Ocorrência', required=False),
    FieldSpec('filler_c', 111, 120, 'Brancos', required=False),
    FieldSpec('data_vencimento', 121, 126, 'Data Vencimento', pattern=DATE_RE, transform=parse_date_ddmmaa),
    FieldSpec('valor_titulo', 127, 139, 'Valor Título (13,2)', pattern=AMOUNT_13_2_RE, transform=amount_13_2_safe),
    FieldSpec('codigo_banco_cobrador', 140, 142, 'Banco Cobrador', required=False, pattern=re.compile(r'\d{3}')),
    FieldSpec('agencia_cobradora', 143, 147, 'Agência Cobradora', pattern=re.compile(r'\d{5}')),
    FieldSpec('especie', 148, 149, 'Espécie', pattern=re.compile(r'\d{2}')),
    FieldSpec('aceite', 150, 150, 'Aceite', allowed={'A', 'N', ' '}, required=False),
    FieldSpec('data_emissao', 151, 156, 'Data Emissão', pattern=DATE_RE, transform=parse_date_ddmmaa),
    FieldSpec('instrucao1', 157, 160, 'Instrução 1', pattern=re.compile(r'\d{4}'), required=False),
    FieldSpec('instrucao2', 161, 164, 'Instrução 2', pattern=re.compile(r'\d{4}'), required=False),
    FieldSpec('juros_dia', 165, 177, 'Juros por Dia (13,2)', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('data_desconto', 178, 183, 'Data 1º Desconto', pattern=DATE_RE, required=False, transform=parse_date_optional),
    FieldSpec('valor_desconto', 184, 196, 'Valor Desconto (13,2)', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('filler_d', 197, 213, 'Brancos', required=False),
    FieldSpec('valor_iof', 214, 226, 'Valor IOF (13,2)', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('valor_abatimento', 227, 239, 'Valor Abatimento (13,2)', required=False, transform=amount_13_2_optional_digits),
    FieldSpec('tipo_inscricao_pagador', 220, 220, 'Tipo Inscrição Pagador', required=False),  # posição fora de ordem mantida para compat com versão anterior
    FieldSpec('cpf_cnpj_pagador', 221, 234, 'CPF/CNPJ Pagador', pattern=re.compile(r'\d{14}')),
    FieldSpec('nome_pagador', 235, 274, 'Nome Pagador'),
    FieldSpec('endereco_pagador', 275, 314, 'Endereço Pagador'),
    FieldSpec('cep_pagador', 315, 322, 'CEP Pagador', pattern=re.compile(r'\d{8}'), required=False),
    FieldSpec('sacador_avalista', 323, 362, 'Sacador / Avalista', required=False),
    FieldSpec('filler_e', 363, 394, 'Brancos', required=False),
    FieldSpec('sequencial_registro', 395, 400, 'Sequencial Registro', pattern=re.compile(r'\d{6}'), transform=lambda v: int(v)),
]

# ================= TRAILER (Tipo 9) =================
TRAILER_FIELDS = [
    FieldSpec('identificacao_registro', 1, 1, 'Identificação', allowed={'9'}),
    FieldSpec('total_registros', 2, 7, 'Total Registros', pattern=re.compile(r'\d{6}'), required=False, transform=lambda v: int(v) if v.strip() else 0),
    FieldSpec('total_titulos_cobranca', 8, 13, 'Qtd Títulos', pattern=re.compile(r'\d{6}'), required=False, transform=lambda v: int(v) if v.strip() else 0),
    FieldSpec('valor_total_titulos', 14, 26, 'Valor Total Títulos', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('valor_total_abatimentos', 27, 39, 'Total Abatimentos', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('valor_total_descontos', 40, 52, 'Total Descontos', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('valor_total_juros', 53, 65, 'Total Juros/Mora', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('valor_total_iof', 66, 78, 'Total IOF', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('valor_total_outros', 79, 91, 'Total Outros', pattern=AMOUNT_13_2_RE, required=False, transform=amount_13_2_safe),
    FieldSpec('filler_trailer', 92, 394, 'Brancos', required=False),
    FieldSpec('sequencial_registro', 395, 400, 'Sequencial Registro', pattern=re.compile(r'\d{6}'), transform=lambda v: int(v)),
]

# ================= Tipos adicionais (simplificados) =================
REGISTRO2_FIELDS = [
    FieldSpec('identificacao_registro', 1, 1, 'Identificação', allowed={'2'}),
    FieldSpec('mensagem', 2, 394, 'Mensagem / Instruções', required=False),
    FieldSpec('sequencial_registro', 395, 400, 'Sequencial Registro', pattern=re.compile(r'\d{6}'), transform=lambda v: int(v)),
]

REGISTRO3_FIELDS = [
    FieldSpec('identificacao_registro', 1, 1, 'Identificação', allowed={'3'}),
    FieldSpec('conteudo', 2, 394, 'Conteúdo Registro 3 (placeholder)', required=False),
    FieldSpec('sequencial_registro', 395, 400, 'Sequencial Registro', pattern=re.compile(r'\d{6}'), transform=lambda v: int(v)),
]

REGISTRO6_FIELDS = [
    FieldSpec('identificacao_registro', 1, 1, 'Identificação', allowed={'6'}),
    FieldSpec('conteudo', 2, 394, 'Conteúdo Registro 6 (placeholder)', required=False),
    FieldSpec('sequencial_registro', 395, 400, 'Sequencial Registro', pattern=re.compile(r'\d{6}'), transform=lambda v: int(v)),
]

REGISTRO7_FIELDS = [
    FieldSpec('identificacao_registro', 1, 1, 'Identificação', allowed={'7'}),
    FieldSpec('endereco_complementar', 2, 394, 'Endereço Complementar', required=False),
    FieldSpec('sequencial_registro', 395, 400, 'Sequencial Registro', pattern=re.compile(r'\d{6}'), transform=lambda v: int(v)),
]

# ================= Regras de Negócio =================

def valida_multa(percent_raw: str, ctx: dict):
    ind = ctx.get('indicador_multa', '')
    try:
        perc = float(ctx.get('percentual_multa', 0))
    except Exception:
        perc = 0
    if ind == '2' and perc <= 0:
        return 'percentual_multa deve ser > 0 quando indicador_multa = 2'
    if ind in {'0', ' '} and perc > 0:
        return 'percentual_multa deve ser zeros quando indicador_multa = 0 ou em branco'
    return None

def validar_datas_registro1(ctx: dict):
    errs = []
    dv = ctx.get('data_vencimento')
    de = ctx.get('data_emissao')
    d1 = ctx.get('data_desconto')
    d2 = ctx.get('data_segundo_desconto')
    if dv and de and dv < de:
        errs.append({'error': 'data_vencimento_menor_emissao', 'emissao': de.strftime('%Y-%m-%d'), 'vencimento': dv.strftime('%Y-%m-%d'), 'severity': 'business'})
    for label, dd, code in [('desconto1', d1, 'data_desconto1'), ('desconto2', d2, 'data_desconto2')]:
        if dd:
            if dv and dd > dv:
                errs.append({'error': f'{code}_maior_vencimento', 'severity': 'business'})
            if de and dd < de:
                errs.append({'error': f'{code}_menor_emissao', 'severity': 'business'})
    if d1 and d2 and d2 < d1:
        errs.append({'error': 'desconto2_anterior_desconto1', 'severity': 'business'})
    return errs

def compute_bradesco_nosso_numero_dv(base11: str) -> str:
    """Calcula DV do Nosso Número (modelo Bradesco) para 11 primeiros dígitos.
    Regra usual: pesos 2..7 cíclicos da direita p/ esquerda, soma, mod 11, DV = 11 - resto; se resultado em (10,11) => '0'.
    """
    pesos = [2,3,4,5,6,7]
    soma = 0
    for i, dig in enumerate(reversed(base11)):
        peso = pesos[i % len(pesos)]
        soma += int(dig) * peso
    resto = soma % 11
    dv = 11 - resto
    if dv in (10,11):
        return '0'
    return str(dv)

def validar_nosso_numero(raw: str, ctx: dict):
    if not VALIDATE_NOSSO_NUMERO:
        return None
    # raw já deve ter 12 dígitos: 11 base + DV
    if len(raw) != 12 or not raw.isdigit():
        return 'formato inválido para validação DV'
    base = raw[:11]
    dv = raw[11]
    esperado = compute_bradesco_nosso_numero_dv(base)
    if dv != esperado:
        return f'DV inválido. Esperado {esperado}'
    return None

def validar_contato_registro2(ctx: dict):
    """Detecta telefone incompleto (apenas DDD com 2 dígitos isolado) no registro 2.
    Heurística: sequência de exatamente 2 dígitos entre blocos grandes de espaços (ex: '  11     ')."""
    errs = []
    msg = ctx.get('mensagem', '')
    # procurar padrão de dois dígitos cercado por espaços largos
    if re.search(r'\s{2}\d{2}\s{3,}', msg):
        # extrai o primeiro
        m = re.search(r'(\d{2})', msg)
        if m:
            errs.append({'error': 'telefone_incompleto', 'found': m.group(1), 'severity': 'field'})
    return errs

# Anexa validator de multa
for f in REGISTRO1_FIELDS:
    if f.name == 'percentual_multa':
        f.validator = valida_multa

# Atribui validator ao campo nosso_numero
for f in REGISTRO1_FIELDS:
    if f.name == 'nosso_numero':
        f.validator = validar_nosso_numero

FIELD_MAP = {
    '0': HEADER_FIELDS,
    '1': REGISTRO1_FIELDS,
    '2': REGISTRO2_FIELDS,
    '3': REGISTRO3_FIELDS,
    '6': REGISTRO6_FIELDS,
    '7': REGISTRO7_FIELDS,
    '9': TRAILER_FIELDS,
}

RECORD_LEVEL_VALIDATORS = {
    '1': [validar_datas_registro1],
    '2': [validar_contato_registro2]
}

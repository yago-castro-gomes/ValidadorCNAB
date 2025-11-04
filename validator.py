from typing import List, Dict, Any
from layouts.bradesco_cnab400 import FIELD_MAP, FieldSpec, RECORD_LEVEL_VALIDATORS, set_codigo_banco
from decimal import Decimal

class ValidationResult:
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
    @property
    def valid(self):
        return len(self.errors) == 0

    def add(self, line_num: int, record_type: str, field_error: Dict[str, Any]):
        enriched = {'line': line_num, 'record_type': record_type}
        enriched.update(field_error)
        if 'severity' not in enriched:
            enriched['severity'] = 'field'
        self.errors.append(enriched)

    def add_global(self, error: Dict[str, Any]):
        if 'severity' not in error:
            # classificação simples
            structural = {
                'empty_file', 'missing_header_first_line', 'missing_trailer_last_line', 'no_detail_records_tipo1',
                'non_increasing_sequencial_registro', 'trailer_total_registros_invalid'
            }
            error['severity'] = 'fatal' if error.get('error') in structural else 'business'
        self.errors.append(error)


def validate_line(line: str, line_num: int, result: ValidationResult):
    # Aceitar 400 ou 402 caracteres (alguns arquivos têm \r\n extras)
    line_len = len(line)
    
    # Normalizar linha para 400 caracteres (remover extras no final se necessário)
    if line_len > 400:
        line = line[:400]
    
    # Reportar erro apenas se linha for muito curta ou muito longa (não 400-402)
    if line_len < 400 or line_len > 402:
        result.errors.append({
            'line': line_num,
            'record_type': line[:1],
            'error': 'invalid_line_length',
            'expected_length': 400,
            'found_length': line_len,
            'severity': 'field'
        })
    
    record_type = line[0:1]
    fields: List[FieldSpec] = FIELD_MAP.get(record_type, [])
    context: Dict[str, Any] = {}
    for spec in fields:
        field_errors = spec.validate(line, context)
        for fe in field_errors:
            result.add(line_num, record_type, fe)
    # record-level validators
    validators = RECORD_LEVEL_VALIDATORS.get(record_type, [])
    for fn in validators:
        try:
            errs = fn(context)
            for e in errs:
                e['field'] = e.get('field','__record__')
                result.add(line_num, record_type, e)
        except Exception as ex:
            result.add(line_num, record_type, {'field': '__record__', 'error': 'record_validator_exception', 'detail': str(ex)})


def validate_file(path: str, tolerancia_centavos: int = 0) -> ValidationResult:
    """Valida arquivo CNAB400.

    tolerancia_centavos: diferença máxima (em centavos) permitida entre total declarado e somado.
    """
    result = ValidationResult()
    lines_cache = []
    total_valores = Decimal('0')
    total_abatimento = Decimal('0')
    total_descontos = Decimal('0')
    total_juros = Decimal('0')
    total_iof = Decimal('0')
    total_outros = Decimal('0')
    titulos_count = 0
    trailer_line = None
    tol = Decimal(tolerancia_centavos) / Decimal('100')
    
    with open(path, 'r', encoding='latin1') as f:
        for idx, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip('\n').rstrip('\r')
            lines_cache.append(line)
            
            # Capturar código do banco do header (linha 1, tipo 0, posições 77-79)
            if idx == 1 and line.startswith('0') and len(line) >= 79:
                codigo_banco = line[76:79]  # posições 77-79 (índice 76-78)
                set_codigo_banco(codigo_banco)
            
            validate_line(line, idx, result)
            if len(line) == 400 and line.startswith('1'):
                titulos_count += 1
                valor_raw = line[126:139]
                if valor_raw.isdigit():
                    total_valores += Decimal(valor_raw) / Decimal('100')
                abat_raw = line[226:239]
                if abat_raw.isdigit():
                    total_abatimento += Decimal(abat_raw)/Decimal('100')
                desc_raw = line[183:196]
                if desc_raw.isdigit():
                    total_descontos += Decimal(desc_raw)/Decimal('100')
                juros_raw = line[164:177]
                if juros_raw.isdigit():
                    total_juros += Decimal(juros_raw)/Decimal('100')
                iof_raw = line[213:226]
                if iof_raw.isdigit():
                    total_iof += Decimal(iof_raw)/Decimal('100')
                # outros permanece zero (placeholder)
            if len(line) == 400 and line.startswith('9'):
                trailer_line = (idx, line)
    if not lines_cache:
        result.add_global({'error': 'empty_file'})
        return result
    # Structural checks
    if lines_cache[0][:1] != '0':
        result.add_global({'error': 'missing_header_first_line'})
    if lines_cache[-1][:1] != '9':
        result.add_global({'error': 'missing_trailer_last_line'})
    if titulos_count == 0:
        result.add_global({'error': 'no_detail_records_tipo1'})
    # Sequencial registro check per line end positions 395-400
    last_seq = 0
    for idx, line in enumerate(lines_cache, start=1):
        if len(line) == 400:
            seq = line[394:400]
            if seq.strip().isdigit():
                seq_int = int(seq)
                if seq_int <= last_seq:
                    result.add_global({'error': 'non_increasing_sequencial_registro', 'line': idx, 'found': seq_int, 'previous': last_seq})
                last_seq = seq_int
    # Trailer validations
    if trailer_line:
        t_idx, t = trailer_line
        raw_total_registros = t[1:7]
        if raw_total_registros.strip():
            try:
                total_registros_decl = int(raw_total_registros)
                if total_registros_decl != len(lines_cache):
                    result.add_global({'error': 'trailer_total_registros_mismatch', 'line': t_idx, 'declared': total_registros_decl, 'found': len(lines_cache)})
            except ValueError:
                result.add_global({'error': 'trailer_total_registros_invalid', 'line': t_idx})
        try:
            total_titulos_decl = int(t[7:13])
            if total_titulos_decl and total_titulos_decl != titulos_count:
                result.add_global({'error': 'trailer_total_titulos_mismatch', 'line': t_idx, 'declared': total_titulos_decl, 'found': titulos_count})
        except ValueError:
            pass
        valor_total_decl_raw = t[13:26]
        abat_decl_raw = t[26:39]
        desc_decl_raw = t[39:52]
        juros_decl_raw = t[52:65]
        iof_decl_raw = t[65:78]
        outros_decl_raw = t[78:91]
        # função auxiliar para comparar com tolerância
        def compara(nome_err, raw, soma):
            if raw.strip().isdigit():
                val = Decimal(raw)/Decimal('100')
                if val and abs(val - soma) > tol:
                    result.add_global({'error': nome_err, 'declared': float(val), 'summed': float(soma), 'diff': float(abs(val - soma)), 'tolerance': float(tol)})
        compara('trailer_total_abatimento_mismatch', abat_decl_raw, total_abatimento)
        compara('trailer_total_descontos_mismatch', desc_decl_raw, total_descontos)
        compara('trailer_total_juros_mismatch', juros_decl_raw, total_juros)
        compara('trailer_total_iof_mismatch', iof_decl_raw, total_iof)
        compara('trailer_total_outros_mismatch', outros_decl_raw, total_outros)
        # Valor total títulos (principal)
        if valor_total_decl_raw.strip().isdigit():
            val_total = Decimal(valor_total_decl_raw)/Decimal('100')
            if val_total and abs(val_total - total_valores) > tol:
                result.add_global({'error': 'trailer_valor_total_titulos_mismatch', 'declared': float(val_total), 'summed': float(total_valores), 'diff': float(abs(val_total - total_valores)), 'tolerance': float(tol)})
    # Removido bloco de validações de datas duplicadas (já cobertas por RECORD_LEVEL_VALIDATORS)
    return result

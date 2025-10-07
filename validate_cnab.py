import argparse, json, sys
from validator import validate_file
from layouts.bradesco_cnab400 import set_current_century, set_validate_nosso_numero

def main():
    parser = argparse.ArgumentParser(description='Validador CNAB400 Bradesco (MVP)')
    parser.add_argument('arquivo')
    parser.add_argument('--formato', choices=['json','texto'], default='texto')
    parser.add_argument('--seculo-base', type=int, default=2000, help='Século base para datas de 2 dígitos (ex: 1900 ou 2000).')
    parser.add_argument('--tolerancia-centavos', type=int, default=0, help='Tolerância nos comparativos de totais (em centavos).')
    parser.add_argument('--min-severidade', choices=['fatal','field','business'], default='field', help='Filtra erros exibidos >= severidade informada.')
    parser.add_argument('--validar-nosso-numero', action='store_true', help='Ativa validação do DV do Nosso Número Bradesco.')
    args = parser.parse_args()
    try:
        set_current_century(args.seculo_base)
        set_validate_nosso_numero(args.validar_nosso_numero)
    except Exception as e:
        print(f'Erro: {e}', file=sys.stderr)
        sys.exit(2)
    res = validate_file(args.arquivo, tolerancia_centavos=args.tolerancia_centavos)
    severidade_ordem = {'fatal':0,'field':1,'business':2}
    corte = severidade_ordem[args.min_severidade]
    filtered = [e for e in res.errors if severidade_ordem.get(e.get('severity','field'),1) <= corte]
    if args.formato == 'json':
        print(json.dumps({'valid': len(filtered)==0, 'errors': filtered}, ensure_ascii=False, indent=2))
    else:
        if len(filtered)==0:
            print('Arquivo válido (sem erros dentro do filtro).')
        else:
            print(f'Foram encontrados {len(filtered)} erros (após filtro de severidade):')
            for e in filtered:
                print(f"Linha {e.get('line')} (Tipo {e.get('record_type')}): Campo {e.get('field')} - {e.get('error')} - {e.get('position','')} - encontrado={e.get('found','')} esperado={e.get('expected','')}")

if __name__ == '__main__':
    main()

# app.py
from flask import Flask, render_template, request, session, redirect, url_for
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

class CalculadoraTributaria:
    def __init__(self, dados):
        self.faturamento_vendas = float(dados.get('faturamento_vendas', 0))
        self.faturamento_servicos = float(dados.get('faturamento_servicos', 0))
        self.rbt12 = float(dados.get('rbt12', 0))
        self.folha_salarial = float(dados.get('folha_salarial', 0))
        self.prolabore = float(dados.get('prolabore', 0))
        self.base_inss_salario = float(dados.get('base_inss_salario', 0))
        self.base_inss_prolabore = float(dados.get('base_inss_prolabore', 0))
        self.fgts_anual = float(dados.get('fgts_anual', 0))
        self.cmv = float(dados.get('cmv', 0))
        self.despesas_operacionais = float(dados.get('despesas_operacionais', 0))
        self.aliquota_iss = float(dados.get('aliquota_iss', 0))
        self.aliquota_icms = float(dados.get('aliquota_icms', 0))
        self.pis_cofins_creditos = float(dados.get('pis_cofins_creditos', 0))
        self.servico_intelectual = dados.get('servico_intelectual') == 'on'
        self.faturamento_total = self.faturamento_vendas + self.faturamento_servicos
        
    def calcular_simples_nacional(self):
        """Calcula tributos pelo Simples Nacional"""
        rbt12 = self.rbt12
        faturamento = self.faturamento_total
        
        # Determina a faixa e alíquota (Anexo I - Comércio como exemplo)
        if rbt12 <= 180000:
            aliquota = 4.0
            parcela_deduzir = 0
        elif rbt12 <= 360000:
            aliquota = 7.3
            parcela_deduzir = 5940
        elif rbt12 <= 720000:
            aliquota = 9.5
            parcela_deduzir = 13860
        elif rbt12 <= 1800000:
            aliquota = 10.7
            parcela_deduzir = 22500
        elif rbt12 <= 3600000:
            aliquota = 14.3
            parcela_deduzir = 87300
        else:
            aliquota = 19.0
            parcela_deduzir = 378000
        
        # Calcula o imposto do mês
        imposto_mensal = (faturamento * aliquota / 100) - (parcela_deduzir / 12)
        
        # INSS sobre pró-labore
        inss_prolabore = self.prolabore * 0.11
        
        imposto_total = imposto_mensal + inss_prolabore
        carga_tributaria = (imposto_total / faturamento * 100) if faturamento > 0 else 0
        
        return {
            'regime': 'Simples Nacional',
            'imposto_total': imposto_total,
            'imposto_mensal': imposto_mensal,
            'inss_prolabore': inss_prolabore,
            'aliquota_efetiva': aliquota,
            'carga_tributaria': carga_tributaria,
            'faixa_rbt12': rbt12
        }
    
    def calcular_lucro_presumido(self):
        """Calcula tributos pelo Lucro Presumido"""
        faturamento = self.faturamento_total
        
        # PIS e COFINS
        pis = faturamento * 0.0065
        cofins = faturamento * 0.03
        
        # Base de cálculo presumida (32% para serviços)
        base_presumida = faturamento * 0.32
        
        # IRPJ e CSLL
        irpj = base_presumida * 0.15
        csll = base_presumida * 0.09
        
        # INSS Patronal
        inss_patronal = (self.folha_salarial + self.prolabore) * 0.20
        inss_prolabore = self.prolabore * 0.11
        
        # ISS (se aplicável)
        iss = self.faturamento_servicos * (self.aliquota_iss / 100)
        
        imposto_total = pis + cofins + irpj + csll + inss_patronal + inss_prolabore + iss
        carga_tributaria = (imposto_total / faturamento * 100) if faturamento > 0 else 0
        
        return {
            'regime': 'Lucro Presumido',
            'imposto_total': imposto_total,
            'pis': pis,
            'cofins': cofins,
            'irpj': irpj,
            'csll': csll,
            'inss': inss_patronal + inss_prolabore,
            'iss': iss,
            'carga_tributaria': carga_tributaria
        }
    
    def calcular_lucro_real(self):
        """Calcula tributos pelo Lucro Real"""
        faturamento = self.faturamento_total
        
        # PIS e COFINS não cumulativo
        creditos_pis_cofins = self.pis_cofins_creditos
        pis = (faturamento * 0.0165) - (creditos_pis_cofins * 0.0165)
        cofins = (faturamento * 0.076) - (creditos_pis_cofins * 0.076)
        
        # Lucro Real
        lucro_real = faturamento - self.cmv - self.despesas_operacionais - self.folha_salarial - self.prolabore
        
        # IRPJ e CSLL sobre lucro real
        irpj = lucro_real * 0.15 if lucro_real > 0 else 0
        csll = lucro_real * 0.09 if lucro_real > 0 else 0
        
        # INSS
        inss_patronal = (self.folha_salarial + self.prolabore) * 0.20
        inss_prolabore = self.prolabore * 0.11
        
        # ISS
        iss = self.faturamento_servicos * (self.aliquota_iss / 100)
        
        imposto_total = pis + cofins + irpj + csll + inss_patronal + inss_prolabore + iss
        carga_tributaria = (imposto_total / faturamento * 100) if faturamento > 0 else 0
        
        return {
            'regime': 'Lucro Real',
            'imposto_total': imposto_total,
            'pis': pis,
            'cofins': cofins,
            'irpj': irpj,
            'csll': csll,
            'inss': inss_patronal + inss_prolabore,
            'iss': iss,
            'lucro_real': lucro_real,
            'carga_tributaria': carga_tributaria
        }

def calcular_projecao_rbt12(rbt12_atual, projecao1, projecao2, projecao3):
    """Calcula a projeção do RBT12 para os próximos meses"""
    if not projecao1 and not projecao2 and not projecao3:
        return None
    
    faturamento_medio = rbt12_atual / 12
    
    # Mês 1
    rbt12_mes1 = rbt12_atual - faturamento_medio + (projecao1 or 0)
    
    # Mês 2
    rbt12_mes2 = rbt12_mes1 - faturamento_medio + (projecao2 or 0)
    
    # Mês 3
    rbt12_mes3 = rbt12_mes2 - faturamento_medio + (projecao3 or 0)
    
    return {
        'mes1': rbt12_mes1,
        'mes2': rbt12_mes2,
        'mes3': rbt12_mes3
    }

@app.route('/')
def index():
    return render_template('simulacao.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    modo_calculo = request.form.get('modo_calculo', 'simple')
    
    # Armazena dados do formulário na sessão
    dados = {
        'faturamento_vendas': request.form.get('faturamento_vendas', 0),
        'faturamento_servicos': request.form.get('faturamento_servicos', 0),
        'folha_salarial': request.form.get('folha_salarial', 0),
        'prolabore': request.form.get('prolabore', 0),
        'base_inss_salario': request.form.get('base_inss_salario', 0),
        'base_inss_prolabore': request.form.get('base_inss_prolabore', 0),
        'fgts_anual': request.form.get('fgts_anual', 0),
        'cmv': request.form.get('cmv', 0),
        'despesas_operacionais': request.form.get('despesas_operacionais', 0),
        'aliquota_iss': request.form.get('aliquota_iss', 0),
        'aliquota_icms': request.form.get('aliquota_icms', 0),
        'pis_cofins_creditos': request.form.get('pis_cofins_creditos', 0),
        'servico_intelectual': request.form.get('servico_intelectual'),
        'projecao1': request.form.get('projecao1', ''),
        'projecao2': request.form.get('projecao2', ''),
        'projecao3': request.form.get('projecao3', ''),
        'modo_calculo': modo_calculo
    }
    
    # Se for modo detalhado, calcular RBT12 a partir dos 12 meses
    if modo_calculo == 'detailed':
        rbt12 = 0
        valores_mensais = []
        impostos_mensais = []
        
        for i in range(1, 13):
            valor = request.form.get(f'mes_{i}', 0)
            valor_float = float(valor) if valor else 0
            valores_mensais.append(valor_float)
            rbt12 += valor_float
        
        dados['rbt12'] = rbt12
        dados['valores_mensais'] = valores_mensais
        
        # Calcula o imposto mês a mês para o Simples Nacional
        calc_temp = CalculadoraTributaria(dados)
        for valor_mes in valores_mensais:
            # Cria dados temporários para cada mês
            dados_temp = dados.copy()
            dados_temp['faturamento_vendas'] = valor_mes
            dados_temp['faturamento_servicos'] = 0
            
            calc_mes = CalculadoraTributaria(dados_temp)
            resultado_mes = calc_mes.calcular_simples_nacional()
            impostos_mensais.append(resultado_mes['imposto_mensal'])
        
        dados['impostos_mensais'] = impostos_mensais
    else:
        dados['rbt12'] = request.form.get('rbt12', 0)
    
    session['dados_simulacao'] = dados
    
    # Regimes selecionados
    regimes_selecionados = request.form.getlist('regimes')
    
    # Calcula
    calc = CalculadoraTributaria(dados)
    resultados = {}
    
    if 'simples' in regimes_selecionados:
        resultados['simples_nacional'] = calc.calcular_simples_nacional()
    
    if 'presumido' in regimes_selecionados:
        resultados['lucro_presumido'] = calc.calcular_lucro_presumido()
    
    if 'real' in regimes_selecionados:
        resultados['lucro_real'] = calc.calcular_lucro_real()
    
    # Calcula projeção se houver dados
    projecao1 = float(dados['projecao1']) if dados['projecao1'] else 0
    projecao2 = float(dados['projecao2']) if dados['projecao2'] else 0
    projecao3 = float(dados['projecao3']) if dados['projecao3'] else 0
    
    projecao = None
    if projecao1 or projecao2 or projecao3:
        projecao = calcular_projecao_rbt12(
            float(dados['rbt12']),
            projecao1,
            projecao2,
            projecao3
        )
    
    # Determina o regime recomendado (menor carga tributária)
    recomendado = None
    if resultados:
        recomendado = min(resultados.keys(), key=lambda r: resultados[r]['carga_tributaria'])
    
    session['resultados'] = resultados
    session['projecao'] = projecao
    session['recomendado'] = recomendado
    
    return redirect(url_for('resultados'))

@app.route('/resultados')
def resultados():
    resultados = session.get('resultados', {})
    dados = session.get('dados_simulacao', {})
    projecao = session.get('projecao')
    recomendado = session.get('recomendado')
    
    return render_template('resultado.html', 
                         resultados=resultados,
                         dados=dados,
                         projecao=projecao,
                         recomendado=recomendado)

@app.template_filter('currency')
def currency_filter(value):
    """Formata valor como moeda brasileira"""
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

if __name__ == '__main__':
    app.run(debug=True)





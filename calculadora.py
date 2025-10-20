# -*- coding: utf-8 -*-
"""
Calculadora Tributária Avançada com Modo Simples e Detalhado
Inclui projeções, análise de mudança de faixa e otimizações tributárias
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json


class CalculadoraTributariaAvancada:
    """
    Calcula impostos com duas modalidades:
    - Modo Simples: RBT12 direto
    - Modo Detalhado: Histórico mensal + projeções
    """
    
    # Tabelas do Simples Nacional
    ANEXO_I_COMERCIO = [
        (180000, 0.04, 0),
        (360000, 0.073, 5940),
        (720000, 0.095, 13860),
        (1800000, 0.107, 22500),
        (3600000, 0.143, 87300),
        (4800000, 0.19, 378000),
    ]
    
    ANEXO_III_SERVICOS = [
        (180000, 0.06, 0),
        (360000, 0.112, 9360),
        (720000, 0.135, 17640),
        (1800000, 0.16, 35640),
        (3600000, 0.21, 125640),
        (4800000, 0.33, 648000),
    ]
    
    ANEXO_V_SERVICOS_INTELECTUAIS = [
        (180000, 0.155, 0),
        (360000, 0.18, 4500),
        (720000, 0.195, 11250),
        (1800000, 0.205, 17100),
        (3600000, 0.23, 62100),
        (4800000, 0.305, 540000),
    ]
    
    def __init__(self, **kwargs):
        """Inicializa calculadora com modo simples ou detalhado"""
        
        # Modo de cálculo
        self.modo_calculo = kwargs.get('modo_calculo', 'simples')
        
        # Dados básicos
        self.faturamento_vendas = kwargs.get('faturamento_vendas', 0)
        self.faturamento_servicos = kwargs.get('faturamento_servicos', 0)
        self.faturamento_total = self.faturamento_vendas + self.faturamento_servicos
        self.servicoIntelectual = kwargs.get('servicoIntelectual', False)
        
        # Tratamento do RBT12 baseado no modo
        if self.modo_calculo == 'detalhado':
            # Modo detalhado: calcular RBT12 dos meses informados
            self.meses_anteriores = []
            for i in range(12):
                mes_valor = kwargs.get(f'mes_{i}', 0)
                self.meses_anteriores.append(float(mes_valor) if mes_valor else 0)
            
            self.rbt12 = sum(self.meses_anteriores)
            
            # Projeções para análise futura
            self.projecoes = []
            for i in range(1, 7):  # Até 6 meses de projeção
                proj = kwargs.get(f'projecao_{i}', 0)
                if proj:
                    self.projecoes.append(float(proj))
                else:
                    # Se não informado, usar média dos últimos 3 meses
                    if len(self.meses_anteriores) >= 3:
                        media_3_meses = sum(self.meses_anteriores[-3:]) / 3
                        self.projecoes.append(media_3_meses)
                    else:
                        self.projecoes.append(0)
        else:
            # Modo simples: usar RBT12 direto
            self.rbt12 = kwargs.get('rbt12_direto', kwargs.get('rbt12', self.faturamento_total))
            self.meses_anteriores = []
            self.projecoes = []
        
        # Dados de folha e encargos
        self.folha_salarial = kwargs.get('folha_salarial', 0)
        self.prolabore = kwargs.get('prolabore', 0)
        self.base_inss_salario = kwargs.get('base_inss_salario', 0)
        self.base_inss_prolabore = kwargs.get('base_inss_prolabore', 0)
        self.fgts_anual = kwargs.get('fgts_anual', 0)
        
        # Custos e despesas
        self.cmv = kwargs.get('cmv', 0)
        self.despesas_operacionais = kwargs.get('despesas_operacionais', 0)
        
        # Tributos estaduais/municipais (para implementação futura)
        self.aliquota_icms = kwargs.get('aliquota_icms', 0.17)  # 17% padrão SP
        self.aliquota_iss = kwargs.get('aliquota_iss', 0.05)   # 5% padrão
    
    def _get_faixa_simples(self, rbt12: float, tabela: List) -> Tuple[float, float, int]:
        """Retorna alíquota, dedução e número da faixa"""
        for i, (limite, aliquota, deducao) in enumerate(tabela):
            if rbt12 <= limite:
                return aliquota, deducao, i + 1
        return tabela[-1][1], tabela[-1][2], len(tabela)
    
    def _calcular_rbt12_mes(self, mes_futuro: int) -> float:
        """Calcula RBT12 para um mês futuro específico"""
        if self.modo_calculo != 'detalhado':
            return self.rbt12
        
        if mes_futuro == 0:
            return self.rbt12
        
        # Remove meses antigos e adiciona projeções
        meses_calc = self.meses_anteriores[mes_futuro:] + self.projecoes[:mes_futuro]
        return sum(meses_calc)
    
    def calcular_simples_nacional(self, rbt12_custom: Optional[float] = None) -> Dict:
        """Calcula Simples Nacional com RBT12 customizado ou padrão"""
        rbt12_usado = rbt12_custom or self.rbt12
        
        if self.faturamento_total == 0:
            return {
                'imposto_das': 0,
                'carga_tributaria_total': 0,
                'lucro_liquido': 0,
                'aliquota_efetiva': 0,
                'faixa': 1
            }
        
        # Cálculo para vendas
        imposto_vendas = 0
        faixa_vendas = 1
        if self.faturamento_vendas > 0:
            aliq_nom, deducao, faixa_vendas = self._get_faixa_simples(rbt12_usado, self.ANEXO_I_COMERCIO)
            aliq_efetiva = ((rbt12_usado * aliq_nom) - deducao) / rbt12_usado if rbt12_usado > 0 else 0
            imposto_vendas = self.faturamento_vendas * aliq_efetiva
        
        # Cálculo para serviços
        imposto_servicos = 0
        faixa_servicos = 1
        if self.faturamento_servicos > 0:
            # Verificar Fator R para serviços intelectuais
            tabela_servicos = self.ANEXO_V_SERVICOS_INTELECTUAIS if self.servicoIntelectual else self.ANEXO_III_SERVICOS
            
            if self.servicoIntelectual:
                massa_salarial = self.folha_salarial + self.prolabore
                fator_r = massa_salarial / self.faturamento_total if self.faturamento_total > 0 else 0
                
                if fator_r >= 0.28:
                    tabela_servicos = self.ANEXO_III_SERVICOS
            
            aliq_nom_serv, deducao_serv, faixa_servicos = self._get_faixa_simples(rbt12_usado, tabela_servicos)
            aliq_efetiva_serv = ((rbt12_usado * aliq_nom_serv) - deducao_serv) / rbt12_usado if rbt12_usado > 0 else 0
            imposto_servicos = self.faturamento_servicos * aliq_efetiva_serv
        
        # Total de impostos
        imposto_das_total = imposto_vendas + imposto_servicos
        encargos_totais = self.fgts_anual
        custo_total = imposto_das_total + encargos_totais
        
        # Determinar faixa predominante
        faixa_atual = max(faixa_vendas, faixa_servicos)
        
        return {
            'imposto_das': imposto_das_total,
            'carga_tributaria_total': custo_total,
            'faixa': faixa_atual,
            'rbt12_usado': rbt12_usado
        }
    
    def calcular_lucro_presumido(self) -> Dict:
        """Calcula Lucro Presumido"""
        # Bases de presunção
        base_irpj = (self.faturamento_vendas * 0.08) + (self.faturamento_servicos * 0.32)
        base_csll = (self.faturamento_vendas * 0.12) + (self.faturamento_servicos * 0.32)
        
        # Impostos federais
        irpj = base_irpj * 0.15
        adicional_irpj = max(0, (base_irpj - 240000)) * 0.10  # 240k = 20k * 12 meses
        csll = base_csll * 0.09
        pis = self.faturamento_total * 0.0065
        cofins = self.faturamento_total * 0.03
        
        impostos_federais = irpj + adicional_irpj + csll + pis + cofins
        
        # Encargos sobre folha
        inss_patronal = (self.base_inss_salario * 0.258) + (self.base_inss_prolabore * 0.20)
        encargos_totais = inss_patronal + self.fgts_anual
        
        custo_total = impostos_federais + encargos_totais
        
        return {
            'irpj': irpj,
            'adicional_irpj': adicional_irpj,
            'csll': csll,
            'pis': pis,
            'cofins': cofins,
            'inss_patronal': inss_patronal,
            'carga_tributaria_total': custo_total
        }
    
    def calcular_lucro_real(self) -> Dict:
        """Calcula Lucro Real"""
        # Lucro contábil
        lucro_contabil = (self.faturamento_total - self.cmv - self.despesas_operacionais - 
                         self.folha_salarial - self.prolabore - self.fgts_anual)
        
        # Encargos sobre folha
        inss_patronal = (self.base_inss_salario * 0.258) + (self.base_inss_prolabore * 0.20)
        encargos_totais = inss_patronal + self.fgts_anual
        
        if lucro_contabil <= 0:
            # Empresa com prejuízo - apenas encargos
            return {
                'irpj': 0,
                'adicional_irpj': 0,
                'csll': 0,
                'pis': 0,
                'cofins': 0,
                'prejuizo_fiscal': abs(lucro_contabil),
                'carga_tributaria_total': encargos_totais
            }
        
        # Impostos sobre o lucro
        irpj = lucro_contabil * 0.15
        adicional_irpj = max(0, (lucro_contabil - 240000)) * 0.10
        csll = lucro_contabil * 0.09
        
        # PIS/COFINS não cumulativo
        pis_debito = self.faturamento_total * 0.0165
        cofins_debito = self.faturamento_total * 0.076
        pis_credito = self.cmv * 0.0165
        cofins_credito = self.cmv * 0.076
        pis_a_pagar = max(0, pis_debito - pis_credito)
        cofins_a_pagar = max(0, cofins_debito - cofins_credito)
        
        impostos_federais = irpj + adicional_irpj + csll + pis_a_pagar + cofins_a_pagar
        custo_total = impostos_federais + encargos_totais
        
        return {
            'irpj': irpj,
            'adicional_irpj': adicional_irpj,
            'csll': csll,
            'pis': pis_a_pagar,
            'cofins': cofins_a_pagar,
            'lucro_contabil': lucro_contabil,
            'carga_tributaria_total': custo_total
        }
    
    def analisar_mudanca_faixa(self) -> List[Dict]:
        """Analisa mudanças de faixa nos próximos meses (modo detalhado)"""
        if self.modo_calculo != 'detalhado':
            return []
        
        alertas = []
        faixas_nome = ['1ª Faixa', '2ª Faixa', '3ª Faixa', '4ª Faixa', '5ª Faixa', '6ª Faixa']
        
        for mes in range(min(6, len(self.projecoes))):
            rbt12_atual = self._calcular_rbt12_mes(mes)
            rbt12_proximo = self._calcular_rbt12_mes(mes + 1)
            
            resultado_atual = self.calcular_simples_nacional(rbt12_atual)
            resultado_proximo = self.calcular_simples_nacional(rbt12_proximo)
            
            faixa_atual = resultado_atual['faixa']
            faixa_proxima = resultado_proximo['faixa']
            
            if faixa_atual != faixa_proxima:
                impacto_mensal = (resultado_proximo['carga_tributaria_total'] - 
                                 resultado_atual['carga_tributaria_total']) / 12
                
                alertas.append({
                    'mes': mes + 1,
                    'de_faixa': faixas_nome[faixa_atual - 1],
                    'para_faixa': faixas_nome[faixa_proxima - 1],
                    'rbt12_atual': rbt12_atual,
                    'rbt12_novo': rbt12_proximo,
                    'impacto_mensal': impacto_mensal,
                    'alerta': 'crítico' if abs(impacto_mensal) > 5000 else 'moderado',
                    'subindo': faixa_proxima > faixa_atual
                })
        
        return alertas
    
    def gerar_projecao_completa(self, meses: int = 6) -> List[Dict]:
        """Gera projeção completa para os próximos meses"""
        if self.modo_calculo != 'detalhado':
            return []
        
        projecoes = []
        
        for mes in range(meses):
            rbt12_mes = self._calcular_rbt12_mes(mes)
            
            # Calcular para cada regime
            resultado_sn = self.calcular_simples_nacional(rbt12_mes)
            resultado_lp = self.calcular_lucro_presumido()
            resultado_lr = self.calcular_lucro_real()
            
            projecoes.append({
                'mes': mes,
                'rbt12': rbt12_mes,
                'simples_nacional': resultado_sn['carga_tributaria_total'],
                'lucro_presumido': resultado_lp['carga_tributaria_total'],
                'lucro_real': resultado_lr['carga_tributaria_total'],
                'faixa_sn': resultado_sn['faixa']
            })
        
        return projecoes
    
    def sugerir_otimizacoes(self) -> List[Dict]:
        """Sugere otimizações tributárias baseadas na análise"""
        sugestoes = []
        
        # Análise de mudança de faixa
        mudancas = self.analisar_mudanca_faixa()
        for mudanca in mudancas:
            if mudanca['subindo'] and mudanca['alerta'] == 'crítico':
                diferenca_rbt = mudanca['rbt12_novo'] - mudanca['rbt12_atual']
                sugestoes.append({
                    'tipo': 'mudanca_faixa',
                    'prioridade': 'alta',
                    'titulo': f"Mudança de faixa em {mudanca['mes']} mês(es)",
                    'descricao': f"Você mudará da {mudanca['de_faixa']} para a {mudanca['para_faixa']}",
                    'impacto': f"Aumento de {mudanca['impacto_mensal']:.2f} por mês em impostos",
                    'sugestao': f"Considere diferir {diferenca_rbt:.2f} em vendas para o mês seguinte"
                })
        
        # Análise de Fator R
        if self.servicoIntelectual and self.faturamento_servicos > 0:
            massa_salarial = self.folha_salarial + self.prolabore
            fator_r = massa_salarial / self.faturamento_total if self.faturamento_total > 0 else 0
            
            if fator_r < 0.28:
                aumento_necessario = (0.28 * self.faturamento_total) - massa_salarial
                sugestoes.append({
                    'tipo': 'fator_r',
                    'prioridade': 'media',
                    'titulo': 'Otimização do Fator R',
                    'descricao': f'Seu Fator R atual é {fator_r:.2%}',
                    'impacto': 'Você está no Anexo V (alíquotas maiores)',
                    'sugestao': f'Aumente a massa salarial em {aumento_necessario:.2f} para migrar ao Anexo III'
                })
        
        # Comparação de regimes
        resultado_sn = self.calcular_simples_nacional()
        resultado_lp = self.calcular_lucro_presumido()
        resultado_lr = self.calcular_lucro_real()
        
        regimes = {
            'Simples Nacional': resultado_sn['carga_tributaria_total'],
            'Lucro Presumido': resultado_lp['carga_tributaria_total'],
            'Lucro Real': resultado_lr['carga_tributaria_total']
        }
        
        melhor_regime = min(regimes, key=regimes.get)
        economia_potencial = max(regimes.values()) - min(regimes.values())
        
        if economia_potencial > 10000:
            sugestoes.append({
                'tipo': 'regime_tributario',
                'prioridade': 'alta',
                'titulo': 'Oportunidade de economia com mudança de regime',
                'descricao': f'O {melhor_regime} é o mais vantajoso',
                'impacto': f'Economia potencial de até {economia_potencial:.2f} por ano',
                'sugestao': 'Considere mudar de regime no próximo ano fiscal'
            })
        
        return sugestoes
    
    def calcular_todos_regimes(self) -> Dict:
        """Calcula todos os regimes e adiciona informações extras"""
        resultados = {
            'simples_nacional': self.calcular_simples_nacional(),
            'lucro_presumido': self.calcular_lucro_presumido(),
            'lucro_real': self.calcular_lucro_real()
        }
        
        # Calcular lucro líquido e alíquota efetiva
        for regime, valores in resultados.items():
            custos_operacionais = (self.cmv + self.despesas_operacionais + 
                                  self.folha_salarial + self.prolabore + self.fgts_anual)
            carga_total = valores['carga_tributaria_total']
            
            valores['lucro_liquido'] = self.faturamento_total - custos_operacionais - carga_total
            valores['aliquota_efetiva'] = (carga_total / self.faturamento_total * 100 
                                          if self.faturamento_total > 0 else 0)
        
        # Adicionar análises extras se modo detalhado
        if self.modo_calculo == 'detalhado':
            resultados['mudancas_faixa'] = self.analisar_mudanca_faixa()
            resultados['projecoes'] = self.gerar_projecao_completa()
            resultados['sugestoes'] = self.sugerir_otimizacoes()
        
        return resultados
    
    def exportar_relatorio(self) -> Dict:
        """Exporta relatório completo em formato JSON"""
        relatorio = {
            'data_geracao': datetime.now().isoformat(),
            'modo_calculo': self.modo_calculo,
            'dados_entrada': {
                'faturamento_vendas': self.faturamento_vendas,
                'faturamento_servicos': self.faturamento_servicos,
                'rbt12': self.rbt12,
                'folha_salarial': self.folha_salarial,
                'prolabore': self.prolabore,
                'cmv': self.cmv,
                'despesas_operacionais': self.despesas_operacionais
            },
            'resultados': self.calcular_todos_regimes()
        }
        
        return relatorio
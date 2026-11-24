"""Classificação por competência, sem imputação histórica."""
import pandas as pd
import streamlit as st

REGIMES = ['Simples Nacional', 'Lucro Presumido', 'Lucro Real', 'Outros', 'Sem classificação']

def normalizar_regime(valor):
    if pd.isna(valor) or not str(valor).strip():
        return 'Sem classificação'
    texto = ' '.join(str(valor).split()).casefold()
    return next((r for r in REGIMES if r.casefold() == texto), 'Sem classificação')

def consolidar_regime(valores):
    conhecidos = set(map(normalizar_regime, valores)) - {'Sem classificação'}
    return next(iter(conhecidos)) if len(conhecidos) == 1 else 'Sem classificação'

def selecionar_regimes(chave):
    return st.multiselect('Regime tributário', REGIMES, default=REGIMES, key=chave,
                          help='Regime da competência selecionada. O histórico dos clientes selecionados é preservado.')

def filtrar_historico(df, competencia, regimes):
    if set(regimes) == set(REGIMES):
        return df
    atual = df[df['competencia'] == competencia]
    codigos = atual.loc[atual['regime_tributario'].map(normalizar_regime).isin(regimes), 'codigo_cliente']
    return df[df['codigo_cliente'].isin(codigos)].copy()

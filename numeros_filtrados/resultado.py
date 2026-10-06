#%%
import os
import pandas as pd

todas_as_tabelas = []

for arquivo in sorted(os.listdir('.')):
    if arquivo.endswith(".txt") and arquivo != "resultado_leitura.txt":
        
        aux = pd.read_csv(arquivo, sep=' ', header=None)
        aux.columns = ['Classe', 'Centro_X', 'Centro_Y', 'Largura', 'Altura']
        
        todas_as_tabelas.append(aux)

df_completo = pd.concat(todas_as_tabelas, ignore_index=True)
df_completo

df_completo.to_csv("resultado_filtrado.csv", index=False)

# %%

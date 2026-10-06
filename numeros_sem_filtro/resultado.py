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

df_completo.to_csv("resultado_sem_filtro.csv", index=False)
# %%

df_completo['revisado'] = [0, 0, 0, 6, 4, 2, 0, 0, 0, 2, 4, 9, 0, 9, 0, 6, 0, 8, 10, 10, 0, 1, 6, 0, 8, 10, 10, 0, 0, 6, 1, 7, 8, 7, 9, 9, 9, 5, 0, 1, 2, 4, 5, 5, 3, 1, 0, 6, 3, 1, 7, 2, 10, 10, 99, 99, 99]
# %%
df_completo
# %%

import sys
from app.core.database import engine, SessionLocal, Base
from app.models.usuario import Usuario
from app.models.apartamento import Apartamento
from app.models.leitura import Leitura
from app.core.security import gerar_hash_senha

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def inicializar_banco_sqlite():
    """
    Cria automaticamente as tabelas no arquivo SQLite (hidroreader.db)
    e cadastra os usuários e apartamentos iniciais se o banco for novo.
    """
    # Cria todas as tabelas (se não existirem)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Usuários Padrão
        qtd_usuarios = db.query(Usuario).count()
        if qtd_usuarios == 0:
            usuarios_iniciais = [
                Usuario(
                    usuario="admin",
                    senha_hash=gerar_hash_senha("admin"),
                    nome="Administrador do Sistema",
                    cargo="Gestor de Medições",
                    ativo=True
                ),
                Usuario(
                    usuario="operador",
                    senha_hash=gerar_hash_senha("123456"),
                    nome="Operador de Campo",
                    cargo="Técnico de Leitura",
                    ativo=True
                )
            ]
            db.add_all(usuarios_iniciais)
            db.commit()
            print("[SQLite] Usuários padrão criados (admin/admin, operador/123456).")

        # 2. Apartamentos Padrão (Ex: 101, 102, 103, 104, 201, 202, 203...)
        qtd_aptos = db.query(Apartamento).count()
        if qtd_aptos == 0:
            aptos_iniciais = []
            for andar in [1, 2, 3, 4]:
                for num in [1, 2, 3, 4]:
                    numero_apto = f"{andar}0{num}"
                    aptos_iniciais.append(
                        Apartamento(
                            numero=numero_apto,
                            bloco="Bloco A",
                            morador=f"Morador Apto {numero_apto}",
                            ativo=True
                        )
                    )
            db.add_all(aptos_iniciais)
            db.commit()
            print(f"[SQLite] {len(aptos_iniciais)} Apartamentos padrão cadastrados com sucesso!")

        print("[SQLite] Banco de dados hidroreader.db pronto e operacional.")
    except Exception as e:
        print(f"[SQLite] Erro ao inicializar banco: {e}")
        db.rollback()
    finally:
        db.close()

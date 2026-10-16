from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
import io
import csv
from banco.conexao import get_db
from banco.modelos import Usuario, Apartamento, Leitura
from seguranca.autenticacao import obter_usuario_logado

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

@router.get("/resumo", summary="Resumo do dashboard para a tela inicial")
async def obter_resumo_dashboard(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """
    Retorna estatísticas consolidadas para a tela inicial estilo Nubank:
    - Total de apartamentos cadastrados
    - Total de leituras realizadas
    - Consumo total acumulado (m³)
    - Lista das últimas leituras registradas
    """
    total_aptos = db.query(Apartamento).filter(Apartamento.ativo == True).count()
    total_leituras = db.query(Leitura).count()

    # Cálculo estimado do volume total acumulado
    leituras = db.query(Leitura).order_by(Leitura.criado_em.desc()).limit(15).all()

    ultimas = []
    volume_total = 0.0

    for l in leituras:
        # Tenta extrair os m³ dos dígitos pretos ou leitura
        valor_str = l.leitura_yolo or "0"
        try:
            m3_val = float(valor_str[:4]) if len(valor_str) >= 4 else float(valor_str)
            volume_total += m3_val
        except Exception:
            pass

        ultimas.append({
            "id": l.id,
            "apartamento": l.apartamento_numero or "---",
            "leitura": l.leitura_yolo,
            "operador": l.usuario_nome or "Operador",
            "confianca": f"{l.confianca_media:.0f}%",
            "data": l.criado_em.strftime("%d/%m/%Y %H:%M") if l.criado_em else "---",
            "observacoes": l.observacoes or "Normal"
        })

    return {
        "operador_nome": usuario.nome,
        "operador_cargo": usuario.cargo,
        "total_apartamentos": total_aptos,
        "total_leituras": total_leituras,
        "volume_acumulado_m3": f"{volume_total:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "ultimas_leituras": ultimas
    }

@router.get("/exportar-csv", summary="Exportar relatório de leituras em planilha CSV")
async def exportar_leituras_csv(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obter_usuario_logado)
):
    """Gera e faz download de uma planilha CSV com todo o histórico de leituras do condomínio."""
    leituras = db.query(Leitura).order_by(Leitura.criado_em.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["ID", "Apartamento", "Leitura Completa (m³)", "Confiança IA", "Operador", "Observações", "Data/Hora"])

    for l in leituras:
        writer.writerow([
            l.id,
            l.apartamento_numero or "",
            l.leitura_yolo or "",
            f"{l.confianca_media:.1f}%",
            l.usuario_nome or "",
            l.observacoes or "",
            l.criado_em.strftime("%d/%m/%Y %H:%M:%S") if l.criado_em else ""
        ])

    csv_data = output.getvalue().encode('utf-8-sig') # utf-8-sig para abrir com acentuação correta no Excel brasileiro
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=relatorio_leituras_hidrometro.csv"}
    )


"""
Analitik ve raporlama sorguları.
PostgreSQL ve SQLite uyumludur.
"""
from datetime import datetime, timedelta
from database.db_manager import fetch_all, fetch_one, _USE_PG


def _month_trunc(col: str) -> str:
    """Aya göre gruplama ifadesi — DB'ye göre seç."""
    if _USE_PG:
        return f"TO_CHAR({col}, 'YYYY-MM')"
    return f"strftime('%Y-%m', {col})"


def revenue_last_6_months() -> list[dict]:
    """Son 6 ay aylık gelir ve randevu sayısı."""
    q = f"""
        SELECT {_month_trunc('appointment_at')} AS month,
               COUNT(*)                          AS total,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
               COALESCE(SUM(CASE WHEN status='completed' THEN price ELSE 0 END), 0) AS revenue
        FROM appointments
        WHERE appointment_at >= CURRENT_TIMESTAMP - INTERVAL '6 months'
        GROUP BY 1
        ORDER BY 1
    """ if _USE_PG else f"""
        SELECT {_month_trunc('appointment_at')} AS month,
               COUNT(*)                          AS total,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
               COALESCE(SUM(CASE WHEN status='completed' THEN price ELSE 0 END), 0) AS revenue
        FROM appointments
        WHERE appointment_at >= datetime('now', '-6 months')
        GROUP BY 1
        ORDER BY 1
    """
    return fetch_all(q)


def revenue_summary() -> dict:
    """Bu ay, geçen ay, bu yıl toplam gelir."""
    if _USE_PG:
        q = """
            SELECT
              COALESCE(SUM(CASE WHEN DATE_TRUNC('month', appointment_at) = DATE_TRUNC('month', CURRENT_DATE)
                           AND status='completed' THEN price ELSE 0 END), 0) AS this_month,
              COALESCE(SUM(CASE WHEN DATE_TRUNC('month', appointment_at) = DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
                           AND status='completed' THEN price ELSE 0 END), 0) AS last_month,
              COALESCE(SUM(CASE WHEN EXTRACT(YEAR FROM appointment_at) = EXTRACT(YEAR FROM CURRENT_DATE)
                           AND status='completed' THEN price ELSE 0 END), 0) AS this_year,
              COUNT(CASE WHEN DATE_TRUNC('month', appointment_at) = DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS appt_this_month
            FROM appointments
        """
    else:
        q = """
            SELECT
              COALESCE(SUM(CASE WHEN strftime('%Y-%m', appointment_at) = strftime('%Y-%m', 'now')
                           AND status='completed' THEN price ELSE 0 END), 0) AS this_month,
              COALESCE(SUM(CASE WHEN strftime('%Y-%m', appointment_at) = strftime('%Y-%m', date('now', '-1 month'))
                           AND status='completed' THEN price ELSE 0 END), 0) AS last_month,
              COALESCE(SUM(CASE WHEN strftime('%Y', appointment_at) = strftime('%Y', 'now')
                           AND status='completed' THEN price ELSE 0 END), 0) AS this_year,
              COUNT(CASE WHEN strftime('%Y-%m', appointment_at) = strftime('%Y-%m', 'now') THEN 1 END) AS appt_this_month
            FROM appointments
        """
    row = fetch_one(q)
    return dict(row) if row else {}


def staff_performance() -> list[dict]:
    """Personel başına randevu sayısı, tamamlanma oranı ve gelir."""
    q = """
        SELECT st.id,
               st.first_name || ' ' || st.last_name AS name,
               st.color,
               COUNT(a.id)                           AS total,
               SUM(CASE WHEN a.status='completed' THEN 1 ELSE 0 END) AS completed,
               SUM(CASE WHEN a.status='cancelled' OR a.status='no_show' THEN 1 ELSE 0 END) AS cancelled,
               COALESCE(SUM(CASE WHEN a.status='completed' THEN a.price ELSE 0 END), 0) AS revenue
        FROM staff st
        LEFT JOIN appointments a ON a.staff_id = st.id
        WHERE st.active = 1
        GROUP BY st.id, st.first_name, st.last_name, st.color
        ORDER BY revenue DESC, total DESC
    """
    return fetch_all(q)


def service_stats() -> list[dict]:
    """Hizmet başına randevu sayısı ve gelir."""
    q = """
        SELECT sv.id,
               sv.name,
               sv.price          AS unit_price,
               COUNT(a.id)       AS total,
               SUM(CASE WHEN a.status='completed' THEN 1 ELSE 0 END) AS completed,
               COALESCE(SUM(CASE WHEN a.status='completed' THEN a.price ELSE 0 END), 0) AS revenue
        FROM services sv
        LEFT JOIN appointments a ON a.service_id = sv.id
        WHERE sv.active = 1
        GROUP BY sv.id, sv.name, sv.price
        ORDER BY total DESC
    """
    return fetch_all(q)


def appointment_status_breakdown() -> dict:
    """Tüm randevuların durum dağılımı."""
    q = """
        SELECT status, COUNT(*) AS cnt
        FROM appointments
        GROUP BY status
    """
    rows = fetch_all(q)
    return {r["status"]: r["cnt"] for r in rows}

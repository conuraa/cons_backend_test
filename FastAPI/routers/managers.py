"""
API endpoints для работы с менеджерами и их загрузкой.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.security import verify_front_secret, verify_api_token
from ..services.manager_selector import ManagerSelector
from ..models import Consultation

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_front_secret)])


@router.get("/load")
async def get_managers_load(
    db: AsyncSession = Depends(get_db),
    current_time: Optional[datetime] = Query(None, description="Текущее время (по умолчанию now())"),
) -> List[dict]:
    """
    Получить загрузку всех менеджеров.
    
    Returns:
        Список менеджеров с информацией о загрузке:
        - manager_key: cl_ref_key менеджера
        - manager_id: account_id менеджера
        - chatwoot_user_id: ID в Chatwoot
        - name: Имя менеджера
        - queue_count: Количество консультаций в очереди
        - limit: Лимит менеджера
        - load_percent: Процент загрузки (0-100)
        - available_slots: Свободные слоты
        - start_hour: Время начала работы
        - end_hour: Время окончания работы
    """
    manager_selector = ManagerSelector(db)
    
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    try:
        managers_load = await manager_selector.get_all_managers_load(current_time=current_time)
        return managers_load
    except Exception as e:
        logger.error(f"Failed to get managers load: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get managers load: {str(e)}")


@router.get("/{manager_key}/load")
async def get_manager_load(
    manager_key: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Получить загрузку конкретного менеджера.
    
    Args:
        manager_key: cl_ref_key менеджера
    
    Returns:
        Информация о загрузке менеджера
    """
    manager_selector = ManagerSelector(db)
    
    try:
        load_info = await manager_selector.get_manager_current_load(manager_key)
        return load_info
    except Exception as e:
        logger.error(f"Failed to get manager load: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get manager load: {str(e)}")


@router.get("/{manager_key}/wait-time")
async def get_manager_wait_time(
    manager_key: str,
    db: AsyncSession = Depends(get_db),
    average_duration_minutes: int = Query(60, description="Средняя длительность консультации в минутах"),
) -> dict:
    """
    Рассчитать примерное время ожидания для менеджера.
    
    Args:
        manager_key: cl_ref_key менеджера
        average_duration_minutes: Средняя длительность консультации в минутах
    
    Returns:
        Информация о времени ожидания:
        - queue_position: Позиция в очереди
        - estimated_wait_minutes: Примерное время ожидания в минутах
        - estimated_wait_hours: Примерное время ожидания в часах
    """
    manager_selector = ManagerSelector(db)
    
    try:
        wait_info = await manager_selector.calculate_wait_time(
            manager_key=manager_key,
            average_consultation_duration_minutes=average_duration_minutes,
        )
        return wait_info
    except Exception as e:
        logger.error(f"Failed to calculate wait time: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate wait time: {str(e)}")


@router.get("/available")
async def get_available_managers(
    db: AsyncSession = Depends(get_db),
    po_section_key: Optional[str] = Query(None, description="Ключ раздела ПО"),
    po_type_key: Optional[str] = Query(None, description="Ключ типа ПО"),
    category_key: Optional[str] = Query(None, description="Ключ категории вопроса"),
    current_time: Optional[datetime] = Query(None, description="Текущее время"),
) -> List[dict]:
    """
    Получить список доступных менеджеров.
    
    Args:
        po_section_key: Ключ раздела ПО
        po_type_key: Ключ типа ПО
        category_key: Ключ категории вопроса
        current_time: Текущее время
    
    Returns:
        Список доступных менеджеров с информацией о загрузке
    """
    manager_selector = ManagerSelector(db)
    
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    try:
        # Для эндпоинта /available показываем всех менеджеров с лимитами
        # без фильтрации по времени работы (чтобы видеть всех менеджеров)
        managers = await manager_selector.get_available_managers(
            current_time=current_time,
            po_section_key=po_section_key,
            po_type_key=po_type_key,
            category_key=category_key,
            filter_by_working_hours=False,  # Показываем всех менеджеров, независимо от времени работы
        )
        
        # Добавляем информацию о загрузке для каждого менеджера
        result = []
        for manager in managers:
            if not manager.cl_ref_key:
                continue
            
            load_info = await manager_selector.get_manager_current_load(manager.cl_ref_key)
            
            # Получаем среднее время решения за 2 дня
            avg_info = await manager_selector.get_manager_avg_resolution(manager.cl_ref_key, days=30)
            avg_minutes = avg_info["avg_resolution_minutes"]
            
            # Рассчитываем примерное время ожидания
            queue_count = load_info["queue_count"]
            if avg_minutes and queue_count > 0:
                estimated_wait = round(avg_minutes * queue_count)
                # Форматируем в человекочитаемый вид
                if estimated_wait < 60:
                    wait_text = f"~{estimated_wait} мин"
                else:
                    hours = estimated_wait / 60
                    if hours < 2:
                        wait_text = f"~{round(hours, 1)} час"
                    else:
                        wait_text = f"~{round(hours, 1)} часа"
            else:
                estimated_wait = None
                wait_text = None
            
            result.append({
                "manager_key": manager.cl_ref_key,
                "manager_id": str(manager.account_id),
                "chatwoot_user_id": manager.chatwoot_user_id,
                "name": manager.description or manager.user_id or "Unknown",
                "queue_count": queue_count,
                "limit": load_info["limit"],
                "load_percent": load_info["load_percent"],
                "available_slots": load_info["available_slots"],
                "avg_resolution_minutes": avg_minutes,
                "estimated_wait_minutes": estimated_wait,
                "estimated_wait_text": wait_text,
            })
        
        return result
    except Exception as e:
        logger.error(f"Failed to get available managers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get available managers: {str(e)}")


@router.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(verify_api_token)])
async def managers_dashboard(
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """
    HTML страница с очередью менеджеров для Chatwoot Dashboard App.
    
    Авторизация через query параметр: ?api_token=YOUR_TOKEN
    """
    manager_selector = ManagerSelector(db)
    current_time = datetime.now(timezone.utc)
    
    try:
        managers = await manager_selector.get_available_managers(
            current_time=current_time,
            filter_by_working_hours=False,
        )
        
        # Собираем данные менеджеров
        managers_data = []
        for manager in managers:
            if not manager.cl_ref_key:
                continue
            
            load_info = await manager_selector.get_manager_current_load(manager.cl_ref_key)
            avg_info = await manager_selector.get_manager_avg_resolution(manager.cl_ref_key, days=30)
            avg_minutes = avg_info["avg_resolution_minutes"]
            
            queue_count = load_info["queue_count"]
            if avg_minutes and queue_count > 0:
                estimated_wait = round(avg_minutes * queue_count)
                if estimated_wait < 60:
                    wait_text = f"~{estimated_wait} мин"
                else:
                    hours = estimated_wait / 60
                    wait_text = f"~{round(hours, 1)} ч"
            else:
                wait_text = "-"
            
            managers_data.append({
                "name": manager.description or manager.user_id or "Unknown",
                "queue_count": queue_count,
                "limit": load_info["limit"],
                "load_percent": load_info["load_percent"],
                "avg_minutes": round(avg_minutes) if avg_minutes else "-",
                "wait_text": wait_text,
            })
        
        # Сортируем по загрузке
        managers_data.sort(key=lambda x: x["load_percent"], reverse=True)
        
        # Генерируем HTML
        rows_html = ""
        for m in managers_data:
            # Цвет в зависимости от загрузки
            if m["load_percent"] >= 80:
                color = "#ffcccc"  # красный
            elif m["load_percent"] >= 50:
                color = "#ffffcc"  # жёлтый
            else:
                color = "#ccffcc"  # зелёный
            
            rows_html += f"""
            <tr style="background-color: {color};">
                <td>{m["name"]}</td>
                <td style="text-align: center;">{m["queue_count"]}/{m["limit"]}</td>
                <td style="text-align: center;">{m["load_percent"]}%</td>
                <td style="text-align: center;">{m["avg_minutes"]}</td>
                <td style="text-align: center;">{m["wait_text"]}</td>
            </tr>"""
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Очередь консультантов</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 16px;
            background: #fff;
        }}
        h1 {{
            font-size: 18px;
            margin: 0 0 16px 0;
            color: #333;
        }}
        input {{
            width: 100%;
            padding: 8px 12px;
            margin-bottom: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{
            padding: 8px 12px;
            border: 1px solid #e0e0e0;
            text-align: left;
        }}
        th {{
            background: #f5f5f5;
            font-weight: 600;
        }}
        tr:hover {{
            opacity: 0.9;
        }}
        .refresh {{
            float: right;
            font-size: 12px;
            color: #666;
            cursor: pointer;
        }}
        .refresh:hover {{
            color: #333;
        }}
    </style>
</head>
<body>
    <h1>
        Очередь консультантов
        <span class="refresh" onclick="location.reload()">Обновить</span>
    </h1>
    <input type="text" id="search" placeholder="Поиск по имени..." onkeyup="filterTable()">
    <table id="managersTable">
        <thead>
            <tr>
                <th>Имя</th>
                <th style="text-align: center;">Очередь</th>
                <th style="text-align: center;">Загрузка</th>
                <th style="text-align: center;">Ср.время</th>
                <th style="text-align: center;">Ожидание</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <script>
        function filterTable() {{
            var input = document.getElementById("search");
            var filter = input.value.toLowerCase();
            var table = document.getElementById("managersTable");
            var tr = table.getElementsByTagName("tr");
            for (var i = 1; i < tr.length; i++) {{
                var td = tr[i].getElementsByTagName("td")[0];
                if (td) {{
                    var txtValue = td.textContent || td.innerText;
                    if (txtValue.toLowerCase().indexOf(filter) > -1) {{
                        tr[i].style.display = "";
                    }} else {{
                        tr[i].style.display = "none";
                    }}
                }}
            }}
        }}
        // Автообновление каждые 30 секунд
        setTimeout(function(){{ location.reload(); }}, 30000);
    </script>
</body>
</html>"""
        
        return HTMLResponse(content=html)
    
    except Exception as e:
        logger.error(f"Failed to generate dashboard: {e}", exc_info=True)
        return HTMLResponse(content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", status_code=500)


@router.get("/consultations/{cons_id}/queue-info")
async def get_consultation_queue_info(
    cons_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Получить информацию об очереди для конкретной консультации.
    
    Args:
        cons_id: ID консультации
    
    Returns:
        Информация об очереди:
        - queue_position: Позиция в очереди
        - estimated_wait_minutes: Примерное время ожидания в минутах
        - estimated_wait_hours: Примерное время ожидания в часах
        - manager_key: Ключ менеджера
    """
    from sqlalchemy import select
    
    # Получаем консультацию
    result = await db.execute(
        select(Consultation).where(Consultation.cons_id == cons_id)
    )
    consultation = result.scalar_one_or_none()
    
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    
    if not consultation.manager:
        return {
            "queue_position": None,
            "estimated_wait_minutes": None,
            "estimated_wait_hours": None,
            "manager_key": None,
        }
    
    manager_selector = ManagerSelector(db)
    
    try:
        # Передаем cons_id для расчета позиции именно этой консультации в очереди
        wait_info = await manager_selector.calculate_wait_time(
            consultation.manager,
            cons_id=cons_id  # Передаем ID консультации для получения её реальной позиции
        )
        wait_info["manager_key"] = consultation.manager
        return wait_info
    except Exception as e:
        logger.error(f"Failed to get queue info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get queue info: {str(e)}")


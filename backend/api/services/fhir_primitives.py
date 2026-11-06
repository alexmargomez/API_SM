"""
Primitivas de dominio y vocabularios controlados de la Resolución 1888 / HL7 FHIR Colombia (IHCE).
Extraído de fhir_inspector.py para separar diccionarios normativos y extractores puros de CodeableConcept
del orquestador de módulos clínicos.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional


PERIOD_UNIT_MAP = {
    's': 'segundos',
    'min': 'minutos',
    'h': 'horas',
    'd': 'días',
    'wk': 'semanas',
    'mo': 'meses',
    'a': 'años',
}

GENDER_MAP = {
    'male': 'Masculino / Hombre',
    'female': 'Femenino / Mujer',
    'other': 'Otro / Intersexual',
    'unknown': 'No especificado',
}

ENCOUNTER_STATUS_MAP = {
    'planned': 'Planeado',
    'arrived': 'En sala de espera',
    'triaged': 'Con triaje realizado',
    'in-progress': 'En curso',
    'onleave': 'En pausa',
    'finished': 'Finalizado',
    'cancelled': 'Cancelado',
}

CLINICAL_STATUS_MAP = {
    'active': 'Activo',
    'recurrence': 'Recurrente',
    'relapse': 'Recaída',
    'inactive': 'Inactivo',
    'remission': 'En remisión',
    'resolved': 'Resuelto',
}

VERIFICATION_STATUS_MAP = {
    'unconfirmed': 'No confirmado',
    'provisional': 'Provisional',
    'differential': 'Diferencial',
    'confirmed': 'Confirmado',
    'refuted': 'Refutado / Descartado',
    'entered-in-error': 'Ingresado por error',
}

FAMILY_HISTORY_STATUS_MAP = {
    'partial': 'Parcial',
    'completed': 'Completado',
    'entered-in-error': 'Ingresado por error',
    'health-unknown': 'Salud desconocida',
}

MED_STATEMENT_STATUS_MAP = {
    'active': 'Activo',
    'completed': 'Completado',
    'entered-in-error': 'Ingresado por error',
    'intended': 'Previsto',
    'stopped': 'Suspendido',
    'on-hold': 'En pausa',
    'unknown': 'Desconocido',
    'not-taken': 'No tomado',
}

ALLERGY_CATEGORY_MAP = {
    'food': '02 - Alimento',
    'medication': '01 - Medicamento',
    'environment': '03 - Sustancia del ambiente',
    'biologic': '04 - Biológico',
}

RISK_STATUS_MAP = {
    'registered': 'Registrado',
    'preliminary': 'Preliminar',
    'final': 'Final',
    'amended': 'Modificado',
    'corrected': 'Corregido',
    'cancelled': 'Cancelado',
    'entered-in-error': 'Ingresado por error',
    'unknown': 'Desconocido',
}

ZONA_MAP = {
    '01': '01 - Urbana',
    '02': '02 - Rural',
    'U': 'Urbana',
    'R': 'Rural',
}


def _safe_str(val: Any) -> str:
    if val is None:
        return ''
    return str(val).strip()


def _extract_coding_info(codeable: Any) -> Dict[str, str]:
    """Extrae código, display, texto y system desde un CodeableConcept o Coding,
    priorizando los CodeSystem colombianos de Minsalud / IHCE Res. 1888 sobre HL7 v2-0203."""
    if not isinstance(codeable, dict):
        return {'code': '', 'display': '', 'system': '', 'text': ''}

    if 'code' in codeable or 'display' in codeable:
        return {
            'code': _safe_str(codeable.get('code')),
            'display': _safe_str(codeable.get('display')),
            'system': _safe_str(codeable.get('system')),
            'text': _safe_str(codeable.get('text') or codeable.get('display') or codeable.get('code')),
        }

    codings = [c for c in (codeable.get('coding') or []) if isinstance(c, dict)]
    text = _safe_str(codeable.get('text'))
    if codings:
        selected = codings[0]
        if len(codings) > 1:
            for c in codings:
                sys_low = _safe_str(c.get('system')).lower()
                if any(k in sys_low for k in ('minsalud.gov.co', 'colombian', 'co.fhir.guide', 'sispro')):
                    selected = c
                    break
            else:
                for c in codings:
                    sys_low = _safe_str(c.get('system')).lower()
                    if 'v2-0203' not in sys_low and c.get('code'):
                        selected = c
                        break

        code = _safe_str(selected.get('code'))
        display = _safe_str(selected.get('display'))
        system = _safe_str(selected.get('system'))
        label = display or text or code
        return {
            'code': code,
            'display': display,
            'system': system,
            'text': f"{code} - {label}" if code and label and code not in label else (label or code),
        }

    return {'code': '', 'display': text, 'system': '', 'text': text}


def _extract_all_codings(codeable: Any) -> List[Dict[str, str]]:
    """Devuelve todas las codificaciones presentes en un CodeableConcept."""
    if not isinstance(codeable, dict):
        return []
    codings = codeable.get('coding') or []
    out = []
    if isinstance(codings, list):
        for c in codings:
            if isinstance(c, dict):
                out.append({
                    'code': _safe_str(c.get('code')),
                    'display': _safe_str(c.get('display')) or _safe_str(codeable.get('text')),
                    'system': _safe_str(c.get('system')),
                })
    return out


def _find_extension(extensions: Any, url_keyword: str) -> Optional[Dict[str, Any]]:
    if not isinstance(extensions, list):
        return None
    kw = url_keyword.lower()
    for ext in extensions:
        if isinstance(ext, dict) and kw in _safe_str(ext.get('url')).lower():
            return ext
    return None


def _extract_extension_value(ext: Optional[Dict[str, Any]]) -> str:
    if not isinstance(ext, dict):
        return ''
    if 'valueString' in ext:
        return _safe_str(ext.get('valueString'))
    if 'valueCode' in ext:
        return _safe_str(ext.get('valueCode'))
    if 'valueBoolean' in ext:
        return 'Sí' if ext.get('valueBoolean') else 'No'
    if 'valueDate' in ext:
        return _safe_str(ext.get('valueDate'))
    if 'valueDateTime' in ext:
        return _safe_str(ext.get('valueDateTime'))
    if 'valueCoding' in ext:
        info = _extract_coding_info(ext.get('valueCoding'))
        return info['text']
    if 'valueCodeableConcept' in ext:
        info = _extract_coding_info(ext.get('valueCodeableConcept'))
        return info['text']
    if 'valueReference' in ext and isinstance(ext['valueReference'], dict):
        return _safe_str(ext['valueReference'].get('display') or ext['valueReference'].get('reference'))
    if isinstance(ext.get('extension'), list):
        sub_vals = [_extract_extension_value(sub) for sub in ext['extension'] if isinstance(sub, dict)]
        sub_vals = [v for v in sub_vals if v]
        if sub_vals:
            return ' | '.join(sub_vals)
    return ''


def _calculate_age(birth_date_str: str) -> str:
    if not birth_date_str:
        return ''
    try:
        clean = birth_date_str.split('T')[0]
        bdate = datetime.strptime(clean, '%Y-%m-%d').date()
        today = date.today()
        years = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
        if years < 0:
            return ''
        return f"{years} años"
    except Exception:
        return ''

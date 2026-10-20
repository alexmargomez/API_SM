import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from ..models import Cie10, Cups, Eps


# Mapas de traducción de códigos frecuentes en Resolución 1888 / HL7 FHIR Colombia
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
    'unconfirmed': 'Impresión diagnóstica (No confirmado)',
    'provisional': 'Impresión diagnóstica (Provisional)',
    'differential': 'Diagnóstico diferencial',
    'confirmed': 'Confirmado',
    'refuted': 'Descartado / Refutado',
    'entered-in-error': 'Ingresado por error',
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

    # Si es directamente un Coding
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
            # 1. Priorizar CodeSystem oficial de Minsalud / IHCE Colombia
            for c in codings:
                sys_low = _safe_str(c.get('system')).lower()
                if any(k in sys_low for k in ('minsalud.gov.co', 'colombian', 'co.fhir.guide', 'sispro')):
                    selected = c
                    break
            else:
                # 2. Si el primero es el genérico HL7 v2-0203 (PN, TAX, PRN), preferir otro más específico
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


class FhirBundleInspectorService:
    """
    Traductor e Inspector de Bundles FHIR (Resolución 1888 / IHCE Colombia).
    Convierte un JSON FHIR técnico en módulos clínicos/administrativos en español claro
    y valida automáticamente códigos CIE-10, CUPS y EPS contra la base de datos de API_SM.
    """

    @classmethod
    def inspect_payload(cls, raw_input: Any) -> Dict[str, Any]:
        # 1. Parsear entrada JSON
        if isinstance(raw_input, str):
            raw_text = raw_input.strip()
            if not raw_text:
                raise ValueError('Por favor pega un JSON de Bundle FHIR o sube un archivo .json.')
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f'El contenido no es un JSON válido (Error en línea {exc.lineno}, columna {exc.colno}: {exc.msg}).'
                )
        elif isinstance(raw_input, dict):
            parsed = raw_input
        else:
            raise ValueError('Formato de entrada no soportado. Se esperaba un objeto o texto JSON.')

        # 2. Detectar si viene envuelto en otra clave (ej. {"rda": {...}}, {"bundle": {...}}, {"data": {...}})
        wrapper_info = None
        bundle = parsed
        if isinstance(parsed, dict) and parsed.get('resourceType') != 'Bundle':
            for candidate_key in ('rda', 'bundle', 'fhirBundle', 'data', 'payload'):
                if isinstance(parsed.get(candidate_key), dict) and parsed[candidate_key].get('resourceType') == 'Bundle':
                    bundle = parsed[candidate_key]
                    wrapper_info = f"Se detectó un contenedor externo ('{candidate_key}') y se extrajo el Bundle FHIR automáticamente."
                    break
            else:
                # Si pegaron un único recurso suelto (ej. Patient o MedicationRequest), lo envolvemos
                if parsed.get('resourceType'):
                    bundle = {
                        'resourceType': 'Bundle',
                        'type': 'collection',
                        'entry': [{'resource': parsed}],
                    }
                    wrapper_info = f"Se detectó un recurso individual ({parsed.get('resourceType')}) y se analizó directamente."
                else:
                    raise ValueError(
                        'El JSON no contiene la propiedad "resourceType": "Bundle" ni corresponde a una estructura FHIR válida.'
                    )

        entries = bundle.get('entry') or []
        if not isinstance(entries, list):
            raise ValueError('La propiedad "entry" del Bundle FHIR debe ser una lista de recursos.')

        # 3. Indexar todos los recursos y recolectar códigos para validar en lote contra la BD
        resources_by_type: Dict[str, List[Dict[str, Any]]] = {}
        resource_index: Dict[str, Dict[str, Any]] = {}
        structural_warnings: List[str] = []

        cie10_codes_to_check = set()
        cups_codes_to_check = set()
        eps_codes_to_check = set()

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            res = entry.get('resource')
            if not isinstance(res, dict):
                structural_warnings.append(f'La entrada #{idx + 1} de "entry[]" no contiene un objeto "resource" válido.')
                continue

            rtype = _safe_str(res.get('resourceType')) or 'Desconocido'
            rid = _safe_str(res.get('id'))
            full_url = _safe_str(entry.get('fullUrl'))

            resources_by_type.setdefault(rtype, []).append(res)

            if rid:
                resource_index[f"#{rid}"] = res
                resource_index[f"{rtype}/{rid}"] = res
                resource_index[rid] = res
            if full_url:
                resource_index[full_url] = res

            # Recolectar códigos candidatos para validación masiva en BD
            cls._collect_codes_from_resource(
                res,
                rtype,
                cie10_codes_to_check,
                cups_codes_to_check,
                eps_codes_to_check,
            )

        # 4. Consultar en bloque la base de datos de API_SM (CIE-10, CUPS, EPS)
        catalog_maps = cls._load_catalog_maps(
            cie10_codes_to_check,
            cups_codes_to_check,
            eps_codes_to_check,
        )

        # 5. Resolver secciones declaradas en Composition y validar referencias
        composition_list = resources_by_type.get('Composition', [])
        composition = composition_list[0] if composition_list else None
        section_membership: Dict[str, str] = {}

        if composition:
            cls._validate_and_index_composition_refs(
                composition,
                resource_index,
                section_membership,
                structural_warnings,
            )
        else:
            structural_warnings.append(
                'El Bundle no incluye un recurso "Composition" (Encabezado obligatorio en todo RDA de la Resolución 1888).'
            )

        # 6. Construir módulos traducidos a lenguaje humano
        catalog_validation_items: List[Dict[str, Any]] = []

        mod_encabezado = cls._build_header_module(bundle, composition, resource_index, wrapper_info)
        mod_paciente = cls._build_patient_module(
            resources_by_type.get('Patient', []),
            resource_index,
            structural_warnings,
        )
        mod_entidades = cls._build_organizations_module(
            resources_by_type.get('Organization', []),
            composition,
            resources_by_type.get('Patient', []),
            catalog_maps['eps'],
            catalog_validation_items,
        )
        mod_atencion = cls._build_encounter_module(
            resources_by_type.get('Encounter', []),
            resources_by_type.get('Practitioner', []),
            resources_by_type.get('PractitionerRole', []),
             resources_by_type.get('Location', []),
            resource_index,
        )
        mod_diagnosticos = cls._build_conditions_module(
            resources_by_type.get('Condition', []),
            resources_by_type.get('Encounter', []),
            section_membership,
            catalog_maps['cie10'],
            catalog_validation_items,
        )
        mod_medicamentos = cls._build_medications_module(
            resources_by_type.get('MedicationRequest', []),
            resources_by_type.get('MedicationStatement', []),
            resources_by_type.get('MedicationAdministration', []),
            resources_by_type.get('Medication', []),
            resource_index,
            catalog_maps['cie10'],
            catalog_validation_items,
        )
        mod_solicitudes = cls._build_procedures_and_requests_module(
            resources_by_type.get('ServiceRequest', []),
            resources_by_type.get('Procedure', []),
            resource_index,
            catalog_maps['cups'],
            catalog_maps['cie10'],
            catalog_validation_items,
        )
        mod_antecedentes_otros = cls._build_allergies_family_observations_module(
            resources_by_type.get('AllergyIntolerance', []),
            resources_by_type.get('FamilyMemberHistory', []),
            resources_by_type.get('Observation', []),
            resources_by_type.get('RiskAssessment', []),
            resources_by_type.get('DocumentReference', []),
            catalog_maps['cie10'],
            catalog_validation_items,
        )

        modules = [
            mod_encabezado,
            mod_paciente,
            mod_entidades,
            mod_atencion,
            mod_diagnosticos,
            mod_medicamentos,
            mod_solicitudes,
            mod_antecedentes_otros,
        ]

        valid_codes_count = sum(1 for item in catalog_validation_items if item['valid'])
        invalid_codes_count = sum(1 for item in catalog_validation_items if not item['valid'])

        resource_counts = {rtype: len(rlist) for rtype, rlist in resources_by_type.items()}

        # 7. Construir resumen global en texto plano listo para copiar
        plain_text_report = cls._build_plain_text_report(
            mod_encabezado,
            modules,
            catalog_validation_items,
            structural_warnings,
        )

        return {
            'summary': {
                'rda_type': mod_encabezado.get('rda_type_label', 'Bundle FHIR'),
                'rda_date': mod_encabezado.get('rda_date', 'No especificada'),
                'total_resources': sum(resource_counts.values()),
                'resource_counts': resource_counts,
                'total_codes_checked': len(catalog_validation_items),
                'valid_codes_count': valid_codes_count,
                'invalid_codes_count': invalid_codes_count,
                'structural_warnings_count': len(structural_warnings),
                'is_fully_valid': invalid_codes_count == 0 and len(structural_warnings) == 0,
            },
            'structural_warnings': structural_warnings,
            'catalog_validations': catalog_validation_items,
            'modules': modules,
            'plain_text_report': plain_text_report,
        }

    @classmethod
    def _collect_codes_from_resource(
        cls,
        res: Dict[str, Any],
        rtype: str,
        cie10_set: set,
        cups_set: set,
        eps_set: set,
    ) -> None:
        if rtype == 'Organization':
            idents = res.get('identifier') or []
            for ident in idents:
                if not isinstance(ident, dict):
                    continue
                val = _safe_str(ident.get('value'))
                type_info = _extract_coding_info(ident.get('type'))
                sys_str = _safe_str(ident.get('system')).lower()
                code_low = type_info['code'].lower()
                if any(k in code_low or k in sys_str for k in ('nit', 'tax', 'prestador', 'reps', 'prn', 'prv')):
                    continue
                if val and (
                    'eapb' in sys_str
                    or 'administradora' in sys_str
                    or 'eapb' in code_low
                    or 'pay' in code_low
                    or 'eps' in type_info['text'].lower()
                    or len(val) <= 8
                ):
                    eps_set.add(val.upper())
            if not idents:
                org_id = _safe_str(res.get('id'))
                if org_id and len(org_id) <= 8 and not org_id.lower().startswith('organization'):
                    eps_set.add(org_id.upper())

        elif rtype == 'Condition':
            for c in _extract_all_codings(res.get('code')):
                if c['code']:
                    cie10_set.add(c['code'].upper())

        elif rtype == 'FamilyMemberHistory':
            for cond in res.get('condition') or []:
                if isinstance(cond, dict):
                    for c in _extract_all_codings(cond.get('code')):
                        if c['code']:
                            cie10_set.add(c['code'].upper())

        elif rtype in ('ServiceRequest', 'Procedure'):
            for c in _extract_all_codings(res.get('code')):
                if c['code']:
                    cups_set.add(c['code'].upper())
            for reason in res.get('reasonCode') or []:
                for c in _extract_all_codings(reason):
                    if c['code']:
                        cie10_set.add(c['code'].upper())

        elif rtype in ('MedicationRequest', 'MedicationStatement', 'MedicationAdministration'):
            for reason in res.get('reasonCode') or []:
                for c in _extract_all_codings(reason):
                    if c['code']:
                        cie10_set.add(c['code'].upper())

    @classmethod
    def _load_catalog_maps(
        cls,
        cie10_codes: set,
        cups_codes: set,
        eps_codes: set,
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        cie10_map: Dict[str, Dict[str, str]] = {}
        cups_map: Dict[str, Dict[str, str]] = {}
        eps_map: Dict[str, Dict[str, str]] = {}

        if cie10_codes:
            for obj in Cie10.objects.filter(codigo__in=list(cie10_codes)):
                cie10_map[obj.codigo.strip().upper()] = {
                    'codigo': obj.codigo,
                    'descripcion': obj.descripcion,
                    'version': obj.version or '',
                }

        if cups_codes:
            for obj in Cups.objects.filter(codigo__in=list(cups_codes)):
                cups_map[obj.codigo.strip().upper()] = {
                    'codigo': obj.codigo,
                    'descripcion': obj.descripcion,
                    'version': obj.version or '',
                }

        if eps_codes:
            for obj in Eps.objects.filter(codigo__in=list(eps_codes)):
                eps_map[obj.codigo.strip().upper()] = {
                    'codigo': obj.codigo,
                    'nombre': obj.nombre,
                    'nit': obj.nit or '',
                    'regimen': obj.regimen or '',
                }

        return {'cie10': cie10_map, 'cups': cups_map, 'eps': eps_map}

    @classmethod
    def _validate_and_index_composition_refs(
        cls,
        composition: Dict[str, Any],
        resource_index: Dict[str, Dict[str, Any]],
        section_membership: Dict[str, str],
        structural_warnings: List[str],
    ) -> None:
        # Verificar subject (Paciente)
        subj_ref = _safe_str((composition.get('subject') or {}).get('reference'))
        if subj_ref and subj_ref not in resource_index:
            structural_warnings.append(
                f'El encabezado (Composition.subject) apunta al paciente "{subj_ref}", pero ese recurso no existe dentro de "entry[]".'
            )

        # Verificar encounter (Encuentro)
        enc_ref = _safe_str((composition.get('encounter') or {}).get('reference'))
        if enc_ref and enc_ref not in resource_index:
            structural_warnings.append(
                f'El encabezado (Composition.encounter) apunta a la atención "{enc_ref}", pero ese recurso no existe dentro de "entry[]".'
            )

        # Recorrer secciones
        for sec in composition.get('section') or []:
            if not isinstance(sec, dict):
                continue
            sec_title = _safe_str(sec.get('title')) or _extract_coding_info(sec.get('code'))['text'] or 'Sección sin título'
            for entry_ref in sec.get('entry') or []:
                if not isinstance(entry_ref, dict):
                    continue
                ref_str = _safe_str(entry_ref.get('reference'))
                if not ref_str:
                    continue
                section_membership[ref_str] = sec_title
                clean_id = ref_str.lstrip('#').split('/')[-1]
                section_membership[clean_id] = sec_title
                if ref_str not in resource_index and clean_id not in resource_index:
                    structural_warnings.append(
                        f'La sección "{sec_title}" referencia el elemento "{ref_str}", pero no existe ningún recurso con ese ID en el Bundle.'
                    )

    @classmethod
    def _resolve_ref(cls, ref_obj: Any, resource_index: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(ref_obj, dict):
            return None
        ref_str = _safe_str(ref_obj.get('reference'))
        if not ref_str:
            return None
        if ref_str in resource_index:
            return resource_index[ref_str]
        clean = ref_str.lstrip('#')
        if clean in resource_index:
            return resource_index[clean]
        last_part = clean.split('/')[-1]
        return resource_index.get(last_part)

    @classmethod
    def _classify_rda_type(cls, composition: Optional[Dict[str, Any]], resources_by_type_Check: bool = True) -> str:
        if not composition:
            return 'Bundle FHIR (Sin encabezado Composition)'
        title = _safe_str(composition.get('title'))
        type_info = _extract_coding_info(composition.get('type'))
        combined = f"{title} {type_info['text']}".lower()
        if 'paciente' in combined or 'patient summary' in combined:
            return 'RDA de Paciente (Antecedentes)'
        if 'urgencia' in combined:
            return 'RDA de Atención de Urgencias'
        if 'hospitalizaci' in combined:
            return 'RDA de Episodio de Hospitalización'
        if 'consulta' in combined or 'ambulator' in combined or 'externa' in combined:
            return 'RDA de Consulta Externa'
        return title or type_info['text'] or 'Resumen Digital de Atención (RDA - Res. 1888)'

    @classmethod
    def _build_header_module(
        cls,
        bundle: Dict[str, Any],
        composition: Optional[Dict[str, Any]],
        resource_index: Dict[str, Dict[str, Any]],
        wrapper_info: Optional[str],
    ) -> Dict[str, Any]:
        rda_type_label = cls._classify_rda_type(composition)
        rda_date = _safe_str(composition.get('date') if composition else bundle.get('timestamp')) or 'No registrada'
        doc_status = _safe_str(composition.get('status') if composition else '') or 'final'
        title = _safe_str(composition.get('title') if composition else '') or rda_type_label
        custodian_res = cls._resolve_ref(composition.get('custodian') if composition else None, resource_index)
        custodian_name = _safe_str((custodian_res or {}).get('name')) or 'No especificado'

        sections_summary = []
        if composition:
            for sec in composition.get('section') or []:
                if isinstance(sec, dict):
                    sec_title = _safe_str(sec.get('title')) or _extract_coding_info(sec.get('code'))['text'] or 'Sección'
                    sec_entries = sec.get('entry') or []
                    empty_reason = _extract_coding_info(sec.get('emptyReason'))['text']
                    sections_summary.append({
                        'title': sec_title,
                        'count': len(sec_entries),
                        'status': f"{len(sec_entries)} registro(s)" if sec_entries else (f"Vacía ({empty_reason})" if empty_reason else "Sin registros"),
                    })

        narrative = (
            f"Este archivo es un **{title}** ({rda_type_label}), generado en la fecha **{rda_date}** "
            f"con estado **{doc_status.upper()}**, bajo la custodia de la entidad prestadora **{custodian_name}**."
        )
        if wrapper_info:
            narrative = f"{wrapper_info} {narrative}"

        items = [{
            'title': title,
            'subtitle': f"Tipo: {rda_type_label}",
            'badge': doc_status.upper(),
            'badge_type': 'success' if doc_status == 'final' else 'warning',
            'explanation': narrative,
            'fields': [
                {'label': 'Tipo de Documento RDA', 'value': rda_type_label},
                {'label': 'Fecha y Hora de Generación', 'value': rda_date},
                {'label': 'Estado del Documento', 'value': doc_status.upper()},
                {'label': 'Entidad Custodio (IPS)', 'value': custodian_name},
                {
                    'label': 'Secciones declaradas en el RDA',
                    'value': ', '.join(f"{s['title']} ({s['status']})" for s in sections_summary) or 'Ninguna sección declarada',
                },
            ],
            'raw_resource': composition or bundle,
        }]

        return {
            'id': 'encabezado',
            'title': '1. Encabezado del Documento (RDA)',
            'icon': 'fa-file-Waveform',
            'fa_icon': 'fas fa-file-signature',
            'color': 'primary',
            'count': 1 if composition else 0,
            'rda_type_label': rda_type_label,
            'rda_date': rda_date,
            'narrative': narrative,
            'items': items,
        }

    @classmethod
    def _build_patient_module(
        cls,
        patients: List[Dict[str, Any]],
        resource_index: Dict[str, Dict[str, Any]],
        structural_warnings: List[str],
    ) -> Dict[str, Any]:
        if not patients:
            structural_warnings.append('No se encontró ningún recurso "Patient" (Datos del Paciente) en el Bundle.')
            return {
                'id': 'paciente',
                'title': '2. Datos del Paciente',
                'fa_icon': 'fas fa-user-injured',
                'color': 'info',
                'count': 0,
                'narrative': 'No se encontró bloque de Paciente (Patient) dentro del archivo JSON.',
                'items': [],
            }

        items = []
        narratives = []

        for pat in patients:
            # Documento de identidad (prioriza ColombianPersonIdentifier -> ej. DE-095305827-14)
            doc_type = ''
            doc_type_display = ''
            doc_number = ''
            doc_country = ''
            for ident in pat.get('identifier') or []:
                if not isinstance(ident, dict):
                    continue
                val = _safe_str(ident.get('value'))
                t_info = _extract_coding_info(ident.get('type'))
                if val and not doc_number:
                    doc_number = val
                    doc_type = t_info['code'] or t_info['display'] or 'DOC'
                    doc_type_display = t_info['display']
                    country_ext = (
                        _find_extension(ident.get('extension'), 'divipolaCountry')
                        or _find_extension(ident.get('extension'), 'country')
                        or _find_extension(ident.get('extension'), 'pais')
                    )
                    doc_country = _extract_extension_value(country_ext)

            doc_ihce_code = f"{doc_type}-{doc_number}" if doc_type and doc_number else (doc_number or doc_type or 'No registrado')
            doc_full_label = (
                f"{doc_ihce_code} ({doc_type_display})"
                if doc_type_display and doc_type_display.lower() != doc_type.lower()
                else doc_ihce_code
            )

            # Nombres y apellidos (incluyendo fathersFamily y mothersFamily de Res 1888)
            first_name = ''
            second_name = ''
            first_surname = ''
            second_surname = ''
            full_name = ''

            names = pat.get('name') or []
            if isinstance(names, list) and names and isinstance(names[0], dict):
                n0 = names[0]
                givens = n0.get('given') or []
                if len(givens) > 0:
                    first_name = _safe_str(givens[0])
                if len(givens) > 1:
                    second_name = ' '.join(_safe_str(g) for g in givens[1:])

                family_raw = _safe_str(n0.get('family'))
                fam_ext = (n0.get('_family') or {}).get('extension') or []
                father_ext = _find_extension(fam_ext, 'fathersFamily') or _find_extension(fam_ext, 'primerApellido')
                mother_ext = _find_extension(fam_ext, 'mothersFamily') or _find_extension(fam_ext, 'segundoApellido')
                first_surname = _extract_extension_value(father_ext) or family_raw
                second_surname = _extract_extension_value(mother_ext)
                parts = [p for p in [first_name, second_name, first_surname, second_surname] if p]
                full_name = ' '.join(parts) or _safe_str(n0.get('text')) or family_raw

            birth_date = _safe_str(pat.get('birthDate'))
            age_label = _calculate_age(birth_date)
            gender_code = _safe_str(pat.get('gender')).lower()
            gender_label = GENDER_MAP.get(gender_code, gender_code or 'No especificado')

            # Extensiones colombianas del Paciente (Sexo biológico en extension o _gender.extension, Identidad de género, Etnia, Discapacidad, Nacionalidad, Ocupación)
            exts = (pat.get('extension') or []) + ((pat.get('_gender') or {}).get('extension') or [])
            bio_sex = _extract_extension_value(
                _find_extension(exts, 'biologicalSex')
                or _find_extension(exts, 'biologicalGender')
                or _find_extension(exts, 'sexoBiologico')
            )
            gender_id = _extract_extension_value(_find_extension(exts, 'genderIdentity') or _find_extension(exts, 'identidadGenero'))
            nationality = _extract_extension_value(_find_extension(exts, 'nationality') or _find_extension(exts, 'nacionalidad'))
            ethnicity = _extract_extension_value(_find_extension(exts, 'ethnicity') or _find_extension(exts, 'etnia'))
            ethnic_group = _extract_extension_value(_find_extension(exts, 'ethnicGroup') or _find_extension(exts, 'comunidadEtnica'))
            disability = _extract_extension_value(_find_extension(exts, 'disability') or _find_extension(exts, 'discapacidad'))
            occupation = _extract_extension_value(_find_extension(exts, 'occupation') or _find_extension(exts, 'ocupacion'))

            # Dirección, Municipio DANE y Zona
            city_text = ''
            state_text = ''
            zone_text = ''
            address_line = ''
            addresses = pat.get('address') or []
            if isinstance(addresses, list) and addresses and isinstance(addresses[0], dict):
                a0 = addresses[0]
                address_line = _safe_str(a0.get('text')) or ', '.join(_safe_str(l) for l in (a0.get('line') or []) if l)
                city_code = _extract_extension_value(_find_extension((a0.get('_city') or {}).get('extension'), 'divipolaMunicipality') or _find_extension(a0.get('extension'), 'municip'))
                city_name = _safe_str(a0.get('city'))
                city_text = f"{city_code} - {city_name}" if city_code and city_name else (city_name or city_code)
                state_code = _extract_extension_value(_find_extension((a0.get('_state') or {}).get('extension'), 'divipolaDepartment'))
                state_name = _safe_str(a0.get('state'))
                state_text = f"{state_code} - {state_name}" if state_code and state_name else (state_name or state_code)
                zone_raw = _extract_extension_value(_find_extension(a0.get('extension'), 'zone') or _find_extension(a0.get('extension'), 'zona'))
                zone_text = ZONA_MAP.get(zone_raw, zone_raw)

            pat_narrative = (
                f"Paciente **{full_name or 'Sin nombre registrado'}**, identificado con **{doc_full_label}**, "
                f"fecha de nacimiento **{birth_date or 'No indicada'}** ({age_label or 'Edad no calculable'}), "
                f"sexo **{bio_sex or gender_label}**."
            )
            if city_text or zone_text:
                pat_narrative += f" Residencia: **{city_text or 'No especificada'}** (Zona: **{zone_text or 'No indicada'}**)."
            narratives.append(pat_narrative)

            items.append({
                'title': full_name or f"Paciente ({pat.get('id', 'Sin ID')})",
                'subtitle': f"Documento: {doc_full_label}",
                'badge': doc_ihce_code if doc_type and doc_number else (age_label or gender_label),
                'badge_type': 'info',
                'explanation': pat_narrative,
                'fields': [
                    {'label': 'Tipo y Número de Documento (IHCE)', 'value': doc_full_label},
                    {'label': 'Primer y Segundo Nombre', 'value': f"{first_name} {second_name}".strip() or 'No registrado'},
                    {'label': 'Primer y Segundo Apellido', 'value': f"{first_surname} {second_surname}".strip() or 'No registrado'},
                    {'label': 'Fecha de Nacimiento y Edad', 'value': f"{birth_date} ({age_label})" if age_label else (birth_date or 'No registrada')},
                    {'label': 'Sexo Biológico / Género FHIR', 'value': bio_sex or gender_label},
                    {'label': 'Identidad de Género', 'value': gender_id or 'No especificada'},
                    {'label': 'Nacionalidad / País Doc.', 'value': nationality or doc_country or 'Colombia (Por defecto)'},
                    {'label': 'Pertenencia Étnica / Comunidad', 'value': f"{ethnicity} {ethnic_group}".strip() or 'Ninguna / No aplica'},
                    {'label': 'Discapacidad', 'value': disability or 'Sin discapacidad / No especificada'},
                    {'label': 'Ocupación (CIUO)', 'value': occupation or 'No especificada'},
                    {'label': 'Municipio / Departamento (DANE)', 'value': f"{city_text} / {state_text}".strip(' /') or 'No especificado'},
                    {'label': 'Zona de Residencia y Dirección', 'value': f"{zone_text} — {address_line}".strip(' —') or 'No especificada'},
                ],
                'raw_resource': pat,
            })

        return {
            'id': 'paciente',
            'title': '2. Datos del Paciente',
            'fa_icon': 'fas fa-user-injured',
            'color': 'info',
            'count': len(items),
            'narrative': ' '.join(narratives),
            'items': items,
        }

    @classmethod
    def _build_organizations_module(
        cls,
        organizations: List[Dict[str, Any]],
        composition: Optional[Dict[str, Any]],
        patients: List[Dict[str, Any]],
        eps_map: Dict[str, Dict[str, str]],
        catalog_validation_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        custodian_ref = _safe_str(((composition or {}).get('custodian') or {}).get('reference')).lstrip('#').split('/')[-1]
        items = []
        narratives = []

        for org in organizations:
            org_id = _safe_str(org.get('id'))
            org_name = _safe_str(org.get('name')) or 'Entidad sin nombre'
            nit_val = ''
            reps_val = ''
            eapb_val = ''

            for ident in org.get('identifier') or []:
                if not isinstance(ident, dict):
                    continue
                val = _safe_str(ident.get('value'))
                t_info = _extract_coding_info(ident.get('type'))
                sys_str = _safe_str(ident.get('system')).lower()
                code_upper = t_info['code'].upper()

                if 'NIT' in code_upper or 'TAX' in code_upper or 'nit' in sys_str:
                    nit_val = val
                elif (
                    'REPS' in code_upper
                    or 'PRESTADOR' in code_upper
                    or 'PRN' in code_upper
                    or 'PRV' in code_upper
                    or 'prestador' in sys_str
                    or 'reps' in sys_str
                ):
                    reps_val = val
                elif 'EAPB' in code_upper or 'PAY' in code_upper or 'administradora' in sys_str or 'eapb' in sys_str:
                    eapb_val = val
                elif not eapb_val and len(val) <= 6:
                    eapb_val = val
                elif not reps_val and len(val) >= 10 and not nit_val:
                    reps_val = val

            is_ips = (org_id and org_id == custodian_ref) or bool(reps_val and not eapb_val)
            if not is_ips and not eapb_val and org_id and len(org_id) <= 8 and not org_id.lower().startswith('organization'):
                eapb_val = org_id
            role_label = 'IPS Prestadora de Salud' if is_ips else 'EPS / Aseguradora (Pagador EAPB)'

            catalog_check = None
            if not is_ips and eapb_val:
                db_eps = eps_map.get(eapb_val.upper())
                is_valid = db_eps is not None
                catalog_check = {
                    'catalog': 'EPS / Entidades',
                    'code': eapb_val,
                    'sent_name': org_name,
                    'valid': is_valid,
                    'official_name': db_eps['nombre'] if db_eps else 'Código EAPB no encontrado en catálogo de Entidades de API_SM',
                    'extra': f"Régimen: {db_eps['regimen']} | NIT: {db_eps['nit']}" if db_eps else '',
                }
                catalog_validation_items.append(catalog_check)

            explanation = (
                f"**{role_label}:** {org_name} "
                + (f"(NIT: {nit_val}, Código REPS: {reps_val})" if is_ips else f"(Código EAPB: {eapb_val or 'No enviado'}, NIT: {nit_val or 'N/A'})")
            )
            narratives.append(explanation)

            fields = [
                {'label': 'Rol de la Entidad en el RDA', 'value': role_label},
                {'label': 'Nombre o Razón Social', 'value': org_name},
                {'label': 'NIT', 'value': nit_val or 'No registrado'},
            ]
            if is_ips:
                fields.append({'label': 'Código de Habilitación REPS', 'value': reps_val or 'No registrado'})
            else:
                fields.append({'label': 'Código de Aseguradora (EAPB)', 'value': eapb_val or 'No registrado'})

            items.append({
                'title': org_name,
                'subtitle': role_label,
                'badge': f"REPS: {reps_val}" if is_ips and reps_val else (f"EAPB: {eapb_val}" if eapb_val else role_label),
                'badge_type': 'primary' if is_ips else ('success' if (catalog_check and catalog_check['valid']) else 'warning'),
                'explanation': explanation,
                'catalog_check': catalog_check,
                'fields': fields,
                'raw_resource': org,
            })

        return {
            'id': 'entidades',
            'title': '3. Entidades: IPS Prestadora y Aseguradora (EPS)',
            'fa_icon': 'fas fa-hospital-user',
            'color': 'primary',
            'count': len(items),
            'narrative': ' | '.join(narratives) if narratives else 'No se registraron organizaciones (IPS/EPS) en el Bundle.',
            'items': items,
        }

    @classmethod
    def _build_encounter_module(
        cls,
        encounters: List[Dict[str, Any]],
        practitioners: List[Dict[str, Any]],
        practitioner_roles: List[Dict[str, Any]],
        locations: List[Dict[str, Any]],
        resource_index: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        items = []
        narratives = []

        # Preparar resumen de profesionales
        practitioner_summaries = []
        for prac in practitioners:
            p_doc = ''
            for ident in prac.get('identifier') or []:
                if isinstance(ident, dict) and ident.get('value'):
                    t_code = _extract_coding_info(ident.get('type'))['code'] or 'DOC'
                    p_doc = f"{t_code}-{_safe_str(ident.get('value'))}"
                    break
            p_name = ''
            names = prac.get('name') or []
            if names and isinstance(names[0], dict):
                n0 = names[0]
                givens = ' '.join(_safe_str(g) for g in (n0.get('given') or []) if g)
                fam = _safe_str(n0.get('family'))
                p_name = f"{givens} {fam}".strip() or _safe_str(n0.get('text'))
            practitioner_summaries.append(f"{p_name or 'Profesional'} ({p_doc or 'Sin doc.'})")

        prof_text = ', '.join(practitioner_summaries) if practitioner_summaries else 'No especificado en el RDA'

        for enc in encounters:
            status_raw = _safe_str(enc.get('status')).lower()
            status_label = ENCOUNTER_STATUS_MAP.get(status_raw, status_raw or 'Finalizado')
            class_info = _extract_coding_info(enc.get('class'))
            service_type = _extract_coding_info(enc.get('serviceType'))['text']

            # Revisar también Encounter.type[] (Modalidad, Grupo de Servicios, Entorno de Atención en Res. 1888)
            modality_text = ''
            type_service_group = ''
            type_env_care = ''
            for t_concept in enc.get('type') or []:
                t_info = _extract_coding_info(t_concept)
                sys_low = t_info['system'].lower()
                if 'modality' in sys_low or 'modalidad' in sys_low:
                    modality_text = t_info['text']
                elif 'gruposervicio' in sys_low or 'servicegroup' in sys_low:
                    type_service_group = t_info['text']
                elif 'entorno' in sys_low or 'environment' in sys_low:
                    type_env_care = t_info['text']

            period = enc.get('period') or {}
            start_dt = _safe_str(period.get('start'))
            end_dt = _safe_str(period.get('end'))

            # Causa de atención
            reasons = [_extract_coding_info(r)['text'] for r in (enc.get('reasonCode') or []) if _extract_coding_info(r)['text']]
            reason_text = ', '.join(reasons) or 'No especificada'

            # Hospitalización / Vía de ingreso / Destino y condición de egreso
            hosp = enc.get('hospitalization') or {}
            admit_source = _extract_coding_info(hosp.get('admitSource'))['text']
            discharge_disp = _extract_coding_info(hosp.get('dischargeDisposition'))['text']

            # Extensiones del encuentro (Grupo de servicios, entorno, condición de egreso)
            exts = enc.get('extension') or []
            service_group = (
                _extract_extension_value(_find_extension(exts, 'serviceGroup') or _find_extension(exts, 'grupoServicio'))
                or type_service_group
            )
            env_care = (
                _extract_extension_value(_find_extension(exts, 'environment') or _find_extension(exts, 'entorno'))
                or type_env_care
            )
            if not discharge_disp:
                discharge_disp = _extract_extension_value(
                    _find_extension(exts, 'dischargeDisposition') or _find_extension(exts, 'destinoEgreso')
                )

            modality_combined = f"{class_info['text']} / {modality_text}".strip(' /') if modality_text else class_info['text']

            explanation = (
                f"Atención en estado **{status_label}**, modalidad **{modality_combined or 'Ambulatoria'}**"
                + (f", servicio **{service_type or service_group}**" if (service_type or service_group) else "")
                + f", iniciada el **{start_dt or 'N/A'}** y finalizada el **{end_dt or 'N/A'}**. "
                f"Atendido por: **{prof_text}**. Causa externa / motivo: **{reason_text}**."
            )
            if discharge_disp:
                explanation += f" Condición/Destino de egreso: **{discharge_disp}**."
            narratives.append(explanation)

            items.append({
                'title': f"Atención Clínica ({modality_combined or service_type or 'Encuentro'})",
                'subtitle': f"Inicio: {start_dt or 'N/A'} — Fin: {end_dt or 'N/A'}",
                'badge': status_label,
                'badge_type': 'success' if status_raw == 'finished' else 'info',
                'explanation': explanation,
                'fields': [
                    {'label': 'Estado de la Atención', 'value': status_label},
                    {'label': 'Modalidad / Clase de Encuentro', 'value': modality_combined or 'No especificada'},
                    {'label': 'Tipo / Grupo de Servicio', 'value': f"{service_group} — {service_type}".strip(' —') or 'No especificado'},
                    {'label': 'Entorno de Atención', 'value': env_care or 'Institucional / No especificado'},
                    {'label': 'Fecha y Hora de Inicio', 'value': start_dt or 'No registrada'},
                    {'label': 'Fecha y Hora de Fin / Egreso', 'value': end_dt or 'No registrada'},
                    {'label': 'Causa que Motiva la Atención', 'value': reason_text},
                    {'label': 'Vía de Ingreso', 'value': admit_source or 'No aplica / Consulta externa'},
                    {'label': 'Condición y Destino de Egreso', 'value': discharge_disp or 'No aplica / Alta ambulatoria'},
                    {'label': 'Profesional(es) de la Salud', 'value': prof_text},
                ],
                'raw_resource': enc,
            })

        # Si hay profesionales pero no hay Encounter (ej. RDA de Paciente)
        if not items and practitioners:
            for prac in practitioners:
                items.append({
                    'title': f"Profesional Responsable: {prof_text}",
                    'subtitle': 'Autor del Resumen Digital de Atención (RDA)',
                    'badge': 'Profesional',
                    'badge_type': 'info',
                    'explanation': f"El RDA fue firmado/generado por el profesional de la salud **{prof_text}**.",
                    'fields': [
                        {'label': 'Profesional que registra', 'value': prof_text},
                    ],
                    'raw_resource': prac,
                })

        return {
            'id': 'atencion',
            'title': '4. Datos de la Atención (Cita / Encuentro y Profesional)',
            'fa_icon': 'fas fa-user-md',
            'color': 'secondary',
            'count': len(items),
            'narrative': ' '.join(narratives) if narratives else (f"Profesional que registra el RDA: **{prof_text}** (Sin bloque Encounter por ser RDA de antecedentes)." if practitioners else 'No se encontró información de encuentro clínico.'),
            'items': items,
        }

    @classmethod
    def _build_conditions_module(
        cls,
        conditions: List[Dict[str, Any]],
        encounters: List[Dict[str, Any]],
        section_membership: Dict[str, str],
        cie10_map: Dict[str, Dict[str, str]],
        catalog_validation_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        # Identificar roles de diagnóstico desde Encounter.diagnosis
        encounter_diag_roles: Dict[str, str] = {}
        for enc in encounters:
            for idx, diag in enumerate(enc.get('diagnosis') or []):
                if not isinstance(diag, dict):
                    continue
                ref_id = _safe_str((diag.get('condition') or {}).get('reference')).lstrip('#').split('/')[-1]
                use_text = _extract_coding_info(diag.get('use'))['text']
                rank = diag.get('rank')
                if ref_id:
                    role_str = use_text or ('Diagnóstico Principal' if rank == 1 or idx == 0 else f'Diagnóstico Relacionado #{idx + 1}')
                    encounter_diag_roles[ref_id] = role_str

        items = []
        narratives = []

        for idx, cond in enumerate(conditions):
            cid = _safe_str(cond.get('id'))
            code_info = _extract_coding_info(cond.get('code'))
            cie_code = code_info['code'].upper()
            sent_display = code_info['display'] or code_info['text']

            clin_status_code = _extract_coding_info(cond.get('clinicalStatus'))['code'].lower()
            clin_status = CLINICAL_STATUS_MAP.get(clin_status_code, clin_status_code or 'Activo')

            verif_code = _extract_coding_info(cond.get('verificationStatus'))['code'].lower()
            verif_status = VERIFICATION_STATUS_MAP.get(verif_code, _extract_coding_info(cond.get('verificationStatus'))['text'] or 'Confirmado')

            sec_title = section_membership.get(cid) or section_membership.get(f"#{cid}") or ''
            diag_role = encounter_diag_roles.get(cid)
            if not diag_role:
                if 'antecedente' in sec_title.lower() or 'history' in sec_title.lower() or 'problem' in sec_title.lower():
                    diag_role = f"Antecedente Patológico ({sec_title})"
                else:
                    diag_role = sec_title or (f"Diagnóstico Principal" if idx == 0 else f"Diagnóstico #{idx + 1}")

            # Validar CIE-10 contra la BD de API_SM
            catalog_check = None
            if cie_code:
                db_cie = cie10_map.get(cie_code)
                is_valid = db_cie is not None
                catalog_check = {
                    'catalog': 'CIE-10 (Diagnósticos)',
                    'code': cie_code,
                    'sent_name': sent_display,
                    'valid': is_valid,
                    'official_name': db_cie['descripcion'] if db_cie else 'Código CIE-10 NO existe en el catálogo oficial de API_SM',
                    'extra': f"Versión catálogo: {db_cie['version']}" if (db_cie and db_cie.get('version')) else '',
                }
                catalog_validation_items.append(catalog_check)

            notes = '; '.join(_safe_str(n.get('text')) for n in (cond.get('note') or []) if isinstance(n, dict) and n.get('text'))

            explanation = (
                f"**{diag_role}:** Código CIE-10 **{cie_code or 'SIN CÓDIGO'}** — *{sent_display or 'Sin descripción'}* "
                f"(Estado: **{clin_status}**, Certeza: **{verif_status}**)."
            )
            narratives.append(explanation)

            items.append({
                'title': f"{cie_code} — {sent_display}" if cie_code else (sent_display or f"Condición #{idx + 1}"),
                'subtitle': diag_role,
                'badge': 'CIE-10 Válido' if (catalog_check and catalog_check['valid']) else ('CIE-10 No Encontrado' if catalog_check else clin_status),
                'badge_type': 'success' if (catalog_check and catalog_check['valid']) else ('danger' if catalog_check else 'secondary'),
                'explanation': explanation,
                'catalog_check': catalog_check,
                'fields': [
                    {'label': 'Clasificación / Módulo', 'value': diag_role},
                    {'label': 'Código CIE-10 Enviado', 'value': cie_code or 'No enviado'},
                    {'label': 'Nombre Enviado en el JSON', 'value': sent_display or 'No enviado'},
                    {'label': 'Nombre Oficial en Base de Datos (API_SM)', 'value': catalog_check['official_name'] if catalog_check else 'Sin código para validar'},
                    {'label': 'Tipo / Certeza del Diagnóstico', 'value': verif_status},
                    {'label': 'Estado Clínico', 'value': clin_status},
                    {'label': 'Observaciones / Notas', 'value': notes or 'Sin notas adicionales'},
                ],
                'raw_resource': cond,
            })

        return {
            'id': 'diagnosticos',
            'title': '5. Diagnósticos Clínicos y Antecedentes Patológicos (CIE-10)',
            'fa_icon': 'fas fa-stethoscope',
            'color': 'success',
            'count': len(items),
            'narrative': ' '.join(narratives) if narratives else 'No se registraron diagnósticos ni condiciones (Condition) en este Bundle.',
            'items': items,
        }

    @classmethod
    def _build_medications_module(
        cls,
        med_requests: List[Dict[str, Any]],
        med_statements: List[Dict[str, Any]],
        med_administrations: List[Dict[str, Any]],
        medications: List[Dict[str, Any]],
        resource_index: Dict[str, Dict[str, Any]],
        cie10_map: Dict[str, Dict[str, str]],
        catalog_validation_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        items = []
        narratives = []

        # 1. Prescripciones / Fórmula Médica (MedicationRequest)
        for idx, mreq in enumerate(med_requests):
            med_info = cls._extract_medication_identity(mreq, resource_index)
            dosages = mreq.get('dosageInstruction') or []
            d0 = dosages[0] if (isinstance(dosages, list) and dosages and isinstance(dosages[0], dict)) else {}

            # Extraer dosis, vía, cada cuánto y por cuánto tiempo
            dose_text = ''
            dose_rates = d0.get('doseAndRate') or []
            if dose_rates and isinstance(dose_rates[0], dict):
                dq = dose_rates[0].get('doseQuantity') or {}
                if dq.get('value') is not None:
                    dose_text = f"{dq.get('value')} {_safe_str(dq.get('unit') or dq.get('code'))}".strip()

            route_text = _extract_coding_info(d0.get('route'))['text'] or 'Vía no especificada'
            repeat = (d0.get('timing') or {}).get('repeat') or {}
            freq = repeat.get('frequency')
            period = repeat.get('period')
            p_unit = PERIOD_UNIT_MAP.get(_safe_str(repeat.get('periodUnit')), _safe_str(repeat.get('periodUnit')))
            freq_text = f"cada {period} {p_unit}" if period and p_unit else (f"{freq} vez/veces" if freq else 'Segun indicación médica')

            bounds = repeat.get('boundsDuration') or {}
            dur_val = bounds.get('value') if bounds.get('value') is not None else repeat.get('duration')
            raw_dur_unit = _safe_str(bounds.get('unit') or bounds.get('code') or repeat.get('durationUnit'))
            dur_unit = PERIOD_UNIT_MAP.get(raw_dur_unit, raw_dur_unit)
            duration_text = f"durante {dur_val} {dur_unit}".strip() if dur_val is not None else 'Duración no especificada'

            # Cantidad total prescrita (dispenseRequest)
            disp_req = mreq.get('dispenseRequest') or {}
            qty_obj = disp_req.get('quantity') or {}
            total_qty = f"{qty_obj.get('value')} {_safe_str(qty_obj.get('unit') or qty_obj.get('code'))}".strip() if qty_obj.get('value') is not None else 'No especificada'

            # Diagnóstico asociado a la prescripción
            diag_codes = []
            for rcode in mreq.get('reasonCode') or []:
                c_info = _extract_coding_info(rcode)
                if c_info['code']:
                    diag_codes.append(c_info['code'])
            for rref in mreq.get('reasonReference') or []:
                resolved_cond = cls._resolve_ref(rref, resource_index)
                if resolved_cond:
                    c_info = _extract_coding_info(resolved_cond.get('code'))
                    if c_info['code']:
                        diag_codes.append(c_info['code'])

            free_instruction = _safe_str(d0.get('text')) or _safe_str(d0.get('patientInstruction'))
            explanation = (
                f"**Prescripción / Receta Médica:** **{med_info['name']}** ({med_info['codes_label']}). "
                f"Posología traducida: Administrar **{dose_text or 'dosis indicada'}** por vía **{route_text}**, "
                f"**{freq_text}**, **{duration_text}**. Cantidad total formulada: **{total_qty}**."
            )
            if diag_codes:
                explanation += f" Diagnóstico asociado: **{', '.join(diag_codes)}**."
            if free_instruction:
                explanation += f" Nota al paciente: *{free_instruction}*."
            narratives.append(explanation)

            items.append({
                'title': f"💊 Prescripción: {med_info['name']}",
                'subtitle': f"Posología: {dose_text or ''} • {route_text} • {freq_text} • {duration_text}".strip(' •'),
                'badge': 'Prescripción (Receta)',
                'badge_type': 'warning',
                'explanation': explanation,
                'fields': [
                    {'label': 'Tipo de Registro', 'value': 'Prescripción / Fórmula Médica (MedicationRequest)'},
                    {'label': 'Medicamento (Nombre / DCI)', 'value': med_info['name']},
                    {'label': 'Código(s) Enviados (CUM / IUM / ATC)', 'value': med_info['codes_label']},
                    {'label': 'Dosis por Toma', 'value': dose_text or 'No especificada'},
                    {'label': 'Vía de Administración', 'value': route_text},
                    {'label': 'Frecuencia de Administración', 'value': freq_text},
                    {'label': 'Duración del Tratamiento', 'value': duration_text},
                    {'label': 'Cantidad Total a Dispensar', 'value': total_qty},
                    {'label': 'Diagnóstico(s) Asociado(s)', 'value': ', '.join(diag_codes) or 'No especificado'},
                    {'label': 'Instrucción / Indicaciones Especiales', 'value': free_instruction or 'Sin indicaciones adicionales'},
                ],
                'raw_resource': mreq,
            })

        # 2. Antecedentes Farmacológicos (MedicationStatement)
        for idx, mstat in enumerate(med_statements):
            med_info = cls._extract_medication_identity(mstat, resource_index)
            dosages = mstat.get('dosage') or []
            d0 = dosages[0] if (isinstance(dosages, list) and dosages and isinstance(dosages[0], dict)) else {}
            dosage_text = _safe_str(d0.get('text')) or _extract_coding_info(d0.get('route'))['text'] or 'Uso reportado en antecedentes'
            explanation = (
                f"**Antecedente Farmacológico (Medicamento que consume el paciente):** **{med_info['name']}** "
                f"({med_info['codes_label']}) — {dosage_text}."
            )
            narratives.append(explanation)
            items.append({
                'title': f"📋 Antecedente Farmacológico: {med_info['name']}",
                'subtitle': med_info['codes_label'],
                'badge': 'Antecedente (MedicationStatement)',
                'badge_type': 'info',
                'explanation': explanation,
                'fields': [
                    {'label': 'Tipo de Registro', 'value': 'Antecedente Farmacológico (MedicationStatement)'},
                    {'label': 'Medicamento', 'value': med_info['name']},
                    {'label': 'Código(s) (CUM / IUM / DCI)', 'value': med_info['codes_label']},
                    {'label': 'Posología / Detalle', 'value': dosage_text},
                ],
                'raw_resource': mstat,
            })

        # 3. Administración de Medicamentos en la Atención (MedicationAdministration)
        for idx, madm in enumerate(med_administrations):
            med_info = cls._extract_medication_identity(madm, resource_index)
            dosage = madm.get('dosage') or {}
            route_text = _extract_coding_info(dosage.get('route'))['text'] or 'No especificada'
            dose_q = dosage.get('dose') or {}
            dose_str = f"{dose_q.get('value')} {_safe_str(dose_q.get('unit') or dose_q.get('code'))}".strip() if dose_q.get('value') is not None else 'No especificada'
            eff_time = _safe_str(madm.get('effectiveDateTime') or (madm.get('effectivePeriod') or {}).get('start'))

            explanation = (
                f"**Medicamento Administrado en la Atención:** **{med_info['name']}** ({med_info['codes_label']}), "
                f"dosis aplicada: **{dose_str}** por vía **{route_text}** en fecha/hora **{eff_time or 'N/A'}**."
            )
            narratives.append(explanation)
            items.append({
                'title': f"💉 Administrado: {med_info['name']}",
                'subtitle': f"Dosis: {dose_str} • Vía: {route_text}",
                'badge': 'Administrado en Atención',
                'badge_type': 'primary',
                'explanation': explanation,
                'fields': [
                    {'label': 'Tipo de Registro', 'value': 'Administración de Medicamento (MedicationAdministration)'},
                    {'label': 'Medicamento', 'value': med_info['name']},
                    {'label': 'Código(s) (CUM / IUM / DCI)', 'value': med_info['codes_label']},
                    {'label': 'Dosis Aplicada y Vía', 'value': f"{dose_str} ({route_text})"},
                    {'label': 'Fecha y Hora de Aplicación', 'value': eff_time or 'No registrada'},
                ],
                'raw_resource': madm,
            })

        return {
            'id': 'medicamentos',
            'title': '6. Medicamentos: Prescripciones (Recetas), Antecedentes y Administración',
            'fa_icon': 'fas fa-pills',
            'color': 'warning',
            'count': len(items),
            'narrative': ' '.join(narratives) if narratives else 'No se registraron prescripciones de medicamentos ni antecedentes farmacológicos en este Bundle.',
            'items': items,
        }

    @classmethod
    def _extract_medication_identity(
        cls,
        med_resource: Dict[str, Any],
        resource_index: Dict[str, Dict[str, Any]],
    ) -> Dict[str, str]:
        concept = med_resource.get('medicationCodeableConcept')
        if not concept and med_resource.get('medicationReference'):
            resolved_med = cls._resolve_ref(med_resource.get('medicationReference'), resource_index)
            if resolved_med:
                concept = resolved_med.get('code')

        codings = _extract_all_codings(concept)
        concept_text = _safe_str((concept or {}).get('text'))
        if not codings:
            txt = concept_text or 'Medicamento sin descripción'
            return {'name': txt, 'codes_label': 'Sin código CUM/IUM/DCI'}

        names = [c['display'] for c in codings if c['display']]
        codes_formatted = []
        for c in codings:
            sys_l = c['system'].lower()
            tag = 'Código'
            if 'ium' in sys_l:
                tag = 'IUM'
            elif 'cum' in sys_l or 'invima' in sys_l:
                tag = 'CUM'
            elif 'atc' in sys_l or 'dci' in sys_l:
                tag = 'DCI/ATC'
            codes_formatted.append(f"{tag}: {c['code']}" + (f" ({c['display']})" if c['display'] else ''))

        primary_name = names[0] if names else codings[0]['code']
        if concept_text and concept_text.lower() not in primary_name.lower():
            primary_name = f"{primary_name} ({concept_text})"
        return {
            'name': primary_name,
            'codes_label': ' | '.join(codes_formatted),
        }

    @classmethod
    def _build_procedures_and_requests_module(
        cls,
        service_requests: List[Dict[str, Any]],
        procedures: List[Dict[str, Any]],
        resource_index: Dict[str, Dict[str, Any]],
        cups_map: Dict[str, Dict[str, str]],
        cie10_map: Dict[str, Dict[str, str]],
        catalog_validation_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        items = []
        narratives = []

        # 1. Solicitudes / Órdenes Médicas (ServiceRequest)
        for idx, sreq in enumerate(service_requests):
            c_info = _extract_coding_info(sreq.get('code'))
            cups_code = c_info['code'].upper()
            sent_name = c_info['display'] or c_info['text']
            authored_on = _safe_str(sreq.get('authoredOn'))
            notes = '; '.join(_safe_str(n.get('text')) for n in (sreq.get('note') or []) if isinstance(n, dict) and n.get('text'))

            catalog_check = None
            if cups_code:
                db_cups = cups_map.get(cups_code)
                is_valid = db_cups is not None
                catalog_check = {
                    'catalog': 'CUPS (Procedimientos / Órdenes)',
                    'code': cups_code,
                    'sent_name': sent_name,
                    'valid': is_valid,
                    'official_name': db_cups['descripcion'] if db_cups else 'Código CUPS NO existe en el catálogo oficial de API_SM',
                    'extra': f"Versión catálogo: {db_cups['version']}" if (db_cups and db_cups.get('version')) else '',
                }
                catalog_validation_items.append(catalog_check)

            explanation = (
                f"**Solicitud / Orden Médica (ServiceRequest):** Código CUPS **{cups_code or 'SIN CÓDIGO'}** — "
                f"*{sent_name or 'Sin nombre'}* (Fecha de orden: **{authored_on or 'No indicada'}**)."
            )
            narratives.append(explanation)

            items.append({
                'title': f"📋 Orden / Solicitud: {cups_code} — {sent_name}",
                'subtitle': 'Solicitud / Orden de Procedimiento o Apoyo Diagnóstico (ServiceRequest)',
                'badge': 'CUPS Válido' if (catalog_check and catalog_check['valid']) else ('CUPS No Encontrado' if catalog_check else 'Solicitud'),
                'badge_type': 'success' if (catalog_check and catalog_check['valid']) else ('danger' if catalog_check else 'info'),
                'explanation': explanation,
                'catalog_check': catalog_check,
                'fields': [
                    {'label': 'Tipo de Registro', 'value': 'Solicitud / Orden Médica (ServiceRequest)'},
                    {'label': 'Código CUPS Enviado', 'value': cups_code or 'No enviado'},
                    {'label': 'Descripción Enviada en el JSON', 'value': sent_name or 'No enviada'},
                    {'label': 'Descripción Oficial en Base de Datos (API_SM)', 'value': catalog_check['official_name'] if catalog_check else 'Sin código para validar'},
                    {'label': 'Fecha de la Solicitud', 'value': authored_on or 'No registrada'},
                    {'label': 'Indicaciones / Notas', 'value': notes or 'Sin notas'},
                ],
                'raw_resource': sreq,
            })

        # 2. Procedimientos Realizados (Procedure)
        for idx, proc in enumerate(procedures):
            c_info = _extract_coding_info(proc.get('code'))
            cups_code = c_info['code'].upper()
            sent_name = c_info['display'] or c_info['text']
            perf_date = _safe_str(proc.get('performedDateTime') or (proc.get('performedPeriod') or {}).get('start'))
            outcome_text = _extract_coding_info(proc.get('outcome'))['text']
            notes = '; '.join(_safe_str(n.get('text')) for n in (proc.get('note') or []) if isinstance(n, dict) and n.get('text'))

            catalog_check = None
            if cups_code:
                db_cups = cups_map.get(cups_code)
                is_valid = db_cups is not None
                catalog_check = {
                    'catalog': 'CUPS (Procedimientos Realizados)',
                    'code': cups_code,
                    'sent_name': sent_name,
                    'valid': is_valid,
                    'official_name': db_cups['descripcion'] if db_cups else 'Código CUPS NO existe en el catálogo oficial de API_SM',
                    'extra': f"Versión catálogo: {db_cups['version']}" if (db_cups and db_cups.get('version')) else '',
                }
                catalog_validation_items.append(catalog_check)

            explanation = (
                f"**Procedimiento Realizado (Procedure):** Código CUPS **{cups_code or 'SIN CÓDIGO'}** — "
                f"*{sent_name or 'Sin nombre'}* (Ejecutado el: **{perf_date or 'No indicado'}**)."
            )
            narratives.append(explanation)

            items.append({
                'title': f"⚡ Procedimiento Realizado: {cups_code} — {sent_name}",
                'subtitle': 'Procedimiento Ejecutado Durante la Atención (Procedure)',
                'badge': 'CUPS Válido' if (catalog_check and catalog_check['valid']) else ('CUPS No Encontrado' if catalog_check else 'Ejecutado'),
                'badge_type': 'success' if (catalog_check and catalog_check['valid']) else ('danger' if catalog_check else 'primary'),
                'explanation': explanation,
                'catalog_check': catalog_check,
                'fields': [
                    {'label': 'Tipo de Registro', 'value': 'Procedimiento Realizado (Procedure)'},
                    {'label': 'Código CUPS Enviado', 'value': cups_code or 'No enviado'},
                    {'label': 'Descripción Enviada en el JSON', 'value': sent_name or 'No enviada'},
                    {'label': 'Descripción Oficial en Base de Datos (API_SM)', 'value': catalog_check['official_name'] if catalog_check else 'Sin código para validar'},
                    {'label': 'Fecha de Ejecución', 'value': perf_date or 'No registrada'},
                    {'label': 'Resultado / Notas del Procedimiento', 'value': outcome_text or notes or 'Sin notas'},
                ],
                'raw_resource': proc,
            })

        return {
            'id': 'solicitudes_procedimientos',
            'title': '7. Solicitudes / Órdenes y Procedimientos Realizados (CUPS)',
            'fa_icon': 'fas fa-notes-medical',
            'color': 'primary',
            'count': len(items),
            'narrative': ' '.join(narratives) if narratives else 'No se registraron órdenes de procedimientos (ServiceRequest) ni procedimientos ejecutados (Procedure) en este Bundle.',
            'items': items,
        }

    @classmethod
    def _build_allergies_family_observations_module(
        cls,
        allergies: List[Dict[str, Any]],
        family_histories: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
        risks: List[Dict[str, Any]],
        documents: List[Dict[str, Any]],
        cie10_map: Dict[str, Dict[str, str]],
        catalog_validation_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        items = []
        narratives = []

        # Alergias
        for alg in allergies:
            code_info = _extract_coding_info(alg.get('code'))
            clin_status = _extract_coding_info(alg.get('clinicalStatus'))['text'] or 'Activa'
            categories = ', '.join(_safe_str(c) for c in (alg.get('category') or []) if c) or 'Alergia / Intolerancia'
            explanation = f"**Alergia / Intolerancia:** Sustancia o agente **{code_info['text'] or 'No especificado'}** (Categoría: {categories}, Estado: {clin_status})."
            narratives.append(explanation)
            items.append({
                'title': f"⚠️ Alergia: {code_info['text'] or 'Sustancia no especificada'}",
                'subtitle': 'Alergia o Intolerancia del Paciente (AllergyIntolerance)',
                'badge': 'Alergia',
                'badge_type': 'danger',
                'explanation': explanation,
                'fields': [
                    {'label': 'Sustancia / Alérgeno', 'value': code_info['text'] or 'No especificado'},
                    {'label': 'Categoría / Tipo', 'value': categories},
                    {'label': 'Estado Clínico', 'value': clin_status},
                ],
                'raw_resource': alg,
            })

        # Antecedentes Familiares
        for fam in family_histories:
            rel_info = _extract_coding_info(fam.get('relationship'))
            for cond in fam.get('condition') or []:
                if not isinstance(cond, dict):
                    continue
                c_info = _extract_coding_info(cond.get('code'))
                cie_code = c_info['code'].upper()
                sent_name = c_info['display'] or c_info['text']
                catalog_check = None
                if cie_code:
                    db_cie = cie10_map.get(cie_code)
                    catalog_check = {
                        'catalog': 'CIE-10 (Antecedente Familiar)',
                        'code': cie_code,
                        'sent_name': sent_name,
                        'valid': db_cie is not None,
                        'official_name': db_cie['descripcion'] if db_cie else 'Código CIE-10 NO existe en el catálogo oficial de API_SM',
                        'extra': '',
                    }
                    catalog_validation_items.append(catalog_check)

                explanation = f"**Antecedente Familiar ({rel_info['text'] or 'Familiar'}):** {cie_code} — *{sent_name}*."
                narratives.append(explanation)
                items.append({
                    'title': f"👪 Familiar ({rel_info['text'] or 'Parentesco'}): {cie_code} — {sent_name}",
                    'subtitle': 'Antecedente Familiar (FamilyMemberHistory)',
                    'badge': 'CIE-10 Válido' if (catalog_check and catalog_check['valid']) else 'Antecedente Familiar',
                    'badge_type': 'success' if (catalog_check and catalog_check['valid']) else 'info',
                    'explanation': explanation,
                    'catalog_check': catalog_check,
                    'fields': [
                        {'label': 'Parentesco Familiar', 'value': rel_info['text'] or 'No especificado'},
                        {'label': 'Diagnóstico CIE-10', 'value': f"{cie_code} - {sent_name}"},
                        {'label': 'Nombre Oficial en BD (API_SM)', 'value': catalog_check['official_name'] if catalog_check else 'N/A'},
                    ],
                    'raw_resource': fam,
                })

        # Observaciones / Signos Vitales / Antropometría
        for obs in observations:
            code_info = _extract_coding_info(obs.get('code'))
            val_str = ''
            if 'valueQuantity' in obs and isinstance(obs['valueQuantity'], dict):
                vq = obs['valueQuantity']
                val_str = f"{vq.get('value')} {_safe_str(vq.get('unit') or vq.get('code'))}".strip()
            elif 'valueString' in obs:
                val_str = _safe_str(obs.get('valueString'))
            elif 'valueCodeableConcept' in obs:
                val_str = _extract_coding_info(obs.get('valueCodeableConcept'))['text']

            explanation = f"**Medición / Observación ({code_info['text'] or 'Hallazgo'}):** Valor registrado = **{val_str or 'Ver componentes'}**."
            narratives.append(explanation)
            items.append({
                'title': f"📊 Observación: {code_info['text'] or 'Medición Clínica'}",
                'subtitle': f"Resultado: {val_str or 'Registrado'}",
                'badge': 'Observación / Medición',
                'badge_type': 'secondary',
                'explanation': explanation,
                'fields': [
                    {'label': 'Concepto Evaluado (LOINC / SNOMED)', 'value': code_info['text'] or 'No especificado'},
                    {'label': 'Valor / Resultado', 'value': val_str or 'Registrado en componentes'},
                    {'label': 'Fecha de Medición', 'value': _safe_str(obs.get('effectiveDateTime')) or 'No especificada'},
                ],
                'raw_resource': obs,
            })

        # Factores de Riesgo y Documentos Adjuntos (Incapacidad, etc.)
        for rsk in risks:
            pred = (rsk.get('prediction') or [{}])[0]
            outcome = _extract_coding_info(pred.get('outcome'))['text'] or _extract_coding_info(rsk.get('code'))['text'] or 'Factor de riesgo evaluado'
            explanation = f"**Factor de Riesgo (RiskAssessment):** {outcome}."
            narratives.append(explanation)
            items.append({
                'title': f"🛡️ Factor de Riesgo: {outcome}",
                'subtitle': 'Evaluación de Riesgo (RiskAssessment)',
                'badge': 'Factor de Riesgo',
                'badge_type': 'warning',
                'explanation': explanation,
                'fields': [{'label': 'Riesgo Evaluado', 'value': outcome}],
                'raw_resource': rsk,
            })

        for doc in documents:
            doc_type = _extract_coding_info(doc.get('type'))['text'] or _safe_str(doc.get('description')) or 'Documento Clínico / Incapacidad'
            explanation = f"**Documento Adjunto / Soporte (DocumentReference):** {doc_type}."
            narratives.append(explanation)
            items.append({
                'title': f"📎 Documento / Soporte: {doc_type}",
                'subtitle': 'Referencia Documental (DocumentReference)',
                'badge': 'Documento',
                'badge_type': 'info',
                'explanation': explanation,
                'fields': [{'label': 'Tipo de Documento', 'value': doc_type}],
                'raw_resource': doc,
            })

        return {
            'id': 'alergias_familiares_otros',
            'title': '8. Alergias, Antecedentes Familiares, Signos Vitales y Otros',
            'fa_icon': 'fas fa-heartbeat',
            'color': 'danger',
            'count': len(items),
            'narrative': ' '.join(narratives) if narratives else 'No se registraron alergias, antecedentes familiares, mediciones u otros anexos en este Bundle.',
            'items': items,
        }

    @classmethod
    def _build_plain_text_report(
        cls,
        header_mod: Dict[str, Any],
        modules: List[Dict[str, Any]],
        catalog_validations: List[Dict[str, Any]],
        structural_warnings: List[str],
    ) -> str:
        lines = [
            "======================================================================",
            " REPORTE DE INSPECCIÓN Y TRADUCCIÓN FHIR (RESOLUCIÓN 1888 / IHCE)",
            " Generado por API_SM",
            "======================================================================",
            f"Tipo de Documento : {header_mod.get('rda_type_label')}",
            f"Fecha Generación  : {header_mod.get('rda_date')}",
            "",
        ]

        if structural_warnings:
            lines.append("⚠️ ALERTAS DE ESTRUCTURA FHIR:")
            for w in structural_warnings:
                lines.append(f"  - {w}")
            lines.append("")

        if catalog_validations:
            lines.append("🔍 VALIDACIÓN CONTRA CATÁLOGOS OFICIALES (SISPRO - API_SM):")
            for cv in catalog_validations:
                icon = "✅ VÁLIDO" if cv['valid'] else "❌ NO ENCONTRADO"
                lines.append(
                    f"  - [{cv['catalog']}] Código {cv['code']}: {icon} | Enviado: '{cv['sent_name']}' -> Oficial BD: '{cv['official_name']}'"
                )
            lines.append("")

        lines.append("📋 DESGLOSE EN LENGUAJE CLARO POR MÓDULOS:")
        for mod in modules:
            lines.append(f"\n--- {mod['title']} ({mod['count']} registro(s)) ---")
            lines.append(mod['narrative'].replace('**', '').replace('*', ''))

        return "\n".join(lines)

    @classmethod
    def get_sample_bundle(cls) -> Dict[str, Any]:
        """Devuelve un Bundle FHIR de ejemplo (Resolución 1888) generado desde el backend Python."""
        return {
            'resourceType': 'Bundle',
            'id': 'bundle-rda-consulta-1888',
            'type': 'document',
            'timestamp': '2026-10-19T14:35:00-05:00',
            'entry': [
                {
                    'fullUrl': '#Composition-0',
                    'resource': {
                        'resourceType': 'Composition',
                        'id': 'Composition-0',
                        'status': 'final',
                        'type': {
                            'coding': [
                                {
                                    'system': 'http://loinc.org',
                                    'code': '34108-1',
                                    'display': 'Outpatient Note - RDA Consulta Externa',
                                }
                            ]
                        },
                        'subject': {'reference': '#Patient-0'},
                        'encounter': {'reference': '#Encounter-0'},
                        'date': '2026-10-19T14:35:00-05:00',
                        'author': [{'reference': '#Practitioner-0'}],
                        'title': 'Resumen Digital de Atención (RDA) - Consulta Externa',
                        'custodian': {'reference': '#Organization-IPS'},
                        'section': [
                            {
                                'title': 'Diagnósticos de la Atención',
                                'code': {'coding': [{'code': '29548-5', 'display': 'Diagnosis'}]},
                                'entry': [
                                    {'reference': '#Condition-Principal'},
                                    {'reference': '#Condition-Relacionado'},
                                ],
                            },
                            {
                                'title': 'Medicamentos Prescritos (Fórmula Médica)',
                                'code': {'coding': [{'code': '10160-0', 'display': 'History of Medication use'}]},
                                'entry': [
                                    {'reference': '#MedicationRequest-0'},
                                    {'reference': '#MedicationStatement-0'},
                                ],
                            },
                            {
                                'title': 'Procedimientos y Órdenes Médicas',
                                'code': {'coding': [{'code': '47519-4', 'display': 'History of Procedures'}]},
                                'entry': [
                                    {'reference': '#ServiceRequest-0'},
                                    {'reference': '#Procedure-0'},
                                ],
                            },
                            {
                                'title': 'Alergias, Antecedentes Familiares y Signos Vitales',
                                'code': {'coding': [{'code': '48765-2', 'display': 'Allergies and adverse reactions'}]},
                                'entry': [
                                    {'reference': '#AllergyIntolerance-0'},
                                    {'reference': '#FamilyMemberHistory-0'},
                                    {'reference': '#Observation-Peso'},
                                ],
                            },
                        ],
                    },
                },
                {
                    'fullUrl': '#Patient-0',
                    'resource': {
                        'resourceType': 'Patient',
                        'id': 'Patient-0',
                        'identifier': [
                            {
                                'type': {
                                    'coding': [
                                        {
                                            'system': 'https://fhir.minsalud.gov.co/rda/CodeSystem/ColombianPersonIdentifier',
                                            'code': 'CC',
                                            'display': 'Cédula de Ciudadanía',
                                        }
                                    ]
                                },
                                'value': '1020456789',
                            }
                        ],
                        'name': [
                            {
                                'use': 'official',
                                'family': 'GÓMEZ PÉREZ',
                                '_family': {
                                    'extension': [
                                        {
                                            'url': 'http://hl7.org/fhir/StructureDefinition/humanname-fathers-family',
                                            'valueString': 'GÓMEZ',
                                        },
                                        {
                                            'url': 'http://hl7.org/fhir/StructureDefinition/humanname-mothers-family',
                                            'valueString': 'PÉREZ',
                                        },
                                    ]
                                },
                                'given': ['CARLOS', 'ANDRÉS'],
                            }
                        ],
                        'gender': 'male',
                        'birthDate': '1988-04-12',
                        'extension': [
                            {
                                'url': 'https://fhir.minsalud.gov.co/rda/StructureDefinition/ExtensionBiologicalSex',
                                'valueCoding': {'code': '01', 'display': '01 - Hombre'},
                            },
                            {
                                'url': 'https://fhir.minsalud.gov.co/rda/StructureDefinition/ExtensionOccupation',
                                'valueCoding': {'code': '2512', 'display': '2512 - Desarrolladores de software'},
                            },
                        ],
                        'address': [
                            {
                                'text': 'Calle 100 # 15-20',
                                'city': 'BOGOTÁ, D.C.',
                                'state': 'BOGOTÁ, D.C.',
                                '_city': {
                                    'extension': [
                                        {
                                            'url': 'https://fhir.minsalud.gov.co/rda/StructureDefinition/DivipolaMunicipality',
                                            'valueCode': '11001',
                                        }
                                    ]
                                },
                                'extension': [
                                    {
                                        'url': 'https://fhir.minsalud.gov.co/rda/StructureDefinition/AddressZone',
                                        'valueCode': '01',
                                    }
                                ],
                            }
                        ],
                    },
                },
                {
                    'fullUrl': '#Organization-IPS',
                    'resource': {
                        'resourceType': 'Organization',
                        'id': 'Organization-IPS',
                        'name': 'CLÍNICA INTEGRAL DEL ORIENTE S.A.S.',
                        'identifier': [
                            {'type': {'coding': [{'code': 'NIT', 'display': 'NIT'}]}, 'value': '900123456-7'},
                            {
                                'type': {'coding': [{'code': 'REPS', 'display': 'Código Habilitación REPS'}]},
                                'value': '110010123401',
                            },
                        ],
                    },
                },
                {
                    'fullUrl': '#Organization-EPS',
                    'resource': {
                        'resourceType': 'Organization',
                        'id': 'Organization-EPS',
                        'name': 'EPS SANITAS S.A.S.',
                        'identifier': [
                            {
                                'type': {'coding': [{'code': 'EAPB', 'display': 'Código Administradora EAPB'}]},
                                'value': 'EPS005',
                            },
                            {'type': {'coding': [{'code': 'NIT', 'display': 'NIT'}]}, 'value': '800251440'},
                        ],
                    },
                },
                {
                    'fullUrl': '#Practitioner-0',
                    'resource': {
                        'resourceType': 'Practitioner',
                        'id': 'Practitioner-0',
                        'identifier': [{'type': {'coding': [{'code': 'CC'}]}, 'value': '79888999'}],
                        'name': [{'given': ['LAURA', 'MARCELA'], 'family': 'RODRÍGUEZ VARGAS'}],
                    },
                },
                {
                    'fullUrl': '#Encounter-0',
                    'resource': {
                        'resourceType': 'Encounter',
                        'id': 'Encounter-0',
                        'status': 'finished',
                        'class': {'code': 'AMB', 'display': 'Intramural / Ambulatorio'},
                        'serviceType': {'coding': [{'code': '01', 'display': 'Consulta Externa General'}]},
                        'subject': {'reference': '#Patient-0'},
                        'period': {
                            'start': '2026-10-19T14:00:00-05:00',
                            'end': '2026-10-19T14:30:00-05:00',
                        },
                        'reasonCode': [{'coding': [{'code': '38', 'display': 'Enfermedad general'}]}],
                        'diagnosis': [
                            {
                                'condition': {'reference': '#Condition-Principal'},
                                'use': {'coding': [{'code': 'AD', 'display': 'Diagnóstico Principal de Atención'}]},
                                'rank': 1,
                            },
                            {
                                'condition': {'reference': '#Condition-Relacionado'},
                                'use': {'coding': [{'code': 'DD', 'display': 'Diagnóstico Relacionado'}]},
                                'rank': 2,
                            },
                        ],
                        'hospitalization': {
                            'dischargeDisposition': {
                                'coding': [{'code': '01', 'display': 'Alta médica ambulatoria (Vivo)'}]
                            }
                        },
                    },
                },
                {
                    'fullUrl': '#Condition-Principal',
                    'resource': {
                        'resourceType': 'Condition',
                        'id': 'Condition-Principal',
                        'clinicalStatus': {'coding': [{'code': 'active', 'display': 'Activo'}]},
                        'verificationStatus': {'coding': [{'code': 'confirmed', 'display': 'Confirmado Nuevo'}]},
                        'code': {
                            'coding': [
                                {
                                    'system': 'http://hl7.org/fhir/sid/icd-10',
                                    'code': 'J00X',
                                    'display': 'RINOFARINGITIS AGUDA (RESFRIADO COMUN)',
                                }
                            ]
                        },
                        'subject': {'reference': '#Patient-0'},
                    },
                },
                {
                    'fullUrl': '#Condition-Relacionado',
                    'resource': {
                        'resourceType': 'Condition',
                        'id': 'Condition-Relacionado',
                        'clinicalStatus': {'coding': [{'code': 'active', 'display': 'Activo'}]},
                        'verificationStatus': {'coding': [{'code': 'provisional', 'display': 'Impresión Diagnóstica'}]},
                        'code': {
                            'coding': [
                                {
                                    'system': 'http://hl7.org/fhir/sid/icd-10',
                                    'code': 'I10X',
                                    'display': 'HIPERTENSION ESENCIAL (PRIMARIA)',
                                }
                            ]
                        },
                        'subject': {'reference': '#Patient-0'},
                    },
                },
                {
                    'fullUrl': '#MedicationRequest-0',
                    'resource': {
                        'resourceType': 'MedicationRequest',
                        'id': 'MedicationRequest-0',
                        'status': 'active',
                        'intent': 'order',
                        'medicationCodeableConcept': {
                            'coding': [
                                {
                                    'system': 'https://fhir.minsalud.gov.co/rda/CodeSystem/ColombianMedicationIUM',
                                    'code': '10002345601',
                                    'display': 'ACETAMINOFÉN 500 MG TABLETA',
                                },
                                {
                                    'system': 'http://www.whocc.no/atc',
                                    'code': 'N02BE01',
                                    'display': 'PARACETAMOL (DCI)',
                                },
                            ]
                        },
                        'subject': {'reference': '#Patient-0'},
                        'encounter': {'reference': '#Encounter-0'},
                        'reasonReference': [{'reference': '#Condition-Principal'}],
                        'dosageInstruction': [
                            {
                                'text': 'Tomar 1 tableta de 500 mg vía oral cada 8 horas por 5 días si hay fiebre o dolor.',
                                'route': {'coding': [{'code': '048', 'display': 'Oral (Vía Oral)'}]},
                                'timing': {
                                    'repeat': {
                                        'frequency': 1,
                                        'period': 8,
                                        'periodUnit': 'h',
                                        'boundsDuration': {'value': 5, 'unit': 'd', 'code': 'd'},
                                    }
                                },
                                'doseAndRate': [{'doseQuantity': {'value': 500, 'unit': 'mg', 'code': 'mg'}}],
                            }
                        ],
                        'dispenseRequest': {'quantity': {'value': 15, 'unit': 'TABLETA', 'code': 'TAB'}},
                    },
                },
                {
                    'fullUrl': '#MedicationStatement-0',
                    'resource': {
                        'resourceType': 'MedicationStatement',
                        'id': 'MedicationStatement-0',
                        'status': 'active',
                        'medicationCodeableConcept': {
                            'coding': [
                                {
                                    'system': 'https://fhir.minsalud.gov.co/rda/CodeSystem/ColombianMedicationCUM',
                                    'code': '19912345-01',
                                    'display': 'LOSARTÁN POTÁSICO 50 MG TABLETA',
                                }
                            ]
                        },
                        'subject': {'reference': '#Patient-0'},
                        'dosage': [{'text': '1 tableta de 50 mg cada 24 horas en la mañana (Tratamiento crónico HTA)'}],
                    },
                },
                {
                    'fullUrl': '#ServiceRequest-0',
                    'resource': {
                        'resourceType': 'ServiceRequest',
                        'id': 'ServiceRequest-0',
                        'status': 'active',
                        'intent': 'order',
                        'code': {
                            'coding': [
                                {
                                    'system': 'https://fhir.minsalud.gov.co/rda/CodeSystem/CUPS',
                                    'code': '902210',
                                    'display': 'HEMOGRAMA IV AUTOMATIZADO',
                                }
                            ]
                        },
                        'subject': {'reference': '#Patient-0'},
                        'authoredOn': '2026-10-19T14:25:00-05:00',
                        'note': [{'text': 'Control de cuadro hemático ambulatorio.'}],
                    },
                },
                {
                    'fullUrl': '#Procedure-0',
                    'resource': {
                        'resourceType': 'Procedure',
                        'id': 'Procedure-0',
                        'status': 'completed',
                        'code': {
                            'coding': [
                                {
                                    'system': 'https://fhir.minsalud.gov.co/rda/CodeSystem/CUPS',
                                    'code': '890201',
                                    'display': 'CONSULTA DE PRIMERA VEZ POR MEDICINA GENERAL',
                                }
                            ]
                        },
                        'subject': {'reference': '#Patient-0'},
                        'performedDateTime': '2026-10-19T14:15:00-05:00',
                        'note': [{'text': 'Consulta médica general realizada sin complicaciones.'}],
                    },
                },
                {
                    'fullUrl': '#AllergyIntolerance-0',
                    'resource': {
                        'resourceType': 'AllergyIntolerance',
                        'id': 'AllergyIntolerance-0',
                        'clinicalStatus': {'coding': [{'code': 'active', 'display': 'Activa'}]},
                        'category': ['medication'],
                        'code': {'coding': [{'code': 'PENICILINA', 'display': 'Alergia a Penicilina y derivados betalactámicos'}]},
                        'patient': {'reference': '#Patient-0'},
                    },
                },
                {
                    'fullUrl': '#FamilyMemberHistory-0',
                    'resource': {
                        'resourceType': 'FamilyMemberHistory',
                        'id': 'FamilyMemberHistory-0',
                        'status': 'completed',
                        'patient': {'reference': '#Patient-0'},
                        'relationship': {'coding': [{'code': 'FTH', 'display': 'Padre'}]},
                        'condition': [
                            {
                                'code': {
                                    'coding': [{'code': 'I10X', 'display': 'HIPERTENSION ESENCIAL (PRIMARIA)'}]
                                }
                            }
                        ],
                    },
                },
                {
                    'fullUrl': '#Observation-Peso',
                    'resource': {
                        'resourceType': 'Observation',
                        'id': 'Observation-Peso',
                        'status': 'final',
                        'code': {'coding': [{'system': 'http://loinc.org', 'code': '29463-7', 'display': 'Peso Corporal'}]},
                        'subject': {'reference': '#Patient-0'},
                        'effectiveDateTime': '2026-10-19T14:05:00-05:00',
                        'valueQuantity': {'value': 74.5, 'unit': 'kg', 'code': 'kg'},
                    },
                },
            ],
        }


"""
Validador de Apartados y Datos de Estructura Obligatorios para Bundles HL7 FHIR R4 (Resolución 1888 / IHCE Colombia).

Cuando en el software médico un código (CUPS de la consulta/procedimiento, CIE-10 del diagnóstico,
EAPB de la aseguradora, DANE del municipio, CIUO de la ocupación, DCI/IUM del medicamento, Modalidad,
Grupo de Servicios, Causa Externa, etc.) no es válido o está vacío, el generador FHIR NO construye
ese apartado dentro del JSON.

Este validador comprueba:
  1. Que SÍ estén presentes todos los APARTADOS OBLIGATORIOS según el tipo de RDA (avisando explícitamente:
     "🚨 ¡Falta este apartado obligatorio!").
  2. Que dentro de cada apartado estén construidos todos sus campos y códigos obligatorios.
"""

from typing import Any, Dict, List, Optional

from .fhir_primitives import (
    ALLERGY_CATEGORY_MAP,
    CLINICAL_STATUS_MAP,
    ENCOUNTER_STATUS_MAP,
    FAMILY_HISTORY_STATUS_MAP,
    GENDER_MAP,
    MED_STATEMENT_STATUS_MAP,
    RISK_STATUS_MAP,
    VERIFICATION_STATUS_MAP,
    ZONA_MAP,
    _extract_all_codings,
    _extract_coding_info,
    _extract_extension_value,
    _find_extension,
    _safe_str,
)

COLOMBIAN_DOC_CODES = {
    'CC', 'TI', 'CE', 'DE', 'PA', 'RC', 'MS', 'AS', 'CN', 'PE', 'PT', 'SC', 'CD', 'SI', 'NIT'
}


def validate_mandatory_fhir_structure(
    bundle: Dict[str, Any],
    composition: Optional[Dict[str, Any]],
    resources_by_type: Dict[str, List[Dict[str, Any]]],
    resource_index: Dict[str, Dict[str, Any]],
    rda_type_label: str,
) -> Dict[str, Any]:
    """
    Evalúa que todos los apartados y campos obligatorios según el tipo de RDA (Res. 1888) existan en el FHIR.
    Retorna:
      - checks: Lista de validaciones [{module, module_id, resource, field, value, status, valid, is_section_missing}]
      - passed_count: Cantidad de apartados/datos obligatorios presentes
      - failed_count: Cantidad de apartados/datos obligatorios faltantes
      - empty_sections_count: Cantidad de secciones opcionales en 0
      - alerts: Lista de alertas explícitas de apartados o datos obligatorios faltantes
      - module_missing_alerts: Dict[module_id, List[str]] para pintar en rojo los módulos a los que les falte un apartado obligatorio
    """
    checks: List[Dict[str, Any]] = []
    alerts: List[str] = []
    module_missing_alerts: Dict[str, List[str]] = {}

    def add_check(
        module_id: str,
        module_name: str,
        resource_label: str,
        field_label: str,
        built_value: str,
        is_valid: bool,
        missing_reason: str = 'El sistema no construyó este apartado en el FHIR porque el código o dato en origen es inválido o está vacío.',
        status_override: Optional[str] = None,
        is_entire_apartado: bool = False,
    ) -> None:
        status_code = status_override or ('ok' if is_valid else 'missing')
        prefix = '🚨 ¡FALTA ESTE APARTADO OBLIGATORIO!' if is_entire_apartado else '❌ FALTA DATO OBLIGATORIO:'
        display_val = built_value if is_valid else f"{prefix} {missing_reason}"
        checks.append({
            'module_id': module_id,
            'module': module_name,
            'resource': resource_label,
            'field': field_label,
            'value': display_val,
            'valid': is_valid,
            'status': status_code,
            'is_apartado': is_entire_apartado,
        })
        if not is_valid and status_code == 'missing':
            alert_text = (
                f"🚨 ¡Falta apartado obligatorio en {module_name}!: '{field_label}' ({resource_label}) — {missing_reason}"
                if is_entire_apartado
                else f"❌ Falta dato obligatorio en {module_name} ({resource_label}): '{field_label}' — {missing_reason}"
            )
            alerts.append(alert_text)
            module_missing_alerts.setdefault(module_id, []).append(alert_text)

    rda_low = rda_type_label.lower()
    is_patient_rda = 'paciente' in rda_low or 'antecedente' in rda_low
    is_consulta_rda = 'consulta' in rda_low or 'ambulator' in rda_low or 'externa' in rda_low
    is_urg_rda = 'urgencia' in rda_low
    is_hosp_rda = 'hospitalizaci' in rda_low
    is_encounter_rda = is_consulta_rda or is_urg_rda or is_hosp_rda or (not is_patient_rda)
    is_urg_or_hosp = is_urg_rda or is_hosp_rda

    # =========================================================================
    # 1. APARTADO: ENCABEZADO DEL DOCUMENTO (Bundle / Composition)
    # =========================================================================
    mod_1_id = 'encabezado'
    mod_1 = '1. Encabezado (Composition)'
    bundle_type = _safe_str(bundle.get('type'))
    add_check(
        mod_1_id,
        mod_1,
        'Bundle',
        'Tipo de Bundle FHIR (Bundle.type)',
        bundle_type,
        bundle_type.lower() in ('document', 'collection', 'transaction'),
        'El JSON no tiene la propiedad obligatoria "type": "document".',
    )

    if not composition:
        add_check(
            mod_1_id,
            mod_1,
            'Composition',
            'Apartado Encabezado del RDA (Composition)',
            '',
            False,
            'No existe el apartado Composition en el Bundle FHIR. Todo RDA de la Resolución 1888 debe iniciar con este apartado.',
            is_entire_apartado=True,
        )
    else:
        comp_status = _safe_str(composition.get('status'))
        add_check(
            mod_1_id,
            mod_1,
            'Composition',
            'Estado del Documento (Composition.status)',
            comp_status.upper(),
            bool(comp_status),
            'No se construyó Composition.status.',
        )

        comp_type_info = _extract_coding_info(composition.get('type'))
        add_check(
            mod_1_id,
            mod_1,
            'Composition',
            'Código LOINC del Tipo de RDA (Composition.type.coding)',
            comp_type_info['text'],
            bool(comp_type_info['code']),
            'No se construyó el código LOINC del tipo de RDA en Composition.type.',
        )

        comp_date = _safe_str(composition.get('date'))
        add_check(
            mod_1_id,
            mod_1,
            'Composition',
            'Fecha de Generación del RDA (Composition.date)',
            comp_date,
            bool(comp_date),
            'No se construyó la fecha de generación en Composition.date.',
        )

        subj_ref = _safe_str((composition.get('subject') or {}).get('reference'))
        subj_exists = bool(subj_ref) and (
            subj_ref in resource_index or subj_ref.lstrip('#').split('/')[-1] in resource_index
        )
        add_check(
            mod_1_id,
            mod_1,
            'Composition',
            'Referencia al Apartado Paciente (Composition.subject)',
            subj_ref,
            subj_exists,
            'Composition.subject está vacío o el apartado Patient referenciado no existe en entry[].',
        )

        authors = composition.get('author') or []
        author_ref = _safe_str((authors[0] if authors and isinstance(authors[0], dict) else {}).get('reference'))
        author_exists = bool(author_ref) and (
            author_ref in resource_index or author_ref.lstrip('#').split('/')[-1] in resource_index
        )
        add_check(
            mod_1_id,
            mod_1,
            'Composition',
            'Referencia al Apartado Profesional Autor (Composition.author)',
            author_ref,
            author_exists,
            'Composition.author está vacío o el apartado Practitioner referenciado no existe en entry[].',
        )

        cust_ref = _safe_str((composition.get('custodian') or {}).get('reference'))
        cust_exists = bool(cust_ref) and (
            cust_ref in resource_index or cust_ref.lstrip('#').split('/')[-1] in resource_index
        )
        add_check(
            mod_1_id,
            mod_1,
            'Composition',
            'Referencia al Apartado IPS Custodio (Composition.custodian)',
            cust_ref,
            cust_exists,
            'Composition.custodian está vacío o el apartado Organization (IPS) no existe en entry[].',
        )

    # =========================================================================
    # 2. APARTADO: DATOS DEL PACIENTE (Patient)
    # =========================================================================
    mod_2_id = 'paciente'
    mod_2 = '2. Datos del Paciente (Patient)'
    patients = resources_by_type.get('Patient', [])
    if not patients:
        add_check(
            mod_2_id,
            mod_2,
            'Patient',
            'Apartado Paciente (Patient)',
            '',
            False,
            'No se construyó el apartado obligatorio Patient en el Bundle FHIR.',
            is_entire_apartado=True,
        )
    else:
        for idx, pat in enumerate(patients):
            p_label = f"Patient #{idx + 1}" if len(patients) > 1 else 'Patient'
            idents = pat.get('identifier') or []
            col_doc_code = ''
            col_doc_display = ''
            any_doc_code = ''
            doc_value = ''
            doc_country = ''

            for ident in idents:
                if not isinstance(ident, dict):
                    continue
                val = _safe_str(ident.get('value'))
                if val and not doc_value:
                    doc_value = val
                codings = _extract_all_codings(ident.get('type'))
                for c in codings:
                    c_code = c['code'].upper()
                    c_sys = c['system'].lower()
                    if not any_doc_code and c_code:
                        any_doc_code = c_code
                    if (
                        'colombianpersonidentifier' in c_sys
                        or 'minsalud.gov.co' in c_sys
                        or c_code in COLOMBIAN_DOC_CODES
                    ):
                        col_doc_code = c_code
                        col_doc_display = c['display']
                        break
                c_ext = (
                    _find_extension(ident.get('extension'), 'divipolaCountry')
                    or _find_extension(ident.get('extension'), 'country')
                    or _find_extension(ident.get('extension'), 'pais')
                )
                if c_ext and not doc_country:
                    doc_country = _extract_extension_value(c_ext)

            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Apartado Tipo de Documento Colombiano (ColombianPersonIdentifier)',
                f"{col_doc_code} ({col_doc_display})" if col_doc_display else col_doc_code,
                bool(col_doc_code),
                (
                    f"Solo se encontró '{any_doc_code}' (HL7 v2-0203) pero NO se construyó el apartado del tipo de documento colombiano (CC, TI, CE, DE, PA, RC, PT, etc.)."
                    if any_doc_code
                    else 'No se construyó el apartado de tipo de documento en Patient.identifier[].type.coding.'
                ),
                is_entire_apartado=True,
            )

            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Número de Identificación (Patient.identifier.value)',
                doc_value,
                bool(doc_value),
                'No se construyó el número de documento del paciente.',
            )

            names = pat.get('name') or []
            n0 = names[0] if (isinstance(names, list) and names and isinstance(names[0], dict)) else {}
            givens = [_safe_str(g) for g in (n0.get('given') or []) if _safe_str(g)]
            first_name = givens[0] if givens else ''
            fam_ext = (n0.get('_family') or {}).get('extension') or []
            father_surname = (
                _extract_extension_value(_find_extension(fam_ext, 'fathersFamily'))
                or _extract_extension_value(_find_extension(fam_ext, 'primerApellido'))
                or _safe_str(n0.get('family'))
            )

            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Primer Apellido (fathersFamily / family)',
                father_surname,
                bool(father_surname),
                'No se construyó el primer apellido del paciente en Patient.name.',
            )

            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Primer Nombre (Patient.name.given[0])',
                first_name,
                bool(first_name),
                'No se construyó el primer nombre del paciente en Patient.name.given.',
            )

            birth_date = _safe_str(pat.get('birthDate'))
            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Fecha de Nacimiento (Patient.birthDate)',
                birth_date,
                bool(birth_date),
                'No se construyó la fecha de nacimiento en Patient.birthDate.',
            )

            exts = (pat.get('extension') or []) + ((pat.get('_gender') or {}).get('extension') or [])
            bio_sex = _extract_extension_value(
                _find_extension(exts, 'biologicalSex')
                or _find_extension(exts, 'biologicalGender')
                or _find_extension(exts, 'sexoBiologico')
            )
            gender_raw = _safe_str(pat.get('gender')).lower()
            gender_label = GENDER_MAP.get(gender_raw, gender_raw)
            sex_built = f"{bio_sex} (FHIR: {gender_label})" if (bio_sex and gender_label) else (bio_sex or gender_label)

            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Apartado Sexo Biológico / Género (biologicalSex / gender)',
                sex_built,
                bool(bio_sex or gender_raw),
                'No se construyó el apartado de sexo biológico ni género administrativo en Patient.',
            )

            nationality = _extract_extension_value(
                _find_extension(exts, 'nationality') or _find_extension(exts, 'nacionalidad')
            )
            country_built = nationality or doc_country
            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Apartado Nacionalidad / País (Nationality / divipolaCountry)',
                country_built,
                bool(country_built),
                'No se construyó el apartado de país/nacionalidad en Patient (el código ISO de país del paciente no es válido o está vacío).',
                is_entire_apartado=True,
            )

            addresses = pat.get('address') or []
            a0 = addresses[0] if (isinstance(addresses, list) and addresses and isinstance(addresses[0], dict)) else {}
            city_code = _extract_extension_value(
                _find_extension((a0.get('_city') or {}).get('extension'), 'divipolaMunicipality')
                or _find_extension(a0.get('extension'), 'municip')
            )
            city_name = _safe_str(a0.get('city'))
            city_built = f"{city_code} - {city_name}" if (city_code and city_name) else (city_code or city_name)

            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Apartado Municipio de Residencia DANE (divipolaMunicipality)',
                city_built,
                bool(city_built),
                'No se construyó el apartado de dirección/municipio DANE en Patient.address (el código DANE del municipio no es válido o está vacío en el paciente).',
                is_entire_apartado=True,
            )

            zone_raw = _extract_extension_value(
                _find_extension(a0.get('extension'), 'zone') or _find_extension(a0.get('extension'), 'zona')
            )
            zone_built = ZONA_MAP.get(zone_raw, zone_raw)
            add_check(
                mod_2_id,
                mod_2,
                p_label,
                'Apartado Zona Territorial de Residencia (AddressZone: Urbana/Rural)',
                zone_built,
                bool(zone_built),
                'No se construyó el apartado de zona residencial (01 Urbana / 02 Rural) en Patient.address.',
                is_entire_apartado=True,
            )

    # =========================================================================
    # 3. APARTADO: ENTIDADES — IPS PRESTADORA Y ASEGURADORA EPS (Organization)
    # =========================================================================
    mod_3_id = 'entidades'
    mod_3 = '3. Entidades: IPS y Aseguradora EPS (Organization)'
    orgs = resources_by_type.get('Organization', [])
    cust_id = _safe_str(((composition or {}).get('custodian') or {}).get('reference')).lstrip('#').split('/')[-1]

    ips_orgs = []
    eps_orgs = []
    for org in orgs:
        oid = _safe_str(org.get('id'))
        has_reps = False
        has_eapb = False
        for ident in org.get('identifier') or []:
            if not isinstance(ident, dict):
                continue
            t_code = _extract_coding_info(ident.get('type'))['code'].upper()
            sys_s = _safe_str(ident.get('system')).lower()
            if any(k in t_code or k in sys_s for k in ('REPS', 'PRESTADOR', 'PRN', 'PRV')):
                has_reps = True
            elif any(k in t_code or k in sys_s for k in ('EAPB', 'PAY', 'ADMINISTRADORA')):
                has_eapb = True

        if (oid and oid == cust_id) or (has_reps and not has_eapb):
            ips_orgs.append(org)
        else:
            eps_orgs.append(org)

    if not ips_orgs and orgs:
        ips_orgs.append(orgs[0])

    if not ips_orgs:
        add_check(
            mod_3_id,
            mod_3,
            'Organization (IPS)',
            'Apartado IPS Prestadora (Organization)',
            '',
            False,
            'No se construyó el apartado Organization de la IPS Prestadora.',
            is_entire_apartado=True,
        )
    else:
        ips = ips_orgs[0]
        ips_name = _safe_str(ips.get('name'))
        ips_nit = ''
        ips_reps = ''
        for ident in ips.get('identifier') or []:
            if not isinstance(ident, dict):
                continue
            val = _safe_str(ident.get('value'))
            t_code = _extract_coding_info(ident.get('type'))['code'].upper()
            sys_s = _safe_str(ident.get('system')).lower()
            if 'NIT' in t_code or 'TAX' in t_code or 'nit' in sys_s:
                ips_nit = val
            elif any(k in t_code or k in sys_s for k in ('REPS', 'PRESTADOR', 'PRN', 'PRV')) or (
                len(val) >= 10 and not ips_reps and val != ips_nit
            ):
                ips_reps = val

        add_check(
            mod_3_id,
            mod_3,
            'Organization (IPS)',
            'Nombre / Razón Social de la IPS (Organization.name)',
            ips_name,
            bool(ips_name),
            'No se construyó el nombre de la IPS en Organization.name.',
        )
        add_check(
            mod_3_id,
            mod_3,
            'Organization (IPS)',
            'Apartado NIT de la IPS Prestadora (identifier NIT)',
            ips_nit,
            bool(ips_nit),
            'No se construyó el apartado NIT de la IPS en Organization.identifier.',
            is_entire_apartado=True,
        )
        add_check(
            mod_3_id,
            mod_3,
            'Organization (IPS)',
            'Apartado Código de Habilitación REPS de la Sede (identifier REPS)',
            ips_reps,
            bool(ips_reps),
            'No se construyó el apartado del código de habilitación REPS de la IPS (verifique el código REPS en la Sede).',
            is_entire_apartado=True,
        )

    if is_encounter_rda or eps_orgs:
        if not eps_orgs:
            add_check(
                mod_3_id,
                mod_3,
                'Organization (EPS / EAPB)',
                'Apartado Aseguradora / Administradora EPS (Organization EAPB)',
                '',
                False,
                'No se construyó el apartado Organization de la Aseguradora/EPS en el FHIR porque el código EAPB de la administradora no es válido o está vacío.',
                is_entire_apartado=True,
            )
        else:
            for e_idx, eps in enumerate(eps_orgs):
                e_label = f"Organization (EPS #{e_idx + 1})" if len(eps_orgs) > 1 else 'Organization (EPS / EAPB)'
                eps_name = _safe_str(eps.get('name'))
                eapb_code = ''
                for ident in eps.get('identifier') or []:
                    if not isinstance(ident, dict):
                        continue
                    val = _safe_str(ident.get('value'))
                    t_code = _extract_coding_info(ident.get('type'))['code'].upper()
                    sys_s = _safe_str(ident.get('system')).lower()
                    if 'NIT' not in t_code and 'TAX' not in t_code and 'nit' not in sys_s and val:
                        eapb_code = val
                        break
                if not eapb_code:
                    oid = _safe_str(eps.get('id'))
                    if oid and len(oid) <= 8 and not oid.lower().startswith('organization'):
                        eapb_code = oid

                add_check(
                    mod_3_id,
                    mod_3,
                    e_label,
                    'Nombre de la Aseguradora / Administradora (EPS)',
                    eps_name,
                    bool(eps_name),
                    'No se construyó el nombre de la EPS en Organization.name.',
                )
                add_check(
                    mod_3_id,
                    mod_3,
                    e_label,
                    'Apartado Código EAPB de la Aseguradora (identifier EAPB)',
                    eapb_code,
                    bool(eapb_code),
                    'No se construyó el código EAPB de la aseguradora en Organization.identifier (código de administradora inválido o vacío).',
                    is_entire_apartado=True,
                )

    # =========================================================================
    # 4. APARTADO: ATENCIÓN / ENCUENTRO Y PROFESIONAL (Encounter / Practitioner)
    # =========================================================================
    mod_4_id = 'atencion'
    mod_4 = '4. Atención y Profesional (Encounter / Practitioner)'
    practitioners = resources_by_type.get('Practitioner', [])
    if not practitioners:
        add_check(
            mod_4_id,
            mod_4,
            'Practitioner',
            'Apartado Profesional de la Salud (Practitioner)',
            '',
            False,
            'No se construyó el apartado Practitioner (Profesional que atiende) porque los datos de documento del médico están incompletos o inválidos.',
            is_entire_apartado=True,
        )
    else:
        for p_idx, prac in enumerate(practitioners):
            pr_label = f"Practitioner #{p_idx + 1}" if len(practitioners) > 1 else 'Practitioner'
            pr_doc_type = ''
            pr_doc_num = ''
            for ident in prac.get('identifier') or []:
                if isinstance(ident, dict):
                    val = _safe_str(ident.get('value'))
                    t_info = _extract_coding_info(ident.get('type'))
                    if val and not pr_doc_num:
                        pr_doc_num = val
                        pr_doc_type = t_info['code']
            pr_names = prac.get('name') or []
            pn0 = pr_names[0] if (isinstance(pr_names, list) and pr_names and isinstance(pr_names[0], dict)) else {}
            pr_given = ' '.join(_safe_str(g) for g in (pn0.get('given') or []) if _safe_str(g))
            pr_family = _safe_str(pn0.get('family'))
            pr_full_name = f"{pr_given} {pr_family}".strip() or _safe_str(pn0.get('text'))

            add_check(
                mod_4_id,
                mod_4,
                pr_label,
                'Apartado Documento del Profesional (Practitioner.identifier)',
                f"{pr_doc_type}-{pr_doc_num}" if (pr_doc_type and pr_doc_num) else '',
                bool(pr_doc_type and pr_doc_num),
                'No se construyó el tipo o número de documento del profesional en Practitioner.identifier.',
                is_entire_apartado=True,
            )
            add_check(
                mod_4_id,
                mod_4,
                pr_label,
                'Nombres y Apellidos del Profesional (Practitioner.name)',
                pr_full_name,
                bool(pr_full_name),
                'No se construyó el nombre del profesional en Practitioner.name.',
            )

    encounters = resources_by_type.get('Encounter', [])
    if is_encounter_rda and not encounters:
        add_check(
            mod_4_id,
            mod_4,
            'Encounter',
            'Apartado Encuentro Clínico de la Atención (Encounter)',
            '',
            False,
            f"Este documento es un {rda_type_label}, pero NO se construyó el apartado obligatorio Encounter en el Bundle FHIR.",
            is_entire_apartado=True,
        )
    elif encounters:
        for e_idx, enc in enumerate(encounters):
            enc_label = f"Encounter #{e_idx + 1}" if len(encounters) > 1 else 'Encounter'
            enc_status = _safe_str(enc.get('status'))
            add_check(
                mod_4_id,
                mod_4,
                enc_label,
                'Estado de la Atención (Encounter.status)',
                ENCOUNTER_STATUS_MAP.get(enc_status.lower(), enc_status),
                bool(enc_status),
                'No se construyó el estado de la atención en Encounter.status.',
            )

            class_info = _extract_coding_info(enc.get('class'))
            service_type_info = _extract_coding_info(enc.get('serviceType'))
            modality_text = ''
            group_text = ''
            for t_obj in enc.get('type') or []:
                t_info = _extract_coding_info(t_obj)
                sys_l = t_info['system'].lower()
                if 'modality' in sys_l or 'modalidad' in sys_l:
                    modality_text = t_info['text']
                elif 'gruposervicio' in sys_l or 'servicegroup' in sys_l:
                    group_text = t_info['text']

            exts = enc.get('extension') or []
            if not group_text:
                group_text = _extract_extension_value(
                    _find_extension(exts, 'serviceGroup') or _find_extension(exts, 'grupoServicio')
                )

            modality_built = modality_text or class_info['text']
            group_built = group_text or service_type_info['text']

            add_check(
                mod_4_id,
                mod_4,
                enc_label,
                'Apartado Modalidad de Atención (Encounter.class / type)',
                modality_built,
                bool(modality_built),
                'No se construyó el apartado de Modalidad de Atención en Encounter (código de modalidad inválido o vacío).',
                is_entire_apartado=True,
            )
            add_check(
                mod_4_id,
                mod_4,
                enc_label,
                'Apartado Grupo / Tipo de Servicio (Encounter.serviceType / type)',
                group_built,
                bool(group_built),
                'No se construyó el apartado de Grupo o Tipo de Servicio en Encounter (código de grupo de servicios inválido o vacío).',
                is_entire_apartado=True,
            )

            period = enc.get('period') or {}
            start_dt = _safe_str(period.get('start'))
            end_dt = _safe_str(period.get('end'))
            add_check(
                mod_4_id,
                mod_4,
                enc_label,
                'Fecha y Hora de Inicio de Atención (Encounter.period.start)',
                start_dt,
                bool(start_dt),
                'No se construyó la fecha/hora de inicio en Encounter.period.start.',
            )
            add_check(
                mod_4_id,
                mod_4,
                enc_label,
                'Fecha y Hora de Fin / Egreso (Encounter.period.end)',
                end_dt,
                bool(end_dt),
                'No se construyó la fecha/hora de finalización en Encounter.period.end.',
            )

            reasons = [
                _extract_coding_info(r)['text']
                for r in (enc.get('reasonCode') or [])
                if _extract_coding_info(r)['code'] or _extract_coding_info(r)['text']
            ]
            reason_built = ', '.join(reasons)
            add_check(
                mod_4_id,
                mod_4,
                enc_label,
                'Apartado Causa que Motiva la Atención (Encounter.reasonCode)',
                reason_built,
                bool(reason_built),
                'No se construyó el apartado de Causa Externa / Motivo de Atención en Encounter.reasonCode porque el código de causa externa no es válido o está vacío.',
                is_entire_apartado=True,
            )

            enc_diags = enc.get('diagnosis') or []
            add_check(
                mod_4_id,
                mod_4,
                enc_label,
                'Apartado Diagnóstico(s) del Encuentro (Encounter.diagnosis)',
                f"{len(enc_diags)} diagnóstico(s) referenciado(s)" if enc_diags else '',
                len(enc_diags) > 0,
                'No se construyó el apartado Encounter.diagnosis[] porque el código CIE-10 principal no es válido o está vacío.',
                is_entire_apartado=True,
            )

            hosp = enc.get('hospitalization') or {}
            admit_src = _extract_coding_info(hosp.get('admitSource'))['text']
            disch_disp = _extract_coding_info(hosp.get('dischargeDisposition'))['text'] or _extract_extension_value(
                _find_extension(exts, 'dischargeDisposition') or _find_extension(exts, 'destinoEgreso')
            )
            if is_urg_or_hosp:
                add_check(
                    mod_4_id,
                    mod_4,
                    enc_label,
                    'Apartado Vía de Ingreso (Encounter.hospitalization.admitSource)',
                    admit_src,
                    bool(admit_src),
                    'No se construyó el apartado de Vía de Ingreso en Encounter.hospitalization.admitSource.',
                    is_entire_apartado=True,
                )
            if is_encounter_rda:
                add_check(
                    mod_4_id,
                    mod_4,
                    enc_label,
                    'Apartado Condición y Destino de Egreso (dischargeDisposition)',
                    disch_disp,
                    bool(disch_disp),
                    'No se construyó el apartado de Condición y Destino de Egreso en Encounter.hospitalization.dischargeDisposition (código inválido o vacío en la consulta/atención).',
                    is_entire_apartado=True,
                )
    elif is_patient_rda and composition:
        events = composition.get('event') or []
        ev0 = events[0] if (isinstance(events, list) and events and isinstance(events[0], dict)) else {}
        ev_period = ev0.get('period') or {}
        ev_start = _safe_str(ev_period.get('start'))
        ev_end = _safe_str(ev_period.get('end'))
        ev_modality = ''
        ev_group = ''
        for c_obj in ev0.get('code') or []:
            c_info = _extract_coding_info(c_obj)
            sys_l = c_info['system'].lower()
            if 'modality' in sys_l or 'modalidad' in sys_l:
                ev_modality = c_info['text']
            elif 'gruposervicio' in sys_l or 'servicegroup' in sys_l:
                ev_group = c_info['text']

        add_check(
            mod_4_id,
            mod_4,
            'Composition.event',
            'Apartado Modalidad de Atención en el Evento (ColombianTechModality)',
            ev_modality,
            bool(ev_modality),
            'No se construyó el apartado de Modalidad de Atención en Composition.event[].code.',
            is_entire_apartado=True,
        )
        add_check(
            mod_4_id,
            mod_4,
            'Composition.event',
            'Apartado Grupo de Servicios en el Evento (GrupoServicios)',
            ev_group,
            bool(ev_group),
            'No se construyó el apartado de Grupo de Servicios en Composition.event[].code.',
            is_entire_apartado=True,
        )
        add_check(
            mod_4_id,
            mod_4,
            'Composition.event',
            'Periodo de Inicio y Fin del Evento (Composition.event.period)',
            f"{ev_start} a {ev_end}" if (ev_start and ev_end) else (ev_start or ev_end),
            bool(ev_start and ev_end),
            'No se construyeron las fechas de inicio y fin del evento en Composition.event[].period.',
        )

    # =========================================================================
    # 5. APARTADO: DIAGNÓSTICOS Y CONDICIONES (Condition - CIE-10)
    # =========================================================================
    mod_5_id = 'diagnosticos'
    mod_5 = '5. Diagnósticos Clínicos (Condition - CIE-10)'
    conditions = resources_by_type.get('Condition', [])
    if is_encounter_rda and not conditions:
        add_check(
            mod_5_id,
            mod_5,
            'Condition',
            'Apartado Diagnóstico Principal de la Atención (Condition / CIE-10)',
            '',
            False,
            f"En un {rda_type_label} es obligatorio que exista el apartado de Diagnóstico (Condition). El sistema NO construyó este apartado porque el código CIE-10 no es válido o está vacío.",
            is_entire_apartado=True,
        )

    for c_idx, cond in enumerate(conditions):
        c_label = f"Condition #{c_idx + 1} ({_safe_str(cond.get('id')) or 'Sin ID'})"
        c_info = _extract_coding_info(cond.get('code'))
        verif_info = _extract_coding_info(cond.get('verificationStatus'))

        add_check(
            mod_5_id,
            mod_5,
            c_label,
            'Código y Nombre CIE-10 (Condition.code.coding)',
            c_info['text'],
            bool(c_info['code']),
            'El apartado Condition existe pero NO se construyó el código CIE-10 en Condition.code.coding.',
        )
        add_check(
            mod_5_id,
            mod_5,
            c_label,
            'Estado de la Condición / Verificación (verificationStatus)',
            VERIFICATION_STATUS_MAP.get(verif_info['code'].lower(), verif_info['text']),
            bool(verif_info['code'] or verif_info['text']),
            'No se construyó el estado de verificación (verificationStatus) en el apartado Condition.',
        )

    # =========================================================================
    # 6. APARTADO: MEDICAMENTOS (MedicationRequest / MedicationStatement / MedicationAdministration)
    # =========================================================================
    mod_6_id = 'medicamentos'
    mod_6 = '6. Medicamentos (Recetas y Antecedentes Farmacológicos)'
    for m_idx, mreq in enumerate(resources_by_type.get('MedicationRequest', [])):
        m_label = f"MedicationRequest #{m_idx + 1}"
        codings = _extract_all_codings(mreq.get('medicationCodeableConcept'))
        if not codings and mreq.get('medicationReference'):
            ref_str = _safe_str((mreq.get('medicationReference') or {}).get('reference'))
            resolved = resource_index.get(ref_str) or resource_index.get(ref_str.lstrip('#').split('/')[-1])
            if resolved:
                codings = _extract_all_codings(resolved.get('code'))
        codes_str = ', '.join(f"{c['code']} ({c['display']})" for c in codings if c['code'])

        add_check(
            mod_6_id,
            mod_6,
            m_label,
            'Apartado Código IUM / CUM / DCI del Medicamento Prescrito',
            codes_str,
            bool(codes_str),
            'No se construyó el código IUM/CUM/DCI en MedicationRequest porque el código del medicamento no es válido.',
            is_entire_apartado=True,
        )

        d_list = mreq.get('dosageInstruction') or []
        d0 = d_list[0] if (isinstance(d_list, list) and d_list and isinstance(d_list[0], dict)) else {}
        route_info = _extract_coding_info(d0.get('route'))
        add_check(
            mod_6_id,
            mod_6,
            m_label,
            'Vía de Administración (dosageInstruction.route)',
            route_info['text'],
            bool(route_info['code'] or route_info['text']),
            'No se construyó la vía de administración en MedicationRequest.dosageInstruction.',
        )

        qty_val = ((mreq.get('dispenseRequest') or {}).get('quantity') or {}).get('value')
        add_check(
            mod_6_id,
            mod_6,
            m_label,
            'Cantidad Total a Dispensar (dispenseRequest.quantity)',
            str(qty_val) if qty_val is not None else '',
            qty_val is not None,
            'No se construyó la cantidad total formulada en MedicationRequest.dispenseRequest.quantity.',
        )

    for ms_idx, mstat in enumerate(resources_by_type.get('MedicationStatement', [])):
        ms_label = f"MedicationStatement #{ms_idx + 1} (Antecedente Farmacológico)"
        ms_status = _safe_str(mstat.get('status')).lower()
        codings = _extract_all_codings(mstat.get('medicationCodeableConcept'))
        codes_str = ', '.join(f"{c['code']} - {c['display']}" for c in codings if c['code'])
        d_list = mstat.get('dosage') or []
        d0 = d_list[0] if (isinstance(d_list, list) and d_list and isinstance(d_list[0], dict)) else {}
        dosage_txt = _safe_str(d0.get('text')) or _safe_str(d0.get('patientInstruction'))

        add_check(
            mod_6_id,
            mod_6,
            ms_label,
            'Estado de la declaración del medicamento (status)',
            MED_STATEMENT_STATUS_MAP.get(ms_status, ms_status),
            bool(ms_status),
            'No se construyó el estado de la declaración en MedicationStatement.status.',
        )
        add_check(
            mod_6_id,
            mod_6,
            ms_label,
            'Código DCI / MipresINN del Medicamento (medicationCodeableConcept)',
            codes_str,
            bool(codes_str),
            'No se construyó el código DCI/MipresINN en MedicationStatement (código DCI inválido en el sistema).',
        )
        add_check(
            mod_6_id,
            mod_6,
            ms_label,
            'Dosificación del Antecedente Farmacológico (dosage.text)',
            dosage_txt,
            bool(dosage_txt),
            'No se construyó la dosificación en MedicationStatement.dosage[].text.',
        )

    # =========================================================================
    # 7. APARTADO: PROCEDIMIENTOS / CUPS DE LA CONSULTA Y ÓRDENES (Procedure / ServiceRequest)
    # =========================================================================
    mod_7_id = 'solicitudes_procedimientos'
    mod_7 = '7. Procedimientos y Órdenes (CUPS)'
    procedures = resources_by_type.get('Procedure', [])
    service_requests = resources_by_type.get('ServiceRequest', [])

    # ¡VALIDACIÓN CLAVE!: En Consulta Externa (y atención clínica) DEBE existir el apartado de CUPS (Procedure)
    if is_encounter_rda and not procedures:
        add_check(
            mod_7_id,
            mod_7,
            'Procedure (CUPS)',
            'Apartado CUPS de la Consulta / Procedimiento de la Atención (Procedure)',
            '',
            False,
            f"En un {rda_type_label} DEBE existir obligatoriamente el apartado de CUPS (Procedure). El sistema NO construyó este apartado en el FHIR porque el código CUPS de la consulta o procedimiento no es válido en el sistema o no está homologado.",
            is_entire_apartado=True,
        )

    for sr_idx, sreq in enumerate(service_requests):
        sr_label = f"ServiceRequest #{sr_idx + 1} (Orden Médica)"
        c_info = _extract_coding_info(sreq.get('code'))
        add_check(
            mod_7_id,
            mod_7,
            sr_label,
            'Código CUPS de la Orden / Solicitud (ServiceRequest.code.coding)',
            c_info['text'],
            bool(c_info['code']),
            'No se construyó el código CUPS en ServiceRequest.code.coding porque el código CUPS no es válido.',
            is_entire_apartado=True,
        )

    for pr_idx, proc in enumerate(procedures):
        pr_label = f"Procedure #{pr_idx + 1} (Procedimiento / Consulta CUPS)"
        c_info = _extract_coding_info(proc.get('code'))
        perf_dt = _safe_str(proc.get('performedDateTime') or (proc.get('performedPeriod') or {}).get('start'))
        add_check(
            mod_7_id,
            mod_7,
            pr_label,
            'Código CUPS de la Consulta / Procedimiento (Procedure.code.coding)',
            c_info['text'],
            bool(c_info['code']),
            'El apartado Procedure existe pero NO se construyó el código CUPS en Procedure.code.coding (código CUPS inválido o vacío).',
            is_entire_apartado=True,
        )
        add_check(
            mod_7_id,
            mod_7,
            pr_label,
            'Fecha de Ejecución (Procedure.performedDateTime / Period)',
            perf_dt,
            bool(perf_dt),
            'No se construyó la fecha de ejecución en Procedure.',
        )

    # =========================================================================
    # 8. APARTADO: ALERGIAS, FAMILIARES, FACTORES DE RIESGO Y SOPORTES
    # =========================================================================
    mod_8_id = 'alergias_familiares_otros'
    mod_8 = '8. Alergias, Familiares, Riesgos y Soportes'
    allergies = resources_by_type.get('AllergyIntolerance', [])
    family_histories = resources_by_type.get('FamilyMemberHistory', [])
    risks = resources_by_type.get('RiskAssessment', [])
    med_statements = resources_by_type.get('MedicationStatement', [])

    # Si es un RDA de Paciente (Antecedentes) y no se construyó absolutamente ningún apartado de antecedentes:
    if is_patient_rda and not (allergies or family_histories or risks or med_statements or conditions):
        add_check(
            mod_8_id,
            mod_8,
            'Antecedentes RDA Paciente',
            'Apartados de Antecedentes Clínicos (Alergias / Familiares / Farmacológicos / Patológicos)',
            '',
            False,
            'Este es un RDA de Paciente (Antecedentes), pero el sistema NO construyó ningún apartado de antecedentes en el FHIR (verifique que los códigos CIE-10, DCI o tipos de alergia sean válidos).',
            is_entire_apartado=True,
        )

    for a_idx, alg in enumerate(allergies):
        a_label = f"AllergyIntolerance #{a_idx + 1} (Alergia)"
        clin_c = _extract_coding_info(alg.get('clinicalStatus'))['code'].lower()
        verif_c = _extract_coding_info(alg.get('verificationStatus'))['code'].lower()
        code_obj = alg.get('code') or {}
        code_info = _extract_coding_info(code_obj)
        raw_cats = [_safe_str(c).lower() for c in (alg.get('category') or []) if c]
        cat_txt = ', '.join(ALLERGY_CATEGORY_MAP.get(c, c) for c in raw_cats)
        type_built = (
            code_info['text']
            if ('tipoalergia' in code_info['system'].lower() or code_info['code'] in ('01', '02', '03', '04', '05'))
            else (cat_txt or code_info['code'])
        )
        allergen_built = (
            (_safe_str(code_obj.get('text')) if isinstance(code_obj, dict) else '')
            or '; '.join(_safe_str(n.get('text')) for n in (alg.get('note') or []) if isinstance(n, dict) and n.get('text'))
            or code_info['display']
        )

        add_check(
            mod_8_id,
            mod_8,
            a_label,
            'Estado clínico de la alergia (clinicalStatus)',
            CLINICAL_STATUS_MAP.get(clin_c, clin_c),
            bool(clin_c),
            'No se construyó el estado clínico en AllergyIntolerance.clinicalStatus.',
        )
        add_check(
            mod_8_id,
            mod_8,
            a_label,
            'Estado de verificación de la alergia (verificationStatus)',
            VERIFICATION_STATUS_MAP.get(verif_c, verif_c),
            bool(verif_c),
            'No se construyó el estado de verificación en AllergyIntolerance.verificationStatus.',
        )
        add_check(
            mod_8_id,
            mod_8,
            a_label,
            'Tipo de alergia (AllergyIntolerance.code / category)',
            type_built,
            bool(type_built),
            'No se construyó el código del tipo de alergia en AllergyIntolerance.',
        )
        add_check(
            mod_8_id,
            mod_8,
            a_label,
            'Nombre del alergeno (AllergyIntolerance.code.text)',
            allergen_built,
            bool(allergen_built),
            'No se construyó el nombre del alergeno en AllergyIntolerance.',
        )

    for f_idx, fam in enumerate(family_histories):
        f_label = f"FamilyMemberHistory #{f_idx + 1} (Antecedente Familiar)"
        f_status = _safe_str(fam.get('status')).lower()
        rel_info = _extract_coding_info(fam.get('relationship'))
        f_conds = fam.get('condition') or []

        add_check(
            mod_8_id,
            mod_8,
            f_label,
            'Estado del antecedente familiar (status)',
            FAMILY_HISTORY_STATUS_MAP.get(f_status, f_status),
            bool(f_status),
            'No se construyó el estado en FamilyMemberHistory.status.',
        )
        add_check(
            mod_8_id,
            mod_8,
            f_label,
            'Parentesco Familiar (relationship.coding)',
            rel_info['text'],
            bool(rel_info['code']),
            'No se construyó el código de parentesco en FamilyMemberHistory.relationship.',
        )

        if not f_conds:
            add_check(
                mod_8_id,
                mod_8,
                f_label,
                'Apartado Diagnóstico CIE-10 Familiar (condition[].code.coding)',
                '',
                False,
                'No se construyó la condición en FamilyMemberHistory.condition[] porque el código CIE-10 familiar no es válido o está vacío.',
                is_entire_apartado=True,
            )
        else:
            for fc_idx, fcond in enumerate(f_conds):
                if isinstance(fcond, dict):
                    fc_info = _extract_coding_info(fcond.get('code'))
                    add_check(
                        mod_8_id,
                        mod_8,
                        f_label,
                        f"Diagnóstico CIE-10 Familiar #{fc_idx + 1} (condition.code.coding)",
                        fc_info['text'],
                        bool(fc_info['code']),
                        'No se construyó el código CIE-10 en FamilyMemberHistory.condition[].code.coding.',
                    )

    for r_idx, rsk in enumerate(risks):
        r_label = f"RiskAssessment #{r_idx + 1} (Factor de Riesgo)"
        r_status = _safe_str(rsk.get('status')).lower()
        pred = (rsk.get('prediction') or [{}])[0]
        r_info = (
            _extract_coding_info(pred.get('outcome'))
            if _extract_coding_info(pred.get('outcome'))['code']
            else _extract_coding_info(rsk.get('code'))
        )
        add_check(
            mod_8_id,
            mod_8,
            r_label,
            'Estado del Factor de Riesgo (RiskAssessment.status)',
            RISK_STATUS_MAP.get(r_status, r_status),
            bool(r_status),
            'No se construyó el estado en RiskAssessment.status.',
        )
        add_check(
            mod_8_id,
            mod_8,
            r_label,
            'Código del Factor de Riesgo (RiskAssessment.code.coding)',
            r_info['text'],
            bool(r_info['code'] or r_info['text']),
            'No se construyó el código del factor de riesgo en RiskAssessment.',
        )

    # =========================================================================
    # 9. AUDITORÍA DE SECCIONES EN COMPOSITION (Apartados Declarados en 0)
    # =========================================================================
    empty_sections_count = 0
    if composition:
        for sec in composition.get('section') or []:
            if not isinstance(sec, dict):
                continue
            sec_title = _safe_str(sec.get('title')) or _extract_coding_info(sec.get('code'))['text'] or 'Sección RDA'
            sec_entries = sec.get('entry') or []
            empty_info = _extract_coding_info(sec.get('emptyReason'))
            sec_low = sec_title.lower()

            # Si en un RDA de Consulta/Urgencias/Hospitalización la sección de Procedimientos o Diagnósticos viene vacía,
            # NO es una sección opcional vacía sino un APARTADO OBLIGATORIO FALTANTE:
            is_mandatory_sec_in_encounter = is_encounter_rda and any(
                kw in sec_low for kw in ('procedimiento', 'procedure', 'diagn', 'problem')
            )

            if len(sec_entries) > 0:
                add_check(
                    mod_1_id,
                    '9. Apartados en Composition.section',
                    f"Sección: {sec_title}",
                    f"Apartado '{sec_title}'",
                    f"✅ {len(sec_entries)} registro(s) construido(s) en el FHIR",
                    True,
                    status_override='ok',
                )
            elif is_mandatory_sec_in_encounter:
                add_check(
                    mod_7_id if ('procedimiento' in sec_low or 'procedure' in sec_low) else mod_5_id,
                    '9. Apartados en Composition.section',
                    f"Sección: {sec_title}",
                    f"Apartado Obligatorio '{sec_title}' en Composition.section",
                    '',
                    False,
                    f"La sección '{sec_title}' vino vacía (0 registros) en el FHIR. El sistema no construyó este apartado porque el código (CUPS / CIE-10) no es válido.",
                    is_entire_apartado=True,
                )
            else:
                empty_sections_count += 1
                empty_msg = (
                    f"⚠️ Apartado sin registros en el FHIR (0 entries, emptyReason: {empty_info['text'] or 'No especificado'}). "
                    f"Si ingresaste datos en '{sec_title}' en el software, el sistema NO construyó el apartado porque su código (CIE-10, CUPS, DCI/IUM, etc.) no era válido."
                )
                checks.append({
                    'module_id': mod_1_id,
                    'module': '9. Apartados en Composition.section',
                    'resource': f"Sección: {sec_title}",
                    'field': f"Apartado '{sec_title}'",
                    'value': empty_msg,
                    'valid': True,
                    'status': 'empty_section',
                    'is_apartado': True,
                })

    passed_count = sum(1 for c in checks if c['status'] == 'ok')
    failed_count = sum(1 for c in checks if c['status'] == 'missing')

    return {
        'checks': checks,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'empty_sections_count': empty_sections_count,
        'total_mandatory_checks': passed_count + failed_count,
        'alerts': alerts,
        'module_missing_alerts': module_missing_alerts,
    }

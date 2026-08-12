# -*- coding: utf-8 -*-
{
    'name': 'Fix Repair',
    'version': '17.0.1.0.250',
    'summary': 'Enhancements to the Customer Care - Repair helpdesk workflow',
    'author': 'Jinasena Agricultural Machinery (Pvt) Ltd.',
    'category': 'Helpdesk',
    'license': 'LGPL-3',
    'depends': ['base_setup', 'helpdesk', 'helpdesk_fsm', 'sale', 'sale_stock', 'industry_fsm_sale', 'industry_fsm_stock', 'BugFix-Sales'],
    'post_init_hook': 'post_init_hook',
    # v244: helpdesk_ticket_studio_ported.xml + _studio_field_hides.xml
    # moved BACK to manifest 'data' now that the button-195 xpath was
    # stripped in v242. Loading via post_init_hook worked once but the
    # created ir.model.data records got purged on the NEXT upgrade by
    # Odoo's module cleanup (records not in manifest 'data' are treated
    # as orphans). Manifest data path keeps them tracked across upgrades.
    # ORDER: ported.xml before field_hides.xml — the latter's xpaths
    # target fields that ported.xml adds to the composed arch.
    'data': [
        # v249: MUST load before security/ir.model.access.csv so the
        # 11 Studio-created model xmlids resolve when the ACL CSV is
        # processed. Fresh installs don't need this (Odoo auto-pins
        # newly-declared models) but existing Clear-DB upgrades do
        # (models pre-existed as state='manual' Studio rows, never
        # got a Fix-repair-owned ir.model.data pin auto-created).
        'data/ir_model_pins.xml',
        'security/ir.model.access.csv',
        'data/fix_repair_data.xml',
        'data/repair_stages.xml',
        'data/repair_sequences.xml',
        'data/helpdesk_ticket_types.xml',
        'data/repair_diagnosis_menus.xml',
        'data/repair_diagnosis_seed.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_ticket_studio_ported.xml',
        'views/helpdesk_ticket_studio_field_hides.xml',
        'views/helpdesk_ticket_type_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_report_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'Fix-repair/static/src/scss/task_toast_triggers.scss',
            'Fix-repair/static/src/js/task_missing_data_notifier.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}

# -*- coding: utf-8 -*-
{
    'name': 'Jinasena : Module : Repair',
    'version': '17.0.1.0.345',
    'summary': 'Enhancements to the Customer Care - Repair helpdesk workflow',
    'author': 'Jinasena Agricultural Machinery (Pvt) Ltd.',
    'category': 'Helpdesk',
    'license': 'LGPL-3',
    # v299: added `repair` to depends — models/repair_order.py ports
    # x_studio_confirm_draft_quotation onto repair.order. Without this
    # dep the _inherit target isn't in the registry when Fix-repair
    # loads on a fresh install.
    'depends': ['base_setup', 'helpdesk', 'helpdesk_fsm', 'repair', 'sale', 'sale_stock', 'industry_fsm_sale', 'industry_fsm_stock', 'BugFix-Sales', 'studio_usermodel_migration'],
    'post_init_hook': 'post_init_hook',
    # v292: added studio_usermodel_migration to depends.
    # helpdesk_ticket.py declares related fields (x_studio_source_location,
    # x_studio_virtual_location, etc.) that traverse user_id -> res.users.
    # Those res.users fields were moved from Fix-repair's own res_users.py
    # to studio_usermodel_migration in v0.0.7 of that module, but the
    # manifest dep was never updated. Without this dep, Odoo's topological
    # loader may process Fix-repair before studio_usermodel_migration,
    # causing setup_related() to fail with KeyError on those fields.
    # Load order is now:
    #   BugFix-Sales -> studio_migrations -> studio_usermodel_migration
    #     -> Fix-repair -> Fix-Repair-Wizard-Nav
    # v244: helpdesk_ticket_studio_ported.xml + _studio_field_hides.xml
    # moved BACK to manifest 'data' now that the button-195 xpath was
    # stripped in v242. Loading via post_init_hook worked once but the
    # created ir.model.data records got purged on the NEXT upgrade by
    # Odoo's module cleanup (records not in manifest 'data' are treated
    # as orphans). Manifest data path keeps them tracked across upgrades.
    # ORDER: ported.xml before field_hides.xml — the latter's xpaths
    # target fields that ported.xml adds to the composed arch.
    'data': [
        'data/approval_rules_relaxed.xml',
        'data/rules_f7.xml',
        'data/server_actions_f5.xml',
        'data/window_actions_f4.xml',
        'data/ir_model_pins.xml',
        'data/fix_repair_data.xml',
        'security/ir.model.access.csv',
        'data/repair_stages.xml',
        'data/repair_sequences.xml',
        'data/helpdesk_ticket_types.xml',
        'views/repair_diagnosis_catalog_views.xml',
        'data/repair_diagnosis_menus.xml',
        'data/repair_diagnosis_seed.xml',
        'data/helpdesk_ticket_server_actions.xml',
        'data/project_task_server_actions.xml',
        'views/helpdesk_ticket_studio_ported.xml',
        'views/helpdesk_ticket_studio_field_hides.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_ticket_type_views.xml',
        'views/project_task_studio_ported.xml',
        'views/sale_order_studio_ported.xml',
        'views/stock_picking_studio_ported.xml',
        'views/res_config_settings_views.xml',
        'views/sale_report_templates.xml',
        'views/helpdesk_stage_studio_ported.xml',
        'views/helpdesk_team_studio_ported.xml',
        'views/helpdesk_ticket_type_studio_ported.xml',
        'data/record_rules.xml',
        'data/server_actions_v4.xml',
        'data/automations_v4.xml',
        'data/window_actions_v2.xml',
        'data/mail_templates_from_routing.xml',
        'data/record_rules_gap.xml',
        'data/server_actions_gap.xml',
        'data/automations_gap.xml',
        'data/window_actions_gap.xml',
        'data/ir_defaults_gap.xml',
        'views/helpdesk_stage_e_views.xml',
        'views/helpdesk_ticket_e_views.xml',
        'views/helpdesk_ticket_type_e_views.xml',
        'views/repair_order_e_views.xml',
        'views/res_users_e_views.xml',
        'views/stock_warehouse_e_views.xml',
        'views/x_conditions_e_views.xml',
        'views/x_diagnosis_areas_e_views.xml',
        'views/x_diagnosis_codes_e_views.xml',
        'views/x_repair_accounts_e_views.xml',
        'views/x_repair_reason_custom_e_views.xml',
        'views/x_repair_reason_e_views.xml',
        'views/x_repair_stages_e_views.xml',
        'views/x_repair_sub_reason_e_views.xml',
        'views/x_resolutions_e_views.xml',
        'views/x_symptom_areas_e_views.xml',
        'views/x_symptom_codes_e_views.xml',
        'views/x_task_diagnosis_e_views.xml',
        'views/views_final.xml',
        'data/menus_f6.xml',
        'data/menus_from_routing.xml',
        'views/qweb_studio_ported.xml',
        'views/res_partner_studio_pages_content.xml',
        'views/res_partner_hide_dev_extras.xml',
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
